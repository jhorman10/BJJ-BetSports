from __future__ import annotations

from fastapi import APIRouter, HTTPException
from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel, PredictionsResponse
from src.api.utils.serializers import _utc_now_iso
from src.domain.services.prediction_service import PredictionService
from src.infrastructure.repositories.async_mongo_adapter import (
    get_async_mongo_repository,
)

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/league/{league_id}", response_model=PredictionsResponse)
async def get_predictions_by_league(league_id: str) -> PredictionsResponse:
    repo = get_async_mongo_repository()
    docs = await repo.get_all_active_predictions()
    league = find_league(league_id)
    # Filter by league
    filtered = [
        d
        for d in docs
        if d.get("prediction", d.get("data", {}))
        .get("match", {})
        .get("league", {})
        .get("id", league_id)
        == league_id
        or d.get("league_id") == league_id
    ]
    # Calculate accuracy history for this league
    service = PredictionService()
    accuracy_history = service.calculate_score_accuracy_history(filtered)
    # Normalize
    normalized = []
    for doc in filtered:
        parsed = normalize_prediction_document(doc, league)
        if parsed is not None:
            parsed.prediction.score_accuracy_history = accuracy_history
            normalized.append(parsed)
    return PredictionsResponse(
        league=league, predictions=normalized, generated_at=_utc_now_iso()
    )


@router.get("/match/{match_id}", response_model=MatchPredictionModel)
async def get_prediction_by_match(match_id: str) -> MatchPredictionModel:
    repo = get_async_mongo_repository()
    document = await repo.get_match_prediction_document(match_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")

    league_id = document.get("league_id", "E0")
    normalized = normalize_prediction_document(document, find_league(league_id))
    if normalized is None:
        raise HTTPException(status_code=404, detail="Predicción no disponible")

    # Calculate accuracy history for this league
    service = PredictionService()
    accuracy_history = service.calculate_score_accuracy_history(
        [document]
        + [
            d
            for d in await repo.get_all_active_predictions()
            if d.get("league_id") == league_id
        ]
    )
    normalized.prediction.score_accuracy_history = accuracy_history
    return normalized
