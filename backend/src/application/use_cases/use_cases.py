from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from pytz import timezone

if TYPE_CHECKING:
    from src.domain.entities.entities import TeamStatistics

from src.application.dtos.dtos import (
    CountryDTO,
    LeagueDTO,
    LeaguesResponseDTO,
    MatchDTO,
    MatchPredictionDTO,
    PredictionDTO,
    PredictionsResponseDTO,
    SuggestedPickDTO,
    TeamDTO,
)
from src.domain.constants import (
    ALL_INTERNATIONAL_TOURNAMENTS,
    CLUB_INTERNATIONAL_LEAGUES,
)
from src.domain.entities.entities import (
    League,
    Match,
    Prediction,
    TrainingDataContextBundle,
)
from src.domain.services.match_aggregator_service import MatchAggregatorService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.data_sources.club_elo import ClubEloSource
from src.infrastructure.data_sources.espn import ESPNSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient

logger = logging.getLogger(__name__)


@dataclass
class DataSources:
    """Container for all data sources."""

    football_data_uk: FootballDataUKSource
    football_data_org: FootballDataOrgSource
    openfootball: OpenFootballSource
    thesportsdb: TheSportsDBClient
    espn: Optional[ESPNSource] = None
    club_elo: Optional[ClubEloSource] = None


# Lightweight type aliases to satisfy linters for runtime-opaque types
MongoRepository = Any
BackgroundProcessor = Any


def _requires_contextual_team_statistics(league_id: str) -> bool:
    """Return True when a match requires contextual international team stats."""
    return league_id in ALL_INTERNATIONAL_TOURNAMENTS


def _context_bundle_has_team_context(
    context_bundle: TrainingDataContextBundle,
    team_name: str,
) -> bool:
    normalized_team_name = StatisticsService.normalize_team_name(team_name)
    if normalized_team_name in context_bundle.support_matches_by_team:
        return True

    return any(
        normalized_team_name
        in {
            StatisticsService.normalize_team_name(match.home_team.name),
            StatisticsService.normalize_team_name(match.away_team.name),
        }
        for match in context_bundle.target_matches
    )


async def _load_contextual_training_bundle(
    league_id: str,
) -> Optional[TrainingDataContextBundle]:
    """Load the contextual target/support bundle for international inference."""
    if not _requires_contextual_team_statistics(league_id):
        return None

    try:
        from src.application.dependencies import get_training_data_service

        context_bundle = cast(
            TrainingDataContextBundle,
            await get_training_data_service().fetch_contextual_training_data(
                leagues=[league_id],
                days_back=550,
            ),
        )
    except Exception as exc:
        logger.warning(
            "Failed to load contextual training bundle for %s: %s",
            league_id,
            exc,
        )
        return None

    if context_bundle.target_matches or context_bundle.support_matches:
        return context_bundle
    return None


def _build_match_team_statistics(
    statistics_service: StatisticsService,
    team_name: str,
    match: Match,
    historical_matches: list[Match],
    context_bundle: Optional[TrainingDataContextBundle] = None,
) -> TeamStatistics:
    """Build team stats with contextual bundles for international matches."""
    if context_bundle and _context_bundle_has_team_context(context_bundle, team_name):
        return statistics_service.build_contextual_team_statistics(
            team_name,
            match,
            context_bundle,
        )

    return statistics_service.calculate_team_statistics(team_name, historical_matches)


class GetLeaguesUseCase:
    """Use case for getting available leagues."""

    def __init__(self, data_sources: DataSources) -> None:
        self.data_sources = data_sources

    async def execute(self) -> "LeaguesResponseDTO":
        """Get all available leagues grouped by country."""
        # Local imports to avoid module-level runtime cycles and satisfy linters
        from src.core.constants import DEFAULT_LEAGUES
        from src.domain.constants import LEAGUES_METADATA

        # Get all default leagues using metadata
        leagues = []
        for lid in DEFAULT_LEAGUES:
            if lid in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[lid]
                leagues.append(
                    League(
                        id=lid,
                        name=meta["name"],
                        country=meta["country"],
                    )
                )

        # Group by country
        countries_dict: dict[str, list[League]] = {}
        for league in leagues:
            if league.country not in countries_dict:
                countries_dict[league.country] = []
            countries_dict[league.country].append(league)

        # Build response
        countries = []
        for country_name, country_leagues in sorted(countries_dict.items()):
            league_dtos = [
                LeagueDTO(
                    id=league.id,
                    name=league.name,
                    country=league.country,
                    season=league.season,
                )
                for league in country_leagues
            ]
            countries.append(
                CountryDTO(
                    name=country_name,
                    code=country_name[:3].upper(),
                    leagues=league_dtos,
                )
            )

        return LeaguesResponseDTO(
            countries=countries,
            total_leagues=len(leagues),
        )


