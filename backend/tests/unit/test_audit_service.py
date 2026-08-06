"""Audit service tests after the D1 re-source from MongoDB.

Verifies the audit no longer reads match_history from the cache; it derives
league coverage and pick integrity from
``persistence_repo.get_all_active_predictions()`` (MatchPredictionDTO shape).
"""

from datetime import datetime

import pytest
from src.core.constants import DEFAULT_LEAGUES
from src.domain.services.audit_service import AuditService

NOW_ISO = datetime.now().isoformat()


class _FakePersistenceRepo:
    def __init__(self, predictions: list[dict]) -> None:
        self.predictions = predictions

    def get_all_active_predictions(self) -> list[dict]:
        return list(self.predictions)


class _FakeOrchestrator:
    def __init__(self, repo) -> None:
        self.persistence_repo = repo
        self.retrained: list[list[str]] = []
        self.fail_retrain = False

    async def run_training_pipeline(
        self, league_ids, days_back: int = 550, force_refresh: bool = False
    ):
        if self.fail_retrain:
            raise RuntimeError("training boom")
        self.retrained.append(list(league_ids))


def _prediction_doc(
    match_id: str,
    league_id: str,
    match_date: str,
    picks: list | None = None,
    top_ml_picks: list | None = None,
) -> dict:
    """Doc shaped like `_to_prediction_result` where `prediction` is a
    `MatchPredictionDTO.model_dump()` (use_cases.py:860)."""
    return {
        "match_id": match_id,
        "league_id": league_id,
        "prediction": {
            "match": {
                "id": match_id,
                "match_date": match_date,
                "league": {"id": league_id},
            },
            "prediction": {"suggested_picks": picks or []},
            "top_ml_picks": top_ml_picks or [],
        },
        "last_updated": NOW_ISO,
    }


def _valid_pick() -> dict:
    return {
        "market_label": "1X2",
        "probability": 0.6,
        "confidence_level": "high",
        "ml_confidence": 0.75,
        "is_ml_confirmed": True,
    }


def _docs_for_all_leagues(picks=None, top_ml_picks=None) -> list[dict]:
    return [
        _prediction_doc(
            f"{league}_2026_HOME_AWAY",
            league,
            NOW_ISO,
            picks=picks,
            top_ml_picks=top_ml_picks,
        )
        for league in DEFAULT_LEAGUES
    ]


@pytest.mark.asyncio
async def test_audit_empty_repo_marks_all_leagues_missing_and_repairs():
    orchestrator = _FakeOrchestrator(_FakePersistenceRepo([]))
    service = AuditService(orchestrator)

    report = await service.audit_and_fix(fix_missing=True)

    assert report["missing_leagues"] == DEFAULT_LEAGUES
    assert report["integrity_issues"] == 0
    assert report["status"] == "repaired"
    assert report["actions_taken"] == [f"Retrained: {DEFAULT_LEAGUES}"]
    assert orchestrator.retrained == [list(DEFAULT_LEAGUES)]


@pytest.mark.asyncio
async def test_audit_with_valid_picks_is_healthy_and_does_not_retrain():
    orchestrator = _FakeOrchestrator(
        _FakePersistenceRepo(_docs_for_all_leagues(picks=[_valid_pick()]))
    )
    service = AuditService(orchestrator)

    report = await service.audit_and_fix(fix_missing=True)

    assert report["missing_leagues"] == []
    assert report["integrity_issues"] == 0
    assert report["status"] == "healthy"
    assert orchestrator.retrained == []


@pytest.mark.asyncio
async def test_audit_detects_missing_picks_as_integrity_issue():
    # Active docs with recent match dates but no picks at all
    orchestrator = _FakeOrchestrator(
        _FakePersistenceRepo(_docs_for_all_leagues(picks=[]))
    )
    service = AuditService(orchestrator)

    report = await service.audit_and_fix()

    assert report["missing_leagues"] == []
    assert report["integrity_issues"] > 0
    assert report["status"] == "degraded"
    assert orchestrator.retrained == []


@pytest.mark.asyncio
async def test_audit_failed_retrain_reports_failed_repair():
    orchestrator = _FakeOrchestrator(_FakePersistenceRepo([]))
    orchestrator.fail_retrain = True
    service = AuditService(orchestrator)

    report = await service.audit_and_fix(fix_missing=True)

    assert report["status"] == "failed_repair"
    assert report["actions_taken"] == []


@pytest.mark.asyncio
async def test_audit_has_no_cache_dependency():
    """The audit must not read match_history from the cache anymore."""
    import src.domain.services.audit_service as audit_module

    # If the module still referenced get_cache_service, this would be True.
    assert not hasattr(audit_module, "get_cache_service")

    orchestrator = _FakeOrchestrator(
        _FakePersistenceRepo(_docs_for_all_leagues(picks=[_valid_pick()]))
    )
    service = AuditService(orchestrator)

    report = await service.audit_and_fix()

    assert report["status"] == "healthy"
    assert report["integrity_issues"] == 0
