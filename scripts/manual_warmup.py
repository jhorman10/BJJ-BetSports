import asyncio
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.getcwd(), 'backend', '.env'))

from src.infrastructure.cache.cache_service import get_cache_service
from src.domain.services.cache_warmup_service import CacheWarmupService
from src.api.dependencies import (
    get_data_sources, 
    get_prediction_service,
    get_statistics_service,
    get_learning_service
)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def manual_warmup():
    logger.info("--- MANUAL CACHE WARMUP START ---")
    
    # Initialize services
    cache = get_cache_service()
    if not cache.redis:
        logger.error("Redis not connected. Exiting.")
        return

    ds = get_data_sources()
    ps = get_prediction_service()
    ss = get_statistics_service()
    ls = get_learning_service()
    
    warmup_service = CacheWarmupService(
        data_sources=ds,
        cache_service=cache,
        prediction_service=ps,
        statistics_service=ss,
        learning_service=ls
    )
    
    # Run Warmup
    await warmup_service.warm_up_predictions(lookahead_days=7)
    
    logger.info("--- MANUAL CACHE WARMUP COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(manual_warmup())
