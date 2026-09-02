from __future__ import annotations

import inspect

from fastapi import APIRouter, HTTPException, Query
from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel, PredictionsResponse
from src.api.utils.serializers import _utc_now_iso
from src.domain.constants import DEFAULT_SPORT
from src.domain.services.prediction_service import PredictionService
from src.infrastructure.cache.cache_service import get_cache_service
from src.infrastructure.repositories.async_mongo_adapter import (
    get_async_mongo_repository,
)
from src.utils.time_utils import get_current_time

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/league/{league_id}", response_model=PredictionsResponse)
async def get_predictions_by_league(
    league_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sport: str = Query(DEFAULT_SPORT),
) -> PredictionsResponse:
    repo = get_async_mongo_repository()
    skip = (page - 1) * page_size
    docs = await repo.get_all_active_predictions(
        skip=skip, limit=page_size, league_id=league_id, sport=sport
    )
    league = find_league(league_id, sport=sport)
    # Calculate accuracy history for this league (cached)
    cache = get_cache_service()
    accuracy_history = await cache.aget_accuracy_history(league_id)
    if accuracy_history is None:
        service = PredictionService()
        accuracy_history = service.calculate_score_accuracy_history(docs)
        await cache.aset_accuracy_history(league_id, accuracy_history)
    # Normalize
    normalized = []
    for doc in docs:
        parsed = normalize_prediction_document(doc, league)
        if parsed is not None:
            parsed.prediction.score_accuracy_history = accuracy_history
            normalized.append(parsed)
    # Count total for pagination metadata (cached briefly)
    total: int | None = None
    collection = getattr(repo, "match_predictions", None)
    if collection is not None:
        count_cache_key = f"predictions_count:{league_id}:{sport}"
        total = await cache.aget(count_cache_key)
        if total is None:
            count_fn = getattr(collection, "count_documents", None)
            if count_fn is not None:
                query = {
                    "expires_at": {"$gt": get_current_time()},
                    "league_id": league_id,
                    "sport": sport,
                }
                raw_total = count_fn(query)
                if inspect.isawaitable(raw_total):
                    total = await raw_total
                else:
                    total = raw_total
            if total is None:
                total = len(docs)
            await cache.aset(count_cache_key, total, 300)
    if total is None:
        total = len(docs)
    return PredictionsResponse(
        league=league,
        predictions=normalized,
        generated_at=_utc_now_iso(),
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/match/{match_id}", response_model=MatchPredictionModel)
async def get_prediction_by_match(match_id: str) -> MatchPredictionModel:
    repo = get_async_mongo_repository()
    document = await repo.get_match_prediction_document(match_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")

    league_id = document.get("league_id", "E0")
    doc_sport = document.get("sport", DEFAULT_SPORT)
    normalized = normalize_prediction_document(document, find_league(league_id, sport=doc_sport))
    if normalized is None:
        raise HTTPException(status_code=404, detail="Predicción no disponible")

    # Calculate accuracy history for this league (cached)
    cache = get_cache_service()
    accuracy_history = await cache.aget_accuracy_history(league_id)
    if accuracy_history is None:
        league_docs = await repo.get_all_active_predictions(league_id=league_id)
        service = PredictionService()
        accuracy_history = service.calculate_score_accuracy_history(league_docs)
        await cache.aset_accuracy_history(league_id, accuracy_history)

    normalized.prediction.score_accuracy_history = accuracy_history
    return normalized
