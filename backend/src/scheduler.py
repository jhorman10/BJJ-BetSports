import logging
import asyncio
import gc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from datetime import datetime
from typing import Generator

logger = logging.getLogger(__name__)

# Colombia timezone
COLOMBIA_TZ = timezone('America/Bogota')

class BotScheduler:
    """Manages scheduled tasks with extreme memory efficiency for Render Free Tier."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=COLOMBIA_TZ)
        self._job_in_progress = False
        
    def _get_league_iterator(self, leagues_dict: dict) -> Generator[str, None, None]:
        """Memory-efficient generator for iterating through leagues."""
        for league_id in leagues_dict.keys():
            yield league_id

    async def run_daily_orchestrated_job(self):
        """
        Execute the daily orchestrated job pipeline with 512MB RAM constraint.
        1. Retraining (Selective)
        2. Massive Inference (Generator-based Chunking)
        3. Garbage Collection Pipeline
        """
        if self._job_in_progress:
            logger.warning("Job already in progress, skipping scheduled run")
            return
            
        try:
            self._job_in_progress = True
            today_str = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d")
            logger.info(f"ARCHITECT: Starting memory-optimized job at {datetime.now(COLOMBIA_TZ)}")
            
            # Dynamic imports to keep initial memory low
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
            
            # 1. RETRAINING (Execute once and clear)
            logger.info("Step 1/3: Starting retraining (Memory window active)...")
            learning_service = get_learning_service()
            data_sources = get_data_sources()
            prediction_service = get_prediction_service()
            statistics_service = get_statistics_service()
            
            request = BacktestRequest(
                league_ids=list(LEAGUES_METADATA.keys()),
                days_back=365,
                reset_weights=False
            )
            
            training_result = await run_training_session(
                request=request,
                learning_service=learning_service,
                data_sources=data_sources,
                prediction_service=prediction_service,
                statistics_service=statistics_service,
                background_tasks=None
            )
            accuracy = getattr(training_result, 'accuracy', 0)
            logger.info(f"Retraining completed. Accuracy: {accuracy:.2%}")
            
            # Cleanup training objects
            del training_result
            del request
            gc.collect()

            # 2. MASSIVE INFERENCE (The Chunking Loop)
            logger.info("Step 2/3: Starting iterative inference (One league at a time)...")
            use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service)
            cache = get_cache_service()
            
            leagues_processed = 0
            # Use generator to avoid holding all league IDs in a list if it scales
            for league_id in self._get_league_iterator(LEAGUES_METADATA):
                try:
                    logger.info(f"Processing {league_id} (RAM status check needed)...")
                    
                    # Generate predictions for THIS league ONLY
                    predictions_dto = await use_case.execute(league_id, limit=50)
                    
                    # Store league forecast in Redis
                    league_cache_key = f"forecasts:league_{league_id}:date_{today_str}"
                    cache.set(league_cache_key, predictions_dto.dict(), cache.TTL_FORECASTS)
                    
                    # Store individual match predictions
                    for match_pred in predictions_dto.predictions:
                        match_id = match_pred.match.id
                        match_cache_key = f"forecasts:match_{match_id}"
                        cache.set(match_cache_key, match_pred.dict(), cache.TTL_FORECASTS)
                    
                    # CRITICAL: Immediate memory liberation
                    del predictions_dto
                    gc.collect()
                    
                    leagues_processed += 1
                    # Subtle sleep to allow CPU to breathe on 0.1 CPU limit
                    await asyncio.sleep(0.5) 
                    
                except Exception as e:
                    logger.error(f"Error processing league {league_id}: {str(e)}")
                    gc.collect() # Ensure we clean up even on error
            
            logger.info(f"ARCHITECT: Orchestrated job finished. {leagues_processed} leagues processed. Memory stabilized.")
                       
        except Exception as e:
            logger.error(f"CRITICAL Error during orchestrated job: {str(e)}", exc_info=True)
            gc.collect()
        finally:
            self._job_in_progress = False
            gc.collect()
    
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

