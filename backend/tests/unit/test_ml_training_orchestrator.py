import asyncio
import datetime
import sys
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.application.services import ml_training_orchestrator as orchestrator
from src.domain.entities.betting_feedback import LearningWeights
from src.domain.entities.entities import TrainingDataContextBundle


class _Simple:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def _run_prepare(  # noqa: C901
    matches,
    feature_values=None,
):
    feature_values = feature_values or [0.1]

    class DummyTrainingDataService:
        async def fetch_comprehensive_training_data(self, **kwargs):
            return matches

    class DummyStatisticsService:
        def create_empty_stats_dict(self):
            return {}

        def convert_to_domain_stats(self, name, raw):
            return {}

        def calculate_league_averages(self, ms):
            return {}

        def update_team_stats_dict(self, raw, match, is_home=True):
            return None

    class DummyPredictionService:
        def generate_prediction(self, **kwargs):
            return _Simple(
                predicted_home_goals=1.0,
                predicted_away_goals=0.0,
                home_win_probability=0.6,
                draw_probability=0.1,
                away_win_probability=0.3,
                confidence=0.5,
            )

    class DummyResolutionService:
        def resolve_pick(self, pick, match):
            return "WIN", 2.0

    class DummyCacheService:
        def get(self, key):
            return None

    class DummyFeatureExtractor:
        def extract_features(self, pick, match, home_stats, away_stats):
            return feature_values

    class DummyLearningService:
        def get_learning_weights(self):
            return LearningWeights()

    class DummyPicksService:
        def generate_suggested_picks(self, **kwargs):
            # return object with suggested_picks attribute
            pick = _Simple(
                market_type=_Simple(value="winner"),
                market_label="1",
                probability=0.5,
                expected_value=1.0,
                priority_score=0.5,
                reasoning="r",
                risk_level="low",
                is_recommended=True,
            )
            return _Simple(suggested_picks=[pick])

    training_service = DummyTrainingDataService()
    stat_service = DummyStatisticsService()
    pred_service = DummyPredictionService()
    res_service = DummyResolutionService()
    cache_service = DummyCacheService()
    feat_extractor = DummyFeatureExtractor()
    learning_service = DummyLearningService()

    (
        ml_features,
        ml_targets,
        daily_stats,
        match_history,
        team_stats_cache,
        matches_processed,
        total_bets,
        total_staked,
        total_return,
        league_averages_map,
        context_summary,
    ) = await orchestrator.prepare_datasets(
        training_service,
        stat_service,
        pred_service,
        res_service,
        cache_service,
        feat_extractor,
        learning_service,
        picks_service_factory=lambda **kw: DummyPicksService(),
        league_ids=["L1"],
        days_back=10,
    )

    return (
        ml_features,
        ml_targets,
        daily_stats,
        match_history,
        team_stats_cache,
        matches_processed,
        total_bets,
        total_staked,
        total_return,
        league_averages_map,
        context_summary,
    )


def _make_match(
    mid=1,
    league_id="L1",
    home_team_name="A",
    away_team_name="B",
    home_goals=2,
    away_goals=1,
):
    league = _Simple(id=league_id)
    home_team = _Simple(name=home_team_name)
    away_team = _Simple(name=away_team_name)
    return _Simple(
        id=mid,
        league=league,
        home_team=home_team,
        away_team=away_team,
        home_goals=home_goals,
        away_goals=away_goals,
        match_date=datetime.datetime.utcnow(),
    )


def test_prepare_datasets_passes_learning_weights_entity_to_picks_factory():
    captured: dict[str, object] = {}

    class DummyTrainingDataService:
        async def fetch_comprehensive_training_data(self, **kwargs):
            return []

    class DummyStatisticsService:
        def calculate_league_averages(self, matches):
            return {}

    class DummyPicksService:
        pass

    def picks_service_factory(**kwargs):
        captured.update(kwargs)
        return DummyPicksService()

    class DummyLearningService:
        def get_learning_weights(self):
            return LearningWeights()

    asyncio.run(
        orchestrator.prepare_datasets(
            training_data_service=DummyTrainingDataService(),
            statistics_service=DummyStatisticsService(),
            prediction_service=_Simple(),
            resolution_service=_Simple(),
            cache_service=_Simple(),
            feature_extractor=_Simple(),
            learning_service=DummyLearningService(),
            picks_service_factory=picks_service_factory,
            league_ids=["L1"],
            days_back=1,
        )
    )

    assert isinstance(captured["learning_weights"], LearningWeights)


