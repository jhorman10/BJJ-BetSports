import logging
import asyncio
import gc
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
from datetime import datetime
from typing import Generator
from src.utils.time_utils import COLOMBIA_TZ, get_today_str

# Configure logger
logger = logging.getLogger(__name__)

class BotScheduler:
    """Manages scheduled tasks with extreme memory efficiency for Render Free Tier."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=COLOMBIA_TZ)
        self._job_in_progress = False
        
    def _get_league_iterator(self, leagues_dict: dict) -> Generator[str, None, None]:
        """Memory-efficient generator for iterating through leagues."""
        for league_id in leagues_dict.keys():
            yield league_id

    async def run_audit_only_job(self):
        """Standalone audit job (08:00 AM)."""
        logger.info("Starting scheduled data audit...")
        try:
             from src.api.dependencies import get_audit_service
             audit_service = get_audit_service()
             report = await audit_service.audit_and_fix(fix_missing=True)
             logger.info(f"Scheduled Audit Complete. Status: {report['status']}")
        except Exception as e:
             logger.error(f"Scheduled audit failed: {e}")

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
            today_str = get_today_str()
            logger.info(f"ARCHITECT: Starting memory-optimized job at {datetime.now(COLOMBIA_TZ)}")
            
            # Dynamic imports to keep initial memory low
            from src.api.dependencies import (
                get_ml_training_orchestrator, get_cache_service, get_data_sources, 
                get_prediction_service, get_statistics_service, get_audit_service, 
                get_persistence_repository
            )
            from src.application.use_cases.use_cases import GetPredictionsUseCase
            from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
            
            orchestrator = get_ml_training_orchestrator()
            cache = get_cache_service()
            persistence_repo = get_persistence_repository()
            data_sources = get_data_sources()
            prediction_service = get_prediction_service()
            statistics_service = get_statistics_service()
            
            leagues = list(LEAGUES_METADATA.keys())
            
            # 1. RETRAINING
            import os
            if os.getenv("DISABLE_ML_TRAINING") == "true":
                 logger.info("Step 1/4: Retraining SKIPPED (DISABLE_ML_TRAINING=true)")
            else:
                logger.info("Step 1/4: Starting retraining...")
                training_result = await orchestrator.run_training_pipeline(
                    league_ids=leagues,
                    days_back=365
                )
                accuracy = getattr(training_result, 'accuracy', 0)
                logger.info(f"Retraining completed. Accuracy: {accuracy:.2%}")
                
                # Update Unified Cache if we actually trained
                try:
                    orchestrator = get_ml_training_orchestrator()
                    history_limit = 500
                    display_history = training_result.match_history[-history_limit:] if len(training_result.match_history) > history_limit else training_result.match_history
                    
                    training_data = {
                        "matches_processed": training_result.matches_processed,
                        "correct_predictions": training_result.correct_predictions,
                        "accuracy": training_result.accuracy,
                        "total_bets": training_result.total_bets,
                        "roi": training_result.roi,
                        "profit_units": training_result.profit_units,
                        "market_stats": training_result.market_stats,
                        "match_history": [h.model_dump() if hasattr(h, 'model_dump') else h for h in display_history],
                        "roi_evolution": training_result.roi_evolution,
                        "pick_efficiency": training_result.pick_efficiency,
                        "team_stats": training_result.team_stats,
                        "global_averages": getattr(training_result, 'global_averages', {})
                    }
                    cache.set(orchestrator.CACHE_KEY_RESULT, training_data, ttl_seconds=cache.TTL_TRAINING)
                    logger.info(f"Unified Cache updated with training results.")
                except Exception as e:
                    logger.error(f"Failed to update unified cache: {e}")
                
                del training_result
                gc.collect()

            # 2. PRE-CACHE LEAGUES
            logger.info("Step 2/4: Pre-caching leagues...")
            try:
                from src.application.use_cases.use_cases import GetLeaguesUseCase
                leagues_use_case = GetLeaguesUseCase(data_sources)
                leagues_result = await leagues_use_case.execute()
                cache.set("leagues:all", leagues_result.model_dump(), cache.TTL_LEAGUES)
                del leagues_result
                gc.collect()
            except Exception as e:
                logger.warning(f"Failed to pre-cache leagues: {e}")

            # 3. MASSIVE INFERENCE
            logger.info("Step 3/4: Iterative inference...")
            use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service)
            
            leagues_processed = 0
            for league_id in self._get_league_iterator(LEAGUES_METADATA):
                try:
                    # Execute inference for league
                    predictions_dto = await use_case.execute(league_id, limit=50)
                    
                    # Unified Cache Key
                    league_cache_key = f"forecasts:league_{league_id}"
                    
                    # 1. Ephemeral Cache
                    cache.set(league_cache_key, predictions_dto.dict(), cache.TTL_FORECASTS)
                    
                    # 2. Persistent Storage (PostgreSQL)
                    if persistence_repo:
                        persistence_repo.save_training_result(league_cache_key, predictions_dto.dict())
                    
                    # Store individual match forecast if needed
                    for match_pred in predictions_dto.predictions:
                        match_key = f"forecasts:match_{match_pred.match.id}"
                        cache.set(match_key, match_pred.dict(), cache.TTL_FORECASTS)
                        # Optional: persist individual matches? (Maybe overkill if league is persisted)
                    
                    del predictions_dto
                    gc.collect()
                    leagues_processed += 1
                    await asyncio.sleep(0.5) 
                except Exception as e:
                    logger.error(f"Error processing league {league_id}: {str(e)}")
                    gc.collect()
            
            # 4. AUDIT
            logger.info("Step 4/4: Post-execution audit...")
            try:
                audit_service = get_audit_service()
                await audit_service.audit_and_fix(fix_missing=True)
            except Exception as e:
                logger.error(f"Audit failed: {e}")
                       
        except Exception as e:
            logger.error(f"CRITICAL Error during orchestrated job: {str(e)}", exc_info=True)
            gc.collect()
        finally:
            self._job_in_progress = False
            gc.collect()
    
    def start(self, run_immediate: bool = False):
        """Start the scheduler with daily job at 06:00 AM Colombia time."""
        try:
            self.scheduler.add_job(
                self.run_daily_orchestrated_job,
                trigger=CronTrigger(hour=6, minute=0, timezone=COLOMBIA_TZ),
                id='daily_orchestrated_job',
                name='Daily Orchestrated Job at 06:00 AM COT',
                replace_existing=True,
                max_instances=1
            )
            
            # Secondary Audit Job at 08:00 AM
            self.scheduler.add_job(
                self.run_audit_only_job,
                trigger=CronTrigger(hour=8, minute=0, timezone=COLOMBIA_TZ),
                id='daily_audit_job',
                name='Daily Data Audit at 08:00 AM COT',
                replace_existing=True
            )
            
            self.scheduler.start()
            logger.info("Scheduler started.")
            
            if run_immediate:
                logger.info("Triggering immediate job execution...")
                asyncio.create_task(self.run_daily_orchestrated_job())
            
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