class GetPredictionsUseCase:
    """Use case for getting match predictions."""

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        match_aggregator: MatchAggregatorService,
        # risk_manager: RiskManager,
        persistence_repository: Optional[Any] = None,
        background_processor: Optional[Any] = None,
    ) -> None:
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.match_aggregator = match_aggregator
        # self.risk_manager = risk_manager
        self.persistence_repository = persistence_repository

        try:
            from src.application.dependencies import get_learning_service

            learning_weights = get_learning_service().get_learning_weights()
        except Exception:
            learning_weights = {}

        from src.domain.services.ai_picks_service import AIPicksService

        self.picks_service = AIPicksService(
            learning_weights=learning_weights,
            persistence_repo=self.persistence_repository,
        )

        self.background_processor = background_processor

        # Reuse the DB-first loader from AIPicksService so training and
        # prediction consume the same persisted artifact source.
        self.ml_model = self.picks_service.ml_model
        if self.ml_model is None:
            logger.info(
                "ML model unavailable from DB/disk. Using heuristic probabilities."
            )
        else:
            logger.info(
                "✅ Loaded ML Model for rigorous probabilities via AIPicksService"
            )

    def _compute_seasons(self) -> list[str]:
        """Compute current and previous season codes like '2425'."""
        now = datetime.now(timezone("America/Bogota"))
        current_year = now.year
        if now.month < 7:
            s1_start = current_year - 1
            s1_end = current_year
            s2_start = current_year - 2
            s2_end = current_year - 1
        else:
            s1_start = current_year
            s1_end = current_year + 1
            s2_start = current_year - 1
            s2_end = current_year

        current_season = f"{str(s1_start)[-2:]}{str(s1_end)[-2:]}"
        prev_season = f"{str(s2_start)[-2:]}{str(s2_end)[-2:]}"
        return [current_season, prev_season]

    def _filter_upcoming_matches(
        self, upcoming_matches: list[Match], now: datetime
    ) -> list[Match]:
        """Return upcoming matches strictly in the future (timezone-aware)."""
        filtered = []
        for m in upcoming_matches:
            m_date = m.match_date
            if m_date.tzinfo is None:
                try:
                    from pytz import timezone as pytz_tz

                    tz = pytz_tz("America/Bogota")
                    m_date = tz.localize(m_date)
                except Exception:
                    m_date = m_date
            else:
                m_date = m_date.astimezone(now.tzinfo)

            if m_date > now:
                filtered.append(m)
        return filtered

    def _determine_data_sources(self) -> list[str]:
        """Return a list of data source names enabled for predictions."""
        # Local imports for data source classes used at runtime
        from src.infrastructure.data_sources.football_data_org import (
            FootballDataOrgSource,
        )
        from src.infrastructure.data_sources.football_data_uk import (
            FootballDataUKSource,
        )
        from src.infrastructure.data_sources.openfootball import OpenFootballSource

        data_sources_used = [FootballDataUKSource.SOURCE_NAME]

        if self.data_sources.football_data_org.is_configured:
            data_sources_used.append(FootballDataOrgSource.SOURCE_NAME)
        if self.data_sources.openfootball:
            data_sources_used.append(OpenFootballSource.SOURCE_NAME)
        # Ensure ESPN is present as a fallback name
        if hasattr(self.data_sources, "espn") or "ESPN" not in data_sources_used:
            data_sources_used.append("ESPN")

        return data_sources_used

    def _build_ml_feature_batch(
        self,
        match: Match,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        outcomes: list[tuple],
    ) -> list[list[float]]:
        """Build features batch for ML model from outcomes and match stats."""
        # Local imports to avoid circular dependencies and satisfy linters
        from src.domain.entities.suggested_pick import ConfidenceLevel, SuggestedPick
        from src.domain.services.ml_feature_extractor import MLFeatureExtractor

        features_batch = []
        for idx, (m_type, heuristic_prob, label) in enumerate(outcomes):
            p = SuggestedPick(
                market_type=m_type,
                market_label=label,
                probability=heuristic_prob,
                expected_value=0.0,
                risk_level=5,
                confidence_level=ConfidenceLevel.MEDIUM,
                reasoning="ML Eval",
            )

            if idx == 0:
                p.market_label = "Victoria Local"
            elif idx == 1:
                p.market_label = "Empate"
            elif idx == 2:
                p.market_label = "Victoria Visitante"
            elif idx == 3:
                p.market_label = "Más de 2.5 Goles"
            elif idx == 4:
                p.market_label = "Menos de 2.5 Goles"

            feat = MLFeatureExtractor.extract_features(
                p,
                match,
                home_stats,
                away_stats,
            )
            features_batch.append(feat)

        return list(features_batch)

    def _normalize_and_apply_probs(
        self, prediction: Prediction, ml_probs: list[float]
    ) -> None:
        """Normalize ML raw probabilities and apply them to the prediction."""
        # Winner normalization
        raw_h, raw_d, raw_a = ml_probs[0], ml_probs[1], ml_probs[2]
        total_1x2 = raw_h + raw_d + raw_a
        if total_1x2 > 0:
            prediction.home_win_probability = round(raw_h / total_1x2, 4)
            prediction.draw_probability = round(raw_d / total_1x2, 4)
            prediction.away_win_probability = round(raw_a / total_1x2, 4)

        # Over/Under normalization
        raw_o, raw_u = ml_probs[3], ml_probs[4]
        total_ou = raw_o + raw_u
        if total_ou > 0:
            prediction.over_25_probability = round(raw_o / total_ou, 4)
            prediction.under_25_probability = round(raw_u / total_ou, 4)

        # Confidence = max of normalized probabilities
        prediction.confidence = max(
            prediction.home_win_probability,
            prediction.draw_probability,
            prediction.away_win_probability,
            prediction.over_25_probability,
            prediction.under_25_probability,
        )

        if "Rigorous ML" not in prediction.data_sources:
            prediction.data_sources.append("Rigorous ML")

    def _apply_ml_override(
        self,
        prediction: Prediction,
        match: Match,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
    ) -> None:
        """Apply ML model probability overrides to a Prediction object in-place.

        This wraps the ML feature extraction and prediction logic previously inline
        in `execute()` so it can be tested and maintained separately.
        """
        if not self.ml_model:
            return

        # Local import for MarketType enum
        from src.domain.entities.suggested_pick import MarketType

        try:
            outcomes = [
                (MarketType.WINNER, prediction.home_win_probability, "Home"),
                (MarketType.WINNER, prediction.draw_probability, "Draw"),
                (MarketType.WINNER, prediction.away_win_probability, "Away"),
                (MarketType.GOALS_OVER_2_5, prediction.over_25_probability, "Over"),
                (MarketType.GOALS_UNDER_2_5, prediction.under_25_probability, "Under"),
            ]

            features_batch = self._build_ml_feature_batch(
                match, home_stats, away_stats, outcomes
            )

            if features_batch:
                probs = cast(Any, self.ml_model).predict_proba(features_batch)

                # Align probabilities via model.classes_ — never positional indices
                # (ml-model-deployment spec: "Probabilities mapped through classes_").
                from src.domain.services.ml_class_alignment import (
                    outcome_probability_map,
                    positive_class_probability,
                )

                ml_probs: list[float] = []
                for i, (mkt, _, label) in enumerate(outcomes):
                    p = probs[i]
                    try:
                        if mkt == MarketType.WINNER:
                            # Outcome classifier (Home/Draw/Away) — map via classes_
                            label_probs = outcome_probability_map(self.ml_model, p)
                            if label == "Home":
                                ml_probs.append(label_probs["home"])
                            elif label == "Draw":
                                ml_probs.append(label_probs["draw"])
                            else:
                                ml_probs.append(label_probs["away"])
                        else:
                            # Binary pick-success classifier (Over/Under) —
                            # locate positive class via classes_
                            ml_probs.append(positive_class_probability(self.ml_model, p))
                    except ValueError as ve:
                        # Unrecognized layout — treat as blend failure
                        logger.warning(
                            "ML Override classes_ alignment failed for %s (%s) — "
                            "using positional fallback for this outcome",
                            label, ve,
                        )
                        ml_probs.append(p[1] if len(p) > 1 else 0.0)

                # Normalize and apply ML probabilities
                self._normalize_and_apply_probs(prediction, ml_probs)

        except Exception as ml_err:
            logger.warning(
                "ML Probability Override failed for match %s: %s", match.id, ml_err
            )

    async def _generate_suggested_picks(
        self, match_tasks: list[dict[str, Any]]
    ) -> list[Any]:
        """Generate suggested picks either via background processor (parallel)
        or synchronously via the picks service.
        Returns a list of results aligned with `match_tasks`.
        """
        if self.background_processor and match_tasks:
            logger.info(
                f"Generating picks for {len(match_tasks)} matches in parallel..."
            )
            parallel_results = await self.background_processor.process_matches_parallel(
                match_tasks
            )
            return cast(list[Any], parallel_results)

        # Fallback synchronous
        logger.info(f"Generating picks for {len(match_tasks)} matches synchronously...")
        results: list[Any] = []
        for task in match_tasks:
            try:
                res = self.picks_service.generate_suggested_picks(
                    match=task["match"],
                    home_stats=task["home_stats"],
                    away_stats=task["away_stats"],
                    league_averages=task.get("league_averages"),
                    h2h_stats=task.get("h2h_stats"),
                    predicted_home_goals=task["prediction_data"].get(
                        "predicted_home_goals", 0.0
                    ),
                    predicted_away_goals=task["prediction_data"].get(
                        "predicted_away_goals", 0.0
                    ),
                    home_win_prob=task["prediction_data"].get(
                        "home_win_probability", 0.0
                    ),
                    draw_prob=task["prediction_data"].get("draw_probability", 0.0),
                    away_win_prob=task["prediction_data"].get(
                        "away_win_probability", 0.0
                    ),
                    predicted_home_corners=task["prediction_data"].get(
                        "predicted_home_corners", 0.0
                    ),
                    predicted_away_corners=task["prediction_data"].get(
                        "predicted_away_corners", 0.0
                    ),
                    predicted_home_yellow_cards=task["prediction_data"].get(
                        "predicted_home_yellow_cards", 0.0
                    ),
                    predicted_away_yellow_cards=task["prediction_data"].get(
                        "predicted_away_yellow_cards", 0.0
                    ),
                )
                results.append(res)
            except Exception as e:
                logger.error(f"Error generating picks sync: {e}")
                results.append([])

        return results

    def _build_match_tasks(
        self,
        upcoming_matches: list[Match],
        limit: int,
        historical_matches: list[Match],
        league_averages: Any,
        min_matches: int,
        data_sources_used: list[str],
        context_bundle: Optional[TrainingDataContextBundle] = None,
    ) -> tuple[list[dict], list[dict]]:
        """Build match_tasks and matches_processing_data from upcoming matches.

        Returns (match_tasks, matches_processing_data).
        """
        # Local imports for runtime exceptions and entities used below
        from src.domain.entities.entities import Prediction
        from src.domain.exceptions import InsufficientDataException

        match_tasks = []
        matches_processing_data = []

        for match in upcoming_matches[:limit]:
            # Get team statistics using the generic service
            home_stats = _build_match_team_statistics(
                self.statistics_service,
                match.home_team.name,
                match,
                historical_matches,
                context_bundle=context_bundle,
            )
            away_stats = _build_match_team_statistics(
                self.statistics_service,
                match.away_team.name,
                match,
                historical_matches,
                context_bundle=context_bundle,
            )

            # Generate prediction
            try:
                # Fetch global averages for fallback
                from src.infrastructure.cache.cache_service import get_cache_service

                cache = get_cache_service()
                global_avg_data = cache.get("global_statistical_averages")
                global_averages = None
                if global_avg_data:
                    from src.domain.value_objects.value_objects import LeagueAverages

                    global_averages = LeagueAverages(**global_avg_data)

                prediction = self.prediction_service.generate_prediction(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_averages,
                    global_averages=global_averages,
                    min_matches=min_matches,
                    data_sources=data_sources_used,
                )

                # Apply ML override if available
                self._apply_ml_override(prediction, match, home_stats, away_stats)

            except InsufficientDataException:
                logger.warning(
                    "Insufficient data for match %s. Skipping match-level prediction.",
                    match.id,
                )
                prediction = Prediction(
                    match_id=match.id,
                    home_win_probability=0.0,
                    draw_probability=0.0,
                    away_win_probability=0.0,
                    predicted_home_goals=0.0,
                    predicted_away_goals=0.0,
                    over_25_probability=0.0,
                    under_25_probability=0.0,
                    confidence=0.0,
                    data_sources=["Insufficient Match Data"],
                    created_at=datetime.now(),
                )
            except Exception as e:
                logger.error(f"Error generating prediction for {match.id}: {e}")
                # Skip this match on error
                continue

            # Calculate H2H
            h2h_stats = self.statistics_service.calculate_h2h_statistics(
                match.home_team.name, match.away_team.name, historical_matches
            )

            # Prepare task data
            task_data = {
                "match": match,
                "home_stats": home_stats,
                "away_stats": away_stats,
                "league_averages": league_averages,
                "h2h_stats": h2h_stats,
                "prediction_data": {
                    "predicted_home_goals": (
                        prediction.predicted_home_goals if prediction else 0.0
                    ),
                    "predicted_away_goals": (
                        prediction.predicted_away_goals if prediction else 0.0
                    ),
                    "home_win_probability": (
                        prediction.home_win_probability if prediction else 0.0
                    ),
                    "draw_probability": (
                        prediction.draw_probability if prediction else 0.0
                    ),
                    "away_win_probability": (
                        prediction.away_win_probability if prediction else 0.0
                    ),
                    "predicted_home_corners": (
                        prediction.predicted_home_corners if prediction else 0.0
                    ),
                    "predicted_away_corners": (
                        prediction.predicted_away_corners if prediction else 0.0
                    ),
                    "predicted_home_yellow_cards": (
                        prediction.predicted_home_yellow_cards if prediction else 0.0
                    ),
                    "predicted_away_yellow_cards": (
                        prediction.predicted_away_yellow_cards if prediction else 0.0
                    ),
                },
            }
            match_tasks.append(task_data)
            matches_processing_data.append(
                {
                    "match": match,
                    "prediction": prediction,
                    "home_stats": home_stats,
                    "away_stats": away_stats,
                }
            )

        return match_tasks, matches_processing_data

    async def _try_serve_cached_predictions(
        self, league_id: str, force_refresh: bool, cache_service: Any, cache_key: str
    ) -> PredictionsResponseDTO | None:
        """Attempt to serve predictions from ephemeral or persistent cache.

        Returns a PredictionsResponseDTO when available, otherwise None.
        """
        if force_refresh:
            logger.info(
                f"🔄 Force Refresh requested for {league_id}. Skipping cache lookup."
            )
            return None

        # Runtime import for DTO used to construct response objects

        # 0.1 Check for new data in DB first (Versioning/Sync)
        db_data, db_last_updated = (None, None)
        if self.persistence_repository:
            try:
                from src.infrastructure.repositories.async_mongo_adapter import (
                    get_async_mongo_repository,
                )

                async_repo = get_async_mongo_repository()
                (
                    db_data,
                    db_last_updated,
                ) = await async_repo.get_training_result_with_timestamp(cache_key)
            except Exception:
                # Fallback to threaded sync repo
                db_data, db_last_updated = await asyncio.to_thread(
                    self.persistence_repository.get_training_result_with_timestamp,
                    cache_key,
                )

        # 0.2 Try Ephemeral Cache (Memory/Disk)
        # Use thread offload for potentially blocking cache implementations
        cached_response = await asyncio.to_thread(cache_service.get, cache_key)

        # SYNC LOGIC: If we have cached response, check if it's stale compared to DB
        is_stale = False
        if cached_response and db_last_updated:
            is_stale = self._is_cached_response_stale(db_last_updated, cached_response)

        if cached_response and not is_stale:
            logger.info("Serving cached (ephemeral) predictions for %s", league_id)
            response = PredictionsResponseDTO(**cached_response)

            # STRICT DATE FILTERING (even for cache)
            filtered = self._filter_future_matches(response.predictions)
            if len(filtered) != len(response.predictions):
                diff = len(response.predictions) - len(filtered)
                logger.info("Filtered %s past matches from cached %s", diff, league_id)
                response.predictions = filtered

            return response

        # 0.3 Try Persistent DB (PostgreSQL fallback)
        if db_data:
            logger.info("Serving persistent (PostgreSQL) predictions for %s", league_id)
            # Warm up ephemeral cache for next time (offload to thread)
            await asyncio.to_thread(
                cache_service.set, cache_key, db_data, ttl_seconds=86400
            )
            response = PredictionsResponseDTO(**db_data)

            # STRICT DATE FILTERING
            filtered = self._filter_future_matches(response.predictions)
            if len(filtered) != len(response.predictions):
                diff = len(response.predictions) - len(filtered)
                logger.info("Filtered %s past matches from DB %s", diff, league_id)
                response.predictions = filtered

            return response

        return None

    def _assemble_predictions(
        self,
        matches_processing_data: list[dict],
        suggested_picks_results: list[Any],
    ) -> list[MatchPredictionDTO]:
        """Assemble `MatchPredictionDTO` values from processing data."""
        # Local import for DTO construction at runtime

        predictions = []

        for i, data in enumerate(matches_processing_data):
            match = data["match"]
            prediction = data["prediction"]
            home_stats = data["home_stats"]
            away_stats = data["away_stats"]

            suggested_picks = (
                suggested_picks_results[i] if i < len(suggested_picks_results) else None
            )

            if not suggested_picks or len(suggested_picks.suggested_picks) == 0:
                continue

            # Convert to DTOs
            match_dto = self._match_to_dto(match)

            # Inject projected stats (historical averages OR prediction fallbacks) for
            # upcoming matches
            if match.status in ["NS", "TIMED", "SCHEDULED"]:
                # Default to historical averages
                h_corners = (
                    home_stats.avg_corners_per_match
                    if home_stats and home_stats.matches_played > 0
                    else 0
                )
                h_yellow = (
                    home_stats.avg_yellow_cards_per_match
                    if home_stats and home_stats.matches_played > 0
                    else 0
                )
                h_red = (
                    home_stats.avg_red_cards_per_match
                    if home_stats and home_stats.matches_played > 0
                    else 0
                )

                a_corners = (
                    away_stats.avg_corners_per_match
                    if away_stats and away_stats.matches_played > 0
                    else 0
                )
                a_yellow = (
                    away_stats.avg_yellow_cards_per_match
                    if away_stats and away_stats.matches_played > 0
                    else 0
                )
                a_red = (
                    away_stats.avg_red_cards_per_match
                    if away_stats and away_stats.matches_played > 0
                    else 0
                )

                # If stats are zero (e.g. OpenFootball fallback),
                # use Prediction Service projections
                if h_corners == 0 and prediction:
                    h_corners = prediction.predicted_home_corners
                if a_corners == 0 and prediction:
                    a_corners = prediction.predicted_away_corners

                if h_yellow == 0 and prediction:
                    h_yellow = prediction.predicted_home_yellow_cards
                if a_yellow == 0 and prediction:
                    a_yellow = prediction.predicted_away_yellow_cards

                if h_red == 0 and prediction:
                    h_red = prediction.predicted_home_red_cards
                if a_red == 0 and prediction:
                    a_red = prediction.predicted_away_red_cards

                match_dto.home_corners = int(round(h_corners))
                match_dto.away_corners = int(round(a_corners))
                match_dto.home_yellow_cards = int(round(h_yellow))
                match_dto.away_yellow_cards = int(round(a_yellow))
                match_dto.home_red_cards = int(round(h_red))
                match_dto.away_red_cards = int(round(a_red))

            prediction_dto = self._prediction_to_dto(
                prediction, suggested_picks.suggested_picks
            )

            predictions.append(
                MatchPredictionDTO(
                    match=match_dto,
                    prediction=prediction_dto,
                )
            )

        return list(predictions)

    def _is_cached_response_stale(
        self, db_last_updated: datetime, cached_response: dict[str, Any]
    ) -> bool:
        """Return True when cached_response is stale compared to db_last_updated."""
        try:
            from datetime import datetime as dt
            from datetime import timedelta
            from datetime import timezone as dt_timezone

            gen_at_val = cached_response.get("generated_at")

            if isinstance(gen_at_val, dt):
                gen_at = gen_at_val
            else:
                if not gen_at_val:
                    return True
                gen_at = dt.fromisoformat(str(gen_at_val))

            if gen_at.tzinfo is None:
                gen_at = gen_at.replace(tzinfo=dt_timezone.utc)
            else:
                gen_at = gen_at.astimezone(dt_timezone.utc)

            if db_last_updated.tzinfo is None:
                db_ts = db_last_updated.replace(tzinfo=dt_timezone.utc)
            else:
                db_ts = db_last_updated.astimezone(dt_timezone.utc)

            return bool(db_ts > (gen_at + timedelta(seconds=10)))
        except Exception as e:
            logger.warning("Error comparing cache vs db timestamp: %s", e)
            return bool(db_last_updated)

    async def _persist_response_and_predictions(
        self,
        cache_service: Any,
        cache_key: str,
        response: Any,
        predictions: list[MatchPredictionDTO],
        league_id: str,
    ) -> None:
        """Persist response to ephemeral cache and optional persistent repository.

        This consolidates caching and DB persistence logic to keep `execute()` small.
        Uses async adapter when available to avoid blocking the event loop.
        """
        try:
            # 1. Ephemeral Cache (offload to thread if implementation is blocking)
            await asyncio.to_thread(
                cache_service.set, cache_key, response.model_dump(), ttl_seconds=86400
            )

            # 2. Persistent DB (Fallback for restarts/deployments)
            if self.persistence_repository:
                prediction_batch = [
                    {
                        "match_id": p_dto.match.id,
                        "league_id": league_id,
                        "data": p_dto.model_dump(),
                        "ttl_seconds": 86400 * 7,
                    }
                    for p_dto in predictions
                ]

                try:
                    from src.infrastructure.repositories.async_mongo_adapter import (
                        get_async_mongo_repository,
                    )

                    async_repo = get_async_mongo_repository()
                    await async_repo.save_training_result(
                        cache_key, response.model_dump()
                    )
                    await async_repo.bulk_save_predictions(prediction_batch)
                    try:
                        from src.infrastructure.cache.cache_service import (
                            get_cache_service,
                        )

                        await get_cache_service().ainvalidate_accuracy_history(
                            league_id
                        )
                    except Exception as cache_exc:
                        logger.debug(
                            "Accuracy history cache invalidation failed: %s", cache_exc
                        )
                    logger.info(
                        (
                            "✓ Massively saved %s pre-calculated predictions "
                            "for league %s (async)"
                        ),
                        len(predictions),
                        league_id,
                    )
                except Exception as e:
                    logger.warning(
                        "Async persist failed, falling back to threaded sync: %s", e
                    )
                    # Fallback to threaded sync calls
                    await asyncio.to_thread(
                        self.persistence_repository.save_training_result,
                        cache_key,
                        response.model_dump(),
                    )
                    await asyncio.to_thread(
                        self.persistence_repository.bulk_save_predictions,
                        prediction_batch,
                    )
                    try:
                        from src.infrastructure.cache.cache_service import (
                            get_cache_service,
                        )

                        await get_cache_service().ainvalidate_accuracy_history(
                            league_id
                        )
                    except Exception as cache_exc:
                        logger.debug(
                            "Accuracy history cache invalidation failed: %s", cache_exc
                        )
                    logger.info(
                        (
                            "✓ Massively saved %s pre-calculated predictions "
                            "for league %s (threaded)"
                        ),
                        len(predictions),
                        league_id,
                    )
        except Exception as e:
            logger.warning("Failed to cache league predictions: %s", e)

    async def _fetch_league_data(
        self, league_id: str, seasons: list[str], limit: int
    ) -> tuple[list[Match], list[Match], Any]:
        """Fetch historical and upcoming matches and compute league averages."""
        logger.info(f"Fetching data for {league_id} via Aggregator Service...")

        # 1. Fetch History Aggregated
        historical_matches = await self.match_aggregator.get_aggregated_history(
            league_id, seasons=seasons
        )

        # 2. Fetch Upcoming Aggregated
        upcoming_matches = await self.match_aggregator.get_upcoming_matches(
            league_id, limit=1000  # Fetch plenty, filter later
        )

        # Calculate league averages from historical data using the service
        league_averages = self.statistics_service.calculate_league_averages(
            historical_matches
        )

        # Strict Date Filter: Only show matches in the future
        # Ensure 'now' and 'match.match_date' are comparable (timezone-aware)
        from src.utils.time_utils import get_current_time

        now = get_current_time()  # Returns Bogota time
        upcoming_matches = self._filter_upcoming_matches(upcoming_matches, now)

        return historical_matches, upcoming_matches, league_averages

    async def execute(
        self, league_id: str, limit: int = 20, force_refresh: bool = False
    ) -> "PredictionsResponseDTO":
        """
        Get predictions for upcoming matches in a league.

        Args:
            league_id: League identifier
            limit: Maximum matches to return

        Returns:
            Predictions response with match predictions
        """
        # Runtime imports for constants and DTOs used below
        from src.domain.constants import LEAGUES_METADATA

        # Get league metadata
        if league_id not in LEAGUES_METADATA:
            raise ValueError(f"Unknown league: {league_id}")

        # 0. Check Cache (Ephemeral & Persistent)
        from src.infrastructure.cache.cache_service import get_cache_service

        cache_service = get_cache_service()

        # Unified Cache Key for League Forecasts
        cache_key = f"forecasts:league_{league_id}"

        cached = await self._try_serve_cached_predictions(
            league_id, force_refresh, cache_service, cache_key
        )
        if cached:
            return cached

        # 0.3 Handle API-only mode
        api_only_response = self._handle_api_only_mode(league_id)
        if api_only_response:
            return api_only_response

        # If not in API-only mode, proceed with real-time computation
        logger.info(
            f"Cache miss for {league_id}. Computing predictions in real-time..."
        )

        meta = LEAGUES_METADATA[league_id]
        league = League(
            id=league_id,
            name=meta["name"],
            country=meta["country"],
        )

        # Get historical data
        # 1. Dynamic Season Calculation
        # Compute seasons using helper
        seasons = self._compute_seasons()

        (
            historical_matches,
            upcoming_matches,
            league_averages,
        ) = await self._fetch_league_data(league_id, seasons, limit)

        if not upcoming_matches:
            logger.info(f"No upcoming future matches found for {league_id}")
            return PredictionsResponseDTO(
                league=LeagueDTO(
                    id=league_id,
                    name=meta["name"],
                    country=meta["country"],
                ),
                predictions=[],
                generated_at=datetime.now(timezone("America/Bogota")),
            )

        # Build predictions
        predictions = []
        data_sources_used = self._determine_data_sources()
        context_bundle = await _load_contextual_training_bundle(league_id)
        if (
            context_bundle
            and "Contextual International History" not in data_sources_used
        ):
            data_sources_used.append("Contextual International History")

        # Prepare parallel tasks
        min_matches = self._calculate_min_matches(league_id)

        # Build match tasks and processing context
        match_tasks, matches_processing_data = self._build_match_tasks(
            upcoming_matches,
            limit,
            historical_matches,
            league_averages,
            min_matches,
            data_sources_used,
            context_bundle=context_bundle,
        )

        # Execute generation (parallel via background processor or synchronous fallback)
        suggested_picks_results = await self._generate_suggested_picks(match_tasks)

        # Apply Risk Management Constraints
        self._apply_risk_management(suggested_picks_results, matches_processing_data)

        predictions = self._assemble_predictions(
            matches_processing_data, suggested_picks_results
        )

        response = PredictionsResponseDTO(
            league=LeagueDTO(
                id=league.id,
                name=league.name,
                country=league.country,
            ),
            predictions=predictions,
            generated_at=datetime.now(timezone("America/Bogota")),
        )

        # Persist results (ephemeral cache + optional persistent DB)
        await self._persist_response_and_predictions(
            cache_service, cache_key, response, predictions, league_id
        )

        return response

    def _handle_api_only_mode(self, league_id: str) -> Optional[PredictionsResponseDTO]:
        """Check if running in API-only mode and return empty response if so."""

        from src.domain.constants import LEAGUES_METADATA

        api_only_mode = os.getenv("API_ONLY_MODE", "false").lower() == "true"
        if not api_only_mode:
            return None

        logger.warning(f"API-ONLY MODE: No cached predictions found for {league_id}")
        logger.info("💡 Predictions will be available after GitHub Actions worker runs")

        meta = LEAGUES_METADATA[league_id]
        return PredictionsResponseDTO(
            league=LeagueDTO(
                id=league_id,
                name=meta["name"],
                country=meta["country"],
            ),
            predictions=[],
            generated_at=datetime.now(timezone("America/Bogota")),
        )

    def _calculate_min_matches(self, league_id: str) -> int:
        """Determine min_matches threshold based on league type."""
        min_matches = 6
        if league_id in CLUB_INTERNATIONAL_LEAGUES:
            min_matches = 3
            logger.info(
                f"Using relaxed min_matches={min_matches} for tournament {league_id}"
            )
        return min_matches

    def _apply_risk_management(
        self, suggested_picks_results: list[Any], matches_processing_data: list[dict]
    ) -> None:
        """Apply risk logic and organize picks."""
        # 1. Flatten picks for batch processing
        flat_picks_map = []
        for i, res in enumerate(suggested_picks_results):
            if res and res.suggested_picks:
                match = matches_processing_data[i]["match"]
                for pick in res.suggested_picks:
                    flat_picks_map.append(
                        {"pick": pick, "match": match, "result_obj": res}
                    )

        # 2. Apply Portfolio Constraints (currently returns all)
        approved_items = flat_picks_map

        # 3. Synchronize suggested_picks structures
        for res in suggested_picks_results:
            if res:
                res.suggested_picks = []

        for item in approved_items:
            item["result_obj"].suggested_picks.append(item["pick"])

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)

        from src.domain.services.team_service import TeamService

        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                country=match.home_team.country,
                logo_url=match.home_team.logo_url
                or TeamService.get_team_logo(match.home_team.name),
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                country=match.away_team.country,
                logo_url=match.away_team.logo_url
                or TeamService.get_team_logo(match.away_team.name),
            ),
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
        )

    def _prediction_to_dto(
        self, prediction: Prediction, picks: Optional[list[Any]] = None
    ) -> PredictionDTO:
        pick_dtos = []
        if picks:
            pick_dtos = [
                SuggestedPickDTO(
                    market_type=(
                        p.market_type.value
                        if hasattr(p.market_type, "value")
                        else p.market_type
                    ),
                    market_label=p.market_label,
                    probability=p.probability,
                    confidence_level=(
                        p.confidence_level.value
                        if hasattr(p.confidence_level, "value")
                        else p.confidence_level
                    ),
                    reasoning=p.reasoning,
                    risk_level=p.risk_level,
                    is_recommended=p.is_recommended,
                    priority_score=p.priority_score,
                    is_ml_confirmed=getattr(p, "is_ml_confirmed", False),
                    is_ia_confirmed=getattr(p, "is_ia_confirmed", False),
                    ml_confidence=getattr(p, "ml_confidence", 0.0),
                    suggested_stake=getattr(p, "suggested_stake", 0.0),
                    kelly_percentage=getattr(p, "kelly_percentage", 0.0),
                    clv_beat=getattr(p, "clv_beat", False),
                    expected_value=getattr(p, "expected_value", 0.0),
                    opening_odds=getattr(p, "odds", 0.0),
                    closing_odds=getattr(p, "closing_odds", 0.0),
                )
                for p in picks
            ]

        # Top ML Picks = All picks with probability >= 75% (ML High Confidence tier)
        top_ml_threshold = 0.75
        top_ml_picks = [p for p in pick_dtos if p.probability >= top_ml_threshold]
        # Sort by probability descending
        top_ml_picks.sort(key=lambda x: x.probability, reverse=True)

        return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            # Map Extended Predictions
            predicted_home_corners=getattr(prediction, "predicted_home_corners", 0.0),
            predicted_away_corners=getattr(prediction, "predicted_away_corners", 0.0),
            predicted_home_yellow_cards=getattr(
                prediction, "predicted_home_yellow_cards", 0.0
            ),
            predicted_away_yellow_cards=getattr(
                prediction, "predicted_away_yellow_cards", 0.0
            ),
            predicted_home_red_cards=getattr(
                prediction, "predicted_home_red_cards", 0.0
            ),
            predicted_away_red_cards=getattr(
                prediction, "predicted_away_red_cards", 0.0
            ),
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            top_ml_picks=top_ml_picks,
            model_metadata=getattr(prediction, "model_metadata", {}),
            created_at=prediction.created_at,
            score_probabilities=getattr(prediction, "score_probabilities", None),
            score_confidence_tier=getattr(prediction, "score_confidence_tier", None),
            score_matrix=getattr(prediction, "score_matrix", None),
            score_accuracy_history=getattr(prediction, "score_accuracy_history", None),
            # ML serving-mode observability (design D6)
            serving_mode=getattr(self.picks_service, "serving_mode", None),
            fallback_reason=getattr(self.picks_service, "fallback_reason", None),
        )

    def _filter_future_matches(
        self, predictions: "list[MatchPredictionDTO]"
    ) -> "list[MatchPredictionDTO]":
        """Filters out matches that have already occurred."""

        # Local import for DTO types used in annotations/runtime

        from src.utils.time_utils import get_current_time

        now = get_current_time()  # Returns Bogota time

        # Statuses that indicate a match is currently in play
        # Added PAUSED/IN_PLAY/HT/1H/2H
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]

        filtered = []
        for p in predictions:
            m_date = p.match.match_date
            if m_date.tzinfo is None:
                from pytz import timezone as pytz_tz

                tz = pytz_tz("America/Bogota")
                m_date = tz.localize(m_date)
            else:
                m_date = m_date.astimezone(now.tzinfo)

            # Allow if:
            # 1. It's in the future
            # 2. It's currently marked as live
            # 3. It's PAUSED/HALFTIME etc.
            # Strictly exclude FT/AET/PEN even if "recent" to avoid confusion
            if p.match.status in ["FT", "AET", "PEN", "FINISHED"]:
                continue

            if m_date > now or p.match.status in live_statuses:
                # Double check status just in case dates are weird
                if p.match.status not in ["FT", "AET", "PEN", "FINISHED"]:
                    filtered.append(p)
        return filtered


