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
    summary="Get AI-suggested picks for a match",
    description="""
    Get AI-suggested betting picks for a specific match.
    
    The picks are prioritized based on:
    - Historical performance (corners and cards have higher priority than goals)
    - Team statistics and form
    - Low-scoring context penalties
    - VA handicap recommendations for dominant teams
    
    Each pick includes:
    - Probability (0-1)
    - Confidence level (high/medium/low)
    - Risk level (1-5)
    - Reasoning explanation
    """,
)
async def get_suggested_picks(
    match_id: str,
    data_sources=Depends(get_data_sources),
    prediction_service=Depends(get_prediction_service),
    statistics_service=Depends(get_statistics_service),
    learning_service=Depends(get_learning_service),
) -> MatchSuggestedPicksDTO:
    """Get AI-suggested picks for a match."""
    use_case = GetSuggestedPicksUseCase(
        data_sources=data_sources,
        prediction_service=prediction_service,
        statistics_service=statistics_service,
        learning_service=learning_service,
    )
    
    result = await use_case.execute(match_id)
    
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Match {match_id} not found or no data available"
        )
    
    return result


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
