"""
Football Betting Prediction Bot - FastAPI Application

Main entry point for the backend API.
This module configures the FastAPI app, middleware, and routes.
"""

import os
import logging
import warnings
from contextlib import asynccontextmanager
from datetime import datetime

# Suppress DeprecationWarnings from utcnow() used in external libraries or old code
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*utcnow.*")

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
- **Football-Data.org** - Fixtures, team data and standings (requires API key)

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
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION}")
    
    # Check if running in API-only mode (production)
    api_only_mode = os.getenv("API_ONLY_MODE", "false").lower() == "true"
    
    if api_only_mode:
        logger.info("🚀 Starting in API-ONLY MODE (Lightweight)")
        logger.info("   - ML computations: DISABLED")
        logger.info("   - Background tasks: DISABLED")
        logger.info("   - Data source: PostgreSQL only")
        logger.info("   - Memory footprint: ~100-150MB")
    else:
        logger.info("🔬 Starting in FULL MODE (Development)")
        logger.info("   - ML computations: ENABLED")
        logger.info("   - Background tasks: ENABLED")
        logger.info("   - Memory footprint: ~512MB+")
    
    # 1. Startup Logic wrapped in try-except for resilience
    try:
        from src.infrastructure.cache.cache_service import get_cache_service
        from src.utils.time_utils import get_today_str, get_current_time
        import asyncio
        
        cache = get_cache_service()
        
        # 1.1 Local Cache Refresh (Requested by User)
        # Allows refreshing the local cache automatically on every server restart (e.g. during development)
        if os.getenv("CLEAR_CACHE_ON_START", "false").lower() == "true":
            logger.info("🧹 CLEAR_CACHE_ON_START is true. Purging all cache layers...")
            cache.clear()
            logger.info("✓ Cache purged successfully.")
        
        # Log basic config status
        if api_only_mode:
            logger.info("📡 Application starting in API-ONLY mode (reads from PostgreSQL).")
        else:
            logger.info("📡 Application starting in Persistent-SQL mode (PostgreSQL + DiskCache).")

        if os.getenv("FOOTBALL_DATA_ORG_KEY"):
            logger.info("✓ Football-Data.org configured")
        else:
            logger.warning("⚠ FOOTBALL_DATA_ORG_KEY not configured (crítico para fixtures)")

        if os.getenv("THE_ODDS_API_KEY"):
            logger.info("✓ The Odds API configured")
        else:
            logger.warning("⚠ THE_ODDS_API_KEY not configured (opcional para cuotas)")

        # Skip heavy initialization in API-only mode
        if not api_only_mode:
            # Initialize CacheWarmupService
            from src.domain.services.cache_warmup_service import CacheWarmupService
            from src.api.dependencies import (
                get_data_sources, get_prediction_service,
                get_statistics_service, get_persistence_repository,
                get_background_processor
            )
            
            warmup_service = CacheWarmupService(
                data_sources=get_data_sources(),
                prediction_service=get_prediction_service(),
                statistics_service=get_statistics_service(),
                persistence_repository=get_persistence_repository(),
                background_processor=get_background_processor()
            )
            
            # Run warmup in background
            # Consolidate background tasks to run SEQUENTIALLY to save RAM
            async def background_tasks_orchestrator():
                try:
                    import gc
                logger.info("⏳ Waiting 15s before heavy background task cycle...")
                await asyncio.sleep(15)
                
                # 0. Initialize Persistence AFTER server is up
                persistence_repo = get_persistence_repository()
                try:
                    logger.info("📡 Initializing database persistence in background...")
                    persistence_repo.create_tables()
                    logger.info("✓ Database tables verified/created.")
                except Exception as db_e:
                    logger.error(f"Failed to initialize DB: {db_e}")

                # Check forecasts (Unified key)
                sample_key = "forecasts:league_E0"
                
                # Check ephemeral cache first
                has_cached_forecasts = cache.get(sample_key) is not None
                
                # If not in ephemeral, check persistent DB (Standard for Render)
                if not has_cached_forecasts:
                    persistence = get_persistence_repository()
                    if persistence.get_training_result(sample_key):
                        has_cached_forecasts = True
                        logger.info("✓ Persistent forecasts found in DB. Skipping heavy startup tasks.")
                
                # 1. Daily Orchestrated Job (Training + Inference)
                # WARNING: Extremely heavy on RAM. Skip by default on Render Free unless forced.
                is_render = os.getenv("RENDER") == "true" or "render" in os.getenv("RENDER_EXTERNAL_HOSTNAME", "").lower()
                disable_training_env = os.getenv("DISABLE_ML_TRAINING", "false").lower() == "true"
                low_memory = os.getenv("LOW_MEMORY_MODE", "false").lower() == "true"
                
                if not has_cached_forecasts and (not disable_training_env and not is_render and not low_memory):
                    logger.info("🚀 Starting Daily Orchestrated Job (Sequenced)...")
                    await scheduler.run_daily_orchestrated_job()
                    logger.info("✓ Daily Orchestrated Job complete. Cleaning memory...")
                    gc.collect()
                    await asyncio.sleep(5)
                elif not has_cached_forecasts and (is_render or low_memory):
                    logger.warning("️⚠️ Cold startup on Render/Low-Memory detected. Skipping heavy training to avoid OOM.")
                    logger.info("💡 Tip: Use GitHub Actions to populate the database periodically.")
                
                # 2. Cache Warmup (Lookahead) - Sequentially
                logger.info("🚀 Starting Cache Warmup (Sequenced)...")
                # We prioritize the top 3 leagues first to give faster UI feedback without spiking RAM
                priority_leagues = ['E0', 'SP1', 'D1']
                await warmup_service.warm_up_predictions(league_ids=priority_leagues)
                
                # If we are NOT in render or low memory, we can do the full warmup
                if not is_render and not low_memory:
                    asyncio.create_task(warmup_service.warm_up_predictions())
                else:
                    logger.info("ℹ️ Full background warmup skipped to conserve RAM on Render.")
                
                logger.info("✓ Initial Cache Warmup complete. System ready.")
                gc.collect()
                
            except Exception as e:
                logger.error(f"Background orchestrator failure: {e}")

            # Trigger the sequential orchestration
            asyncio.create_task(background_tasks_orchestrator())
            
            # Scheduler just for the CRON, no immediate run here (orchestrator handles first run)
            from src.scheduler import get_scheduler
            scheduler = get_scheduler()
            scheduler.start(run_immediate=False)
            logger.info("✓ Daily training scheduler configured (06:00 AM Colombia time)")
        else:
            logger.info("⏭️  Skipping background tasks (API-ONLY mode)")
            logger.info("💡 Predictions will be read from database (populated by GitHub Actions)")

    except Exception as e:
        logger.error(f"FAILURE: Lifespan startup error: {e}", exc_info=True)

    yield
    
    # 2. Shutdown Logic wrapped in try-except
    try:
        logger.info("Shutting down...")
        if not api_only_mode:
            from src.scheduler import get_scheduler
            scheduler_to_stop = get_scheduler()
            scheduler_to_stop.shutdown()
            logger.info("✓ Scheduler shutdown complete")
        else:
            logger.info("✓ API-only mode shutdown (no scheduler to stop)")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


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
base_origins = [
    "http://localhost:3000", 
    "http://localhost:5173", 
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "https://football-prediction-frontend-nz9r.onrender.com"
]
env_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
# Combine, remove duplicates, and ensure NO trailing slashes
all_origins = list(set([o.rstrip("/") for o in base_origins + env_origins if o]))

# Added allow_origin_regex for flexibility in Render subdomains
app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins + ["*"] if os.getenv("DEBUG") == "true" else all_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=r"https://.*\.onrender\.com", 
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
    description="Check ephemeral cache status and sampled keys.",
)
async def cache_status():
    """Get cache status for debugging."""
    from src.infrastructure.cache.cache_service import get_cache_service
    
    cache = get_cache_service()
    
    # Get forecast keys (Best effort)
    forecast_keys = []
    # Note: DiskCache doesn't have a direct 'keys' method like Redis, 
    # but we can check the length of memory cache for a sample.
    memory_sample = list(cache._memory_cache.keys())[:10]
    
    return {
        "persistence_layer": "PostgreSQL",
        "ephemeral_layer": "Memory + DiskCache",
        "cached_items_sample": memory_sample,
        "cache_hits": getattr(cache, '_hits', 0),
        "cache_misses": getattr(cache, '_misses', 0),
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
app.include_router(matches.router, prefix="/api/v1")
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