class GetMatchDetailsUseCase:
    """Use case for getting details and prediction for a single match."""

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        from src.application.dependencies import get_learning_service
        from src.domain.services.ai_picks_service import AIPicksService

        self.picks_service = AIPicksService(
            learning_weights=get_learning_service().get_learning_weights()
        )

    async def execute(self, match_id: str) -> Optional["MatchPredictionDTO"]:
        match = await self._get_match_from_sources(match_id)
        if not match:
            return None

        # 2. Optimized Lookup: Fetch Pre-calculated prediction
        precalculated = self._lookup_precalculated_prediction(match_id)
        if precalculated:
            return precalculated

        # 3. Get historical data context
        internal_league_code = self._get_internal_league_code(match)
        historical_matches = []
        if internal_league_code:
            historical_matches = await self._fetch_historical_matches(
                internal_league_code, match
            )

        # 4. Calculate stats using whatever history we found (or empty list)
        home_stats = self.statistics_service.calculate_team_statistics(
            match.home_team.name, historical_matches
        )
        away_stats = self.statistics_service.calculate_team_statistics(
            match.away_team.name, historical_matches
        )

        # Calculate league averages from history to enable fallback picks
        # (Corners/Cards)
        league_averages = self.statistics_service.calculate_league_averages(
            historical_matches
        )

        # 5. Generate prediction
        try:
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=None,
                data_sources=self._get_active_source_names(historical_matches),
            )
        except Exception as e:
            from src.domain.exceptions import InsufficientDataException

            if isinstance(e, InsufficientDataException):
                return self._create_skeleton_prediction(match)
            raise e

        # Generate suggested picks
        h2h_stats = self.statistics_service.calculate_h2h_statistics(
            match.home_team.name, match.away_team.name, historical_matches
        )

        suggested_picks = self.picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            h2h_stats=h2h_stats,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            home_win_prob=prediction.home_win_probability,
            draw_prob=prediction.draw_probability,
            away_win_prob=prediction.away_win_probability,
        )

        # Enhanced Match DTO with projected stats if NS
        match_dto = self._enrich_match_dto_with_projections(
            match, home_stats, away_stats, prediction
        )

        return MatchPredictionDTO(
            match=match_dto,
            prediction=self._prediction_to_dto(
                prediction, suggested_picks.suggested_picks
            ),
        )

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                country=match.home_team.country,
                logo_url=match.home_team.logo_url,
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                country=match.away_team.country,
                logo_url=match.away_team.logo_url,
            ),
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
        )

    def _prediction_to_dto(
        self, prediction: Prediction, picks: Optional[list] = None
    ) -> PredictionDTO:
        # Map suggested picks to DTOs
        from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO

        pick_dtos = []
        if picks:
            pick_dtos = [
                SuggestedPickDTO(
                    market_type=(
                        p.market_type.value
                        if hasattr(p.market_type, "value")
                        else p.market_type
                    ),
                    market_label=p.market_label,
                    probability=p.probability,
                    confidence_level=(
                        p.confidence_level.value
                        if hasattr(p.confidence_level, "value")
                        else p.confidence_level
                    ),
                    reasoning=p.reasoning,
                    risk_level=p.risk_level,
                    is_recommended=p.is_recommended,
                    priority_score=p.priority_score,
                    is_ml_confirmed=getattr(p, "is_ml_confirmed", False),
                    is_ia_confirmed=getattr(p, "is_ia_confirmed", False),
                    ml_confidence=getattr(p, "ml_confidence", 0.0),
                    suggested_stake=getattr(p, "suggested_stake", 0.0),
                    kelly_percentage=getattr(p, "kelly_percentage", 0.0),
                    clv_beat=getattr(p, "clv_beat", False),
                    expected_value=getattr(p, "expected_value", 0.0),
                    opening_odds=getattr(p, "odds", 0.0),
                    closing_odds=getattr(p, "closing_odds", 0.0),
                )
                for p in picks
            ]

        # Top ML Picks calculation
        top_ml_threshold = 0.75
        top_ml_picks = [p for p in pick_dtos if p.probability >= top_ml_threshold]
        top_ml_picks.sort(key=lambda x: x.probability, reverse=True)

        return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            # Map Extended Predictions
            predicted_home_corners=getattr(prediction, "predicted_home_corners", 0.0),
            predicted_away_corners=getattr(prediction, "predicted_away_corners", 0.0),
            predicted_home_yellow_cards=getattr(
                prediction, "predicted_home_yellow_cards", 0.0
            ),
            predicted_away_yellow_cards=getattr(
                prediction, "predicted_away_yellow_cards", 0.0
            ),
            predicted_home_red_cards=getattr(
                prediction, "predicted_home_red_cards", 0.0
            ),
            predicted_away_red_cards=getattr(
                prediction, "predicted_away_red_cards", 0.0
            ),
            over_95_corners_probability=getattr(
                prediction, "over_95_corners_probability", 0.0
            ),
            under_95_corners_probability=getattr(
                prediction, "under_95_corners_probability", 0.0
            ),
            over_45_cards_probability=getattr(
                prediction, "over_45_cards_probability", 0.0
            ),
            under_45_cards_probability=getattr(
                prediction, "under_45_cards_probability", 0.0
            ),
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            top_ml_picks=top_ml_picks,
            model_metadata=getattr(prediction, "model_metadata", {}),
            created_at=prediction.created_at,
        )

    async def _get_match_from_sources(self, match_id: str) -> Optional[Any]:
        """Try multiple data sources to find match details."""
        match = None
        if self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(
                match_id
            )

        if not match:
            try:
                match = await self.data_sources.thesportsdb.get_match_details(match_id)
            except Exception as exc:
                logger.warning("TheSportsDB lookup failed for %s: %s", match_id, exc)
        return match

    def _lookup_precalculated_prediction(
        self, match_id: str
    ) -> Optional[MatchPredictionDTO]:
        """Try to fetch a pre-calculated prediction from persistence."""
        try:
            from src.dependencies import get_persistence_repository

            repo = cast(Any, get_persistence_repository())
            pred_data, _ = repo.get_match_prediction_with_timestamp(match_id)
            if pred_data:
                logger.info(
                    f"Serving optimized pre-calculated prediction for match {match_id}"
                )
                return MatchPredictionDTO(**pred_data)
        except Exception as e:
            logger.error(f"Failed to fetch optimized prediction for {match_id}: {e}")
        return None

    def _get_internal_league_code(self, match: Any) -> Optional[str]:
        """Map API league ID to internal league code."""
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING

        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        try:
            lid = int(match.league.id)
            return api_id_to_code.get(lid)
        except (ValueError, TypeError):
            return None

    async def _fetch_historical_matches(self, league_code: str, match: Any) -> list:
        """Fetch historical matches from multiple sources."""
        if not league_code:
            return []

        matches = []
        try:
            matches = await self.data_sources.football_data_uk.get_historical_matches(
                league_code, seasons=["2425", "2324"]
            )
        except Exception as e:
            logger.warning(f"Failed to fetch CSV history details: {e}")

        if not matches and self.data_sources.openfootball:
            try:
                from src.domain.entities.league import League

                temp_league = League(
                    id=league_code,
                    name=match.league.name,
                    country=match.league.country,
                    season=match.league.season,
                )
                open_matches = await self.data_sources.openfootball.get_matches(
                    temp_league
                )
                matches = [m for m in open_matches if m.status in ["FT", "AET", "PEN"]]
            except Exception as e:
                logger.warning(f"Failed to fetch OpenFootball history details: {e}")
        return matches

    def _get_active_source_names(self, historical_matches: list) -> list[str]:
        """Get names of active data sources for tracking."""
        from src.infrastructure.data_sources.football_data_org import (
            FootballDataOrgSource,
        )
        from src.infrastructure.data_sources.football_data_uk import (
            FootballDataUKSource,
        )

        sources = [FootballDataOrgSource.SOURCE_NAME]
        if historical_matches:
            sources.append(FootballDataUKSource.SOURCE_NAME)
        return sources

    def _create_skeleton_prediction(self, match: Any) -> MatchPredictionDTO:
        """Create a zero-probability skeleton prediction when data is missing."""
        from src.utils.time_utils import get_current_time

        return MatchPredictionDTO(
            match=self._match_to_dto(match),
            prediction=PredictionDTO(
                match_id=match.id,
                home_win_probability=0.0,
                draw_probability=0.0,
                away_win_probability=0.0,
                over_25_probability=0.0,
                under_25_probability=0.0,
                predicted_home_goals=0.0,
                predicted_away_goals=0.0,
                confidence=0.0,
                data_sources=[],
                recommended_bet="N/A",
                over_under_recommendation="N/A",
                created_at=get_current_time(),
            ),
        )

    def _enrich_match_dto_with_projections(
        self,
        match: Match,
        home_stats: TeamStatistics | None,
        away_stats: TeamStatistics | None,
        prediction: Prediction | None,
    ) -> MatchDTO:
        """Add projected statistics to MatchDTO for non-started matches."""
        match_dto = self._match_to_dto(match)
        if match.status not in ["NS", "TIMED", "SCHEDULED"]:
            return match_dto

        # Extract projected values using averages or direct predictions
        def get_stat(stats: TeamStatistics | None, attr: str, pred_val: float) -> float:
            val = float(
                getattr(stats, attr, 0.0) if stats and stats.matches_played > 0 else 0.0
            )
            if val == 0.0 and prediction:
                return pred_val
            return val

        h_corners = get_stat(
            home_stats,
            "avg_corners_per_match",
            prediction.predicted_home_corners if prediction else 0.0,
        )
        h_yellow = get_stat(
            home_stats,
            "avg_yellow_cards_per_match",
            prediction.predicted_home_yellow_cards if prediction else 0.0,
        )
        h_red = get_stat(
            home_stats,
            "avg_red_cards_per_match",
            prediction.predicted_home_red_cards if prediction else 0.0,
        )

        a_corners = get_stat(
            away_stats,
            "avg_corners_per_match",
            prediction.predicted_away_corners if prediction else 0.0,
        )
        a_yellow = get_stat(
            away_stats,
            "avg_yellow_cards_per_match",
            prediction.predicted_away_yellow_cards if prediction else 0.0,
        )
        a_red = get_stat(
            away_stats,
            "avg_red_cards_per_match",
            prediction.predicted_away_red_cards if prediction else 0.0,
        )

        match_dto.home_corners = int(round(h_corners))
        match_dto.away_corners = int(round(a_corners))
        match_dto.home_yellow_cards = int(round(h_yellow))
        match_dto.away_yellow_cards = int(round(a_yellow))
        match_dto.home_red_cards = int(round(h_red))
        match_dto.away_red_cards = int(round(a_red))

        return match_dto


