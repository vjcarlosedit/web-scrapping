from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import time
from backend.config import REQUEST_DELAY, MAX_RETRIES

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers"""
    
    def __init__(self):
        self.delay = REQUEST_DELAY
        self.max_retries = MAX_RETRIES
    
    @abstractmethod
    def extract_product_id(self, url: str) -> Optional[str]:
        """Extract product ID from URL"""
        pass
    
    @abstractmethod
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape product information from URL
        
        Returns a dictionary with:
        - name: Product name
        - price: Current price
        - original_price: Original price (if discounted)
        - discount_percentage: Discount percentage
        - currency: Currency code
        - image_url: Product image URL
        - availability: Availability status
        - product_id: Platform-specific product ID
        """
        pass
    
    def sleep(self, seconds: Optional[float] = None):
        """Sleep between requests"""
        time.sleep(seconds or self.delay)
    
    def retry_on_failure(self, func, *args, **kwargs):
        """Retry a function on failure"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    self.sleep(self.delay * (attempt + 1))
                else:
                    logger.error(f"All {self.max_retries} attempts failed")
                    raise
    
    @staticmethod
    def validate_url(url: str, domain: str) -> bool:
        """Validate if URL belongs to the expected domain"""
        return domain in url.lower()