def test_prepare_datasets_basic():
    matches = [_make_match()]
    (
        ml_features,
        ml_targets,
        daily_stats,
        match_history,
        team_stats_cache,
        matches_processed,
        total_bets,
        total_staked,
        total_return,
        league_averages_map,
        context_summary,
    ) = asyncio.run(_run_prepare(matches))

    assert isinstance(ml_features, list)
    assert isinstance(ml_targets, list)
    assert len(ml_features) == len(ml_targets) == 1
    assert matches_processed == 1
    assert total_bets >= 0
    assert isinstance(match_history, list)


def test_train_league_models_calls_fit(monkeypatch):
    # Replace RandomForestClassifier in module with dummy
    class DummyRF:
        def __init__(self, **kwargs):
            self.fitted = False
            self.fit_args = None

        def fit(self, x, y):
            self.fit_args = (x, y)
            self.fitted = True

    monkeypatch.setattr(orchestrator, "RandomForestClassifier", DummyRF)

    x = [[0.1, 0.2], [0.2, 0.3]]
    y = [1, 0]

    clf = orchestrator.train_league_models(x, y)

    assert hasattr(clf, "fitted") and clf.fitted is True
    assert clf.fit_args == (x, y)


def test_prepare_datasets_passes_match_context_to_feature_extractor():
    calls = []

    def create_empty_stats_dict():
        return {
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "home_wins": 0,
            "away_wins": 0,
            "corners_for": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "matches_with_corners": 0,
            "matches_with_cards": 0,
            "shots": 0,
            "shots_on_target": 0,
            "fouls": 0,
            "recent_corners": [],
            "recent_yellow_cards": [],
            "recent_shots": [],
            "recent_form": "",
        }

    def convert_to_domain_stats(name, raw):
        return _Simple(
            matches_played=raw.get("matches_played", 0),
            wins=raw.get("wins", 0),
            draws=raw.get("draws", 0),
            losses=raw.get("losses", 0),
            goals_scored=raw.get("goals_scored", 0),
            goals_conceded=raw.get("goals_conceded", 0),
            home_wins=raw.get("home_wins", 0),
            away_wins=raw.get("away_wins", 0),
            total_corners=raw.get("corners_for", 0),
            total_yellow_cards=raw.get("yellow_cards", 0),
            total_red_cards=raw.get("red_cards", 0),
            total_shots=raw.get("shots", 0),
            total_shots_on_target=raw.get("shots_on_target", 0),
            total_fouls=raw.get("fouls", 0),
            matches_with_corners=raw.get("matches_with_corners", 0),
            matches_with_cards=raw.get("matches_with_cards", 0),
            recent_corners=raw.get("recent_corners", []),
            recent_yellow_cards=raw.get("recent_yellow_cards", []),
            recent_shots=raw.get("recent_shots", []),
            recent_form=raw.get("recent_form", ""),
            domestic_stats=raw.get("domestic_stats"),
            international_stats=raw.get("international_stats"),
        )

    def update_team_stats_dict(raw, match, is_home=True):
        raw["matches_played"] = raw.get("matches_played", 0) + 1
        goals_for = match.home_goals if is_home else match.away_goals
        goals_against = match.away_goals if is_home else match.home_goals
        raw["goals_scored"] = raw.get("goals_scored", 0) + goals_for
        raw["goals_conceded"] = raw.get("goals_conceded", 0) + goals_against

    def generate_prediction(**kwargs):
        return _Simple(
            predicted_home_goals=1.0,
            predicted_away_goals=0.0,
            home_win_probability=0.6,
            draw_probability=0.1,
            away_win_probability=0.3,
            confidence=0.5,
        )

    def extract_features(pick, match, home_stats, away_stats):
        calls.append((match.id, home_stats.matches_played, away_stats.matches_played))
        return [0.1, 0.2]

    def generate_suggested_picks(**kwargs):
        pick = _Simple(
            market_type=_Simple(value="winner"),
            market_label="1",
            probability=0.5,
            expected_value=1.0,
            priority_score=0.5,
            reasoning="r",
            risk_level="low",
            is_recommended=True,
        )
        return _Simple(suggested_picks=[pick])

    asyncio.run(
        orchestrator.prepare_datasets(
            _Simple(
                fetch_comprehensive_training_data=AsyncMock(
                    return_value=[_make_match(1), _make_match(2)]
                )
            ),
            _Simple(
                create_empty_stats_dict=create_empty_stats_dict,
                convert_to_domain_stats=convert_to_domain_stats,
                calculate_league_averages=lambda matches: {},
                update_team_stats_dict=update_team_stats_dict,
            ),
            _Simple(generate_prediction=generate_prediction),
            _Simple(resolve_pick=lambda pick, match: ("WIN", 2.0)),
            _Simple(get=lambda key: None),
            _Simple(extract_features=extract_features),
            _Simple(get_learning_weights=lambda: LearningWeights()),
            picks_service_factory=lambda **kw: _Simple(
                generate_suggested_picks=generate_suggested_picks,
            ),
            league_ids=["L1"],
            days_back=10,
        )
    )

    assert calls == [(1, 0, 0), (2, 1, 1)]


