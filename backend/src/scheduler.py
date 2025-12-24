"""
Scheduler for automated bot training tasks.
Runs the training model daily at 7:00 AM Colombia time (UTC-5).
Results are cached for same-day queries.
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
        """Execute the daily training task and cache results."""
        if self._training_in_progress:
            logger.warning("Training already in progress, skipping scheduled run")
            return
            
        try:
            self._training_in_progress = True
            logger.info(f"Starting scheduled training at {datetime.now(COLOMBIA_TZ)}")
            
            # Import here to avoid circular imports
            from src.api.routes.learning import BacktestRequest
            from src.api.dependencies import get_learning_service, get_football_data_uk, get_prediction_service, get_statistics_service, get_data_sources
            from src.infrastructure.cache import get_training_cache
            
            # Get dependencies
            learning_service = get_learning_service()
            data_sources = get_data_sources()
            prediction_service = get_prediction_service()
            statistics_service = get_statistics_service()
            
            # Create request for full year
            request = BacktestRequest(
                league_ids=["E0", "SP1", "D1", "I1", "F1"],
                days_back=3650,  # Full 10 year history
                reset_weights=False
            )
            
            # Run training (dynamically import to avoid issues)
            from src.api.routes.learning import run_training_session
            result = await run_training_session(
                request=request,
                learning_service=learning_service,
                data_sources=data_sources,
                prediction_service=prediction_service,
                statistics_service=statistics_service
            )
            
            # Cache the results
            cache = get_training_cache()
            cache.set_training_results(result)
            
            logger.info(f"Scheduled training completed successfully. "
                       f"Processed {result.get('matches_processed', 0)} matches, "
                       f"Accuracy: {result.get('accuracy', 0):.2%}. "
                       f"Results cached.")
                       
        except Exception as e:
            logger.error(f"Error during scheduled training: {str(e)}", exc_info=True)
        finally:
            self._training_in_progress = False
    
    def start(self):
        """Start the scheduler with daily training at 7:00 AM Colombia time."""
        try:
            # Schedule daily training at 7:00 AM Colombia time
            self.scheduler.add_job(
                self.run_daily_training,
                trigger=CronTrigger(hour=7, minute=0, timezone=COLOMBIA_TZ),
                id='daily_training',
                name='Daily Bot Training at 7:00 AM COT',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            self.scheduler.start()
            logger.info("Scheduler started. Daily training scheduled for 7:00 AM Colombia time")
            
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

