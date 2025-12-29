"""
Suggested Picks API Routes Module

Contains endpoints for AI-suggested picks and betting feedback.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import ORJSONResponse

from src.api.dependencies import (
    get_data_sources,
    get_prediction_service,
    get_statistics_service,
    get_learning_service,
)
from src.application.use_cases.suggested_picks_use_case import (
    GetSuggestedPicksUseCase,
    RegisterFeedbackUseCase,
    GetLearningStatsUseCase,
)
from src.application.dtos.dtos import (
    MatchSuggestedPicksDTO,
    BettingFeedbackRequestDTO,
    BettingFeedbackResponseDTO,
    LearningStatsResponseDTO,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/suggested-picks",
    tags=["Suggested Picks"],
)


@router.get(
    "/match/{match_id}",
    response_model=MatchSuggestedPicksDTO,
    response_class=ORJSONResponse,
    summary="Get AI-suggested picks for a match",
    description="Returns AI-suggested betting picks for a match. Checks cache first, then generates on demand.",
)
async def get_suggested_picks(
    match_id: str,
    data_sources=Depends(get_data_sources),
    prediction_service=Depends(get_prediction_service),
    statistics_service=Depends(get_statistics_service),
    learning_service=Depends(get_learning_service),
) -> MatchSuggestedPicksDTO:
    """Get AI-suggested picks for a match (Cache -> Live)."""
    from src.infrastructure.cache.cache_service import get_cache_service
    from datetime import datetime
    
    # 1. Try Cache
    try:
        cache = get_cache_service()
        cache_key = f"forecasts:match_{match_id}"
        cached_match = cache.get(cache_key)
        
        if cached_match:
            if isinstance(cached_match, dict):
                from src.application.dtos.dtos import MatchPredictionDTO
                match_pred = MatchPredictionDTO(**cached_match)
            else:
                match_pred = cached_match
                
            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=match_pred.prediction.suggested_picks,
                generated_at=match_pred.prediction.created_at or datetime.utcnow()
            )
    except Exception as e:
        logger.warning(f"Cache lookup failed for {match_id}: {e}")

    # 2. Generate On-Demand
    use_case = GetSuggestedPicksUseCase(
        data_sources=data_sources,
        prediction_service=prediction_service,
        statistics_service=statistics_service,
        learning_service=learning_service,
    )
    
    result = await use_case.execute(match_id)
    if result:
        return result
        
    raise HTTPException(
        status_code=404,
        detail=f"Match {match_id} not found or insufficient data to generate picks."
    )


@router.post(
    "/feedback",
    response_model=BettingFeedbackResponseDTO,
    summary="Register betting feedback",
    description="""
    Register the outcome of a bet to improve future predictions.
    
    This enables continuous learning by:
    - Tracking success rates per market type
    - Adjusting confidence weights based on performance
    - Penalizing consistently failing market types
    
    Feedback is persisted and used to improve future suggested picks.
    """,
)
async def register_feedback(
    request: BettingFeedbackRequestDTO,
    learning_service=Depends(get_learning_service),
) -> BettingFeedbackResponseDTO:
    """Register betting feedback for continuous learning."""
    use_case = RegisterFeedbackUseCase(learning_service=learning_service)
    return use_case.execute(request)


@router.get(
    "/learning-stats",
    response_model=LearningStatsResponseDTO,
    summary="Get learning statistics",
    description="""
    Get statistics on how the model has learned from feedback.
    
    Returns:
    - Performance metrics for each market type
    - Total feedback count
    - Success rates and confidence adjustments
    """,
)
async def get_learning_stats(
    learning_service=Depends(get_learning_service),
) -> LearningStatsResponseDTO:
    """Get learning statistics from feedback."""
    use_case = GetLearningStatsUseCase(learning_service=learning_service)
    return use_case.execute()