def test_prepare_datasets_uses_contextual_bundle_for_international_leagues():
    calls = []
    target_match = _make_match(1, league_id="LIB")
    support_matches = [
        _make_match(2, league_id="BRA1", home_team_name="A", away_team_name="C"),
        _make_match(3, league_id="ARG1", home_team_name="D", away_team_name="B"),
    ]
    context_bundle = TrainingDataContextBundle(
        target_matches=[target_match],
        support_matches=support_matches,
        support_matches_by_team={
            "a": [support_matches[0]],
            "b": [support_matches[1]],
        },
        coverage_report={
            "mode": "international",
            "requested_league_ids": ("LIB",),
            "target_match_count": 1,
            "support_match_count": 2,
            "team_count": 2,
            "teams": {},
        },
    )

    def create_empty_stats_dict():
        return {
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "home_wins": 0,
            "away_wins": 0,
            "corners_for": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "matches_with_corners": 0,
            "matches_with_cards": 0,
            "shots": 0,
            "shots_on_target": 0,
            "fouls": 0,
            "recent_corners": [],
            "recent_yellow_cards": [],
            "recent_shots": [],
            "recent_form": "",
        }

    def convert_to_domain_stats(name, raw):
        return _Simple(
            matches_played=raw.get("matches_played", 0),
            domestic_stats=raw.get("domestic_stats"),
            international_stats=raw.get("international_stats"),
        )

    def update_team_stats_dict(raw, match, is_home=True):
        raw["matches_played"] = raw.get("matches_played", 0) + 1
        context_key = (
            "international_stats" if match.league.id == "LIB" else "domestic_stats"
        )
        if context_key not in raw:
            raw[context_key] = {"matches_played": 0}
        raw[context_key]["matches_played"] += 1

    def extract_features(pick, match, home_stats, away_stats):
        calls.append(
            {
                "match_id": match.id,
                "home_matches": home_stats.matches_played,
                "away_matches": away_stats.matches_played,
                "home_domestic": home_stats.domestic_stats,
                "away_domestic": away_stats.domestic_stats,
            }
        )
        return [0.1, 0.2]

    def generate_prediction(**kwargs):
        return _Simple(
            predicted_home_goals=1.0,
            predicted_away_goals=0.0,
            home_win_probability=0.6,
            draw_probability=0.1,
            away_win_probability=0.3,
            confidence=0.5,
        )

    def generate_suggested_picks(**kwargs):
        return _Simple(
            suggested_picks=[
                _Simple(
                    market_type=_Simple(value="winner"),
                    market_label="1",
                    probability=0.5,
                    expected_value=1.0,
                    priority_score=0.5,
                    reasoning="r",
                    risk_level="low",
                    is_recommended=True,
                )
            ]
        )

    training_data_service = _Simple(
        fetch_contextual_training_data=AsyncMock(return_value=context_bundle),
        fetch_comprehensive_training_data=AsyncMock(return_value=[target_match]),
    )

    asyncio.run(
        orchestrator.prepare_datasets(
            training_data_service,
            _Simple(
                create_empty_stats_dict=create_empty_stats_dict,
                convert_to_domain_stats=convert_to_domain_stats,
                calculate_league_averages=lambda matches: {},
                update_team_stats_dict=update_team_stats_dict,
            ),
            _Simple(generate_prediction=generate_prediction),
            _Simple(resolve_pick=lambda pick, match: ("WIN", 2.0)),
            _Simple(get=lambda key: None),
            _Simple(extract_features=extract_features),
            _Simple(get_learning_weights=lambda: LearningWeights()),
            picks_service_factory=lambda **kw: _Simple(
                generate_suggested_picks=generate_suggested_picks,
            ),
            league_ids=["LIB"],
            days_back=10,
        )
    )

    training_data_service.fetch_contextual_training_data.assert_awaited_once()
    training_data_service.fetch_comprehensive_training_data.assert_not_awaited()
    assert calls == [
        {
            "match_id": 1,
            "home_matches": 1,
            "away_matches": 1,
            "home_domestic": {"matches_played": 1},
            "away_domestic": {"matches_played": 1},
        }
    ]