class GetTeamPredictionsUseCase:
    """Use case for getting matches for a specific team with predictions."""

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        from src.application.dependencies import get_learning_service
        from src.domain.services.ai_picks_service import AIPicksService

        self.picks_service = AIPicksService(
            learning_weights=get_learning_service().get_learning_weights()
        )

    async def execute(self, team_name: str) -> list[MatchPredictionDTO]:
        """
        Get matches for a specific team with predictions.

        Args:
            team_name: Name of the team to search for

        Returns:
            List of MatchPredictionDTOs
        """
        # 1. Get matches
        matches = await self.data_sources.football_data_org.get_team_history(
            team_name, limit=10
        )
        if not matches:
            return []

        # 2. Process each match
        match_prediction_dtos = []
        for match in matches:
            try:
                dto = await self._process_single_match(match)
                if dto:
                    match_prediction_dtos.append(dto)
            except Exception as e:
                logger.warning(
                    f"Error processing team match "
                    f"{getattr(match, 'id', 'unknown')}: {e}"
                )
                continue

        return match_prediction_dtos

    async def _process_single_match(self, match: Any) -> Optional[MatchPredictionDTO]:
        """
        Process a single match: fetch history, calculate stats,
        and generate prediction.
        """
        from src.domain.exceptions import InsufficientDataException

        # 1. Get historical context
        internal_league_code = self._get_internal_league_code(match)
        historical_matches = []
        if internal_league_code:
            historical_matches = await self._fetch_historical_matches(
                internal_league_code, match
            )

        # 2. Calculate stats
        home_stats = self.statistics_service.calculate_team_statistics(
            match.home_team.name, historical_matches
        )
        away_stats = self.statistics_service.calculate_team_statistics(
            match.away_team.name, historical_matches
        )
        league_averages = self.statistics_service.calculate_league_averages(
            historical_matches
        )

        # 3. Generate prediction
        try:
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=None,
                data_sources=self._get_active_source_names(historical_matches),
            )
        except InsufficientDataException:
            return None

        # 4. Generate suggested picks
        h2h_stats = self.statistics_service.calculate_h2h_statistics(
            match.home_team.name, match.away_team.name, historical_matches
        )
        suggested_picks = self.picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            h2h_stats=h2h_stats,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            home_win_prob=prediction.home_win_probability,
            draw_prob=prediction.draw_probability,
            away_win_prob=prediction.away_win_probability,
        )

        # 5. Create DTOs
        match_dto = self._enrich_match_dto_with_projections(
            match, home_stats, away_stats, prediction
        )
        prediction_dto = self._prediction_to_dto(
            prediction, suggested_picks.suggested_picks
        )

        return MatchPredictionDTO(match=match_dto, prediction=prediction_dto)

    def _get_internal_league_code(self, match: Any) -> Optional[str]:
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING

        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        try:
            if match.league.id and match.league.id.isdigit():
                lid = int(match.league.id)
                return api_id_to_code.get(lid)
        except Exception:
            pass
        return None

    async def _fetch_historical_matches(
        self, league_code: str, match: Any
    ) -> list[Match]:
        if not league_code:
            return []
        try:
            historical_matches = (
                await self.data_sources.football_data_uk.get_historical_matches(
                    league_code,
                    seasons=["2425", "2324"],
                )
            )
            return cast(list[Match], historical_matches)
        except Exception as exc:
            logger.warning(f"Failed to fetch CSV history: {exc}")
            return []

    def _get_active_source_names(self, historical_matches: list) -> list[str]:
        sources = ["Football-Data.org"]
        if historical_matches:
            sources.append("Football-Data.co.uk")
        return sources

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now to avoid cross-cutting refactor
        from src.application.dtos.dtos import LeagueDTO, MatchDTO, TeamDTO
        from src.domain.services.team_service import TeamService

        home_team = TeamDTO(
            id=match.home_team.id,
            name=match.home_team.name,
            short_name=match.home_team.short_name
            or TeamService.get_team_short_name(match.home_team.name),
            country=match.home_team.country,
            logo_url=match.home_team.logo_url
            or TeamService.get_team_logo(match.home_team.name),
        )
        away_team = TeamDTO(
            id=match.away_team.id,
            name=match.away_team.name,
            short_name=match.away_team.short_name
            or TeamService.get_team_short_name(match.away_team.name),
            country=match.away_team.country,
            logo_url=match.away_team.logo_url
            or TeamService.get_team_logo(match.away_team.name),
        )
        return MatchDTO(
            id=match.id,
            home_team=home_team,
            away_team=away_team,
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
            minute=match.minute,
            # Extended Stats
            home_shots_on_target=match.home_shots_on_target,
            away_shots_on_target=match.away_shots_on_target,
            home_total_shots=match.home_total_shots,
            away_total_shots=match.away_total_shots,
            home_possession=match.home_possession,
            away_possession=match.away_possession,
            home_fouls=match.home_fouls,
            away_fouls=match.away_fouls,
            home_offsides=match.home_offsides,
            away_offsides=match.away_offsides,
        )

    def _prediction_to_dto(
        self, prediction: Prediction, picks: Optional[list] = None
    ) -> PredictionDTO:
        from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO

        pick_dtos = []
        if picks:
            pick_dtos = [
                SuggestedPickDTO(
                    market_type=(
                        p.market_type.value
                        if hasattr(p.market_type, "value")
                        else p.market_type
                    ),
                    market_label=p.market_label,
                    probability=p.probability,
                    confidence_level=(
                        p.confidence_level.value
                        if hasattr(p.confidence_level, "value")
                        else p.confidence_level
                    ),
                    reasoning=p.reasoning,
                    risk_level=p.risk_level,
                    is_recommended=p.is_recommended,
                    priority_score=p.priority_score,
                    is_ml_confirmed=getattr(p, "is_ml_confirmed", False),
                    is_ia_confirmed=getattr(p, "is_ia_confirmed", False),
                    ml_confidence=getattr(p, "ml_confidence", 0.0),
                    suggested_stake=getattr(p, "suggested_stake", 0.0),
                    kelly_percentage=getattr(p, "kelly_percentage", 0.0),
                    clv_beat=getattr(p, "clv_beat", False),
                    expected_value=getattr(p, "expected_value", 0.0),
                    opening_odds=getattr(p, "odds", 0.0),
                    closing_odds=getattr(p, "closing_odds", 0.0),
                )
                for p in picks
            ]

        # Top ML Picks
        top_ml_threshold = 0.75
        top_ml_picks = [p for p in pick_dtos if p.probability >= top_ml_threshold]
        top_ml_picks.sort(key=lambda x: x.probability, reverse=True)

        return PredictionDTO(
            match_id=prediction.match_id,
            home_win_probability=prediction.home_win_probability,
            draw_probability=prediction.draw_probability,
            away_win_probability=prediction.away_win_probability,
            over_25_probability=prediction.over_25_probability,
            under_25_probability=prediction.under_25_probability,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            # Map Extended Predictions
            predicted_home_corners=getattr(prediction, "predicted_home_corners", 0.0),
            predicted_away_corners=getattr(prediction, "predicted_away_corners", 0.0),
            predicted_home_yellow_cards=getattr(
                prediction, "predicted_home_yellow_cards", 0.0
            ),
            predicted_away_yellow_cards=getattr(
                prediction, "predicted_away_yellow_cards", 0.0
            ),
            predicted_home_red_cards=getattr(
                prediction, "predicted_home_red_cards", 0.0
            ),
            predicted_away_red_cards=getattr(
                prediction, "predicted_away_red_cards", 0.0
            ),
            over_95_corners_probability=getattr(
                prediction, "over_95_corners_probability", 0.0
            ),
            under_95_corners_probability=getattr(
                prediction, "under_95_corners_probability", 0.0
            ),
            over_45_cards_probability=getattr(
                prediction, "over_45_cards_probability", 0.0
            ),
            under_45_cards_probability=getattr(
                prediction, "under_45_cards_probability", 0.0
            ),
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=pick_dtos,
            top_ml_picks=top_ml_picks,
            model_metadata=getattr(prediction, "model_metadata", {}),
            created_at=prediction.created_at,
        )

    def _enrich_match_dto_with_projections(
        self,
        match: Match,
        home_stats: TeamStatistics | None,
        away_stats: TeamStatistics | None,
        prediction: Prediction | None,
    ) -> MatchDTO:
        """Add projected statistics to MatchDTO for non-started matches."""
        match_dto = self._match_to_dto(match)
        if match.status not in ["NS", "TIMED", "SCHEDULED"]:
            return match_dto

        def get_stat(stats: TeamStatistics | None, attr: str, pred_val: float) -> float:
            value = float(
                getattr(stats, attr, 0.0) if stats and stats.matches_played > 0 else 0.0
            )
            if value == 0.0 and prediction:
                return pred_val
            return value

        home_corners = get_stat(
            home_stats,
            "avg_corners_per_match",
            prediction.predicted_home_corners if prediction else 0.0,
        )
        away_corners = get_stat(
            away_stats,
            "avg_corners_per_match",
            prediction.predicted_away_corners if prediction else 0.0,
        )
        home_yellow_cards = get_stat(
            home_stats,
            "avg_yellow_cards_per_match",
            prediction.predicted_home_yellow_cards if prediction else 0.0,
        )
        away_yellow_cards = get_stat(
            away_stats,
            "avg_yellow_cards_per_match",
            prediction.predicted_away_yellow_cards if prediction else 0.0,
        )
        home_red_cards = get_stat(
            home_stats,
            "avg_red_cards_per_match",
            prediction.predicted_home_red_cards if prediction else 0.0,
        )
        away_red_cards = get_stat(
            away_stats,
            "avg_red_cards_per_match",
            prediction.predicted_away_red_cards if prediction else 0.0,
        )

        match_dto.home_corners = int(round(home_corners))
        match_dto.away_corners = int(round(away_corners))
        match_dto.home_yellow_cards = int(round(home_yellow_cards))
        match_dto.away_yellow_cards = int(round(away_yellow_cards))
        match_dto.home_red_cards = int(round(home_red_cards))
        match_dto.away_red_cards = int(round(away_red_cards))
        return match_dto


