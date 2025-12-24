"""
Predictions Router

API endpoints for getting match predictions.
"""

from fastapi import APIRouter, HTTPException, Query

from src.application.dtos.dtos import (
    PredictionsResponseDTO,
    MatchPredictionDTO,
    ErrorResponseDTO,
    SortBy,
)
from src.api.dependencies import get_data_sources, get_prediction_service


router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get(
    "/league/{league_id}",
    response_model=PredictionsResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "League not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get predictions for a league",
    description="Returns match predictions for upcoming matches in a specific league. Results can be sorted by confidence, date, or probability.",
)
async def get_league_predictions(
    league_id: str,
    limit: int = Query(default=20, ge=1, le=50, description="Maximum matches to return"),
    sort_by: SortBy = Query(default=SortBy.CONFIDENCE, description="Field to sort by"),
    sort_desc: bool = Query(default=True, description="Sort in descending order (highest first)"),
) -> PredictionsResponseDTO:
    """Get predictions for all upcoming matches in a league."""
    from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
    from src.infrastructure.cache.cache_service import get_cache_service
    
    if league_id not in LEAGUES_METADATA:
        raise HTTPException(
            status_code=404,
            detail=f"League not found: {league_id}. Available leagues: {list(LEAGUES_METADATA.keys())}",
        )
    
    # Check cache first
    cache = get_cache_service()
    cache_key = f"predictions:{league_id}:{limit}:{sort_by.value}:{sort_desc}"
    cached_result = cache.get(cache_key)
    if cached_result:
        return cached_result
    
    data_sources = get_data_sources()
    prediction_service = get_prediction_service()
    from src.api.dependencies import get_statistics_service
    statistics_service = get_statistics_service()
    
    use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service)
    
    try:
        result = await use_case.execute(league_id, limit)
        
        # Apply sorting
        # For dates: ascending (closest event first)
        # For confidence/probability: descending (highest first)
        if result.predictions:
            if sort_by == SortBy.CONFIDENCE:
                result.predictions.sort(
                    key=lambda x: x.prediction.confidence,
                    reverse=True  # Highest confidence first
                )
            elif sort_by == SortBy.DATE:
                result.predictions.sort(
                    key=lambda x: x.match.match_date,
                    reverse=False  # Closest date first (ascending)
                )
            elif sort_by == SortBy.HOME_PROBABILITY:
                result.predictions.sort(
                    key=lambda x: x.prediction.home_win_probability,
                    reverse=True  # Highest probability first
                )
            elif sort_by == SortBy.AWAY_PROBABILITY:
                result.predictions.sort(
                    key=lambda x: x.prediction.away_win_probability,
                    reverse=True  # Highest probability first
                )
        
        # Cache the result for 5 minutes
        cache.set(cache_key, result, cache.TTL_PREDICTIONS)
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/match/{match_id}",
    response_model=MatchPredictionDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Match not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal server error"},
    },
    summary="Get prediction for a specific match",
    description="Returns prediction for a specific match by ID.",
)
async def get_match_prediction(match_id: str) -> MatchPredictionDTO:
    """Get prediction for a specific match."""
    from src.application.use_cases.use_cases import GetMatchDetailsUseCase
    from src.api.dependencies import get_statistics_service
    
    data_sources = get_data_sources()
    prediction_service = get_prediction_service()
    statistics_service = get_statistics_service()
    
    use_case = GetMatchDetailsUseCase(data_sources, prediction_service, statistics_service)
    
    result = await use_case.execute(match_id)
    if not result:
        raise HTTPException(status_code=404, detail="Match not found")
        
    return result
