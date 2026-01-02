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
    summary="Get predictions for a league",
    description="Returns match predictions for upcoming matches. Priorities: Ephemeral Cache -> Persistent DB -> Real-time Calculation.",
)
async def get_league_predictions(
    league_id: str,
) -> PredictionsResponseDTO:
    """Get predictions for a league with multi-layer fallback."""
    from src.api.dependencies import (
        get_data_sources, get_prediction_service, 
        get_background_processor, get_statistics_service,
        get_persistence_repository
    )
    from src.application.use_cases.use_cases import GetPredictionsUseCase
    
    try:
        # GetPredictionsUseCase now handles Cache -> DB logic internally
        use_case = GetPredictionsUseCase(
            data_sources=get_data_sources(),
            prediction_service=get_prediction_service(),
            statistics_service=get_statistics_service(),
            persistence_repository=get_persistence_repository(),
            background_processor=get_background_processor()
        )
        
        result = await use_case.execute(league_id, limit=30)
        
        if not result.predictions:
            logger.warning(f"No predictions found for {league_id}")
            # We still return the empty DTO rather than 404 to avoid frontend errors
            # but we could raise 404 if preferred.
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch predictions for {league_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error serving predictions for {league_id}: {str(e)}"
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
    """Get pre-calculated prediction for a specific match from local cache."""
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