class GetGlobalLiveMatchesUseCase:
    """
    Use case for getting all live matches globally from ALL available sources.

    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data or simulated matches allowed.
    - Aggregates and deduplicates data to provide the most complete picture.
    """

    def __init__(
        self,
        data_sources: DataSources,
        persistence_repository: Optional["MongoRepository"] = None,
    ):
        self.data_sources = data_sources
        self.persistence_repository = persistence_repository

    async def execute(self) -> "list[MatchDTO]":
        """
        Execute the use case.

        Returns:
            List of unique live matches from all sources.
        """
        # 1. Fetch from all sources
        all_matches = await self._fetch_all_live_matches()

        # 2. Deduplicate using richness score
        unique_matches = self._deduplicate_matches(all_matches)

        # 3. Filter for truly live or very recent matches
        filtered_dtos = self._filter_live_or_recent_matches(
            list(unique_matches.values())
        )

        # 4. Persistence: Index live matches
        self._persist_live_matches(filtered_dtos)

        return filtered_dtos

    async def _fetch_all_live_matches(self) -> list[Match]:
        """Fetch live matches from all configured sources."""
        import asyncio

        tasks = []
        if self.data_sources.football_data_org.is_configured:
            tasks.append(self.data_sources.football_data_org.get_live_matches())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
        return all_matches

    def _calculate_richness(self, m: Match) -> int:
        """Calculate how many extended statistics a match has."""
        score = 0
        attrs = [
            "home_corners",
            "home_yellow_cards",
            "home_red_cards",
            "home_shots_on_target",
            "home_total_shots",
            "home_fouls",
            "home_offsides",
        ]
        for attr in attrs:
            if getattr(m, attr, None) is not None:
                score += 1
        if getattr(m, "home_possession", None):
            score += 1
        if getattr(m, "minute", None):
            score += 1
        if getattr(m, "events", None):
            score += 1
        return score

    def _deduplicate_matches(self, matches: list[Match]) -> dict[str, Match]:
        """Create a unique set of matches, preferring those with more data."""
        unique_matches = {}
        for match in matches:
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                existing = unique_matches[key]
                if self._calculate_richness(match) > self._calculate_richness(existing):
                    unique_matches[key] = match
        return unique_matches

    def _filter_live_or_recent_matches(self, matches: list[Match]) -> list[MatchDTO]:
        """Filter matches based on live status and recent timing."""
        from datetime import timedelta

        from src.utils.time_utils import get_current_time

        now = get_current_time()
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]

        filtered = []
        for match in matches:
            dto = self._match_to_dto(match)
            is_recent = (now - dto.match_date) < timedelta(minutes=150)

            if dto.status in ["FT", "AET", "PEN", "FINISHED"] and not is_recent:
                continue

            if dto.match_date > now or dto.status in live_statuses or is_recent:
                filtered.append(dto)
        return filtered

    def _persist_live_matches(self, matches: list[MatchDTO]) -> None:
        """Store live matches in persistence for exploration."""
        if not self.persistence_repository or not matches:
            return

        try:
            prediction_batch = [
                {
                    "match_id": m.id,
                    "league_id": m.league.id,
                    "data": MatchPredictionDTO(
                        match=m,
                        prediction=PredictionDTO(
                            match_id=m.id,
                            home_win_probability=0.0,
                            draw_probability=0.0,
                            away_win_probability=0.0,
                            over_25_probability=0.0,
                            under_25_probability=0.0,
                            predicted_home_goals=0.0,
                            predicted_away_goals=0.0,
                            confidence=0.0,
                            data_sources=["Discovery"],
                            recommended_bet="N/A",
                            over_under_recommendation="N/A",
                            created_at=datetime.now(),
                        ),
                    ).model_dump(),
                    "ttl_seconds": 3600,
                }
                for m in matches
            ]
            self.persistence_repository.bulk_save_predictions(prediction_batch)
            logger.info(f"Indexed {len(matches)} live matches in Explorer DB")
        except Exception as e:
            logger.warning(f"Failed to index live matches: {e}")

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Re-using MatchDTO mapping logic
        from src.domain.services.team_service import TeamService

        h_short = match.home_team.short_name or TeamService.get_team_short_name(
            match.home_team.name
        )
        h_logo = match.home_team.logo_url or TeamService.get_team_logo(
            match.home_team.name
        )
        a_short = match.away_team.short_name or TeamService.get_team_short_name(
            match.away_team.name
        )
        a_logo = match.away_team.logo_url or TeamService.get_team_logo(
            match.away_team.name
        )

        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=h_short,
                country=match.home_team.country,
                logo_url=h_logo,
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=a_short,
                country=match.away_team.country,
                logo_url=a_logo,
            ),
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
            minute=match.minute,
            home_shots_on_target=match.home_shots_on_target,
            away_shots_on_target=match.away_shots_on_target,
            home_total_shots=match.home_total_shots,
            away_total_shots=match.away_total_shots,
            home_possession=match.home_possession,
            away_possession=match.away_possession,
            home_fouls=match.home_fouls,
            away_fouls=match.away_fouls,
            home_offsides=match.home_offsides,
            away_offsides=match.away_offsides,
        )


