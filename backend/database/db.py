from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os

from backend.database.models import Base, Product, PriceHistory
from backend.config import DATABASE_URL, DATA_DIR


# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


# Product CRUD operations
def create_product(
    db: Session,
    name: str,
    url: str,
    platform: str,
    product_id: str,
    image_url: Optional[str] = None,
    currency: str = "USD"
) -> Product:
    """Create a new product"""
    product = Product(
        name=name,
        url=url,
        platform=platform,
        product_id=product_id,
        image_url=image_url,
        currency=currency
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def get_product(db: Session, product_id: int) -> Optional[Product]:
    """Get a product by ID"""
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_url(db: Session, url: str) -> Optional[Product]:
    """Get a product by URL"""
    return db.query(Product).filter(Product.url == url).first()


def get_all_products(db: Session, active_only: bool = True) -> List[Product]:
    """Get all products"""
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == 1)
    return query.order_by(desc(Product.created_at)).all()


def update_product(db: Session, product_id: int, **kwargs) -> Optional[Product]:
    """Update a product"""
    product = get_product(db, product_id)
    if product:
        for key, value in kwargs.items():
            if hasattr(product, key):
                setattr(product, key, value)
        db.commit()
        db.refresh(product)
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete a product (soft delete)"""
    product = get_product(db, product_id)
    if product:
        product.is_active = 0
        db.commit()
        return True
    return False


def hard_delete_product(db: Session, product_id: int) -> bool:
    """Permanently delete a product and its history"""
    product = get_product(db, product_id)
    if product:
        db.delete(product)
        db.commit()
        return True
    return False


# Price History CRUD operations
def add_price_history(
    db: Session,
    product_id: int,
    price: float,
    original_price: Optional[float] = None,
    discount_percentage: Optional[float] = None,
    availability: str = "available"
) -> PriceHistory:
    """Add a price history entry"""
    price_entry = PriceHistory(
        product_id=product_id,
        price=price,
        original_price=original_price,
        discount_percentage=discount_percentage,
        availability=availability
    )
    db.add(price_entry)
    
    # Update product's last_checked timestamp
    product = get_product(db, product_id)
    if product:
        product.last_checked = datetime.utcnow()
    
    db.commit()
    db.refresh(price_entry)
    return price_entry


def get_price_history(
    db: Session,
    product_id: int,
    days: Optional[int] = None,
    limit: Optional[int] = None
) -> List[PriceHistory]:
    """Get price history for a product"""
    query = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)
    
    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(PriceHistory.scraped_at >= start_date)
    
    query = query.order_by(desc(PriceHistory.scraped_at))
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_latest_price(db: Session, product_id: int) -> Optional[PriceHistory]:
    """Get the most recent price for a product"""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(desc(PriceHistory.scraped_at))
        .first()
    )


def get_price_statistics(db: Session, product_id: int, days: int = 30) -> Dict[str, Any]:
    """Get price statistics for a product"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    stats = (
        db.query(
            func.min(PriceHistory.price).label("min_price"),
            func.max(PriceHistory.price).label("max_price"),
            func.avg(PriceHistory.price).label("avg_price"),
            func.count(PriceHistory.id).label("count")
        )
        .filter(
            PriceHistory.product_id == product_id,
            PriceHistory.scraped_at >= start_date
        )
        .first()
    )
    
    latest = get_latest_price(db, product_id)
    
    return {
        "min_price": float(stats.min_price) if stats.min_price else None,
        "max_price": float(stats.max_price) if stats.max_price else None,
        "avg_price": float(stats.avg_price) if stats.avg_price else None,
        "current_price": float(latest.price) if latest else None,
        "data_points": stats.count,
        "period_days": days
    }


def get_all_statistics(db: Session) -> Dict[str, Any]:
    """Get overall statistics"""
    total_products = db.query(func.count(Product.id)).filter(Product.is_active == 1).scalar()
    total_prices = db.query(func.count(PriceHistory.id)).scalar()
    
    # Get products checked in last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_checks = (
        db.query(func.count(Product.id))
        .filter(Product.last_checked >= yesterday)
        .scalar()
    )
    
    return {
        "total_products": total_products,
        "total_price_records": total_prices,
        "checked_last_24h": recent_checks
    }

