from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
import logging

from ...domain.entities.parley import Parley
from ...application.use_cases.get_parleys_use_case import GetParleysUseCase, GetParleysRequest
from ...application.use_cases.use_cases import GetPredictionsUseCase
from src.api.dependencies import get_prediction_service, get_parley_service, get_statistics_service, get_data_sources

router = APIRouter(prefix="/parleys", tags=["parleys"])
logger = logging.getLogger(__name__)

@router.get("/", response_model=List[Parley])
async def get_suggested_parleys(
    min_probability: float = Query(0.60, ge=0.5, le=1.0, description="Minimum probability for individual picks"),
    min_picks: int = Query(3, ge=2, le=10, description="Minimum number of picks per parley"),
    max_picks: int = Query(5, ge=2, le=10, description="Maximum number of picks per parley"),
    count: int = Query(3, ge=1, le=10, description="Number of suggested parleys to return"),
    prediction_service = Depends(get_prediction_service),
    statistics_service = Depends(get_statistics_service),
    data_sources = Depends(get_data_sources),
    parley_service = Depends(get_parley_service)
):
    """
    Get suggested parleys (accumulators) based on AI predictions.
    """
    try:
        if min_picks > max_picks:
             raise HTTPException(status_code=400, detail="min_picks cannot be greater than max_picks")

        get_predictions_use_case = GetPredictionsUseCase(data_sources, prediction_service, statistics_service)
        use_case = GetParleysUseCase(get_predictions_use_case, parley_service)
        
        request = GetParleysRequest(
            min_probability=min_probability,
            min_picks=min_picks,
            max_picks=max_picks,
            count=count
        )
        
        parleys = await use_case.execute(request)

        return parleys
        
    except Exception as e:
        logger.error(f"Error generating parleys: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error generating parleys")
