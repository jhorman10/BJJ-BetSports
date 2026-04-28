import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.application.use_cases.use_cases import (
    GetPredictionsUseCase,
    _build_match_team_statistics,
    _requires_contextual_team_statistics,
)
from src.domain.entities.entities import League, Match, Team, TrainingDataContextBundle


def test_is_cached_response_stale_false():
    inst = object.__new__(GetPredictionsUseCase)
    db_last_updated = datetime(2026, 3, 29, 12, 0, 0, tzinfo=timezone.utc)
    cached_response = {
        "generated_at": (db_last_updated - timedelta(seconds=5)).isoformat()
    }

    assert inst._is_cached_response_stale(db_last_updated, cached_response) is False


def test_is_cached_response_stale_true():
    inst = object.__new__(GetPredictionsUseCase)
    db_last_updated = datetime(2026, 3, 29, 12, 0, 20, tzinfo=timezone.utc)
    cached_response = {
        "generated_at": (db_last_updated - timedelta(seconds=20)).isoformat()
    }

    assert inst._is_cached_response_stale(db_last_updated, cached_response) is True


def test_normalize_and_apply_probs():
    inst = object.__new__(GetPredictionsUseCase)

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

    inst._normalize_and_apply_probs(pred, ml_probs)

    # Winner normalization
    assert pred.home_win_probability == round(0.6 / (0.6 + 0.2 + 0.2), 4)
    assert pred.draw_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)
    assert pred.away_win_probability == round(0.2 / (0.6 + 0.2 + 0.2), 4)

    # Over/Under normalization
    assert pred.over_25_probability == round(0.3 / (0.3 + 0.7), 4)
    assert pred.under_25_probability == round(0.7 / (0.3 + 0.7), 4)

    # Confidence should be the max of normalized probabilities
    expected_conf = max(
        pred.home_win_probability,
        pred.draw_probability,
        pred.away_win_probability,
        pred.over_25_probability,
        pred.under_25_probability,
    )
    assert pred.confidence == expected_conf

    assert "Rigorous ML" in pred.data_sources


def test_calculate_min_matches_relaxes_all_club_international_tournaments():
    inst = object.__new__(GetPredictionsUseCase)

    assert inst._calculate_min_matches("UCL") == 3
    assert inst._calculate_min_matches("LIB") == 3
    assert inst._calculate_min_matches("SUD") == 3
    assert inst._calculate_min_matches("EURO") == 6
    assert inst._calculate_min_matches("E0") == 6


def test_requires_contextual_team_statistics_for_all_international_tournaments():
    assert _requires_contextual_team_statistics("UCL") is True
    assert _requires_contextual_team_statistics("LIB") is True
    assert _requires_contextual_team_statistics("SUD") is True
    assert _requires_contextual_team_statistics("EURO") is True
    assert _requires_contextual_team_statistics("E0") is False


def test_build_match_team_statistics_prefers_contextual_bundle_when_available():
    class DummyStatisticsService:
        def __init__(self):
            self.calls = []

        def build_contextual_team_statistics(self, team_name, match, context_bundle):
            self.calls.append(("contextual", team_name, match.id))
            return {"mode": "contextual", "team_name": team_name}

        def calculate_team_statistics(self, team_name, historical_matches):
            self.calls.append(("flat", team_name, len(historical_matches)))
            return {"mode": "flat", "team_name": team_name}

    target_match = Match(
        id="lib-upcoming",
        home_team=Team(id="h", name="Palmeiras"),
        away_team=Team(id="a", name="River Plate"),
        league=League(id="LIB", name="Copa Libertadores", country="South America"),
        match_date=datetime(2026, 5, 10),
    )
    historical_target_match = Match(
        id="lib-played",
        home_team=Team(id="h2", name="Palmeiras"),
        away_team=Team(id="a2", name="Nacional"),
        league=League(id="LIB", name="Copa Libertadores", country="South America"),
        match_date=datetime(2026, 4, 1),
        home_goals=2,
        away_goals=1,
        status="FT",
    )
    bundle = TrainingDataContextBundle(
        target_matches=[historical_target_match],
        support_matches_by_team={"palmeiras": [historical_target_match]},
        coverage_report={"mode": "international"},
    )
    statistics_service = DummyStatisticsService()

    result = _build_match_team_statistics(
        statistics_service,
        "Palmeiras",
        target_match,
        historical_matches=[historical_target_match],
        context_bundle=bundle,
    )

    assert result["mode"] == "contextual"
    assert statistics_service.calls == [("contextual", "Palmeiras", "lib-upcoming")]