class GetGlobalDailyMatchesUseCase:
    """
    Use case for getting all daily matches from ALL available sources.

    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data allowed.
    """

    def __init__(
        self,
        data_sources: DataSources,
        persistence_repository: Optional["MongoRepository"] = None,
    ):
        self.data_sources = data_sources
        self.persistence_repository = persistence_repository

    async def execute(self, date_str: Optional[str] = None) -> list[MatchDTO]:
        """Get daily matches combined from all sources."""
        # 1. Fetch from all sources
        all_matches = await self._fetch_all_daily_matches()

        # 2. Deduplicate using richness score
        unique_matches = self._deduplicate_matches(all_matches)

        # 3. Filter for daily matches and map to DTOs
        filtered_dtos = self._filter_and_map_to_dtos(list(unique_matches.values()))

        # 4. Persistence: Index daily matches for the Explorer
        self._persist_daily_matches(filtered_dtos)

        return filtered_dtos

    async def _fetch_all_daily_matches(self) -> list[Match]:
        """Fetch daily matches from all configured sources."""
        import asyncio

        tasks = []
        if self.data_sources.football_data_org.is_configured:
            tasks.append(self.data_sources.football_data_org.get_live_matches())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
        return all_matches

    def _calculate_richness(self, m: Match) -> int:
        """Calculate how many extended statistics a match has."""
        score = 0
        attrs = [
            "home_corners",
            "home_yellow_cards",
            "home_red_cards",
            "home_shots_on_target",
            "home_total_shots",
        ]
        for attr in attrs:
            if getattr(m, attr, None) is not None:
                score += 1
        if getattr(m, "home_possession", None):
            score += 1
        return score

    def _deduplicate_matches(self, matches: list[Match]) -> dict[str, Match]:
        """Create a unique set of matches, preferring those with more data."""
        unique_matches = {}
        for match in matches:
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                existing = unique_matches[key]
                if self._calculate_richness(match) > self._calculate_richness(existing):
                    unique_matches[key] = match
        return unique_matches

    def _filter_and_map_to_dtos(self, matches: list[Match]) -> list[MatchDTO]:
        """Convert matches to DTOs and filter based on timing."""
        from datetime import timedelta

        from src.utils.time_utils import get_current_time

        now = get_current_time()
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]

        dtos = []
        for match in matches:
            dto = self._match_to_dto(match)
            is_recent = (now - dto.match_date) < timedelta(minutes=150)
            if dto.match_date > now or dto.status in live_statuses or is_recent:
                if dto.status == "FT" and not is_recent:
                    continue
                dtos.append(dto)
        return dtos

    def _persist_daily_matches(self, dtos: list[MatchDTO]) -> None:
        """Store daily matches in persistence for exploration."""
        if not self.persistence_repository or not dtos:
            return

        try:
            prediction_batch = [
                {
                    "match_id": m.id,
                    "league_id": m.league.id,
                    "data": MatchPredictionDTO(
                        match=m,
                        prediction=PredictionDTO(
                            match_id=m.id,
                            home_win_probability=0.0,
                            draw_probability=0.0,
                            away_win_probability=0.0,
                            over_25_probability=0.0,
                            under_25_probability=0.0,
                            predicted_home_goals=0.0,
                            predicted_away_goals=0.0,
                            confidence=0.0,
                            data_sources=["Discovery"],
                            recommended_bet="N/A",
                            over_under_recommendation="N/A",
                            created_at=datetime.now(),
                        ),
                    ).model_dump(),
                    "ttl_seconds": 86400,
                }
                for m in dtos
            ]
            self.persistence_repository.bulk_save_predictions(prediction_batch)
            logger.info(f"Indexed {len(dtos)} daily matches in Explorer DB")
        except Exception as e:
            logger.warning(f"Failed to index daily matches: {e}")

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Re-using MatchDTO mapping logic
        from src.domain.services.team_service import TeamService

        h_short = match.home_team.short_name or TeamService.get_team_short_name(
            match.home_team.name
        )
        h_logo = match.home_team.logo_url or TeamService.get_team_logo(
            match.home_team.name
        )
        a_short = match.away_team.short_name or TeamService.get_team_short_name(
            match.away_team.name
        )
        a_logo = match.away_team.logo_url or TeamService.get_team_logo(
            match.away_team.name
        )

        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=h_short,
                country=match.home_team.country,
                logo_url=h_logo,
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=a_short,
                country=match.away_team.country,
                logo_url=a_logo,
            ),
            league=LeagueDTO(
                id=match.league.id,
                name=match.league.name,
                country=match.league.country,
                season=match.league.season,
            ),
            match_date=match.match_date,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            status=match.status,
            home_corners=match.home_corners,
            away_corners=match.away_corners,
            home_yellow_cards=match.home_yellow_cards,
            away_yellow_cards=match.away_yellow_cards,
            home_red_cards=match.home_red_cards,
            away_red_cards=match.away_red_cards,
            home_odds=match.home_odds,
            draw_odds=match.draw_odds,
            away_odds=match.away_odds,
            minute=match.minute,
            home_shots_on_target=match.home_shots_on_target,
            away_shots_on_target=match.away_shots_on_target,
            home_total_shots=match.home_total_shots,
            away_total_shots=match.away_total_shots,
            home_possession=match.home_possession,
            away_possession=match.away_possession,
            home_fouls=match.home_fouls,
            away_fouls=match.away_fouls,
            home_offsides=match.home_offsides,
            away_offsides=match.away_offsides,
        )
