"""
Notion API Integration for Price Tracker

This module syncs product price data to a Notion database.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from notion_client import Client
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)


class NotionPriceTracker:
    """Client for syncing price data to Notion"""
    
    def __init__(self, token: str, database_id: str):
        """
        Initialize Notion client
        
        Args:
            token: Notion integration token
            database_id: Notion database ID to sync to
        """
        self.client = Client(auth=token)
        self.token = token  # Store token for direct API calls
        self.database_id = database_id
        self._validate_connection()
    
    def _validate_connection(self):
        """Validate Notion connection and database access"""
        try:
            # Try to retrieve the database to validate access
            self.client.databases.retrieve(database_id=self.database_id)
            logger.info("✓ Notion connection validated successfully")
        except APIResponseError as e:
            logger.error(f"Failed to connect to Notion: {e}")
            raise
    
    def sync_product(
        self,
        product_name: str,
        platform: str,
        url: str,
        current_price: float,
        currency: str,
        lowest_price: float,
        lowest_price_date: datetime,
        last_update: datetime,
        notion_page_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Sync a product to Notion database
        
        Args:
            product_name: Name of the product
            platform: Platform (Amazon, Mercado Libre)
            url: Product URL
            current_price: Current price
            currency: Currency code
            lowest_price: Lowest price ever recorded
            lowest_price_date: Date when lowest price was recorded
            last_update: Last update timestamp
            
        Returns:
            Page ID if successful, None otherwise
        """
        try:
            # Check if product already exists - prefer notion_page_id over name search
            existing_page = None
            if notion_page_id:
                # Try to get page directly by ID
                existing_page = self._get_page_by_id(notion_page_id)
            
            # Fallback to name search if no page found by ID
            if not existing_page:
                existing_page = self._find_product_page(product_name)
            
            properties = self._build_properties(
                product_name=product_name,
                platform=platform,
                url=url,
                current_price=current_price,
                currency=currency,
                lowest_price=lowest_price,
                lowest_price_date=lowest_price_date,
                last_update=last_update
            )
            
            if existing_page:
                # Update existing page
                page_id = existing_page['id']
                self.client.pages.update(page_id=page_id, properties=properties)
                logger.info(f"✓ Updated product in Notion: {product_name}")
                return page_id
            else:
                # Create new page
                response = self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties
                )
                logger.info(f"✓ Created new product in Notion: {product_name}")
                return response['id']
                
        except APIResponseError as e:
            logger.error(f"Error syncing product to Notion: {e}")
            return None
    
    def _get_database_properties(self) -> List[str]:
        """Get list of property names from database (cached)"""
        if not hasattr(self, '_cached_properties'):
            try:
                database = self.client.databases.retrieve(database_id=self.database_id)
                self._cached_properties = list(database.get('properties', {}).keys())
            except:
                self._cached_properties = []
        return self._cached_properties
    
    def _get_page_by_id(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get a Notion page directly by its ID"""
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.debug(f"Could not get page by ID {page_id}: {e}")
            return None
    
    def _find_product_page(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Find a product page by product name (title property)"""
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            # Query all pages and filter by product name
            response = requests.post(
                f"https://api.notion.com/v1/databases/{self.database_id}/query",
                headers=headers,
                json={}
            )
            
            if response.status_code == 200:
                query_response = response.json()
                results = query_response.get('results', [])
                
                # Search for page with matching product name in "Nombre" property
                for page in results:
                    page_props = page.get('properties', {})
                    nombre_prop = page_props.get('Nombre', {})
                    
                    if nombre_prop.get('type') == 'title':
                        title_parts = nombre_prop.get('title', [])
                        if title_parts:
                            page_name = title_parts[0].get('plain_text', '')
                            
                            # Exact match
                            if page_name == product_name:
                                return page
            return None
            
        except Exception as e:
            # If query fails (property might not exist or different name), return None
            # This will cause a new page to be created
            logger.debug(f"Could not query by URL (will create new page if needed): {e}")
            return None
    
    def _build_properties(
        self,
        product_name: str,
        platform: str,
        url: str,
        current_price: float,
        currency: str,
        lowest_price: float,
        lowest_price_date: datetime,
        last_update: datetime
    ) -> Dict[str, Any]:
        """Build Notion page properties"""
        # Truncate product name to 50 characters for Notion display
        truncated_name = product_name[:50] if len(product_name) > 50 else product_name
        
        # Log truncation for debugging
        if len(product_name) > 50:
            logger.info(f"Truncating product name from {len(product_name)} to 50 chars: '{product_name[:50]}...' -> '{truncated_name}'")
        
        # Build properties using the exact names from your Notion database
        properties = {
            "Nombre": {  # Title property - exact name from your DB
                "title": [
                    {
                        "text": {
                            "content": truncated_name
                        }
                    }
                ]
            },
            "Fecha Actualización": {
                "date": {
                    "start": last_update.isoformat()
                }
            },
            "Precio Actual": {
                "number": current_price
            },
            "Fecha Descuento": {
                "date": {
                    "start": lowest_price_date.isoformat()
                }
            },
            "Precio Descuento": {
                "number": lowest_price
            }
        }
        
        # Add Plataforma and URL properties (they exist in the database)
        properties["Plataforma"] = {
            "select": {
                "name": platform
            }
        }
        properties["URL"] = {
            "url": url
        }
        
        return properties
    
    def sync_all_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Sync multiple products to Notion
        
        Args:
            products_data: List of product dictionaries
            
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "synced": 0,
            "failed": 0,
            "total": len(products_data)
        }
        
        for product_data in products_data:
            result = self.sync_product(**product_data)
            if result:
                stats["synced"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(f"Notion sync complete: {stats['synced']}/{stats['total']} synced successfully")
        return stats
    
    def delete_page(self, page_id: str) -> bool:
        """
        Delete (archive) a page from Notion
        
        Args:
            page_id: Notion page ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Notion API doesn't support hard delete, only archive
            self.client.pages.update(page_id=page_id, archived=True)
            logger.info(f"✓ Archived page in Notion: {page_id}")
            return True
        except Exception as e:
            logger.error(f"Error archiving page in Notion: {e}")
            return False

