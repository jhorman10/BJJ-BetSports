import asyncio
import datetime

from src.application.services import ml_training_orchestrator as orchestrator
from src.domain.entities.betting_feedback import LearningWeights


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
        def extract_features(self, pick):
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
    )


def _make_match(mid=1):
    league = _Simple(id="L1")
    home_team = _Simple(name="A")
    away_team = _Simple(name="B")
    return _Simple(
        id=mid,
        league=league,
        home_team=home_team,
        away_team=away_team,
        home_goals=2,
        away_goals=1,
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
