"""
Sync helper to prepare data for Notion integration
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from backend.database.db import get_all_products, get_price_history, get_latest_price
from backend.notion_integration.client import NotionPriceTracker
from backend.config import NOTION_ENABLED, NOTION_TOKEN, NOTION_DATABASE_ID

logger = logging.getLogger(__name__)


def get_notion_client() -> Optional[NotionPriceTracker]:
    """Get Notion client if enabled"""
    if not NOTION_ENABLED:
        return None
    
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        logger.warning("Notion is enabled but TOKEN or DATABASE_ID not configured")
        return None
    
    try:
        return NotionPriceTracker(token=NOTION_TOKEN, database_id=NOTION_DATABASE_ID)
    except Exception as e:
        logger.error(f"Failed to initialize Notion client: {e}")
        return None


def prepare_product_data_for_notion(db: Session, product) -> Optional[Dict[str, Any]]:
    """
    Prepare product data for Notion sync
    
    Calculates:
    - Current price (latest)
    - Lowest price ever recorded
    - Date of lowest price
    """
    try:
        # Get latest price
        latest_price_entry = get_latest_price(db, product.id)
        
        if not latest_price_entry:
            logger.warning(f"No price data for product {product.id}")
            return None
        
        # Get all price history to find lowest
        all_prices = get_price_history(db, product.id)
        
        if not all_prices:
            logger.warning(f"No price history for product {product.id}")
            return None
        
        # Find lowest price
        lowest_entry = min(all_prices, key=lambda x: x.price)
        
        result = {
            "product_name": product.name,
            "platform": "Amazon" if product.platform == "amazon" else "Mercado Libre",
            "url": product.url,
            "current_price": latest_price_entry.price,
            "currency": product.currency,
            "lowest_price": lowest_entry.price,
            "lowest_price_date": lowest_entry.scraped_at,
            "last_update": latest_price_entry.scraped_at
        }
        
        return result
    
    except Exception as e:
        logger.error(f"Error preparing data for product {product.id}: {e}")
        return None


def sync_all_products_to_notion(db: Session) -> Dict[str, int]:
    """
    Sync all products to Notion
    
    Returns:
        Statistics dict with sync results
    """
    stats = {
        "total": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # Check if Notion is enabled
    notion_client = get_notion_client()
    if not notion_client:
        logger.info("Notion sync skipped (not enabled or not configured)")
        return stats
    
    try:
        # Get all active products
        products = get_all_products(db, active_only=True)
        stats["total"] = len(products)
        
        logger.info(f"Starting Notion sync for {stats['total']} products")
        
        # Sync products one by one to save notion_page_id
        from backend.database.db import update_product
        
        for product in products:
            try:
                data = prepare_product_data_for_notion(db, product)
                if not data:
                    stats["skipped"] += 1
                    continue
                
                # Get existing notion_page_id if available
                notion_page_id = product.notion_page_id if hasattr(product, 'notion_page_id') else None
                
                # Sync to Notion
                result_page_id = notion_client.sync_product(
                    notion_page_id=notion_page_id,
                    **data
                )
                
                if result_page_id:
                    # Save notion_page_id to product
                    update_product(db, product.id, notion_page_id=result_page_id)
                    stats["synced"] += 1
                else:
                    stats["failed"] += 1
            except Exception as e:
                logger.error(f"Error syncing product {product.id} to Notion: {e}")
                stats["failed"] += 1
        
        logger.info(f"✓ Notion sync completed: {stats['synced']}/{stats['total']} synced")
        return stats
        
    except Exception as e:
        logger.error(f"Error during Notion sync: {e}")
        return stats


def sync_single_product_to_notion(db: Session, product_id: int) -> bool:
    """
    Sync a single product to Notion and update its notion_page_id
    
    Returns:
        True if successful, False otherwise
    """
    notion_client = get_notion_client()
    if not notion_client:
        return False
    
    try:
        from backend.database.db import get_product, update_product
        
        product = get_product(db, product_id)
        if not product:
            logger.error(f"Product {product_id} not found")
            return False
        
        data = prepare_product_data_for_notion(db, product)
        if not data:
            return False
        
        # Pass existing notion_page_id if available
        notion_page_id = product.notion_page_id if hasattr(product, 'notion_page_id') else None
        
        # Sync to Notion
        result_page_id = notion_client.sync_product(
            notion_page_id=notion_page_id,
            **data
        )
        
        if result_page_id:
            # Update product with notion_page_id
            update_product(db, product_id, notion_page_id=result_page_id)
            logger.info(f"✓ Updated notion_page_id for product {product_id}: {result_page_id}")
            return True
        return False
        
    except Exception as e:
        logger.error(f"Error syncing product {product_id} to Notion: {e}")
        return False

