import asyncio
import importlib.util
import os
import sys
import types
from types import SimpleNamespace

HERE = os.path.abspath(os.path.dirname(__file__))
SCRIPT_PATH = os.path.abspath(
    os.path.join(HERE, "..", "..", "scripts", "orchestrator_cli.py")
)

spec = importlib.util.spec_from_file_location("orchestrator_cli", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod

fake_deps = types.ModuleType("src.dependencies")
fake_deps.get_persistence_repository = lambda: "FAKE_REPO"
fake_deps.get_data_sources = lambda: "FAKE_DS"
fake_deps.get_match_aggregator_service = lambda: "FAKE_MA"
fake_deps.get_prediction_service = lambda: "FAKE_PS"
fake_deps.get_statistics_service = lambda: "FAKE_SS"

fake_uc_mod = types.ModuleType("src.application.use_cases.use_cases")


class FakeGetPredictionsUseCase:
    def __init__(
        self,
        data_sources,
        prediction_service,
        statistics_service,
        match_aggregator,
        persistence_repository,
    ):
        self._args = (
            data_sources,
            prediction_service,
            statistics_service,
            match_aggregator,
            persistence_repository,
        )

    async def execute(self, league_id, limit=None, force_refresh=False):
        return SimpleNamespace(predictions=[1, 2, 3])


fake_uc_mod.GetPredictionsUseCase = FakeGetPredictionsUseCase

# Now load the orchestrator_cli module
spec.loader.exec_module(mod)


def test_prepare_services_returns_use_case_and_repo():
    # Temporarily inject the fake dependency surfaces for this test only.
    _orig_deps = sys.modules.get("src.dependencies")
    _orig = sys.modules.get("src.application.use_cases.use_cases")
    sys.modules["src.dependencies"] = fake_deps
    sys.modules["src.application.use_cases.use_cases"] = fake_uc_mod
    try:
        use_case, repo = mod.prepare_services()
        assert repo == "FAKE_REPO"
        assert hasattr(use_case, "_args")
        assert use_case._args[0] == "FAKE_DS"
    finally:
        if _orig_deps is not None:
            sys.modules["src.dependencies"] = _orig_deps
        else:
            try:
                del sys.modules["src.dependencies"]
            except KeyError:
                pass
        if _orig is not None:
            sys.modules["src.application.use_cases.use_cases"] = _orig
        else:
            try:
                del sys.modules["src.application.use_cases.use_cases"]
            except KeyError:
                pass


def test_generate_predictions_for_league_success():
    class DummyUseCase:
        async def execute(self, league_id, limit=None, force_refresh=False):
            return SimpleNamespace(predictions=[{"a": 1}, {"a": 2}])

    result = asyncio.run(
        mod.generate_predictions_for_league("E0", DummyUseCase(), "FAKE_REPO")
    )
    assert result == ("E0", True)


def test_generate_predictions_for_league_failure():
    class BrokenUseCase:
        async def execute(self, *args, **kwargs):
            raise RuntimeError("boom")

    result = asyncio.run(
        mod.generate_predictions_for_league("E0", BrokenUseCase(), "FAKE_REPO")
    )
    assert result == ("E0", False)


def test_cmd_predict_dry_run(monkeypatch):
    # Simple tqdm shim that yields the iterable as-is
    class DummyTqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])

        def update(self, n=1):
            pass

        def set_postfix_str(self, s):
            pass

    monkeypatch.setattr(mod, "tqdm", DummyTqdm)

    # Replace prepare_services to return a use_case that doesn't persist anything
    class NoopUseCase:
        async def execute(self, league_id, limit=None, force_refresh=False):
            return SimpleNamespace(predictions=[{"id": 1}])

    monkeypatch.setattr(mod, "prepare_services", lambda: (NoopUseCase(), "FAKE_REPO"))

    # Ensure LEAGUES_METADATA contains the test league
    fake_fd = types.ModuleType("src.infrastructure.data_sources.football_data_uk")
    fake_fd.LEAGUES_METADATA = {"E0": {}}
    sys.modules["src.infrastructure.data_sources.football_data_uk"] = fake_fd

    # Run synchronously (sequential mode) to avoid parallel complexity in tests
    asyncio.run(mod.cmd_predict("E0", parallel=False, force=False))
