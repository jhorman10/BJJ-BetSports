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
    get_cache_service,
)
from src.infrastructure.cache.cache_service import CacheService
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
    cache_service: CacheService = Depends(get_cache_service),
) -> MatchSuggestedPicksDTO:
    """Get AI-suggested picks for a match (Cache -> Live)."""
    # 1. Try Cache First (from warmup service or live predictions)
    try:
        cache = cache_service
        
        # Check both potential keys for consistency
        # 'forecasts:' is used by batch warmup, 'predictions:' by live updates
        keys_to_try = [f"forecasts:match_{match_id}", f"predictions:{match_id}"]
        
        for cache_key in keys_to_try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"✅ Cache hit for match {match_id} (key: {cache_key})")
                if isinstance(cached_data, dict):
                    return MatchSuggestedPicksDTO(**cached_data)
                return cached_data
    except Exception as e:
        logger.warning(f"Cache lookup failed for {match_id}: {e}")

    # 2. Generate On-Demand (cache miss)
    logger.info(f"⚠️ Cache miss for match {match_id}, generating picks...")
    use_case = GetSuggestedPicksUseCase(
        data_sources=data_sources,
        prediction_service=prediction_service,
        statistics_service=statistics_service,
        learning_service=learning_service,
        cache_service=cache_service,
    )
    
    result = await use_case.execute(match_id)
    if result:
        # Cache the result for future requests (12h TTL) using both keys for consistency
        try:
            cache = cache_service
            # We cache in both namespaces to ensure future hits regardless of endpoint entry point
            for key in [f"forecasts:match_{match_id}", f"predictions:{match_id}"]:
                cache.set(key, result.model_dump(), ttl_seconds=3600*12)
            logger.info(f"✅ Cached generated picks for {match_id} in multiple namespaces (12h TTL)")
        except Exception as cache_err:
            logger.warning(f"Failed to cache picks for {match_id}: {cache_err}")
        
        return result
        
    # If we still have no result (extreme case where match ID is invalid and not reconstructible)
    # we return a minimal error but try to avoid raw 404s if possible.
    return result # Will be None if everything failed


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
