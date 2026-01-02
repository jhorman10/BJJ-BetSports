
import logging
import asyncio
from typing import List, Optional, Dict
from datetime import datetime
from pytz import timezone
from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
from src.infrastructure.cache.cache_service import CacheService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.repositories.persistence_repository import PersistenceRepository

logger = logging.getLogger(__name__)

class CacheWarmupService:
    """
    Service responsible for warming up the cache.
    Uses GetPredictionsUseCase to ensure consistency with the API.
    """
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        persistence_repository: Optional[PersistenceRepository] = None,
        background_processor: Optional[any] = None,
    ):
        self.use_case = GetPredictionsUseCase(
            data_sources=data_sources,
            prediction_service=prediction_service,
            statistics_service=statistics_service,
            persistence_repository=persistence_repository,
            background_processor=background_processor
        )

    async def warm_up_predictions(self, league_ids: Optional[List[str]] = None):
        """
        Warms up predictions for specific leagues or all priority leagues.
        """
        if not league_ids:
            # Default priority leagues
            league_ids = ['E0', 'SP1', 'D1', 'I1', 'F1', 'B1', 'N1', 'P1', 'T1']
            
        logger.info(f"🔥 Starting Unified Cache Warmup for {len(league_ids)} leagues...")
        
        # We process sequentially to avoid CPU/RAM spikes on low-resource servers
        for league_id in league_ids:
            try:
                logger.info(f"🔥 Warming up league: {league_id}")
                # Execute handles Cache -> Persistence -> Real-time logic
                await self.use_case.execute(league_id, limit=30)
                # Small sleep to yield to other tasks
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Failed to warm up league {league_id}: {e}")
                
        logger.info("🔥 Cache Warmup Complete.")
