import logging
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from backend.database.db import SessionLocal, get_all_products, add_price_history
from backend.scraper.factory import ScraperFactory

logger = logging.getLogger(__name__)


def scrape_all_products() -> dict:
    """
    Scrape all active products and save their prices to the database
    
    Returns:
        Dictionary with scraping results
    """
    logger.info("=" * 60)
    logger.info(f"Starting scheduled scraping job at {datetime.now()}")
    logger.info("=" * 60)
    
    db: Session = SessionLocal()
    results = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    try:
        # Get all active products
        products = get_all_products(db, active_only=True)
        results["total"] = len(products)
        
        logger.info(f"Found {results['total']} active products to scrape")
        
        for product in products:
            try:
                logger.info(f"Scraping: {product.name} ({product.platform})")
                
                # Get appropriate scraper
                scraper = ScraperFactory.get_scraper(product.url)
                if not scraper:
                    logger.error(f"No scraper available for: {product.url}")
                    results["failed"] += 1
                    results["errors"].append(f"No scraper for {product.name}")
                    continue
                
                # Scrape product
                data = scraper.scrape_product(product.url)
                
                if data:
                    # Save price to database
                    add_price_history(
                        db=db,
                        product_id=product.id,
                        price=data["price"],
                        original_price=data.get("original_price"),
                        discount_percentage=data.get("discount_percentage"),
                        availability=data.get("availability", "available")
                    )
                    
                    # Update product information if needed
                    if data.get("image_url") and not product.image_url:
                        product.image_url = data["image_url"]
                    
                    if data.get("currency"):
                        product.currency = data["currency"]
                    
                    db.commit()
                    
                    results["success"] += 1
                    logger.info(f"✓ Successfully scraped: {product.name} - ${data['price']}")
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to scrape {product.name}")
                    logger.error(f"✗ Failed to scrape: {product.name}")
                
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error scraping {product.name}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                continue
        
    except Exception as e:
        logger.error(f"Error in scraping job: {str(e)}")
    finally:
        db.close()
    
    logger.info("=" * 60)
    logger.info(f"Scraping job completed at {datetime.now()}")
    logger.info(f"Results: {results['success']}/{results['total']} successful, {results['failed']} failed")
    logger.info("=" * 60)
    
    # Sync to Notion if enabled
    try:
        from backend.notion_integration.sync import sync_all_products_to_notion
        
        logger.info("Starting Notion synchronization...")
        notion_stats = sync_all_products_to_notion(db)
        results['notion_sync'] = notion_stats
        logger.info(f"✓ Notion sync: {notion_stats['synced']}/{notion_stats['total']} products synced")
    except Exception as e:
        logger.error(f"Notion sync failed: {e}")
        results['notion_sync'] = {"error": str(e)}
    
    return results


def scrape_single_product(product_id: int) -> dict:
    """
    Scrape a single product by ID
    
    Args:
        product_id: Database ID of the product
        
    Returns:
        Dictionary with scraping result
    """
    db: Session = SessionLocal()
    result = {"success": False, "message": "", "data": None}
    
    try:
        from backend.database.db import get_product
        
        product = get_product(db, product_id)
        if not product:
            result["message"] = f"Product with ID {product_id} not found"
            return result
        
        logger.info(f"Scraping single product: {product.name}")
        
        scraper = ScraperFactory.get_scraper(product.url)
        if not scraper:
            result["message"] = f"No scraper available for URL: {product.url}"
            return result
        
        data = scraper.scrape_product(product.url)
        
        if data:
            # Save price to database
            add_price_history(
                db=db,
                product_id=product.id,
                price=data["price"],
                original_price=data.get("original_price"),
                discount_percentage=data.get("discount_percentage"),
                availability=data.get("availability", "available")
            )
            
            # Update product information
            if data.get("image_url") and not product.image_url:
                product.image_url = data["image_url"]
            if data.get("currency"):
                product.currency = data["currency"]
            
            db.commit()
            
            result["success"] = True
            result["message"] = f"Successfully scraped {product.name}"
            result["data"] = data
            logger.info(f"Successfully scraped: {product.name} - ${data['price']}")
            
            # Sync to Notion if enabled
            try:
                from backend.notion_integration.sync import sync_single_product_to_notion
                
                if sync_single_product_to_notion(db, product_id):
                    logger.info(f"✓ Synced {product.name} to Notion")
                    result["notion_synced"] = True
            except Exception as e:
                logger.warning(f"Notion sync failed for product: {e}")
                result["notion_synced"] = False
        else:
            result["message"] = f"Failed to scrape product: {product.name}"
            logger.error(result["message"])
            
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
        logger.error(result["message"])
    finally:
        db.close()
    
    return result

