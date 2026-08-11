import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.domain.value_objects.value_objects import LeagueAverages

# ML Imports
try:
    from sklearn.ensemble import RandomForestClassifier

    ML_AVAILABLE = True
except ImportError:
    RandomForestClassifier = None
    ML_AVAILABLE = False

from src.application.services.ml_training_orchestrator_helper import (
    _process_single_match_task,
)
from src.application.services.training_data_service import TrainingDataService
from src.core.constants import DEFAULT_LEAGUES
from src.core.model_artifacts import cleanup_model_artifacts
from src.domain.constants import ALL_INTERNATIONAL_TOURNAMENTS
from src.domain.services.learning_service import LearningService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.pick_resolution_service import PickResolutionService
from src.domain.services.picks_service import PicksService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.cache.cache_service import CacheService

logger = logging.getLogger(__name__)


def _build_league_averages(
    all_matches: List[Any], statistics_service: StatisticsService
) -> Dict[str, "LeagueAverages"]:
    league_matches_map: Dict[str, List[Any]] = {}
    for m in all_matches:
        league_matches_map.setdefault(m.league.id, []).append(m)
    return {
        lid: statistics_service.calculate_league_averages(ms)
        for lid, ms in league_matches_map.items()
    }


def _get_iterator(all_matches: List[Any]) -> Any:
    try:
        from tqdm import tqdm

        return tqdm(all_matches, desc="Training", unit="match")
    except Exception:
        return all_matches


