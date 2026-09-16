from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from src.api.schemas.auxiliary import (
    BettingFeedbackRequest,
    BettingFeedbackResponse,
    LearningStatsResponse,
    MatchSuggestedPicksResponse,
)
from src.api.utils.serializers import _utc_now_iso
from src.application.dtos.dtos import BettingFeedbackRequestDTO
from src.application.use_cases.suggested_picks_use_case import (
    GetSuggestedPicksUseCase,
    RegisterFeedbackUseCase,
)
from src.dependencies import (
    get_async_learning_service,
    get_cache_service,
    get_data_sources,
    get_learning_service,
    get_prediction_service,
    get_statistics_service,
)
from src.domain.services.learning_service import LearningService

router = APIRouter(prefix="/api/v1/suggested-picks", tags=["suggested-picks"])


@router.get("/match/{match_id}", response_model=MatchSuggestedPicksResponse)
async def get_suggested_picks(
    match_id: str,
    data_sources: Any = Depends(get_data_sources),
    prediction_service: Any = Depends(get_prediction_service),
    statistics_service: Any = Depends(get_statistics_service),
    learning_service: LearningService = Depends(get_async_learning_service),
    cache_service: Any = Depends(get_cache_service),
) -> MatchSuggestedPicksResponse:
    """Generate suggested picks using the real use case and services."""
    use_case = GetSuggestedPicksUseCase(
        data_sources,
        prediction_service,
        statistics_service,
        learning_service,
        cache_service,
    )
    dto = await use_case.execute(match_id)
    if not dto:
        return MatchSuggestedPicksResponse(
            match_id=match_id,
            suggested_picks=[],
            combination_warning="No se pudieron generar sugerencias para este partido.",
            generated_at=_utc_now_iso(),
        )

    picks = [p.model_dump() for p in dto.suggested_picks] if dto.suggested_picks else []
    # Uniform pick shape: soccer picks carry the sport back-reference and their
    # match id so the cross-sport best-combination aggregator can consume them.
    for pick in picks:
        pick.setdefault("sport", "soccer")
        pick["match_id"] = dto.match_id
    generated_at = (
        dto.generated_at.isoformat()
        if hasattr(dto.generated_at, "isoformat")
        else _utc_now_iso()
    )
    return MatchSuggestedPicksResponse(
        match_id=dto.match_id,
        suggested_picks=picks,
        combination_warning=dto.combination_warning,
        highlights_url=dto.highlights_url,
        real_time_odds=dto.real_time_odds,
        generated_at=generated_at,
    )


@router.post("/feedback", response_model=BettingFeedbackResponse)
def register_feedback(
    payload: BettingFeedbackRequest,
    learning_service: LearningService = Depends(get_learning_service),
) -> BettingFeedbackResponse:
    """Register feedback using the injected application learning service."""
    dto = BettingFeedbackRequestDTO(**payload.model_dump())
    use_case = RegisterFeedbackUseCase(learning_service)
    resp = use_case.execute(dto)
    return BettingFeedbackResponse(
        success=resp.success,
        message=resp.message,
        market_type=resp.market_type,
        new_confidence_adjustment=resp.new_confidence_adjustment,
    )


@router.get("/learning-stats", response_model=LearningStatsResponse)
def get_learning_stats(
    learning_service: LearningService = Depends(get_learning_service),
) -> LearningStatsResponse:
    stats = learning_service.get_all_stats()
    performance_list: list[dict] = []
    last_updated = None
    for perf in stats.values():
        last_updated = (
            perf.last_updated
            if last_updated is None or perf.last_updated > last_updated
            else last_updated
        )
        performance_list.append(
            {
                "market_type": perf.market_type,
                "total_predictions": perf.total_predictions,
                "correct_predictions": perf.correct_predictions,
                "success_rate": perf.success_rate,
                "avg_odds": perf.avg_odds,
                "total_profit_loss": perf.total_profit_loss,
                "confidence_adjustment": perf.confidence_adjustment,
                "last_updated": (
                    perf.last_updated.isoformat() if perf.last_updated else None
                ),
            }
        )

    total_count = (
        sum(p["total_predictions"] for p in performance_list) if performance_list else 0
    )
    return LearningStatsResponse(
        market_performances=performance_list,
        total_feedback_count=total_count,
        last_updated=last_updated.isoformat() if last_updated else None,
    )
