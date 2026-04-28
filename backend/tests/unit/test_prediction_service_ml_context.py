import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.entities.entities import League, Match, Team, TeamStatistics
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.prediction_service import PredictionService
from src.domain.value_objects.value_objects import LeagueAverages


def _build_match() -> Match:
    return Match(
        id="match-1",
        home_team=Team(id="home-1", name="Palmeiras"),
        away_team=Team(id="away-1", name="River Plate"),
        league=League(id="LIB", name="Copa Libertadores", country="South America"),
        match_date=datetime(2026, 5, 1),
    )


def _build_stats(team_id: str) -> TeamStatistics:
    return TeamStatistics(
        team_id=team_id,
        matches_played=10,
        wins=6,
        draws=2,
        losses=2,
        goals_scored=16,
        goals_conceded=9,
        home_wins=4,
        away_wins=2,
        home_matches_played=5,
        home_goals_scored=9,
        home_goals_conceded=3,
        away_matches_played=5,
        away_goals_scored=7,
        away_goals_conceded=6,
        total_corners=54,
        total_yellow_cards=21,
        total_red_cards=1,
        matches_with_corners=10,
        matches_with_cards=10,
        total_shots=112,
        total_shots_on_target=48,
        total_fouls=97,
        matches_with_shots=10,
        matches_with_fouls=10,
        recent_corners=[4, 5, 6, 5, 7],
        recent_yellow_cards=[2, 1, 3, 2, 2],
        recent_shots=[9, 10, 12, 11, 8],
        recent_form="WWDLW",
    )


def _build_league_averages() -> LeagueAverages:
    return LeagueAverages(
        avg_home_goals=1.5,
        avg_away_goals=1.1,
        avg_total_goals=2.6,
        avg_corners=9.2,
        avg_cards=4.4,
    )


def test_calculate_corner_probabilities_passes_context_to_feature_extractor(
    monkeypatch,
):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    captured_calls = []

    def fake_extract_features(pick, match, home_stats, away_stats):
        captured_calls.append(
            (pick.market_label, match.id, home_stats.team_id, away_stats.team_id)
        )
        return [0.1, 0.2, 0.3]

    class DummyCornersModel:
        def predict(self, features):
            return [10.4]

    monkeypatch.setattr(
        MLFeatureExtractor,
        "extract_features",
        staticmethod(fake_extract_features),
    )

    service = PredictionService()
    service.calculate_corner_probabilities(
        home_stats,
        away_stats,
        match=match,
        active_models={"corners": DummyCornersModel()},
    )

    assert captured_calls == [
        ("Generic", match.id, home_stats.team_id, away_stats.team_id)
    ]


def test_calculate_card_probabilities_passes_context_to_feature_extractor(
    monkeypatch,
):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    captured_calls = []

    def fake_extract_features(pick, match, home_stats, away_stats):
        captured_calls.append(
            (pick.market_label, match.id, home_stats.team_id, away_stats.team_id)
        )
        return [0.4, 0.5, 0.6]

    class DummyCardsModel:
        def predict(self, features):
            return [4.8]

    monkeypatch.setattr(
        MLFeatureExtractor,
        "extract_features",
        staticmethod(fake_extract_features),
    )

    service = PredictionService()
    service.calculate_card_probabilities(
        home_stats,
        away_stats,
        match=match,
        active_models={"cards": DummyCardsModel()},
    )

    assert captured_calls == [
        ("Generic", match.id, home_stats.team_id, away_stats.team_id)
    ]


def test_generate_prediction_passes_context_to_winner_model(monkeypatch):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    league_averages = _build_league_averages()
    captured_calls = []

    def fake_extract_features(pick, match, home_stats, away_stats):
        captured_calls.append(
            (pick.market_label, match.id, home_stats.team_id, away_stats.team_id)
        )
        return [0.7, 0.8, 0.9]

    class DummyWinnerModel:
        def predict_proba(self, features):
            return [[0.2, 0.6, 0.2]]

    monkeypatch.setattr(
        MLFeatureExtractor,
        "extract_features",
        staticmethod(fake_extract_features),
    )

    service = PredictionService()
    service._get_model = lambda league_id, model_type: None
    prediction = service.generate_prediction(
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        league_averages=league_averages,
        data_sources=[],
        min_matches=6,
        active_models={"winner": DummyWinnerModel()},
    )

    assert captured_calls == [
        ("Generic", match.id, home_stats.team_id, away_stats.team_id)
    ]
    assert prediction.home_win_probability > prediction.draw_probability