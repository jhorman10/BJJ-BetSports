"""
Predictions Router

API endpoints for getting match predictions.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import ORJSONResponse

from src.application.dtos.dtos import (
    PredictionsResponseDTO,
    MatchPredictionDTO,
    ErrorResponseDTO,
    SortBy,
)
from src.api.dependencies import get_data_sources, get_prediction_service

import logging
logger = logging.getLogger(__name__)



router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/league/{league_id}",
    response_model=PredictionsResponseDTO,
    response_class=ORJSONResponse,
    responses={
        404: {"model": ErrorResponseDTO, "description": "League not found or no forecast available"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get predictions for a league (Pre-calculated)",
    description="Returns match predictions for upcoming matches in a specific league. Data is pre-calculated daily at 06:00 AM.",
)
async def get_league_predictions(
    league_id: str,
) -> PredictionsResponseDTO:
    """Get pre-calculated predictions for a league from Redis."""
    from src.infrastructure.cache.cache_service import get_cache_service
    from datetime import datetime, timedelta
    from pytz import timezone
    
    COLOMBIA_TZ = timezone('America/Bogota')
    today_str = datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d")
    
    # Key format: forecasts:league_{id}:date_{today}
    cache_key = f"forecasts:league_{league_id}:date_{today_str}"
    cache = get_cache_service()
    
    cached_result = cache.get(cache_key)
    
    # Fallback to yesterday's cache if today's is not available
    if not cached_result:
        yesterday_str = (datetime.now(COLOMBIA_TZ) - timedelta(days=1)).strftime("%Y-%m-%d")
        yesterday_key = f"forecasts:league_{league_id}:date_{yesterday_str}"
        cached_result = cache.get(yesterday_key)
        if cached_result:
            logger.info(f"Using yesterday's cache for {league_id} (today's not available yet)")
    
    if cached_result:
        # If it's a dict (from Redis), parse it back to DTO
        if isinstance(cached_result, dict):
            dto = PredictionsResponseDTO(**cached_result)
            # Only return if we actually have predictions
            if dto.predictions:
                return dto
            logger.warning(f"Cached data for {league_id} has 0 predictions. Ignoring cache and recalculating...")
        else:
            return cached_result
    
    # FALLBACK: Calculate predictions in real-time if no pre-calculated data
    logger.info(f"No pre-calculated data for {league_id}. Calculating in real-time...")
    
    from src.api.dependencies import get_data_sources, get_prediction_service, get_background_processor
    from src.domain.services.statistics_service import StatisticsService
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    
    try:
        data_sources = get_data_sources()
        prediction_service = get_prediction_service()
        statistics_service = StatisticsService()
        background_processor = get_background_processor()
        
        use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service, background_processor)
        result = await use_case.execute(league_id, limit=30)
        
        # Cache the result for future requests
        cache.set(cache_key, result.model_dump(), cache.TTL_PREDICTIONS)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to calculate predictions for {league_id}: {e}")
        raise HTTPException(
            status_code=404, 
            detail=f"No predictions available for league {league_id}. Error: {str(e)}"
        )



@router.get(
    "/match/{match_id}",
    response_model=MatchPredictionDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Match not found or no forecast available"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get prediction for a specific match (Pre-calculated)",
    description="Returns pre-calculated prediction for a specific match by ID.",
)
async def get_match_prediction(match_id: str) -> MatchPredictionDTO:
    """Get pre-calculated prediction for a specific match from Redis."""
    from src.infrastructure.cache.cache_service import get_cache_service
    
    cache = get_cache_service()
    # Key format: forecasts:match_{match_id}
    cache_key = f"forecasts:match_{match_id}"
    
    cached_match = cache.get(cache_key)
    if cached_match:
        if isinstance(cached_match, dict):
            return MatchPredictionDTO(**cached_match)
        return cached_match
        
    raise HTTPException(
        status_code=404, 
        detail=f"No pre-calculated forecast available for match {match_id}. Ensure the daily job has run."
    )
