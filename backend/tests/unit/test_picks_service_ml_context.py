import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.domain.entities.betting_feedback import LearningWeights
from src.domain.entities.entities import League, Match, Team, TeamStatistics
from src.domain.entities.suggested_pick import (
    ConfidenceLevel,
    MarketType,
    MatchSuggestedPicks,
    SuggestedPick,
)
from src.domain.services.ai_picks_service import AIPicksService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.picks_service import PicksService


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


def _build_result_pick(match: Match) -> SuggestedPick:
    return SuggestedPick(
        market_type=MarketType.RESULT_1X2,
        market_label=match.home_team.name,
        probability=0.72,
        confidence_level=ConfidenceLevel.HIGH,
        reasoning="test",
        risk_level=2,
        priority_score=1.0,
        odds=1.95,
        expected_value=0.18,
    )


def test_apply_ml_refinement_passes_context_to_feature_extractor(monkeypatch):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    pick = _build_result_pick(match)
    picks_container = MatchSuggestedPicks(match_id=match.id, suggested_picks=[pick])
    captured_calls = []

    def fake_extract_features(pick_arg, match_arg, home_arg, away_arg):
        captured_calls.append(
            (pick_arg.market_label, match_arg.id, home_arg.team_id, away_arg.team_id)
        )
        return [0.1, 0.2, 0.3]

    class DummyOutcomeModel:
        def predict_proba(self, features):
            return [[0.05, 0.9, 0.05]]

    monkeypatch.setattr(
        MLFeatureExtractor,
        "extract_features",
        staticmethod(fake_extract_features),
    )

    service = PicksService(learning_weights=LearningWeights())
    service._apply_ml_refinement(
        picks_container,
        DummyOutcomeModel(),
        match,
        home_stats,
        away_stats,
    )

    assert captured_calls == [
        (pick.market_label, match.id, home_stats.team_id, away_stats.team_id)
    ]
    assert pick.is_ml_confirmed is True


def test_ai_picks_batch_refinement_passes_context_to_feature_extractor(monkeypatch):
    match = _build_match()
    home_stats = _build_stats("palmeiras")
    away_stats = _build_stats("river")
    pick = _build_result_pick(match)
    captured_calls = []

    def fake_extract_features(pick_arg, match_arg, home_arg, away_arg):
        captured_calls.append(
            (pick_arg.market_label, match_arg.id, home_arg.team_id, away_arg.team_id)
        )
        return [0.4, 0.5, 0.6]

    class DummyBatchModel:
        def predict_proba(self, features_batch):
            return [[0.2, 0.8] for _ in features_batch]

    def fake_generate_suggested_picks(self, *args, **kwargs):
        return MatchSuggestedPicks(match_id=match.id, suggested_picks=[pick])

    monkeypatch.setattr(
        MLFeatureExtractor,
        "extract_features",
        staticmethod(fake_extract_features),
    )
    monkeypatch.setattr(
        PicksService,
        "generate_suggested_picks",
        fake_generate_suggested_picks,
    )

    service = AIPicksService(learning_weights=LearningWeights())
    result = service.generate_suggested_picks(
        match,
        home_stats,
        away_stats,
        ml_model=DummyBatchModel(),
    )

    assert captured_calls == [
        (pick.market_label, match.id, home_stats.team_id, away_stats.team_id)
    ]
    assert len(result.suggested_picks) == 1
    assert result.suggested_picks[0].ml_confidence == 0.8