from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from src.api.mappers.league_mapper import find_league
from src.api.mappers.prediction_mapper import normalize_prediction_document
from src.api.schemas.predictions import MatchPredictionModel
from src.infrastructure.repositories.mongo_repository import get_mongo_repository
from src.utils.time_utils import get_current_time

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])

# Statuses that prove a fixture is genuinely in progress. Docs that cannot
# prove a live status (missing data.match.status, or finished/not-started)
# are excluded even when expires_at is still in the future.
LIVE_STATUSES = {"1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"}


@router.get("/live", response_model=list[dict[str, Any]])
def get_live_matches() -> list[dict[str, Any]]:
    try:
        repository = get_mongo_repository()
        now = get_current_time()
        documents = repository.match_predictions.find(
            {
                "expires_at": {"$gt": now},
                "data.match.status": {"$in": list(LIVE_STATUSES)},
            }
        )
        matches: list[dict[str, Any]] = []
        for doc in documents:
            try:
                league = find_league(doc.get("league_id", "E0"))
            except HTTPException:
                continue
            normalized = normalize_prediction_document(doc, league)
            if normalized is not None:
                matches.append(normalized.match.model_dump())
        return matches
    except Exception:
        return []


@router.get("/live/with-predictions", response_model=list[dict[str, Any]])
def get_live_matches_with_predictions(
    filter_target_leagues: bool = True,
) -> list[dict[str, Any]]:
    try:
        repository = get_mongo_repository()
        now = get_current_time()
        documents = repository.match_predictions.find(
            {
                "expires_at": {"$gt": now},
                "data.match.status": {"$in": list(LIVE_STATUSES)},
            }
        )
        results: list[dict[str, Any]] = []
        for doc in documents:
            try:
                league = find_league(doc.get("league_id", "E0"))
            except HTTPException:
                continue
            normalized = normalize_prediction_document(doc, league)
            if normalized is not None:
                results.append(normalized.model_dump())
        return results
    except Exception:
        return []


@router.get("/daily", response_model=list[dict[str, Any]])
def get_daily_matches(  # noqa: C901
    date: str | None = None, league_id: str | None = None
) -> list[dict[str, Any]]:
    """Return matches for a given date (YYYY-MM-DD) and optional league filter.

    The function normalizes prediction documents and performs date filtering in
    Python to avoid depending on the exact database storage format for
    `match_date`.
    """
    try:
        repository = get_mongo_repository()

        # Fetch documents; filter by league_id at DB level if provided for perf
        query = {}
        if league_id:
            query["league_id"] = league_id

        documents = repository.match_predictions.find(query)

        # Resolve requested date
        if date:
            try:
                requested_date = datetime.strptime(date, "%Y-%m-%d").date()
            except Exception:
                raise HTTPException(
                    status_code=400, detail="Invalid date format, use YYYY-MM-DD"
                )
        else:
            requested_date = get_current_time().date()

        results: list[dict[str, Any]] = []
        for doc in documents:
            try:
                league = find_league(doc.get("league_id", "E0"))
            except HTTPException:
                continue
            normalized = normalize_prediction_document(doc, league)
            if not normalized:
                continue

            match = normalized.match
            match_date_str = getattr(match, "match_date", None)
            if not match_date_str:
                continue

            try:
                # Support ISO8601 with Z suffix
                dt = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
            except Exception:
                # Skip if unparsable
                continue

            if dt.date() == requested_date:
                results.append(normalized.model_dump())

        return results
    except HTTPException:
        raise
    except Exception:
        return []


@router.get("/team/{team_name}", response_model=list[dict[str, Any]])
def get_team_matches(team_name: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return recent matches where the team appears as home or away.

    Matching is case-insensitive substring search on team names.
    """
    try:
        max_limit = 50
        limit = max(1, min(limit, max_limit))

        repository = get_mongo_repository()
        documents = repository.match_predictions.find({})

        candidates: list[MatchPredictionModel] = []
        for doc in documents:
            try:
                league = find_league(doc.get("league_id", "E0"))
            except HTTPException:
                continue
            normalized = normalize_prediction_document(doc, league)
            if not normalized:
                continue

            home_name = (normalized.match.home_team.name or "").lower()
            away_name = (normalized.match.away_team.name or "").lower()
            q = team_name.lower()
            if q in home_name or q in away_name:
                candidates.append(normalized)

        def _key_dt(n: MatchPredictionModel) -> datetime:
            try:
                return datetime.fromisoformat(n.match.match_date.replace("Z", "+00:00"))
            except Exception:
                return datetime.min

        sorted_candidates = sorted(candidates, key=_key_dt, reverse=True)

        results: list[dict[str, Any]] = []
        for n in sorted_candidates[:limit]:
            results.append(n.model_dump())

        return results
    except Exception:
        return []
