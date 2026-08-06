"""Scheduler cache-payload tests (D1 cache swap + D5 cleanup hook).

Verifies the daily job caches only the lightweight training result in both
cache keys (no match_history/team_stats) and that the post-run cleanup runs
without wiping the cache (forecasts must keep serving the API between runs).
"""

import os
from types import SimpleNamespace

import pytest
from src.scheduler import BotScheduler

# Module-level spy shared by _install_fakes (avoids running the real cleanup
# against the working tree during tests).
cleanup_calls: list[int] = []


class _FakeCache:
    TTL_TRAINING = 86400
    TTL_LEAGUES = 86400
    TTL_FORECASTS = 86400

    def __init__(self) -> None:
        self.store: dict = {}
        self.set_calls: list[tuple[str, dict]] = []
        self.clear_calls = 0

    def set(self, key: str, value: dict, ttl_seconds: int | None = None) -> None:
        self.set_calls.append((key, value))
        self.store[key] = value

    def get(self, key: str, default=None):
        return self.store.get(key, default)

    def clear(self) -> None:
        self.clear_calls += 1
        self.store.clear()


class _FakePersistenceRepo:
    def __init__(self) -> None:
        self.saved: dict = {}

    def save_training_result(self, key: str, data: dict) -> None:
        self.saved[key] = data


class _FakeTrainingResult:
    matches_processed = 120
    correct_predictions = 64
    accuracy = 0.533
    total_bets = 30
    roi = 1.12
    profit_units = 4.2
    market_stats = {"home_win": 0.45}
    match_history = [
        {"match_id": "E0_2026_A_B", "match_date": "2026-01-01", "picks": []}
    ] * 5
    team_stats = {"Team A": {"wins": 10}}
    roi_evolution = [1.0, 1.12]
    pick_efficiency = 0.81
    context_summary = {"window": 550}


class _FakeOrchestrator:
    CACHE_KEY_RESULT = "ml_training_result_data"

    def __init__(self, training_result: _FakeTrainingResult) -> None:
        self._training_result = training_result

    async def run_training_pipeline(self, **kwargs):
        return self._training_result


class _FakeUseCase:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def execute(self, *args, **kwargs):
        return SimpleNamespace(model_dump=lambda: {})


class _FakeAutoLabeler:
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def run(self) -> int:
        return 0


class _FakeAuditService:
    async def audit_and_fix(self, fix_missing: bool = True) -> dict:
        return {"status": "healthy"}


def _install_fakes(monkeypatch, cache, persistence_repo, orchestrator) -> None:
    import src.application.services.auto_labeler as auto_labeler_module
    import src.application.use_cases.use_cases as use_cases_module
    import src.core.constants as constants_module
    import src.core.model_artifacts as model_artifacts_module
    import src.dependencies as dependencies

    # Never run the REAL cleanup against the working tree during tests.
    def fake_cleanup(logger):
        cleanup_calls.append(1)

    monkeypatch.setattr(model_artifacts_module, "cleanup_model_artifacts", fake_cleanup)

    monkeypatch.setattr(dependencies, "get_cache_service", lambda: cache)
    monkeypatch.setattr(
        dependencies, "get_persistence_repository", lambda: persistence_repo
    )
    monkeypatch.setattr(
        dependencies, "get_ml_training_orchestrator", lambda: orchestrator
    )
    monkeypatch.setattr(dependencies, "get_data_sources", lambda: object())
    monkeypatch.setattr(dependencies, "get_prediction_service", lambda: object())
    monkeypatch.setattr(dependencies, "get_statistics_service", lambda: object())
    monkeypatch.setattr(dependencies, "get_match_aggregator_service", lambda: object())
    monkeypatch.setattr(dependencies, "get_audit_service", lambda: _FakeAuditService())
    monkeypatch.setattr(use_cases_module, "GetPredictionsUseCase", _FakeUseCase)
    monkeypatch.setattr(use_cases_module, "GetLeaguesUseCase", _FakeUseCase)
    monkeypatch.setattr(auto_labeler_module, "AutoLabeler", _FakeAutoLabeler)
    monkeypatch.setattr(constants_module, "DEFAULT_LEAGUES", [])


@pytest.mark.asyncio
async def test_daily_job_caches_lightweight_payload_in_both_keys(monkeypatch):
    os.environ.pop("DISABLE_ML_TRAINING", None)
    cache = _FakeCache()
    persistence = _FakePersistenceRepo()
    orchestrator = _FakeOrchestrator(_FakeTrainingResult())
    _install_fakes(monkeypatch, cache, persistence, orchestrator)

    scheduler = BotScheduler()
    await scheduler.run_daily_orchestrated_job()

    training_keys = {"ml_training_result", orchestrator.CACHE_KEY_RESULT}
    cached_keys = {key for key, _ in cache.set_calls}
    assert "ml_training_result" in cached_keys
    assert orchestrator.CACHE_KEY_RESULT in cached_keys

    for key, value in cache.set_calls:
        if key in training_keys:
            assert "match_history" not in value
            assert "team_stats" not in value
            # Previously exposed metrics stay present (spec requirement:
            # accuracy, roi, profit_units, market_stats, pick_efficiency)
            assert value["accuracy"] == 0.533
            assert value["roi"] == 1.12
            assert value["profit_units"] == 4.2
            assert "market_stats" in value
            assert "pick_efficiency" in value

    # The same lightweight dict is the payload posted to MongoDB
    assert "latest_daily" in persistence.saved
    assert "match_history" not in persistence.saved["latest_daily"]
    assert "team_stats" not in persistence.saved["latest_daily"]


@pytest.mark.asyncio
async def test_daily_job_runs_artifact_cleanup_without_cache_clear(monkeypatch):
    os.environ.pop("DISABLE_ML_TRAINING", None)
    cache = _FakeCache()
    persistence = _FakePersistenceRepo()
    orchestrator = _FakeOrchestrator(_FakeTrainingResult())
    cleanup_calls.clear()
    _install_fakes(monkeypatch, cache, persistence, orchestrator)

    scheduler = BotScheduler()
    await scheduler.run_daily_orchestrated_job()

    assert cleanup_calls == [1]
    # D5: scheduler must NOT wipe forecasts between runs
    assert cache.clear_calls == 0
