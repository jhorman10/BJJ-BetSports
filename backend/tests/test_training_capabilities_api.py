from __future__ import annotations

import sys
from pathlib import Path

# ruff: noqa: E402
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.api.main import app  # noqa: E402
from src.api.security import require_training_read  # noqa: E402
from src.dependencies import get_training_result_reader  # noqa: E402


class StubTrainingResultReader:
    def get_latest_result(self):
        return (
            {
                "matches_processed": 120,
                "correct_predictions": 72,
                "accuracy": 60.0,
                "total_bets": 80,
                "roi": 8.5,
                "profit_units": 6.2,
                "market_stats": {},
                "match_history": [],
                "roi_evolution": [],
                "pick_efficiency": [],
                "team_stats": {},
            },
            "2026-05-04T11:00:00+00:00",
        )


def test_get_training_capabilities_returns_catalog() -> None:
    app.dependency_overrides[require_training_read] = lambda: "test-key"
    client = TestClient(app)

    response = client.get("/api/v1/training/capabilities")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert len(body["models"]) >= 1
    assert len(body["executors"]) >= 1
    assert len(body["dataset_profiles"]) >= 1
    assert len(body["feature_profiles"]) >= 1
    assert len(body["league_options"]) >= 1
    assert len(body["days_back_options"]) >= 1

    app.dependency_overrides.clear()


def test_get_training_models_returns_model_catalog() -> None:
    app.dependency_overrides[require_training_read] = lambda: "test-key"
    client = TestClient(app)

    response = client.get("/api/v1/training/models")

    assert response.status_code == 200
    body = response.json()
    assert len(body["models"]) >= 1
    assert body["models"][0]["key"]
    assert body["models"][0]["supported_executor_targets"]

    app.dependency_overrides.clear()


def test_get_latest_training_result_returns_training_namespace_payload() -> None:
    app.dependency_overrides[require_training_read] = lambda: "test-key"
    app.dependency_overrides[get_training_result_reader] = (
        lambda: StubTrainingResultReader()
    )
    client = TestClient(app)

    response = client.get("/api/v1/training/results/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["last_update"] == "2026-05-04T11:00:00+00:00"
    assert body["data"]["matches_processed"] == 120

    app.dependency_overrides.clear()
