from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import atexit

from backend.config import SCRAPING_HOUR, SCRAPING_MINUTE
from backend.scheduler.jobs import scrape_all_products

logger = logging.getLogger(__name__)


class PriceScraperScheduler:
    """Scheduler for automated price scraping"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            # Add daily scraping job
            self.scheduler.add_job(
                func=scrape_all_products,
                trigger=CronTrigger(hour=SCRAPING_HOUR, minute=SCRAPING_MINUTE),
                id="daily_scraping",
                name="Daily price scraping",
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"Scheduler started. Daily scraping scheduled at {SCRAPING_HOUR:02d}:{SCRAPING_MINUTE:02d}")
            
            # Shutdown scheduler on exit
            atexit.register(self.shutdown)
        else:
            logger.warning("Scheduler is already running")
    
    def shutdown(self):
        """Shutdown the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler shutdown")
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def run_now(self):
        """Manually trigger scraping job"""
        logger.info("Manually triggering scraping job")
        return scrape_all_products()


# Global scheduler instance
scheduler_instance = PriceScraperScheduler()


def get_scheduler() -> PriceScraperScheduler:
    """Get the global scheduler instance"""
    return scheduler_instance

