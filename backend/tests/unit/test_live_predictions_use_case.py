import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.application.dtos.dtos import (
    LeagueDTO,
    MatchDTO,
    MatchPredictionDTO,
    PredictionDTO,
    TeamDTO,
)
import src.application.use_cases.live_predictions_use_case as live_module
from src.application.use_cases.live_predictions_use_case import (
    GetLivePredictionsUseCase,
    _get_context_bundle_from_cache,
    _determine_data_sources,
    _normalize_and_apply_probs,
    _persist_and_cache_response,
)
from src.domain.entities.entities import TrainingDataContextBundle


def test_normalize_and_apply_probs_module():
    class DummyPrediction:
        def __init__(self):
            self.home_win_probability = 0.0
            self.draw_probability = 0.0
            self.away_win_probability = 0.0
            self.over_25_probability = 0.0
            self.under_25_probability = 0.0
            self.confidence = 0.0
            self.data_sources = []

    pred = DummyPrediction()
    ml_probs = [0.6, 0.2, 0.2, 0.3, 0.7]

    _normalize_and_apply_probs(pred, ml_probs)

    assert pred.home_win_probability == round(0.6 / (0.6 + 0.2 + 0.2), 4)
    assert pred.draw_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)
    assert pred.away_win_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)

    assert pred.over_25_probability == round(0.3 / (0.3 + 0.7), 4)
    assert pred.under_25_probability == round(0.7 / (0.3 + 0.7), 4)

    expected_conf = max(
        pred.home_win_probability,
        pred.draw_probability,
        pred.away_win_probability,
        pred.over_25_probability,
        pred.under_25_probability,
    )
    assert pred.confidence == expected_conf
    assert "Rigorous ML" in pred.data_sources


def test_determine_data_sources_with_training_results():
    # Dummy cache that returns training_results and global averages
    class DummyCache:
        def __init__(self):
            self.store = {
                "ml_training_result_data": {
                    "team_stats": {
                        "HomeTeam": {"matches_played": 10, "wins": 5},
                        "AwayTeam": {"matches_played": 8, "wins": 3},
                    }
                },
                "global_statistical_averages": {},
            }

        def get(self, key):
            return self.store.get(key)

    class DummyStatistics:
        pass

    class DummyTeam:
        def __init__(self, name):
            self.name = name

    class DummyLeague:
        def __init__(self, lid):
            self.id = lid

    class DummyMatch:
        def __init__(self):
            self.home_team = DummyTeam("HomeTeam")
            self.away_team = DummyTeam("AwayTeam")
            self.league = DummyLeague("X")

    cache = DummyCache()
    stats = DummyStatistics()
    data_sources = type(
        "S", (), {"football_data_org": type("F", (), {"is_configured": False})()}
    )

    (
        training_results,
        home_stats,
        away_stats,
        league_averages,
        global_averages,
        data_sources_used,
    ) = _determine_data_sources(cache, stats, data_sources, DummyMatch(), None)

    assert training_results is not None
    assert home_stats is not None
    assert away_stats is not None
    assert "Historical (10 Years)" in data_sources_used


def test_persist_and_cache_response_calls_backends():
    # Build minimal DTOs
    home = TeamDTO(id="h", name="Home")
    away = TeamDTO(id="a", name="Away")
    league = LeagueDTO(id="L", name="League", country="C")

    match_dto = MatchDTO(
        id="m1",
        home_team=home,
        away_team=away,
        league=league,
        match_date=datetime.utcnow(),
    )

    pred = PredictionDTO(
        match_id="m1",
        home_win_probability=0.5,
        draw_probability=0.25,
        away_win_probability=0.25,
        over_25_probability=0.4,
        under_25_probability=0.6,
        predicted_home_goals=1.0,
        predicted_away_goals=1.0,
        confidence=0.5,
        data_sources=[],
        recommended_bet="N/A",
        over_under_recommendation="N/A",
        created_at=datetime.utcnow(),
    )

    mp = MatchPredictionDTO(match=match_dto, prediction=pred)

    called = {}

    class DummyCache:
        def set_live_matches(self, value, key):
            called["cache"] = (value, key)

    class DummyRepo:
        def bulk_save_predictions(self, batch):
            called["repo"] = batch

    use_case = type("U", (), {})()
    use_case.cache_service = DummyCache()
    use_case.persistence_repository = DummyRepo()

    _persist_and_cache_response(use_case, [mp], "test-key")

    assert "cache" in called
    assert "repo" in called
    assert isinstance(called["repo"], list)


