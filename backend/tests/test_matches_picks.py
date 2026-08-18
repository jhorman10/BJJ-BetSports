from __future__ import annotations

from fastapi.testclient import TestClient
from src.api.main import app


class FakeRepo:
    def __init__(self, docs=None):
        self._docs = docs or []
        self.match_predictions = self

    def find(self, query):
        return self._docs

    def find_one(self, query):
        return self._docs[0] if self._docs else None


def test_live_matches_empty():
    import src.api.routers.matches as matches_module

    matches_module.get_mongo_repository = lambda: FakeRepo([])
    client = TestClient(app)
    r = client.get("/api/v1/matches/live")
    assert r.status_code == 200
    assert r.json() == []


def test_live_matches_with_doc():
    import src.api.routers.matches as matches_module

    sample_doc = {
        "league_id": "E0",
        "data": {
            "match": {
                "id": "m1",
                "home_team": {"id": "t1", "name": "Team A"},
                "away_team": {"id": "t2", "name": "Team B"},
                "league": {"id": "E0", "name": "E0", "country": "X"},
                "match_date": "2026-03-30T12:00:00Z",
                "status": "1H",
            },
            "prediction": {"match_id": "m1", "home_win_probability": 0.6},
        },
    }

    matches_module.get_mongo_repository = lambda: FakeRepo([sample_doc])
    client = TestClient(app)
    r = client.get("/api/v1/matches/live")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["id"] == "m1"


def test_suggested_picks_endpoints():
    import src.dependencies as deps

    class DummyLearningService:
        def register_feedback(self, feedback):
            pass

        def get_market_adjustment(self, market_type):
            return 1.0

        def get_all_stats(self):
            return {}

        def get_learning_weights(self):
            from src.domain.entities.betting_feedback import LearningWeights

            return LearningWeights()

    app.dependency_overrides[deps.get_learning_service] = lambda: DummyLearningService()
    client = TestClient(app)
    try:
        r = client.get("/api/v1/suggested-picks/match/foo")
        assert r.status_code == 200
        assert r.json()["match_id"] == "foo"

        payload = {
            "match_id": "foo",
            "market_type": "win",
            "prediction": "home",
            "actual_outcome": "home",
            "was_correct": True,
            "odds": 1.5,
        }
        r2 = client.post("/api/v1/suggested-picks/feedback", json=payload)
        assert r2.status_code == 200
        assert r2.json()["success"] is True

        r3 = client.get("/api/v1/suggested-picks/learning-stats")
        assert r3.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_daily_and_team_endpoints():
    client = TestClient(app)
    r_daily = client.get("/api/v1/matches/daily")
    assert r_daily.status_code == 200
    assert r_daily.json() == []

    r_team = client.get("/api/v1/matches/team/some-team")
    assert r_team.status_code == 200
    assert r_team.json() == []
