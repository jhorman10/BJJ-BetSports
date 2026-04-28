import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.entities.suggested_pick import (
    ConfidenceLevel,
    MarketType,
    SuggestedPick,
)
from src.domain.services.ml_feature_extractor import MLFeatureExtractor


class _Simple:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _make_pick() -> SuggestedPick:
    return SuggestedPick(
        market_type=MarketType.WINNER,
        market_label="1",
        probability=0.55,
        expected_value=0.12,
        risk_level=2,
        confidence_level=ConfidenceLevel.MEDIUM,
        reasoning="test",
    )


def _make_team_stats() -> _Simple:
    return _Simple(
        matches_played=10,
        wins=6,
        draws=2,
        losses=2,
        goals_scored=15,
        goals_conceded=8,
        total_shots=120,
        total_shots_on_target=55,
        total_fouls=98,
        recent_form="WWDLW",
        avg_possession=0.56,
        avg_pass_accuracy=0.82,
        total_tackles=140,
        total_interceptions=83,
        total_corners=60,
        total_yellow_cards=24,
        total_red_cards=1,
        matches_with_corners=10,
        matches_with_cards=10,
        recent_corners=[4, 5, 7, 6, 5],
        recent_yellow_cards=[2, 1, 3, 2, 2],
        recent_shots=[10, 9, 12, 11, 8],
        domestic_stats={"matches_played": 8, "wins": 5},
        international_stats={"matches_played": 2, "wins": 1},
    )


def test_extract_features_returns_expected_fixed_length_without_stats():
    features = MLFeatureExtractor.extract_features(_make_pick())

    assert len(features) == MLFeatureExtractor.FEATURE_VECTOR_LENGTH


def test_extract_features_returns_expected_fixed_length_with_stats():
    features = MLFeatureExtractor.extract_features(
        _make_pick(),
        match=None,
        home_stats=_make_team_stats(),
        away_stats=_make_team_stats(),
    )

    assert len(features) == MLFeatureExtractor.FEATURE_VECTOR_LENGTH
