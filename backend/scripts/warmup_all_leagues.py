
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.append(os.getcwd())

from src.api.dependencies import (
    get_data_sources, get_prediction_service, 
    get_statistics_service, get_persistence_repository,
    get_background_processor
)
from src.domain.services.cache_warmup_service import CacheWarmupService
from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting manual massive warmup for ALL leagues...")
    
    warmup_service = CacheWarmupService(
        data_sources=get_data_sources(),
        prediction_service=get_prediction_service(),
        statistics_service=get_statistics_service(),
        persistence_repository=get_persistence_repository(),
        background_processor=get_background_processor()
    )
    
    all_leagues = list(LEAGUES_METADATA.keys())
    logger.info(f"Found {len(all_leagues)} leagues to process: {all_leagues}")
    
    await warmup_service.warm_up_predictions(all_leagues)
    
    logger.info("✅ Massive warmup complete. All picks are now persisted in PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(main())
