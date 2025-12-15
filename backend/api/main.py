from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
import logging
from pathlib import Path

from backend.database import db
from backend.database.models import Product, PriceHistory
from backend.scraper.factory import ScraperFactory, scrape_product_from_url
from backend.scheduler.scheduler import get_scheduler
from backend.scheduler.jobs import scrape_single_product

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Price Scraper API",
    description="API for tracking product prices from Amazon and Mercado Libre",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler"""
    logger.info("Starting up application...")
    db.init_database()
    logger.info("Database initialized")
    
    # Start scheduler
    scheduler = get_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

# Pydantic models for request/response
class ProductCreate(BaseModel):
    url: HttpUrl
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.mercadolibre.com.mx/producto-ejemplo"
            }
        }


class ProductResponse(BaseModel):
    id: int
    name: str
    url: str
    platform: str
    product_id: str
    image_url: Optional[str]
    currency: str
    created_at: str
    last_checked: Optional[str]
    current_price: Optional[float]
    is_active: int
    
    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    id: int
    price: float
    original_price: Optional[float]
    discount_percentage: Optional[float]
    availability: str
    scraped_at: str
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    min_price: Optional[float]
    max_price: Optional[float]
    avg_price: Optional[float]
    current_price: Optional[float]
    data_points: int
    period_days: int


# Mount static files (frontend)
frontend_dir = Path(__file__).parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


# Root endpoint - serve frontend
@app.get("/")
async def root():
    """Serve the frontend dashboard"""
    frontend_file = frontend_dir / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "Price Scraper API", "docs": "/docs"}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "price-scraper"}


# Product endpoints
@app.get("/api/products", response_model=List[ProductResponse])
async def get_products(
    active_only: bool = True,
    db_session: Session = Depends(db.get_db)
):
    """Get all products"""
    products = db.get_all_products(db_session, active_only=active_only)
    
    # Add current price to each product
    result = []
    for product in products:
        product_dict = {
            "id": product.id,
            "name": product.name,
            "url": product.url,
            "platform": product.platform,
            "product_id": product.product_id,
            "image_url": product.image_url,
            "currency": product.currency,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "last_checked": product.last_checked.isoformat() if product.last_checked else None,
            "is_active": product.is_active,
            "current_price": None
        }
        
        # Get latest price
        latest_price = db.get_latest_price(db_session, product.id)
        if latest_price:
            product_dict["current_price"] = latest_price.price
        
        result.append(product_dict)
    
    return result


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, db_session: Session = Depends(db.get_db)):
    """Get a specific product by ID"""
    product = db.get_product(db_session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get current price
    latest_price = db.get_latest_price(db_session, product.id)
    
    return {
        "id": product.id,
        "name": product.name,
        "url": product.url,
        "platform": product.platform,
        "product_id": product.product_id,
        "image_url": product.image_url,
        "currency": product.currency,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "last_checked": product.last_checked.isoformat() if product.last_checked else None,
        "is_active": product.is_active,
        "current_price": latest_price.price if latest_price else None
    }


@app.post("/api/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db_session: Session = Depends(db.get_db)
):
    """Add a new product to track"""
    url = str(product_data.url)
    
    # Check if product already exists
    existing = db.get_product_by_url(db_session, url)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Product with this URL already exists"
        )
    
    # Detect platform
    platform = ScraperFactory.get_platform(url)
    if not platform:
        raise HTTPException(
            status_code=400,
            detail="Unsupported platform. Only Amazon and Mercado Libre are supported."
        )
    
    # Scrape product to get initial data
    logger.info(f"Scraping new product: {url}")
    scraped_data = scrape_product_from_url(url)
    
    if not scraped_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to scrape product. Please check the URL and try again."
        )
    
    # Create product in database
    product = db.create_product(
        db_session,
        name=scraped_data["name"],
        url=url,
        platform=platform,
        product_id=scraped_data["product_id"],
        image_url=scraped_data.get("image_url"),
        currency=scraped_data.get("currency", "USD")
    )
    
    # Add initial price
    db.add_price_history(
        db_session,
        product_id=product.id,
        price=scraped_data["price"],
        original_price=scraped_data.get("original_price"),
        discount_percentage=scraped_data.get("discount_percentage"),
        availability=scraped_data.get("availability", "available")
    )
    
    logger.info(f"Successfully added product: {product.name}")
    
    # Sync to Notion if enabled
    try:
        from backend.notion_integration.sync import sync_single_product_to_notion
        
        if sync_single_product_to_notion(db_session, product.id):
            logger.info(f"✓ Synced {product.name} to Notion")
        else:
            logger.warning(f"Failed to sync {product.name} to Notion")
    except Exception as e:
        logger.warning(f"Notion sync failed for new product: {e}")
    
    return {
        "id": product.id,
        "name": product.name,
        "url": product.url,
        "platform": product.platform,
        "product_id": product.product_id,
        "image_url": product.image_url,
        "currency": product.currency,
        "created_at": product.created_at.isoformat(),
        "last_checked": product.last_checked.isoformat() if product.last_checked else None,
        "is_active": product.is_active,
        "current_price": scraped_data["price"]
    }


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int, db_session: Session = Depends(db.get_db)):
    """Delete a product permanently (hard delete) and remove from Notion"""
    
    # Get product before deleting to check for notion_page_id
    product = db.get_product(db_session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete from Notion if it has a notion_page_id
    notion_page_id = getattr(product, 'notion_page_id', None)
    if notion_page_id:
        try:
            from backend.notion_integration.sync import get_notion_client
            notion_client = get_notion_client()
            if notion_client:
                notion_result = notion_client.delete_page(notion_page_id)
                logger.info(f"✓ Deleted product from Notion: {product.name}")
        except Exception as e:
            logger.warning(f"Failed to delete product from Notion: {e}")
            # Continue with local deletion even if Notion deletion fails
    
    # Delete from local database (hard delete - permanent)
    success = db.hard_delete_product(db_session, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted successfully"}


# Price history endpoints
@app.get("/api/products/{product_id}/history", response_model=List[PriceHistoryResponse])
async def get_product_history(
    product_id: int,
    days: Optional[int] = None,
    limit: Optional[int] = None,
    db_session: Session = Depends(db.get_db)
):
    """Get price history for a product"""
    # Check if product exists
    product = db.get_product(db_session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    history = db.get_price_history(db_session, product_id, days=days, limit=limit)
    
    return [
        {
            "id": entry.id,
            "price": entry.price,
            "original_price": entry.original_price,
            "discount_percentage": entry.discount_percentage,
            "availability": entry.availability,
            "scraped_at": entry.scraped_at.isoformat()
        }
        for entry in history
    ]


@app.get("/api/products/{product_id}/stats", response_model=StatsResponse)
async def get_product_stats(
    product_id: int,
    days: int = 30,
    db_session: Session = Depends(db.get_db)
):
    """Get price statistics for a product"""
    # Check if product exists
    product = db.get_product(db_session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    stats = db.get_price_statistics(db_session, product_id, days=days)
    return stats


# Scraping endpoints
@app.post("/api/scrape/run")
async def run_scraping(db_session: Session = Depends(db.get_db)):
    """Manually trigger scraping for all products"""
    logger.info("Manual scraping triggered via API")
    scheduler = get_scheduler()
    results = scheduler.run_now()
    return {
        "message": "Scraping completed",
        "results": results
    }


@app.post("/api/scrape/product/{product_id}")
async def scrape_product(product_id: int):
    """Manually trigger scraping for a specific product"""
    result = scrape_single_product(product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# Statistics endpoint
@app.get("/api/stats")
async def get_stats(db_session: Session = Depends(db.get_db)):
    """Get overall statistics"""
    stats = db.get_all_statistics(db_session)
    
    # Get scheduler info
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    
    return {
        **stats,
        "scheduler_running": scheduler.is_running,
        "scheduled_jobs": len(jobs)
    }


if __name__ == "__main__":
    import uvicorn
    from backend.config import API_HOST, API_PORT
    
    uvicorn.run(
        "backend.api.main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )

