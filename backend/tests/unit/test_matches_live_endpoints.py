from __future__ import annotations

from datetime import timedelta

import pytest
import src.api.routers.matches as matches_module
from fastapi.testclient import TestClient
from src.api.main import app
from src.utils.time_utils import get_current_time


class FakeRepo:
    """Mimics the Mongo collection: applies the query filters (expires_at,
    data.match.status $in) so only genuinely in-progress docs are served."""

    def __init__(self, docs: list[dict]):
        self._docs = docs
        self.match_predictions = self
        self.last_query: dict | None = None

    def find(self, query: dict):
        self.last_query = query
        expires_gt = query.get("expires_at", {}).get("$gt")
        allowed_statuses = query.get("data.match.status", {}).get("$in")
        served = []
        for doc in self._docs:
            if expires_gt is not None and doc.get("expires_at") <= expires_gt:
                continue
            if allowed_statuses is not None:
                status = (doc.get("data") or {}).get("match", {}).get("status")
                if status not in allowed_statuses:
                    continue
            served.append(doc)
        return served


def _live_doc(match_id: str, status: str) -> dict:
    return {
        "match_id": match_id,
        "league_id": "E0",
        "data": {
            "match": {
                "id": match_id,
                "home_team": {"id": "t1", "name": "Team A"},
                "away_team": {"id": "t2", "name": "Team B"},
                "league": {
                    "id": "E0",
                    "name": "Premier League",
                    "country": "England",
                },
                "match_date": "2026-08-11T19:00:00Z",
                "status": status,
                "home_goals": 1,
                "away_goals": 0,
            },
            "prediction": {
                "match_id": match_id,
                "home_win_probability": 0.6,
                "draw_probability": 0.2,
                "away_win_probability": 0.2,
                "over_25_probability": 0.5,
                "under_25_probability": 0.5,
                "predicted_home_goals": 1.5,
                "predicted_away_goals": 0.8,
                "confidence": 0.6,
                "recommended_bet": "N/A",
                "over_under_recommendation": "N/A",
                "created_at": "2026-08-11T10:00:00Z",
            },
        },
        # Future TTL alone is NOT enough to be served — status decides
        "expires_at": get_current_time() + timedelta(hours=2),
    }


@pytest.fixture
def finished_not_started_and_live_docs() -> list[dict]:
    return [
        _live_doc("ft-1", "FT"),
        _live_doc("ns-1", "NS"),
        _live_doc("live-1", "1H"),
    ]


def test_live_endpoint_serves_only_in_progress_docs(
    monkeypatch: pytest.MonkeyPatch,
    finished_not_started_and_live_docs: list[dict],
) -> None:
    repo = FakeRepo(finished_not_started_and_live_docs)
    monkeypatch.setattr(matches_module, "get_mongo_repository", lambda: repo)

    response = TestClient(app).get("/api/v1/matches/live")

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body] == ["live-1"]


def test_live_with_predictions_endpoint_serves_only_in_progress_docs(
    monkeypatch: pytest.MonkeyPatch,
    finished_not_started_and_live_docs: list[dict],
) -> None:
    repo = FakeRepo(finished_not_started_and_live_docs)
    monkeypatch.setattr(matches_module, "get_mongo_repository", lambda: repo)

    response = TestClient(app).get("/api/v1/matches/live/with-predictions")

    assert response.status_code == 200
    body = response.json()
    assert [m["match"]["id"] for m in body] == ["live-1"]


def test_live_queries_carry_the_status_filter(
    monkeypatch: pytest.MonkeyPatch,
    finished_not_started_and_live_docs: list[dict],
) -> None:
    repo = FakeRepo(finished_not_started_and_live_docs)
    monkeypatch.setattr(matches_module, "get_mongo_repository", lambda: repo)

    TestClient(app).get("/api/v1/matches/live")
    TestClient(app).get("/api/v1/matches/live/with-predictions")

    assert repo.last_query is not None
    statuses = repo.last_query.get("data.match.status", {}).get("$in")
    assert set(statuses) == {"1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"}
