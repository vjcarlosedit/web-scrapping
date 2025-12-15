import re
import requests
from typing import Optional, Dict, Any
import logging

from backend.scraper.base import BaseScraper

logger = logging.getLogger(__name__)


class MercadoLibreScraper(BaseScraper):
    """Scraper for Mercado Libre using their public API"""
    
    def __init__(self):
        super().__init__()
        self.base_api_url = "https://api.mercadolibre.com"
        self.domain = "mercadolibre"
    
    def extract_product_id(self, url: str) -> Optional[str]:
        """
        Extract product ID from Mercado Libre URL
        
        Examples:
        - https://www.mercadolibre.com.mx/producto-MLM123456789
        - https://articulo.mercadolibre.com.mx/MLM-123456789-producto
        - https://www.mercadolibre.com.mx/producto/p/MLM2000081745
        """
        patterns = [
            r'/p/(ML[A-Z]\d+)',           # /p/MLM123456789
            r'/(ML[A-Z]-\d+)',            # /MLM-123456789
            r'/(ML[A-Z]\d+)',             # /MLM123456789 or in middle of URL
            r'articulo.*/(ML[A-Z]-\d+)',  # articulo.mercadolibre.com/MLM-123456789
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                product_id = match.group(1).upper()
                # Remove hyphen if present (MLM-123 -> MLM123)
                product_id = product_id.replace('-', '')
                logger.info(f"Extracted product ID: {product_id}")
                return product_id
        logger.error(f"Could not extract product ID from URL: {url}")
        return None
    
    def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape product information from Mercado Libre using their API
        
        API Documentation: https://developers.mercadolibre.com/
        """
        if not self.validate_url(url, self.domain):
            logger.error(f"Invalid Mercado Libre URL: {url}")
            return None
        
        product_id = self.extract_product_id(url)
        if not product_id:
            return None
        
        try:
            # Add headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
            }
            
            # Try primary endpoint first
            api_url = f"{self.base_api_url}/items/{product_id}"
            logger.info(f"Fetching product data from API: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            
            # If we get 403, try the visits endpoint which is less restrictive
            if response.status_code == 403:
                # Try alternative: get product through visits/items endpoint
                api_url_alt = f"{self.base_api_url}/visits/items?ids={product_id}"
                response_alt = requests.get(api_url_alt, headers=headers, timeout=10)
                
                if response_alt.status_code == 200:
                    visits_data = response_alt.json()
                    # If visits work, try items endpoint one more time with different approach
                    if product_id in visits_data:
                        # The product exists, but items endpoint blocks it
                        # Let's try multiget which is more permissive
                        api_url = f"{self.base_api_url}/items?ids={product_id}&attributes=id,title,price,original_price,currency_id,thumbnail,pictures,status,available_quantity"
                        response = requests.get(api_url, headers=headers, timeout=10)
            
            # If API still returns 403, fallback to HTML scraping
            if response.status_code == 403:
                logger.warning("API blocked, attempting HTML scraping fallback")
                return self._scrape_from_html(url, product_id)
            
            response.raise_for_status()
            
            data = response.json()
            
            # Extract relevant information
            price = data.get("price")
            original_price = data.get("original_price")
            
            # Calculate discount if applicable
            discount_percentage = None
            if original_price and original_price > price:
                discount_percentage = ((original_price - price) / original_price) * 100
            
            # Get product image
            image_url = None
            if data.get("pictures") and len(data["pictures"]) > 0:
                image_url = data["pictures"][0].get("url") or data["pictures"][0].get("secure_url")
            elif data.get("thumbnail"):
                image_url = data.get("thumbnail")
            
            # Determine availability
            availability = "available"
            if data.get("status") != "active":
                availability = "unavailable"
            elif data.get("available_quantity", 0) == 0:
                availability = "out_of_stock"
            
            result = {
                "name": data.get("title", "Unknown Product"),
                "price": float(price) if price else 0.0,
                "original_price": float(original_price) if original_price else None,
                "discount_percentage": round(discount_percentage, 2) if discount_percentage else None,
                "currency": data.get("currency_id", "USD"),
                "image_url": image_url,
                "availability": availability,
                "product_id": product_id,
            }
            
            logger.info(f"Successfully scraped product: {result['name']} - ${result['price']}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching product from Mercado Libre API: {str(e)}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Mercado Libre API response: {str(e)}")
            return None
    
    def _scrape_from_html(self, url: str, product_id: str) -> Optional[Dict[str, Any]]:
        """Fallback method: scrape product data from HTML page"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
            }
            
            logger.info(f"Scraping HTML from: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html5lib')
            
            # Extract title
            title_elem = soup.find('h1', class_='ui-pdp-title')
            name = title_elem.get_text().strip() if title_elem else "Unknown Product"
            
            # Extract price - prioritize discounted/promotional price
            price = None
            original_price = None
            discount_percentage = None
            
            # Strategy 1: Look for price in the main price block (ui-pdp-price)
            price_container = soup.find('div', class_='ui-pdp-price')
            
            if price_container:
                # Look for promotional/discounted price first (usually in a specific container)
                # Try to find the price that's NOT strikethrough and NOT in comparison
                all_fractions = price_container.find_all('span', class_='andes-money-amount__fraction')
                
                # Filter out strikethrough prices (original prices)
                non_strikethrough_prices = [pf for pf in all_fractions if not pf.find_parent('s')]
                
                if non_strikethrough_prices:
                    # Usually the first non-strikethrough price is the actual price
                    promo_price = non_strikethrough_prices[0]
                    price_text = promo_price.get_text().strip()
                    price_clean = re.sub(r'[^\d.]', '', price_text.replace(',', ''))
                    try:
                        price = float(price_clean)
                    except ValueError:
                        pass
                
                # Look for original price (usually strikethrough)
                original_prices = price_container.find_all('s')
                for orig in original_prices:
                    orig_fraction = orig.find('span', class_='andes-money-amount__fraction')
                    if orig_fraction:
                        orig_text = orig_fraction.get_text().strip()
                        orig_clean = re.sub(r'[^\d.]', '', orig_text.replace(',', ''))
                        try:
                            original_price = float(orig_clean)
                            break
                        except ValueError:
                            pass
                
                # Calculate discount if both prices exist
                if price and original_price and original_price > price:
                    discount_percentage = round(((original_price - price) / original_price) * 100, 2)
            
            # Fallback: try meta tag if no price found yet
            if not price:
                meta_price = soup.find('meta', {'property': 'og:price:amount'})
                if meta_price:
                    price_text = meta_price.get('content', '')
                    price_clean = re.sub(r'[^\d.]', '', price_text.replace(',', ''))
                    try:
                        price = float(price_clean)
                    except ValueError:
                        pass
            
            # Extract currency
            currency = "MXN"  # Default for Mexico
            currency_elem = soup.find('meta', {'property': 'og:price:currency'})
            if currency_elem:
                currency = currency_elem.get('content', 'MXN')
            
            # Extract image - prioritize high quality sources
            image_url = None
            
            # Try to find the main product image with ui-pdp-image class
            img_elem = soup.find('img', class_='ui-pdp-image')
            if img_elem:
                # Priority order: data-zoom (highest quality) > src > data-src
                image_url = (img_elem.get('data-zoom') or 
                           img_elem.get('src') or 
                           img_elem.get('data-src'))
            
            # Fallback to og:image meta tag if needed
            if not image_url or image_url.startswith('data:image'):
                og_image = soup.find('meta', {'property': 'og:image'})
                if og_image:
                    image_url = og_image.get('content')
            
            # Check availability
            availability = "available"
            sold_out = soup.find(text=re.compile(r'(agotado|sin stock|no disponible)', re.I))
            if sold_out:
                availability = "out_of_stock"
            
            if not price:
                logger.error("Could not extract price from HTML")
                return None
            
            result = {
                "name": name,
                "price": price,
                "original_price": original_price,
                "discount_percentage": discount_percentage,
                "currency": currency,
                "image_url": image_url,
                "availability": availability,
                "product_id": product_id,
            }
            
            logger.info(f"Successfully scraped from HTML: {name} - {currency}{price}")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping HTML: {str(e)}")
            return None
    
    def get_product_description(self, product_id: str) -> Optional[str]:
        """Get product description (optional, for future use)"""
        try:
            api_url = f"{self.base_api_url}/items/{product_id}/description"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("plain_text", "")
        except Exception as e:
            logger.warning(f"Could not fetch description: {str(e)}")
            return None


def test_scraper():
    """Test function for Mercado Libre scraper"""
    scraper = MercadoLibreScraper()
    
    # Test URLs (replace with actual product URLs)
    test_urls = [
        "https://www.mercadolibre.com.mx/apple-iphone-13-128-gb-medianoche/p/MLM18847408",
        "https://articulo.mercadolibre.com.mx/MLM-1234567890-test-product",
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        result = scraper.scrape_product(url)
        if result:
            print(f"Success: {result}")
        else:
            print("Failed to scrape")


if __name__ == "__main__":
    test_scraper()

