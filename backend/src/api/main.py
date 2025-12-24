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


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
    
    # Start the scheduler for daily training (Immediate run on deployment)
    from src.scheduler import get_scheduler
    scheduler = get_scheduler()
    scheduler.start(run_immediate=True)
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
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
    return HealthResponseDTO(
        status="healthy",
        version=APP_VERSION,
        timestamp=datetime.utcnow(),
    )


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
