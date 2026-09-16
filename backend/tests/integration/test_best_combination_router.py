"""
Integration tests for the best-combination router (Phase 3.4).

Uses FastAPI TestClient against the real app; the use case is stubbed so no
external sport services/fixture sources are touched.
"""

from __future__ import annotations

import pytest
import src.api.routers.best_combination as bc_module
from fastapi.testclient import TestClient
from src.api.dtos.best_combination_dtos import (
    BestCombinationAggregate,
    BestCombinationLeg,
    BestCombinationResponse,
    BestCombinationStake,
)
from src.api.main import app
from src.domain.services.combination_optimizer import CombinationError


def canned_response() -> BestCombinationResponse:
    return BestCombinationResponse(
        legs=[
            BestCombinationLeg(
                sport="soccer",
                match_id="s1",
                match_label="A vs B",
                pick_label="ML_H",
                league="E0",
                probability=0.65,
                odds=1.90,
                odds_source="market",
                confidence_level="high",
                is_recommended=True,
                priority_score=60.0,
            ),
            BestCombinationLeg(
                sport="tennis",
                match_id="t1",
                match_label="C vs D",
                pick_label="ML_H",
                odds=2.10,
                probability=0.62,
                odds_source="market",
                confidence_level="high",
            ),
            BestCombinationLeg(
                sport="baseball",
                match_id="b1",
                match_label="E vs F",
                pick_label="ML_H",
                odds=1.80,
                probability=0.60,
                odds_source="market",
                confidence_level="high",
            ),
            BestCombinationLeg(
                sport="basketball",
                match_id="bb1",
                match_label="G vs H",
                pick_label="ML_H",
                odds=2.25,
                probability=0.58,
                odds_source="market",
                confidence_level="high",
            ),
        ],
        aggregate=BestCombinationAggregate(
            total_probability=0.1403,
            total_odds=16.16,
            expected_value=1.2672,
            mixed_odds=False,
        ),
        stake=BestCombinationStake(
            suggested_stake_pct=0.03, risk_level=3, kelly_fraction=0.03
        ),
        generated_at="2026-09-08T12:00:00Z",
        independence_disclaimer="Combinada armada sobre eventos independientes.",
        warnings=[],
    )


class StubUseCase:
    """Stub that replays a canned outcome (response or CombinationError)."""

    def __init__(self, outcome):
        self._outcome = outcome

    async def execute(self, request):
        del request
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


@pytest.fixture()
def stub_use_case(monkeypatch):
    def _patch(outcome):
        stub = StubUseCase(outcome)
        monkeypatch.setattr(bc_module, "get_best_combination_use_case", lambda: stub)
        return stub

    return _patch


def test_post_returns_200_with_combination(stub_use_case) -> None:
    stub_use_case(canned_response())
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={})
    assert r.status_code == 200
    body = r.json()
    assert len(body["legs"]) == 4
    assert body["aggregate"]["total_odds"] == pytest.approx(16.16)
    assert body["stake"]["risk_level"] == 3
    assert body["independence_disclaimer"]


def test_422_on_invalid_min_probability() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={"min_probability": 1.5})
    assert r.status_code == 422


def test_422_on_invalid_exclude_leagues_type() -> None:
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={"exclude_leagues": "E0"})
    assert r.status_code == 422


def test_409_insufficient_pool(stub_use_case) -> None:
    stub_use_case(
        CombinationError(
            "insufficient_pool",
            "No hay suficientes picks para armar una combinada de cuatro piernas.",
            ["tennis", "baseball"],
        )
    )
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={})
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["error"] == "insufficient_pool"
    assert set(body["detail"]["missing_sports"]) == {"tennis", "baseball"}


def test_409_no_positive_ev(stub_use_case) -> None:
    stub_use_case(
        CombinationError(
            "no_positive_ev",
            "La combinada no tiene valor esperado positivo (EV -2.00%).",
        )
    )
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "no_positive_ev"


def test_409_no_picks_available(stub_use_case) -> None:
    stub_use_case(
        CombinationError("no_picks_available", "No hay predicciones disponibles.")
    )
    client = TestClient(app)
    r = client.post("/api/v1/best-combination", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "no_picks_available"
