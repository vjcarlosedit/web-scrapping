import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
import logging
import random

from backend.scraper.base import BaseScraper
from backend.config import USER_AGENTS

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper for Amazon using BeautifulSoup with anti-blocking measures"""
    
    def __init__(self):
        super().__init__()
        self.domain = "amazon"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    
    def get_random_user_agent(self) -> str:
        """Get a random user agent"""
        return random.choice(USER_AGENTS)
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """
        Extract ASIN (Amazon Standard Identification Number) from URL
        
        Examples:
        - https://www.amazon.com/dp/B08N5WRWNW/
        - https://www.amazon.com/product/B08N5WRWNW
        - https://www.amazon.com/Product-Name/dp/B08N5WRWNW/ref=...
        """
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'ASIN=([A-Z0-9]{10})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        logger.error(f"Could not extract ASIN from URL: {url}")
        return None
    
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape product information from Amazon
        
        Note: Amazon actively blocks scrapers. This is for educational purposes only.
        Consider using Amazon Product Advertising API for production use.
        """
        if not self.validate_url(url, self.domain):
            logger.error(f"Invalid Amazon URL: {url}")
            return None
        
        product_id = self.extract_product_id(url)
        if not product_id:
            return None
        
        try:
            # Add random user agent to headers
            headers = self.headers.copy()
            headers["User-Agent"] = self.get_random_user_agent()
            
            logger.info(f"Fetching Amazon product: {url}")
            
            # Add delay before request
            self.sleep()
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # Check if we got blocked
            if "captcha" in response.text.lower() or response.status_code == 503:
                logger.error("Amazon returned a CAPTCHA or blocked the request")
                return None
            
            # Try to use html5lib for better parsing, fallback to html.parser
            try:
                soup = BeautifulSoup(response.content, 'html5lib')
            except:
                soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product name
            name = self._extract_name(soup)
            
            # Extract price
            price_data = self._extract_price(soup)
            
            # Extract image
            image_url = self._extract_image(soup)
            
            # Extract availability
            availability = self._extract_availability(soup)
            
            if not name or not price_data["price"]:
                logger.error("Could not extract essential product information")
                return None
            
            result = {
                "name": name,
                "price": price_data["price"],
                "original_price": price_data.get("original_price"),
                "discount_percentage": price_data.get("discount_percentage"),
                "currency": price_data.get("currency", "USD"),
                "image_url": image_url,
                "availability": availability,
                "product_id": product_id,
            }
            
            logger.info(f"Successfully scraped Amazon product: {result['name']} - ${result['price']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product from Amazon: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing Amazon page: {str(e)}")
            return None
    
    def _extract_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product name from page"""
        selectors = [
            {"id": "productTitle"},
            {"class": "product-title-word-break"},
            {"id": "title"},
        ]
        
        for selector in selectors:
            element = soup.find(**selector)
            if element:
                return element.get_text().strip()
        
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract price information from page"""
        result = {
            "price": None,
            "original_price": None,
            "discount_percentage": None,
            "currency": "USD"
        }
        
        # Try multiple price selectors
        price_selectors = [
            {"class": "a-price-whole"},
            {"class": "a-offscreen"},
            {"id": "priceblock_ourprice"},
            {"id": "priceblock_dealprice"},
            {"class": "a-price"},
        ]
        
        price_text = None
        for selector in price_selectors:
            element = soup.find(**selector)
            if element:
                price_text = element.get_text().strip()
                break
        
        if price_text:
            # Clean and extract numeric value
            # Remove currency symbols and commas
            price_clean = re.sub(r'[^\d.,]', '', price_text)
            # Handle different decimal separators
            price_clean = price_clean.replace(',', '')
            
            try:
                result["price"] = float(price_clean)
            except ValueError:
                logger.warning(f"Could not parse price: {price_text}")
        
        # Try to extract original price (if discounted)
        original_price_selectors = [
            {"class": "a-text-price"},
            {"class": "priceBlockStrikePriceString"},
        ]
        
        for selector in original_price_selectors:
            element = soup.find(**selector)
            if element:
                original_text = element.get_text().strip()
                original_clean = re.sub(r'[^\d.,]', '', original_text)
                original_clean = original_clean.replace(',', '')
                try:
                    original_price = float(original_clean)
                    if original_price > result["price"]:
                        result["original_price"] = original_price
                        result["discount_percentage"] = round(
                            ((original_price - result["price"]) / original_price) * 100, 2
                        )
                except ValueError:
                    pass
                break
        
        # Extract currency
        currency_element = soup.find("span", {"class": "a-price-symbol"})
        if currency_element:
            symbol = currency_element.get_text().strip()
            currency_map = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
            result["currency"] = currency_map.get(symbol, "USD")
        
        return result
    
    def _extract_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image URL"""
        # Try different image selectors
        img_selectors = [
            {"id": "landingImage"},
            {"id": "imgBlkFront"},
            {"class": "a-dynamic-image"},
        ]
        
        for selector in img_selectors:
            img = soup.find("img", selector)
            if img and img.get("src"):
                return img["src"]
        
        return None
    
    def _extract_availability(self, soup: BeautifulSoup) -> str:
        """Extract availability status"""
        availability_selectors = [
            {"id": "availability"},
            {"class": "availability"},
        ]
        
        for selector in availability_selectors:
            element = soup.find(**selector)
            if element:
                text = element.get_text().strip().lower()
                
                if "in stock" in text or "available" in text:
                    return "available"
                elif "out of stock" in text or "unavailable" in text:
                    return "out_of_stock"
                else:
                    return "unknown"
        
        # If we found a price, assume it's available
        return "available"


def test_scraper():
    """Test function for Amazon scraper"""
    scraper = AmazonScraper()
    
    # Test URL (replace with actual product URL)
    test_url = "https://www.amazon.com/dp/B08N5WRWNW"
    
    print(f"Testing URL: {test_url}")
    result = scraper.scrape_product(test_url)
    if result:
        print(f"Success: {result}")
    else:
        print("Failed to scrape")


if __name__ == "__main__":
    test_scraper()

