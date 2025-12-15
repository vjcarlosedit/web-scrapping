#!/usr/bin/env python3
"""
Main script to run the Price Scraper application
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('price_scraper.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    try:
        logger.info("Starting Price Scraper application...")
        
        # Import here to ensure logging is configured first
        import uvicorn
        from backend.config import API_HOST, API_PORT
        
        logger.info(f"Server will start on http://{API_HOST}:{API_PORT}")
        logger.info("Dashboard available at http://localhost:8000")
        logger.info("API documentation at http://localhost:8000/docs")
        logger.info("Press CTRL+C to stop the server")
        
        # Determine if we're in development or production
        is_development = os.getenv("ENVIRONMENT", "development") == "development"
        
        # Run the application
        uvicorn.run(
            "backend.api.main:app",
            host=API_HOST,
            port=API_PORT,
            reload=is_development,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