def test_build_match_team_statistics_falls_back_to_flat_history_without_team_context():
    class DummyStatisticsService:
        def __init__(self):
            self.calls = []

        def build_contextual_team_statistics(self, team_name, match, context_bundle):
            self.calls.append(("contextual", team_name, match.id))
            return {"mode": "contextual", "team_name": team_name}

        def calculate_team_statistics(self, team_name, historical_matches):
            self.calls.append(("flat", team_name, len(historical_matches)))
            return {"mode": "flat", "team_name": team_name}

    target_match = Match(
        id="lib-upcoming",
        home_team=Team(id="h", name="Palmeiras"),
        away_team=Team(id="a", name="River Plate"),
        league=League(id="LIB", name="Copa Libertadores", country="South America"),
        match_date=datetime(2026, 5, 10),
    )
    historical_match = Match(
        id="bra1-played",
        home_team=Team(id="h2", name="Flamengo"),
        away_team=Team(id="a2", name="Santos"),
        league=League(id="BRA1", name="Brasileirao", country="Brazil"),
        match_date=datetime(2026, 4, 1),
        home_goals=2,
        away_goals=1,
        status="FT",
    )
    bundle = TrainingDataContextBundle(
        target_matches=[],
        support_matches_by_team={"riverplate": [historical_match]},
        coverage_report={"mode": "international"},
    )
    statistics_service = DummyStatisticsService()

    result = _build_match_team_statistics(
        statistics_service,
        "Palmeiras",
        target_match,
        historical_matches=[historical_match],
        context_bundle=bundle,
    )

    assert result["mode"] == "flat"
    assert statistics_service.calls == [("flat", "Palmeiras", 1)]


def test_build_match_tasks_uses_contextual_stats_for_both_teams_when_bundle_exists():
    import src.infrastructure.cache.cache_service as cache_module

    class DummyTeamStats:
        def __init__(self, mode):
            self.mode = mode
            self.matches_played = 2

    class DummyStatisticsService:
        def __init__(self):
            self.calls = []

        def build_contextual_team_statistics(self, team_name, match, context_bundle):
            self.calls.append(("contextual", team_name))
            return DummyTeamStats("contextual")

        def calculate_team_statistics(self, team_name, historical_matches):
            self.calls.append(("flat", team_name))
            return DummyTeamStats("flat")

        def calculate_h2h_statistics(self, home_team, away_team, historical_matches):
            return None

    class DummyPrediction:
        predicted_home_goals = 1.0
        predicted_away_goals = 0.5
        home_win_probability = 0.5
        draw_probability = 0.3
        away_win_probability = 0.2
        predicted_home_corners = 4.0
        predicted_away_corners = 3.0
        predicted_home_yellow_cards = 2.0
        predicted_away_yellow_cards = 1.0

    class DummyPredictionService:
        def generate_prediction(self, **kwargs):
            return DummyPrediction()

    class DummyCache:
        def get(self, key):
            return None

    inst = object.__new__(GetPredictionsUseCase)
    inst.statistics_service = DummyStatisticsService()
    inst.prediction_service = DummyPredictionService()
    inst.ml_model = None
    inst._apply_ml_override = lambda prediction, match, home_stats, away_stats: None

    original_get_cache_service = cache_module.get_cache_service
    cache_module.get_cache_service = lambda: DummyCache()
    try:
        upcoming_match = Match(
            id="lib-upcoming",
            home_team=Team(id="h", name="Palmeiras"),
            away_team=Team(id="a", name="River Plate"),
            league=League(
                id="LIB",
                name="Copa Libertadores",
                country="South America",
            ),
            match_date=datetime(2026, 5, 10),
        )
        historical_match = Match(
            id="lib-played",
            home_team=Team(id="h2", name="Palmeiras"),
            away_team=Team(id="a2", name="River Plate"),
            league=League(
                id="LIB",
                name="Copa Libertadores",
                country="South America",
            ),
            match_date=datetime(2026, 4, 1),
            home_goals=2,
            away_goals=1,
            status="FT",
        )
        context_bundle = TrainingDataContextBundle(
            target_matches=[historical_match],
            support_matches_by_team={
                "palmeiras": [historical_match],
                "riverplate": [historical_match],
            },
            coverage_report={"mode": "international"},
        )

        match_tasks, matches_processing_data = inst._build_match_tasks(
            [upcoming_match],
            1,
            [historical_match],
            None,
            3,
            ["Contextual International History"],
            context_bundle=context_bundle,
        )
    finally:
        cache_module.get_cache_service = original_get_cache_service

    assert len(match_tasks) == 1
    assert len(matches_processing_data) == 1
    assert inst.statistics_service.calls == [
        ("contextual", "Palmeiras"),
        ("contextual", "River Plate"),
    ]

