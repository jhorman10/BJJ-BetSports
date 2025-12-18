"""
Predictions Router

API endpoints for getting match predictions.
"""

from fastapi import APIRouter, HTTPException, Query

from src.application.dtos.dtos import (
    PredictionsResponseDTO,
    MatchPredictionDTO,
    ErrorResponseDTO,
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
    description="Returns match predictions for upcoming matches in a specific league.",
)
async def get_league_predictions(
    league_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum matches to return"),
) -> PredictionsResponseDTO:
    """Get predictions for all upcoming matches in a league."""
    from src.application.use_cases.use_cases import GetPredictionsUseCase, DataSources
    from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
    
    if league_id not in LEAGUES_METADATA:
        raise HTTPException(
            status_code=404,
            detail=f"League not found: {league_id}. Available leagues: {list(LEAGUES_METADATA.keys())}",
        )
    
    data_sources = get_data_sources()
    prediction_service = get_prediction_service()
    use_case = GetPredictionsUseCase(data_sources, prediction_service)
    
    try:
        return await use_case.execute(league_id, limit)
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
    # For now, this endpoint requires implementing match lookup
    # which would need to be added to the use cases
    raise HTTPException(
        status_code=501,
        detail="Match-specific predictions not yet implemented. Use /predictions/league/{league_id} instead.",
    )
