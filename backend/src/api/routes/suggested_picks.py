"""
Suggested Picks API Routes Module

Contains endpoints for AI-suggested picks and betting feedback.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException

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
    summary="Get AI-suggested picks for a match (Pre-calculated)",
    description="Returns AI-suggested betting picks for a match. Data is pre-calculated daily at 06:00 AM.",
)
async def get_suggested_picks(
    match_id: str,
) -> MatchSuggestedPicksDTO:
    """Get AI-suggested picks for a match from Redis."""
    from src.infrastructure.cache.cache_service import get_cache_service
    from datetime import datetime
    
    cache = get_cache_service()
    # Key format: forecasts:match_{match_id}
    cache_key = f"forecasts:match_{match_id}"
    
    cached_match = cache.get(cache_key)
    if cached_match:
        # MatchPredictionDTO contains both 'match' and 'prediction'
        # The 'prediction' field contains 'suggested_picks' which we need for MatchSuggestedPicksDTO
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
    
    raise HTTPException(
        status_code=404,
        detail=f"No pre-calculated picks available for match {match_id}. Ensure the daily job has run."
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
