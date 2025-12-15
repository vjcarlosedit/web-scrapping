from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Product(Base):
    """Model for products being tracked"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False, index=True)
    platform = Column(String, nullable=False)  # 'amazon' or 'mercadolibre'
    product_id = Column(String, nullable=False)  # Platform-specific product ID
    image_url = Column(String, nullable=True)
    currency = Column(String, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked = Column(DateTime, nullable=True)
    is_active = Column(Integer, default=1)  # 1 = active, 0 = inactive
    notion_page_id = Column(String, nullable=True, index=True)  # Notion page ID for syncing

    # Relationship
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', platform='{self.platform}')>"


class PriceHistory(Base):
    """Model for storing historical price data"""
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)  # Original price if there's a discount
    discount_percentage = Column(Float, nullable=True)
    availability = Column(String, default="available")  # 'available', 'out_of_stock', 'unavailable'
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(id={self.id}, product_id={self.product_id}, price={self.price}, scraped_at={self.scraped_at})>"


def init_db(database_url: str):
    """Initialize the database and create tables"""
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine

