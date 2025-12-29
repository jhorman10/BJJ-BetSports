"""
Football Betting Prediction Bot - FastAPI Application

Main entry point for the backend API.
This module configures the FastAPI app, middleware, and routes.
"""

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import leagues, predictions, matches, suggested_picks, parleys, learning
from src.application.dtos.dtos import HealthResponseDTO, ErrorResponseDTO

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


from src.utils.time_utils import get_current_time
import time

# Custom logging implementation to use Colombia time
class ColombiaTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = get_current_time()
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%Y-%m-%d %H:%M:%S")
            s = "%s,%03d" % (t, record.msecs)
        return s

formatter = ColombiaTimeFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
handler.setFormatter(formatter)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.handlers = [handler]
logger = logging.getLogger(__name__)


# Application metadata
APP_TITLE = "Football Betting Prediction Bot"
APP_DESCRIPTION = """
🎯 **Football Match Prediction API**

This API provides football match predictions based on historical data,
statistical analysis, and machine learning models.

## Features

* 📊 **Historical Data Analysis** - Analyzes past match results
* 🎲 **Probability Calculations** - Uses Poisson distribution for goal predictions
* 📈 **Multiple Data Sources** - Aggregates data from multiple free sources
* ⚽ **Multiple Leagues** - Supports major European leagues

## Data Sources

- **Football-Data.co.uk** - Historical results and betting odds
- **API-Football** - Real-time fixtures (optional, requires API key)
- **Football-Data.org** - Team data and standings (optional, requires API key)

## Predictions Include

- Home Win / Draw / Away Win probabilities
- Over/Under 2.5 goals probability
- Expected goals for each team
- Confidence score
- Recommended bet

---
⚠️ **Educational purposes only** - Not for actual betting
"""
APP_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    logger.info("Initializing data sources...")
    
    # Check for API keys
    if os.getenv("API_FOOTBALL_KEY"):
        logger.info("✓ API-Football configured")
    else:
        logger.warning("⚠ API-Football not configured (optional)")
    
    if os.getenv("FOOTBALL_DATA_ORG_KEY"):
        logger.info("✓ Football-Data.org configured")
    else:
        logger.warning("⚠ Football-Data.org not configured (optional)")
    
    # Start the scheduler for daily training
    from src.scheduler import get_scheduler
    from src.infrastructure.cache.cache_service import get_cache_service
    from src.utils.time_utils import get_today_str, get_current_time
    
    scheduler = get_scheduler()
    cache = get_cache_service()
    
    # --- NEW: CACHE WARMUP SEQUENCE ---
    # We want to pre-calculate deep predictions for all upcoming matches
    # to avoid user wait times ("loading" spinners).
    
    from src.domain.services.cache_warmup_service import CacheWarmupService
    from src.api.dependencies import (
        get_data_sources, 
        get_prediction_service,
        get_statistics_service,
        get_learning_service
    )
    
    # Initialize services manually since we are outside request context
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
    
    # Run warmup in background so we don't block server startup
    import asyncio
    asyncio.create_task(warmup_service.warm_up_predictions(lookahead_days=7))
    logger.info("🚀 Background Cache Warmup Task Started for upcoming 7 days")
    
    # ----------------------------------
    
    # Check if we already have cached forecasts for today
    today_str = get_today_str()
    
    # Check for any cached forecasts (sample key pattern)
    sample_key = f"forecasts:league_E0:date_{today_str}"
    has_cached_forecasts = cache.get(sample_key) is not None
    
    if has_cached_forecasts:
        # Cache exists, start scheduler in background (normal operation)
        logger.info("✓ Cached forecasts found. Starting scheduler in background...")
        scheduler.start(run_immediate=False)
    else:
        # No cache - run job synchronously and wait for completion
        logger.info("⚠ No cached forecasts found. Running initial job synchronously...")
        logger.info("   This may take a few minutes on first deployment...")
        
        # Start scheduler without immediate run first
        scheduler.start(run_immediate=False)
        
        # Run the job and WAIT for it to complete
        await scheduler.run_daily_orchestrated_job()
        logger.info("✓ Initial cache population complete")
    
    logger.info("✓ Daily training scheduler started (06:00 AM Colombia time)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    scheduler.shutdown()
    logger.info("✓ Scheduler shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# Configure CORS
# Explicitly include loopback IPs which browsers sometimes use instead of 'localhost'
base_origins = [
    "http://localhost:3000", 
    "http://localhost:5173", 
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174"
]
cors_origins = os.getenv("CORS_ORIGINS", "").split(",")
# Combine and remove empty/duplicates
all_origins = list(set([o for o in base_origins + cors_origins if o]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponseDTO(
            error="internal_server_error",
            message="An unexpected error occurred",
            details={"path": str(request.url)},
        ).model_dump(),
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponseDTO,
    tags=["Health"],
    summary="Health check",
    description="Check if the API is running and healthy.",
)
async def health_check() -> HealthResponseDTO:
    """Health check endpoint."""
    from src.utils.time_utils import get_current_time
    return HealthResponseDTO(
        status="healthy",
        version=APP_VERSION,
        timestamp=get_current_time(),
    )


# Cache status endpoint
@app.get(
    "/cache/status",
    tags=["Health"],
    summary="Cache status",
    description="Check Redis cache connection and cached forecasts.",
)
async def cache_status():
    """Get cache status for debugging."""
    from src.infrastructure.cache.cache_service import get_cache_service
    
    cache = get_cache_service()
    redis_connected = cache.redis.is_connected if cache.redis else False
    
    # Get forecast keys
    forecast_keys = []
    if redis_connected:
        forecast_keys = cache.redis.keys("forecasts:*")
    
    return {
        "redis_connected": redis_connected,
        "cached_forecasts_count": len(forecast_keys),
        "sample_keys": forecast_keys[:10] if forecast_keys else [],
        "cache_hits": cache._hits,
        "cache_misses": cache._misses,
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API Information",
    description="Get basic API information and links.",
)
async def root():
    """Root endpoint with API info."""
    return {
        "name": APP_TITLE,
        "version": APP_VERSION,
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "leagues": "/api/v1/leagues",
            "predictions": "/api/v1/predictions/league/{league_id}",
        },
    }


# Include routers
app.include_router(leagues.router, prefix="/api/v1")
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1/matches")
app.include_router(suggested_picks.router, prefix="/api/v1")
app.include_router(parleys.router, prefix="/api/v1")
app.include_router(learning.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
