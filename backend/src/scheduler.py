"""
Scheduler for automated bot tasks.
Runs at 06:00 AM Colombia time (UTC-5).
Pipeline: Retraining -> Massive Inference -> Redis Pre-warming.
"""
import logging
import asyncio
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
        self._job_in_progress = False
        
    async def run_daily_orchestrated_job(self):
        """
        Execute the daily orchestrated job pipeline.
        1. Retraining
        2. Massive Inference (All leagues)
        3. Redis Pre-warming
        """
        if self._job_in_progress:
            logger.warning("Job already in progress, skipping scheduled run")
            return
            
        try:
            self._job_in_progress = True
            today_str = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d")
            logger.info(f"Starting daily orchestrated job at {datetime.now(COLOMBIA_TZ)}")
            
            # Import dependencies dynamically
            from src.api.routes.learning import BacktestRequest, run_training_session
            from src.api.dependencies import (
                get_learning_service, 
                get_prediction_service, 
                get_statistics_service, 
                get_data_sources
            )
            from src.infrastructure.cache.cache_service import get_cache_service
            from src.application.use_cases.use_cases import GetPredictionsUseCase
            from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
            
            # 1. RETRAINING
            logger.info("Step 1/3: Starting retraining...")
            learning_service = get_learning_service()
            data_sources = get_data_sources()
            prediction_service = get_prediction_service()
            statistics_service = get_statistics_service()
            
            request = BacktestRequest(
                league_ids=list(LEAGUES_METADATA.keys()),
                days_back=365,  # 1 year for retraining
                reset_weights=False
            )
            
            training_result = await run_training_session(
                request=request,
                learning_service=learning_service,
                data_sources=data_sources,
                prediction_service=prediction_service,
                statistics_service=statistics_service,
                background_tasks=None # No background tasks needed for scheduler
            )
            logger.info(f"Retraining completed. Accuracy: {training_result.get('accuracy', 0):.2%}")
            
            # 2. MASSIVE INFERENCE & 3. PRE-WARMING
            logger.info("Step 2/3: Starting massive inference and pre-warming...")
            use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service)
            cache = get_cache_service()
            
            leagues_processed = 0
            for league_id in LEAGUES_METADATA.keys():
                try:
                    logger.info(f"Processing league {league_id}...")
                    # Generate predictions for the league
                    predictions_dto = await use_case.execute(league_id, limit=50)
                    
                    # Store league forecast in Redis: forecasts:league_{id}:date_{today}
                    league_cache_key = f"forecasts:league_{league_id}:date_{today_str}"
                    cache.set(league_cache_key, predictions_dto.dict(), cache.TTL_FORECASTS)
                    
                    # Also store individual match predictions for fast lookup by match_id
                    for match_pred in predictions_dto.predictions:
                        match_id = match_pred.match.id
                        # Key format: forecasts:match_{match_id}
                        # No date in key to keep it simple for single match lookup, 
                        # but with 24h TTL it will refresh daily.
                        match_cache_key = f"forecasts:match_{match_id}"
                        cache.set(match_cache_key, match_pred.dict(), cache.TTL_FORECASTS)
                    
                    leagues_processed += 1
                except Exception as e:
                    logger.error(f"Error processing league {league_id}: {str(e)}")
            
            logger.info(f"Daily orchestrated job completed successfully. Processed {leagues_processed} leagues.")
                       
        except Exception as e:
            logger.error(f"Error during orchestrated job: {str(e)}", exc_info=True)
        finally:
            self._job_in_progress = False
    
    def start(self, run_immediate: bool = False):
        """
        Start the scheduler with daily job at 06:00 AM Colombia time.
        
        Args:
            run_immediate: If True, triggers the job immediately in the background.
        """
        try:
            self.scheduler.add_job(
                self.run_daily_orchestrated_job,
                trigger=CronTrigger(hour=6, minute=0, timezone=COLOMBIA_TZ),
                id='daily_orchestrated_job',
                name='Daily Orchestrated Job at 06:00 AM COT',
                replace_existing=True,
                max_instances=1
            )
            
            self.scheduler.start()
            logger.info("Scheduler started. Daily job scheduled for 06:00 AM Colombia time")
            
            if run_immediate:
                logger.info("Triggering immediate job execution as requested...")
                asyncio.create_task(self.run_daily_orchestrated_job())
            
            job = self.scheduler.get_job('daily_orchestrated_job')
            if job:
                logger.info(f"Next scheduled run: {job.next_run_time}")
            
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

