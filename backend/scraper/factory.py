"""Factory pattern for creating appropriate scraper based on URL"""
from typing import Optional
import logging

from backend.scraper.base import BaseScraper
from backend.scraper.mercadolibre import MercadoLibreScraper
from backend.scraper.amazon import AmazonScraper

logger = logging.getLogger(__name__)


class ScraperFactory:
    """Factory to create the appropriate scraper based on URL"""
    
    @staticmethod
    def get_scraper(url: str) -> Optional[BaseScraper]:
        """
        Get the appropriate scraper for a given URL
        
        Args:
            url: Product URL
            
        Returns:
            Appropriate scraper instance or None
        """
        url_lower = url.lower()
        
        if "mercadolibre" in url_lower or "mercadolivre" in url_lower:
            logger.info("Creating Mercado Libre scraper")
            return MercadoLibreScraper()
        elif "amazon" in url_lower:
            logger.info("Creating Amazon scraper")
            return AmazonScraper()
        else:
            logger.error(f"No scraper available for URL: {url}")
            return None
    
    @staticmethod
    def get_platform(url: str) -> Optional[str]:
        """
        Detect the platform from URL
        
        Args:
            url: Product URL
            
        Returns:
            Platform name: 'mercadolibre', 'amazon', or None
        """
        url_lower = url.lower()
        
        if "mercadolibre" in url_lower or "mercadolivre" in url_lower:
            return "mercadolibre"
        elif "amazon" in url_lower:
            return "amazon"
        else:
            return None


def scrape_product_from_url(url: str) -> Optional[dict]:
    """
    Convenience function to scrape a product from any supported URL
    
    Args:
        url: Product URL
        
    Returns:
        Product data dictionary or None
    """
    scraper = ScraperFactory.get_scraper(url)
    if scraper:
        return scraper.scrape_product(url)
    return None