def _ensure_team_stats(
    team_stats_cache: dict[str, dict[str, Any]],
    statistics_service: StatisticsService,
    match: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if match.home_team.name not in team_stats_cache:
        team_stats_cache[match.home_team.name] = (
            statistics_service.create_empty_stats_dict()
        )
    if match.away_team.name not in team_stats_cache:
        team_stats_cache[match.away_team.name] = (
            statistics_service.create_empty_stats_dict()
        )
    return (
        team_stats_cache[match.home_team.name],
        team_stats_cache[match.away_team.name],
    )


def _requires_contextual_training_bundle(leagues: List[str]) -> bool:
    return any(league_id in ALL_INTERNATIONAL_TOURNAMENTS for league_id in leagues)


async def _load_training_matches(
    training_data_service: TrainingDataService,
    leagues: List[str],
    days_back: int,
    start_date: Optional[str],
    force_refresh: bool,
) -> tuple[List[Any], List[Any], Optional[Dict[str, Any]]]:
    if _requires_contextual_training_bundle(leagues):
        context_bundle = await training_data_service.fetch_contextual_training_data(
            leagues=leagues,
            days_back=days_back,
            start_date=start_date,
            force_refresh=force_refresh,
        )
        return (
            context_bundle.target_matches,
            context_bundle.support_matches,
            context_bundle.coverage_report,
        )

    matches = await training_data_service.fetch_comprehensive_training_data(
        leagues=leagues,
        days_back=days_back,
        start_date=start_date,
        force_refresh=force_refresh,
    )
    return matches, [], None


def _seed_support_team_stats(
    support_matches: List[Any],
    team_stats_cache: Dict[str, dict],
    statistics_service: StatisticsService,
) -> None:
    for match in support_matches:
        if match.home_goals is None or match.away_goals is None:
            continue

        raw_home, raw_away = _ensure_team_stats(
            team_stats_cache, statistics_service, match
        )
        statistics_service.update_team_stats_dict(raw_home, match, is_home=True)
        statistics_service.update_team_stats_dict(raw_away, match, is_home=False)


def _summarize_context_coverage(
    coverage_report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not coverage_report:
        return {}

    requested_league_ids = list(coverage_report.get("requested_league_ids", ()))
    requested_league_set = set(requested_league_ids)
    teams = coverage_report.get("teams", {})
    summary = {
        "mode": coverage_report.get("mode", "domestic"),
        "requested_league_ids": requested_league_ids,
        "team_count": coverage_report.get("team_count", len(teams)),
        "target_match_count": coverage_report.get("target_match_count", 0),
        "support_match_count": coverage_report.get("support_match_count", 0),
        "complete_context_teams": 0,
        "ambiguous_resolution_teams": 0,
        "clubs_without_domestic_context": 0,
        "national_teams_without_baseline": 0,
        "teams_without_target_history": 0,
    }

    for team_report in teams.values():
        participant_type = team_report.get("participant_type")
        base_competition_id = team_report.get("base_competition_id")
        support_match_count = int(team_report.get("support_match_count", 0) or 0)
        support_competition_ids = set(team_report.get("support_competition_ids", ()))
        confidence = float(team_report.get("confidence", 0.0) or 0.0)
        evidence = team_report.get("evidence") or {}
        is_ambiguous = evidence.get("resolution") == "ambiguous" or confidence < 0.5

        if is_ambiguous:
            summary["ambiguous_resolution_teams"] += 1

        if requested_league_set.isdisjoint(support_competition_ids):
            summary["teams_without_target_history"] += 1

        if participant_type == "club" and (
            not base_competition_id or support_match_count == 0
        ):
            summary["clubs_without_domestic_context"] += 1

        if participant_type == "national_team" and support_match_count == 0:
            summary["national_teams_without_baseline"] += 1

        has_complete_context = support_match_count > 0 and not is_ambiguous
        if participant_type == "club":
            has_complete_context = has_complete_context and bool(base_competition_id)

        if has_complete_context:
            summary["complete_context_teams"] += 1

    return summary


def _parse_cached_suggested_picks(
    cached_result: Optional[dict[str, Any]], match: Any
) -> Any | None:
    if not cached_result or "suggested_picks" not in cached_result:
        return None
    try:
        from src.application.dtos.dtos import MatchSuggestedPicksDTO
        from src.domain.entities.suggested_pick import (
            ConfidenceLevel,
            MarketType,
            MatchSuggestedPicks,
            SuggestedPick,
        )

        dto = MatchSuggestedPicksDTO(**cached_result)
        suggested_picks_container = MatchSuggestedPicks(match_id=match.id)
        for p in dto.suggested_picks:
            suggested_picks_container.add_pick(
                SuggestedPick(
                    market_type=MarketType(p.market_type),
                    market_label=p.market_label,
                    probability=p.probability,
                    confidence_level=ConfidenceLevel(p.confidence_level),
                    reasoning=p.reasoning,
                    risk_level=p.risk_level,
                    is_recommended=p.is_recommended,
                    priority_score=p.priority_score,
                    expected_value=p.expected_value or 0.0,
                )
            )
        return suggested_picks_container
    except Exception:
        return None


def _compute_picks_metrics(
    picks_to_process: List[Any],
    resolution_service: PickResolutionService,
    feature_extractor: MLFeatureExtractor,
    match: Any,
    home_stats: Any,
    away_stats: Any,
) -> tuple[
    List[dict[str, Any]],
    List[Any],
    List[int],
    int,
    float,
    float,
    Optional[str],
    bool,
    float,
]:
    picks_list: List[dict] = []
    ml_feats: List[Any] = []
    ml_tgts: List[int] = []
    total_bets = 0
    total_staked = 0.0
    total_return = 0.0
    suggested_pick_label = None
    pick_was_correct = False
    max_ev_value = -100.0

    for pick in picks_to_process:
        result_str, payout = resolution_service.resolve_pick(pick, match)
        is_won = result_str == "WIN"

        p_detail = {
            "market_type": (
                pick.market_type.value
                if hasattr(pick.market_type, "value")
                else str(pick.market_type)
            ),
            "market_label": pick.market_label,
            "was_correct": is_won,
            "probability": float(pick.probability),
            "expected_value": float(pick.expected_value),
            "confidence": float(pick.priority_score or pick.probability),
            "reasoning": pick.reasoning,
            "result": result_str,
        }
        picks_list.append(p_detail)

        ml_feats.append(
            feature_extractor.extract_features(
                pick,
                match,
                home_stats,
                away_stats,
            )
        )
        ml_tgts.append(1 if is_won else 0)

        if p_detail["market_type"] in ["winner", "draw", "result_1x2"]:
            total_bets += 1
            total_staked += 1.0
            total_return += payout
            if float(pick.expected_value) > max_ev_value:
                suggested_pick_label = pick.market_label
                pick_was_correct = is_won
                max_ev_value = float(pick.expected_value)

    return (
        picks_list,
        ml_feats,
        ml_tgts,
        total_bets,
        total_staked,
        total_return,
        suggested_pick_label,
        pick_was_correct,
        max_ev_value,
    )


def _update_daily_stats(
    daily_stats: dict, match_date: Any, staked_inc: float, pick_was_correct: bool
) -> None:
    date_key = match_date.strftime("%Y-%m-%d")
    if date_key not in daily_stats:
        daily_stats[date_key] = {"staked": 0.0, "return": 0.0, "count": 0}
    daily_stats[date_key]["staked"] += staked_inc
    daily_stats[date_key]["return"] += 2.0 if pick_was_correct else 0.0
    daily_stats[date_key]["count"] += 1


def _build_match_history_entry(
    match: Any,
    prediction: Any,
    picks_list: List[dict],
    suggested_pick_label: Optional[str],
    pick_was_correct: bool,
    max_ev_value: float,
) -> dict:
    return {
        "match_id": match.id,
        "home_team": match.home_team.name,
        "away_team": match.away_team.name,
        "match_date": match.match_date.isoformat(),
        "predicted_winner": (
            "home"
            if prediction.home_win_probability > prediction.away_win_probability
            and prediction.home_win_probability > prediction.draw_probability
            else (
                "away"
                if prediction.away_win_probability > prediction.home_win_probability
                and prediction.away_win_probability > prediction.draw_probability
                else "draw"
            )
        ),
        "actual_winner": (
            "home"
            if match.home_goals > match.away_goals
            else ("away" if match.away_goals > match.home_goals else "draw")
        ),
        "predicted_home_goals": round(prediction.predicted_home_goals, 2),
        "predicted_away_goals": round(prediction.predicted_away_goals, 2),
        "actual_home_goals": match.home_goals,
        "actual_away_goals": match.away_goals,
        "was_correct": (
            (
                prediction.home_win_probability > prediction.away_win_probability
                and prediction.home_win_probability > prediction.draw_probability
                and match.home_goals > match.away_goals
            )
            or (
                prediction.away_win_probability > prediction.home_win_probability
                and prediction.away_win_probability > prediction.draw_probability
                and match.away_goals > match.home_goals
            )
            or (
                prediction.draw_probability >= prediction.home_win_probability
                and prediction.draw_probability >= prediction.away_win_probability
                and match.home_goals == match.away_goals
            )
        ),
        "confidence": round(prediction.confidence, 3),
        "home_win_probability": round(prediction.home_win_probability, 4),
        "draw_probability": round(prediction.draw_probability, 4),
        "away_win_probability": round(prediction.away_win_probability, 4),
        "picks": picks_list,
        "suggested_pick": suggested_pick_label,
        "pick_was_correct": pick_was_correct,
        "expected_value": max_ev_value,
    }


def _process_match_for_dataset(
    match: Any,
    raw_home: dict[str, Any],
    raw_away: dict[str, Any],
    prediction_service: PredictionService,
    cache_service: CacheService,
    picks_service_instance: PicksService,
    resolution_service: PickResolutionService,
    feature_extractor: MLFeatureExtractor,
    statistics_service: StatisticsService,
    league_averages_map: Dict[str, "LeagueAverages"],
) -> (
    tuple[
        List[Any],
        List[int],
        List[dict[str, Any]],
        int,
        float,
        float,
        Optional[str],
        bool,
        float,
        dict[str, Any],
    ]
    | None
):
    """Process a single match into ML-ready features, targets and a history entry.

    Returns a tuple of (feats_add, tgts_add, picks_list, bets_inc, staked_inc,
    return_inc, suggested_pick_label, pick_was_correct, max_ev_value, match_entry)
    or None on error.
    """
    try:
        league_averages = league_averages_map.get(match.league.id)

        processed_match = _process_single_match_task(
            match=match,
            raw_home=raw_home,
            raw_away=raw_away,
            league_averages=league_averages,
            global_averages_obj=None,
            prediction_service=prediction_service,
            picks_service=picks_service_instance,
            statistics_service=statistics_service,
            resolution_service=resolution_service,
            feature_extractor=feature_extractor,
        )
        if not processed_match:
            return None

        (
            _,
            prediction,
            generated_picks_container,
            home_stats,
            away_stats,
        ) = processed_match

        cache_key = f"forecasts:match_{match.id}"
        cached_result = cache_service.get(cache_key)

        suggested_picks_container = _parse_cached_suggested_picks(cached_result, match)
        if not suggested_picks_container:
            suggested_picks_container = generated_picks_container

        picks_to_process = (
            suggested_picks_container.suggested_picks
            if suggested_picks_container
            else []
        )

        (
            picks_list_local,
            feats_add,
            tgts_add,
            bets_inc,
            staked_inc,
            return_inc,
            suggested_pick_label,
            pick_was_correct,
            max_ev_value,
        ) = _compute_picks_metrics(
            picks_to_process,
            resolution_service,
            feature_extractor,
            match,
            home_stats,
            away_stats,
        )

        match_entry = _build_match_history_entry(
            match,
            prediction,
            picks_list_local,
            suggested_pick_label,
            pick_was_correct,
            max_ev_value,
        )

        return (
            feats_add,
            tgts_add,
            picks_list_local,
            bets_inc,
            staked_inc,
            return_inc,
            suggested_pick_label,
            pick_was_correct,
            max_ev_value,
            match_entry,
        )
    except Exception as exc:  # pragma: no cover - preserve original behaviour
        logger.error("Error processing match %s: %s", getattr(match, "id", "?"), exc)
        return None


async def prepare_datasets(
    training_data_service: TrainingDataService,
    statistics_service: StatisticsService,
    prediction_service: PredictionService,
    resolution_service: PickResolutionService,
    cache_service: CacheService,
    feature_extractor: MLFeatureExtractor,
    learning_service: LearningService,
    picks_service_factory: Callable = PicksService,
    league_ids: Optional[List[str]] = None,
    days_back: int = 365,
    start_date: Optional[str] = None,
    force_refresh: bool = False,
) -> Tuple[
    List[Any],
    List[int],
    Dict[str, dict],
    List[dict],
    Dict[str, dict],
    int,
    int,
    float,
    float,
    Dict[str, "LeagueAverages"],
    Dict[str, Any],
]:
    """Fetches matches and processes them into ML-ready datasets.

    Returns a tuple with: (ml_features, ml_targets, daily_stats, match_history,
    team_stats_cache, matches_processed, total_bets, total_staked, total_return,
    league_averages_map, context_summary)
    """
    picks_service_instance = picks_service_factory(
        learning_weights=learning_service.get_learning_weights()
    )

    matches_processed = 0
    total_bets = 0
    total_staked = 0.0
    total_return = 0.0
    daily_stats: Dict[str, dict] = {}
    match_history: List[dict] = []

    ml_features: List[Any] = []
    ml_targets: List[int] = []

    leagues = league_ids if league_ids else DEFAULT_LEAGUES
    all_matches, support_matches, coverage_report = await _load_training_matches(
        training_data_service,
        leagues=leagues,
        days_back=days_back,
        start_date=start_date,
        force_refresh=force_refresh,
    )
    context_summary = _summarize_context_coverage(coverage_report)

    league_matches_map: Dict[str, List[Any]] = {}
    for m in all_matches:
        if m.league.id not in league_matches_map:
            league_matches_map[m.league.id] = []
        league_matches_map[m.league.id].append(m)

    league_averages_map = {
        lid: statistics_service.calculate_league_averages(ms)
        for lid, ms in league_matches_map.items()
    }

    team_stats_cache: Dict[str, dict] = {}
    _seed_support_team_stats(support_matches, team_stats_cache, statistics_service)

    total_matches = len(all_matches)
    logger.info("Processing %s matches...", total_matches)
    if context_summary:
        logger.info("Context coverage summary: %s", context_summary)

    try:
        from tqdm import tqdm

        iterator = tqdm(all_matches, desc="Training", unit="match")
    except Exception:
        iterator = all_matches

    for match in iterator:
        if match.home_goals is None or match.away_goals is None:
            continue

        # Ensure team stats exist and get the raw dicts
        raw_home, raw_away = _ensure_team_stats(
            team_stats_cache, statistics_service, match
        )

        # Delegate heavy per-match processing to helper
        processed = _process_match_for_dataset(
            match,
            raw_home,
            raw_away,
            prediction_service,
            cache_service,
            picks_service_instance,
            resolution_service,
            feature_extractor,
            statistics_service,
            league_averages_map,
        )

        if not processed:
            continue

        (
            feats_add,
            tgts_add,
            picks_list_local,
            bets_inc,
            staked_inc,
            return_inc,
            suggested_pick_label,
            pick_was_correct,
            max_ev_value,
            match_entry,
        ) = processed

        matches_processed += 1

        ml_features.extend(feats_add)
        ml_targets.extend(tgts_add)
        total_bets += bets_inc
        total_staked += staked_inc
        total_return += return_inc

        _update_daily_stats(daily_stats, match.match_date, staked_inc, pick_was_correct)

        match_history.append(match_entry)

        # Cooperative multitasking for long loops
        if matches_processed % 100 == 0:
            await asyncio.sleep(0)

        statistics_service.update_team_stats_dict(raw_home, match, is_home=True)
        statistics_service.update_team_stats_dict(raw_away, match, is_home=False)

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


def train_league_models(ml_features: List[Any], ml_targets: List[int]) -> Any:
    """Train a RandomForestClassifier on the provided features/targets and return it."""
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=42, n_jobs=-1
    )
    clf.fit(ml_features, ml_targets)
    return clf


def evaluate_models(
    match_history: List[dict], total_staked: float, total_return: float
) -> Tuple[float, float, float]:
    """Compute accuracy, profit and ROI from match history and stake/return totals."""
    if not match_history:
        return 0.0, 0.0, 0.0
    correct = sum(1 for m in match_history if m.get("was_correct"))
    accuracy = correct / len(match_history)
    profit = total_return - total_staked
    roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
    return accuracy, profit, roi


class TrainingResult(BaseModel):
    matches_processed: int
    correct_predictions: int
    accuracy: float
    total_bets: int
    roi: float
    profit_units: float
    market_stats: dict
    match_history: List[Any] = []
    roi_evolution: List[Any] = []
    pick_efficiency: List[Any] = []
    team_stats: dict = {}
    context_summary: dict = {}


class MLTrainingOrchestrator:
    """
    Application service that orchestrates the entire ML training pipeline.
    Coordinates data fetching, feature extraction, training, and result calculation.
    """

    CACHE_KEY_STATUS = "ml_training_status"
    CACHE_KEY_MESSAGE = "ml_training_message"
    CACHE_KEY_RESULT = "ml_training_result_data"

    def __init__(
        self,
        training_data_service: TrainingDataService,
        statistics_service: StatisticsService,
        prediction_service: PredictionService,
        learning_service: LearningService,
        resolution_service: PickResolutionService,
        cache_service: CacheService,
        persistence_repo: Optional[Any] = None,
    ):
        self.training_data_service = training_data_service
        self.statistics_service = statistics_service
        self.prediction_service = prediction_service
        self.learning_service = learning_service
        self.resolution_service = resolution_service
        self.cache_service = cache_service
        self.persistence_repo = persistence_repo
        self.feature_extractor = MLFeatureExtractor()

    async def run_training_pipeline(
        self,
        league_ids: Optional[List[str]] = None,
        days_back: int = 365,
        start_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> TrainingResult:
        """Executes the full training pipeline and returns a TrainingResult.
        This method delegates dataset preparation and model training to module
        level helpers to reduce cognitive complexity.
        """
        logger.info(
            "Starting ML Training Pipeline (leagues=%s, days_back=%s)",
            league_ids,
            days_back,
        )
        try:
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
            ) = await prepare_datasets(
                self.training_data_service,
                self.statistics_service,
                self.prediction_service,
                self.resolution_service,
                self.cache_service,
                self.feature_extractor,
                self.learning_service,
                PicksService,
                league_ids,
                days_back,
                start_date,
                force_refresh,
            )

            # --- TRAIN ML MODEL ---
            if ML_AVAILABLE and RandomForestClassifier and len(ml_features) > 100:
                try:
                    logger.info("Training ML Model on %s samples...", len(ml_features))

                    def _train_model() -> Any:
                        return train_league_models(ml_features, ml_targets)

                    loop = asyncio.get_running_loop()
                    trained_model = await loop.run_in_executor(None, _train_model)

                    # --- PERSIST TO DB ---
                    if self.persistence_repo:
                        from io import BytesIO

                        import joblib
                        from src.core.constants import ML_MODEL_FILENAME

                        logger.info("💾 Persisting trained model to Database...")
                        buffer = BytesIO()
                        joblib.dump(trained_model, buffer)
                        self.persistence_repo.save_binary_artifact(
                            ML_MODEL_FILENAME, buffer.getvalue()
                        )
                        logger.info("✅ Model persisted to Database successfully.")

                    logger.info(
                        "ML Model trained and persisted for the current pipeline run."
                    )
                except Exception as e:
                    logger.exception(f"Failed to train or persist ML model: {e}")

            # --- PREPARE RESULTS ---
            accuracy = self._calculate_accuracy(match_history)
            profit = total_return - total_staked
            roi = (profit / total_staked * 100) if total_staked > 0 else 0.0

            return TrainingResult(
                matches_processed=matches_processed,
                correct_predictions=self._get_correct_count(match_history),
                accuracy=round(accuracy, 4),
                total_bets=total_bets,
                roi=round(roi, 2),
                profit_units=round(profit, 2),
                market_stats=self.learning_service.get_all_stats(),
                match_history=match_history,
                roi_evolution=self._calculate_roi_evolution(daily_stats),
                pick_efficiency=self._calculate_pick_efficiency(match_history),
                team_stats=team_stats_cache,
                context_summary=context_summary,
            )
        finally:
            cleanup_model_artifacts(logger)
            if self.persistence_repo is not None:
                try:
                    from src.infrastructure.training.repositories import (
                        TrainingJobEventRepository,
                        TrainingJobRepository,
                    )

                    TrainingJobRepository(
                        persistence_repo=self.persistence_repo
                    ).delete_completed(logger)
                    TrainingJobEventRepository(
                        persistence_repo=self.persistence_repo
                    ).delete_for_removed_jobs(logger)
                except Exception as exc:
                    logger.warning("Failed to cleanup training jobs: %s", exc)

    def _get_predicted_winner(self, prediction: Any) -> str:
        if (
            prediction.home_win_probability > prediction.away_win_probability
            and prediction.home_win_probability > prediction.draw_probability
        ):
            return "home"
        elif (
            prediction.away_win_probability > prediction.home_win_probability
            and prediction.away_win_probability > prediction.draw_probability
        ):
            return "away"
        return "draw"

    def _get_actual_winner(self, match: Any) -> str:
        if match.home_goals > match.away_goals:
            return "home"
        elif match.away_goals > match.home_goals:
            return "away"
        return "draw"

    def _get_correct_count(self, history: List[dict]) -> int:
        return sum(1 for m in history if m["was_correct"])

    def _calculate_accuracy(self, history: List[dict]) -> float:
        if not history:
            return 0.0
        return self._get_correct_count(history) / len(history)

    def _calculate_roi_evolution(self, daily_stats: dict) -> List[dict]:
        roi_evolution = []
        cum_staked = 0.0
        cum_return = 0.0
        for date_str in sorted(daily_stats.keys()):
            stats = daily_stats[date_str]
            cum_staked += stats["staked"]
            cum_return += stats["return"]
            profit = cum_return - cum_staked
            roi = (profit / cum_staked * 100) if cum_staked > 0 else 0.0
            roi_evolution.append(
                {"date": date_str, "roi": round(roi, 2), "profit": round(profit, 2)}
            )
        return roi_evolution

    def _calculate_pick_efficiency(self, history: List[dict]) -> List[dict]:
        pick_type_stats = {}
        for match in history:
            for pick in match["picks"]:
                ptype = pick["market_type"]
                if ptype not in pick_type_stats:
                    pick_type_stats[ptype] = {
                        "won": 0,
                        "lost": 0,
                        "void": 0,
                        "total": 0,
                    }
                pick_type_stats[ptype]["total"] += 1
                if pick["was_correct"]:
                    pick_type_stats[ptype]["won"] += 1
                else:
                    pick_type_stats[ptype]["lost"] += 1

        results = []
        for ptype, data in pick_type_stats.items():
            efficiency = (
                (data["won"] / data["total"] * 100) if data["total"] > 0 else 0.0
            )
            results.append(
                {
                    "pick_type": ptype,
                    "won": data["won"],
                    "lost": data["lost"],
                    "void": data["void"],
                    "total": data["total"],
                    "efficiency": round(efficiency, 2),
                }
            )
        results.sort(key=lambda x: x["efficiency"], reverse=True)
        return results