def test_run_training_pipeline_exposes_context_summary_for_international_leagues():
    target_match = _make_match(1, league_id="LIB")
    support_matches = [
        _make_match(2, league_id="BRA1", home_team_name="A", away_team_name="C"),
        _make_match(3, league_id="WC", home_team_name="D", away_team_name="B"),
    ]
    context_bundle = TrainingDataContextBundle(
        target_matches=[target_match],
        support_matches=support_matches,
        support_matches_by_team={
            "a": [support_matches[0]],
            "b": [],
        },
        coverage_report={
            "mode": "international",
            "requested_league_ids": ("LIB",),
            "target_match_count": 1,
            "support_match_count": 2,
            "team_count": 2,
            "teams": {
                "a": {
                    "participant_type": "club",
                    "base_competition_id": "BRA1",
                    "support_competition_ids": ("LIB",),
                    "target_match_count": 1,
                    "support_match_count": 1,
                    "confidence": 0.9,
                    "evidence": {"resolution": "resolved"},
                },
                "b": {
                    "participant_type": "national_team",
                    "base_competition_id": "WC",
                    "support_competition_ids": (),
                    "target_match_count": 1,
                    "support_match_count": 0,
                    "confidence": 0.4,
                    "evidence": {"resolution": "ambiguous"},
                },
            },
        },
    )

    def create_empty_stats_dict():
        return {
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "home_wins": 0,
            "away_wins": 0,
            "corners_for": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            "matches_with_corners": 0,
            "matches_with_cards": 0,
            "shots": 0,
            "shots_on_target": 0,
            "fouls": 0,
            "recent_corners": [],
            "recent_yellow_cards": [],
            "recent_shots": [],
            "recent_form": "",
        }

    def convert_to_domain_stats(name, raw):
        return _Simple(
            matches_played=raw.get("matches_played", 0),
            domestic_stats=raw.get("domestic_stats"),
            international_stats=raw.get("international_stats"),
        )

    def update_team_stats_dict(raw, match, is_home=True):
        raw["matches_played"] = raw.get("matches_played", 0) + 1

    training_data_service = _Simple(
        fetch_contextual_training_data=AsyncMock(return_value=context_bundle),
        fetch_comprehensive_training_data=AsyncMock(return_value=[target_match]),
    )
    statistics_service = _Simple(
        create_empty_stats_dict=create_empty_stats_dict,
        convert_to_domain_stats=convert_to_domain_stats,
        calculate_league_averages=lambda matches: {},
        update_team_stats_dict=update_team_stats_dict,
    )
    prediction_service = _Simple(
        generate_prediction=lambda **kwargs: _Simple(
            predicted_home_goals=1.0,
            predicted_away_goals=0.0,
            home_win_probability=0.6,
            draw_probability=0.1,
            away_win_probability=0.3,
            confidence=0.5,
        )
    )
    learning_service = _Simple(
        get_learning_weights=lambda: LearningWeights(),
        get_all_stats=lambda: {},
    )
    orchestrator_service = orchestrator.MLTrainingOrchestrator(
        training_data_service=training_data_service,
        statistics_service=statistics_service,
        prediction_service=prediction_service,
        learning_service=learning_service,
        resolution_service=_Simple(resolve_pick=lambda pick, match: ("WIN", 2.0)),
        cache_service=_Simple(get=lambda key: None),
    )
    orchestrator_service.feature_extractor = _Simple(
        extract_features=lambda pick, match, home_stats, away_stats: [0.1, 0.2],
    )

    result = asyncio.run(orchestrator_service.run_training_pipeline(league_ids=["LIB"]))

    assert result.context_summary == {
        "mode": "international",
        "requested_league_ids": ["LIB"],
        "team_count": 2,
        "target_match_count": 1,
        "support_match_count": 2,
        "complete_context_teams": 1,
        "ambiguous_resolution_teams": 1,
        "clubs_without_domestic_context": 0,
        "national_teams_without_baseline": 1,
        "teams_without_target_history": 1,
    }
