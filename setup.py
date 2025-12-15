#!/usr/bin/env python3
"""
Setup script to initialize the project
"""
import os
import sys
import subprocess
from pathlib import Path


def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "logs",
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory}")


def create_env_file():
    """Create .env file if it doesn't exist"""
    if not os.path.exists(".env"):
        # Default .env content
        env_content = """# Database Configuration
DATABASE_URL=sqlite:///./data/prices.db

# Scheduler Configuration
SCRAPING_HOUR=8
SCRAPING_MINUTE=0

# Scraping Configuration
REQUEST_DELAY=3
MAX_RETRIES=3

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Notion Integration (Optional)
NOTION_ENABLED=false
NOTION_TOKEN=
NOTION_DATABASE_ID=

# Optional: Add your API keys here if needed
# MERCADOLIBRE_API_KEY=your_key_here
# AMAZON_ASSOCIATE_TAG=your_tag_here
"""
        
        with open(".env", "w") as target:
            target.write(env_content)
        
        print("✓ Created .env file with default configuration")
    else:
        print("✓ .env file already exists")


def check_python_version():
    """Check if Python version is adequate"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    print(f"✓ Python version: {sys.version.split()[0]}")


def install_dependencies():
    """Install Python dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)


def initialize_database():
    """Initialize the database"""
    print("\nInitializing database...")
    try:
        from backend.database.db import init_database
        init_database()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        sys.exit(1)


def main():
    """Main setup function"""
    print("=" * 60)
    print("Price Scraper - Setup")
    print("=" * 60)
    print()
    
    # Check Python version
    check_python_version()
    
    # Create directories
    print("\nCreating directories...")
    create_directories()
    
    # Create .env file
    print("\nSetting up configuration...")
    create_env_file()
    
    # Install dependencies
    response = input("\nInstall dependencies? (y/n): ")
    if response.lower() == 'y':
        install_dependencies()
    
    # Initialize database
    print("\nInitializing database...")
    initialize_database()
    
    print("\n" + "=" * 60)
    print("✓ Setup completed successfully!")
    print("=" * 60)
    print("\nTo start the application, run:")
    print("  python run.py")
    print("\nOr manually:")
    print("  python -m uvicorn backend.api.main:app --reload")
    print()


if __name__ == "__main__":
    main()

