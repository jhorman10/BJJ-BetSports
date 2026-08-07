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


def test_score_probabilities_basic():
    service = PredictionService()
    scores = service.calculate_score_probabilities(1.5, 1.2, max_goals=5, top_n=5)

    assert len(scores) == 5
    assert all(
        "home_goals" in s and "away_goals" in s and "probability" in s for s in scores
    )
    assert scores[0]["probability"] >= scores[-1]["probability"]
    total = sum(s["probability"] for s in scores)
    assert total > 0


def test_score_probabilities_most_probable_first():
    service = PredictionService()
    scores = service.calculate_score_probabilities(2.0, 0.8, max_goals=5, top_n=3)

    for i in range(len(scores) - 1):
        assert scores[i]["probability"] >= scores[i + 1]["probability"]


def test_score_probabilities_symmetric():
    service = PredictionService()
    scores = service.calculate_score_probabilities(1.5, 1.5, max_goals=4, top_n=10)

    # When λ are equal, P(h:a) should be approximately P(a:h)
    score_map = {(s["home_goals"], s["away_goals"]): s["probability"] for s in scores}
    for h in range(5):
        for a in range(5):
            if (h, a) in score_map and (a, h) in score_map:
                assert abs(score_map[(h, a)] - score_map[(a, h)]) < 1e-4


def test_score_confidence_tier_alta(monkeypatch):
    service = PredictionService()
    # Mock low entropy scores to force Alta tier
    low_entropy_scores = [
        {"home_goals": 2, "away_goals": 0, "probability": 0.5},
        {"home_goals": 1, "away_goals": 0, "probability": 0.2},
        {"home_goals": 3, "away_goals": 0, "probability": 0.15},
    ]
    monkeypatch.setattr(
        service,
        "calculate_score_probabilities",
        lambda *args, **kwargs: low_entropy_scores,
    )
    tier = service.calculate_score_confidence_tier(
        home_expected=2.5,
        away_expected=0.5,
        base_confidence=0.85,
    )
    assert tier == "Alta"


def test_score_confidence_tier_baja():
    service = PredictionService()
    tier = service.calculate_score_confidence_tier(
        home_expected=1.5,
        away_expected=1.5,
        base_confidence=0.25,
    )
    assert tier == "Baja"


def test_score_probabilities_no_xg():
    service = PredictionService()
    tier = service.calculate_score_confidence_tier(
        home_expected=None,
        away_expected=1.2,
        base_confidence=0.7,
    )
    assert tier == "N/A"

    scores = service.calculate_score_probabilities(None, 1.2)
    assert scores == []


def test_generate_prediction_includes_score_probabilities(monkeypatch):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    league_averages = _build_league_averages()

    service = PredictionService()
    prediction = service.generate_prediction(
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        league_averages=league_averages,
        data_sources=[],
        min_matches=6,
    )

    assert prediction.score_probabilities is not None
    assert len(prediction.score_probabilities) >= 3
    assert prediction.score_confidence_tier in {"Alta", "Media", "Baja", "N/A"}


def test_score_matrix_basic():
    service = PredictionService()
    matrix = service.calculate_score_matrix(1.5, 1.2, max_goals=5)

    assert len(matrix) == 6
    assert all(len(row) == 6 for row in matrix)
    # Sum of all probabilities should be ~1
    total = sum(cell["probability"] for row in matrix for cell in row)
    assert 0.95 < total < 1.05


def test_score_matrix_xg_contributions():
    service = PredictionService()
    matrix = service.calculate_score_matrix(2.0, 1.0, max_goals=3)

    for row in matrix:
        for cell in row:
            assert "home_xg_contribution" in cell
            assert "away_xg_contribution" in cell
            total_contrib = cell["home_xg_contribution"] + cell["away_xg_contribution"]
            assert abs(total_contrib - 1.0) < 1e-3
            # Home xG > away xG => home contribution > 0.5
            assert cell["home_xg_contribution"] > 0.5


def test_score_matrix_no_xg():
    service = PredictionService()
    matrix = service.calculate_score_matrix(None, 1.2)
    assert matrix == []


def test_score_accuracy_history_calculation():
    service = PredictionService()
    history = service.calculate_score_accuracy_history(
        [
            {
                "prediction": {
                    "score_probabilities": [
                        {"home_goals": 2, "away_goals": 1, "probability": 0.15},
                        {"home_goals": 1, "away_goals": 1, "probability": 0.12},
                    ],
                    "match": {"home_goals": 2, "away_goals": 1},
                }
            },
            {
                "prediction": {
                    "score_probabilities": [
                        {"home_goals": 1, "away_goals": 0, "probability": 0.20},
                    ],
                    "match": {"home_goals": 1, "away_goals": 2},
                }
            },
        ]
    )
    assert history["total_predictions"] == 2
    assert history["exact_score_hits"] == 1
    assert abs(history["accuracy_percentage"] - 0.5) < 1e-4


def test_score_accuracy_history_no_data():
    service = PredictionService()
    history = service.calculate_score_accuracy_history([])
    assert history["total_predictions"] == 0
    assert history["exact_score_hits"] == 0
    assert history["accuracy_percentage"] == 0.0


def test_generate_prediction_includes_matrix():
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    league_averages = _build_league_averages()

    service = PredictionService()
    prediction = service.generate_prediction(
        match=match,
        home_stats=home_stats,
        away_stats=away_stats,
        league_averages=league_averages,
        data_sources=[],
        min_matches=6,
    )

    assert prediction.score_matrix is not None
    assert len(prediction.score_matrix) == 6
    assert all(len(row) == 6 for row in prediction.score_matrix)
    assert "home_xg_contribution" in prediction.score_matrix[0][0]
    assert "away_xg_contribution" in prediction.score_matrix[0][0]
