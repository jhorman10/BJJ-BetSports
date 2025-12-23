"""
Scheduler for automated bot training tasks.
Runs the training model daily at 8:00 AM Colombia time (UTC-5).
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

# Colombia timezone
COLOMBIA_TZ = timezone('America/Bogota')

class BotScheduler:
    """Manages scheduled tasks for the bot."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=COLOMBIA_TZ)
        self._training_in_progress = False
        
    async def run_daily_training(self):
        """Execute the daily training task."""
        if self._training_in_progress:
            logger.warning("Training already in progress, skipping scheduled run")
            return
            
        try:
            self._training_in_progress = True
            logger.info(f"Starting scheduled training at {datetime.now(COLOMBIA_TZ)}")
            
            # Import here to avoid circular imports
            from src.api.routes.learning import run_training_session
            
            # Run the training session
            result = await run_training_session()
            
            logger.info(f"Scheduled training completed successfully. "
                       f"Processed {result.get('matches_processed', 0)} matches, "
                       f"Accuracy: {result.get('accuracy', 0):.2%}")
                       
        except Exception as e:
            logger.error(f"Error during scheduled training: {str(e)}", exc_info=True)
        finally:
            self._training_in_progress = False
    
    def start(self):
        """Start the scheduler with daily training at 8:00 AM Colombia time."""
        try:
            # Schedule daily training at 8:00 AM Colombia time
            self.scheduler.add_job(
                self.run_daily_training,
                trigger=CronTrigger(hour=8, minute=0, timezone=COLOMBIA_TZ),
                id='daily_training',
                name='Daily Bot Training at 8:00 AM COT',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            self.scheduler.start()
            logger.info("Scheduler started. Daily training scheduled for 8:00 AM Colombia time")
            
            # Log next run time
            next_run = self.scheduler.get_job('daily_training').next_run_time
            logger.info(f"Next training scheduled for: {next_run}")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
    
    def shutdown(self):
        """Shutdown the scheduler gracefully."""
        try:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {str(e)}")

# Global scheduler instance
_scheduler_instance = None

def get_scheduler() -> BotScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = BotScheduler()
    return _scheduler_instance