class DummyCache:
    def __init__(self):
        self._live = None

    def get_live_matches(self, key):
        return None

    async def aget_live_matches(self, key):
        return self.get_live_matches(key)

    async def aset_live_matches(self, value, key):
        self.set_live_matches(value, key)

    def set_live_matches(self, value, key):
        self._live = (value, key)

    def get_predictions(self, match_id):
        return None

    def set_predictions(self, match_id, pred):
        pass


class DummyTeam:
    def __init__(self, id, name):
        self.id = id
        self.name = name


class DummyLeague:
    def __init__(self, lid):
        self.id = lid


class DummyMatch:
    def __init__(self):
        self.id = "m1"
        self.home_team = DummyTeam("h1", "Home")
        self.away_team = DummyTeam("a1", "Away")
        self.league = DummyLeague("UNKNOWN")
        self.home_goals = 0
        self.away_goals = 0
        self.status = "1H"
        self.minute = "10"


async def _live_fetch():
    return [DummyMatch()]


async def fake_generate_prediction(match, bulk_history=None):
    return PredictionDTO(
        match_id=match.id,
        home_win_probability=0.5,
        draw_probability=0.3,
        away_win_probability=0.2,
        over_25_probability=0.4,
        under_25_probability=0.6,
        predicted_home_goals=1.0,
        predicted_away_goals=1.0,
        confidence=0.5,
        data_sources=[],
        recommended_bet="N/A",
        over_under_recommendation="N/A",
        created_at=datetime.utcnow(),
    )


def fake_match_to_dto(match):
    return MatchDTO(
        id=match.id,
        home_team=TeamDTO(id="h", name="Home"),
        away_team=TeamDTO(id="a", name="Away"),
        league=LeagueDTO(id="L", name="League", country="C"),
        match_date=datetime.utcnow(),
        status="1H",
    )


def _build_dummy_instance():
    inst = object.__new__(GetLivePredictionsUseCase)
    inst.cache_service = DummyCache()
    inst.data_sources = type(
        "DS",
        (),
        {
            "football_data_org": type(
                "F", (), {"is_configured": True, "get_live_matches": _live_fetch}
            )()
        },
    )()
    inst.statistics_service = type("S", (), {})()
    inst.prediction_service = type("P", (), {})()
    inst.picks_service = type(
        "K",
        (),
        {"generate_suggested_picks": lambda *a, **k: type("C", (), {"picks": []})()},
    )()
    inst.persistence_repository = None
    inst._generate_prediction = fake_generate_prediction
    inst._match_to_dto = fake_match_to_dto
    return inst


def test_execute_dry_run():
    inst = _build_dummy_instance()
    results = asyncio.run(inst.execute(filter_target_leagues=False))

    assert isinstance(results, list)
    assert len(results) >= 0


def test_get_context_bundle_from_cache_reuses_loaded_bundle():
    expected_bundle = TrainingDataContextBundle(target_matches=[])
    context_bundle_cache = {}
    calls = []
    original_loader = live_module._load_contextual_training_bundle

    async def fake_loader(league_id):
        calls.append(league_id)
        return expected_bundle

    live_module._load_contextual_training_bundle = fake_loader
    try:
        first_result = asyncio.run(
            _get_context_bundle_from_cache("LIB", context_bundle_cache)
        )
        second_result = asyncio.run(
            _get_context_bundle_from_cache("LIB", context_bundle_cache)
        )
    finally:
        live_module._load_contextual_training_bundle = original_loader

    assert first_result is expected_bundle
    assert second_result is expected_bundle
    assert calls == ["LIB"]


def test_get_context_bundle_from_cache_skips_domestic_leagues():
    context_bundle_cache = {}

    result = asyncio.run(_get_context_bundle_from_cache("E0", context_bundle_cache))

    assert result is None
    assert context_bundle_cache == {}
