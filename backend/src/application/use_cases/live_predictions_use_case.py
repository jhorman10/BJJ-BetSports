"""
Live Predictions Use Case Module

Use case for generating predictions for live matches,
combining real-time data with historical statistics.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

from pytz import timezone
from src.application.dtos.dtos import (
    LeagueDTO,
    MatchDTO,
    MatchPredictionDTO,
    PredictionDTO,
    SuggestedPickDTO,
    TeamDTO,
)
from src.application.use_cases.use_cases import (
    DataSources,
    _build_match_team_statistics,
    _load_contextual_training_bundle,
    _requires_contextual_team_statistics,
)
from src.domain.entities.entities import (
    League,
    Match,
    Prediction,
    TeamStatistics,
    TrainingDataContextBundle,
)
from src.domain.services.picks_service import PicksService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.cache.cache_service import CacheService
from src.infrastructure.data_sources.football_data_org import COMPETITION_CODE_MAPPING
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)


def _determine_data_sources(
    cache_service: CacheService,
    statistics_service: StatisticsService,
    data_sources: DataSources,
    match: Match,
    bulk_history: Optional[Dict[str, List[Match]]],
) -> Tuple[Any, Any, Any, Any, Any, List[str]]:
    """Determine available data sources and load deep training stats
    if present.
    """
    # Local imports to avoid runtime cycles
    from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource

    training_results = cache_service.get("ml_training_result_data")
    home_stats = None
    away_stats = None
    league_averages = None
    data_sources_used = [FootballDataOrgSource.SOURCE_NAME]

    # Global averages (optional)
    global_avg_data = cache_service.get("global_statistical_averages")
    global_averages = None
    if global_avg_data:
        try:
            from src.domain.value_objects.value_objects import LeagueAverages

            global_averages = LeagueAverages(**global_avg_data)
        except Exception:
            global_averages = None

    if training_results and "team_stats" in training_results:
        team_stats_map = training_results["team_stats"]

        from src.domain.entities.entities import TeamStatistics

        def _dict_to_stats(name: str, raw: dict) -> TeamStatistics:
            return TeamStatistics(
                team_id=name.lower().replace(" ", "_"),
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
                recent_form=raw.get("recent_form", ""),
            )

        if match.home_team.name in team_stats_map:
            home_stats = _dict_to_stats(
                match.home_team.name, team_stats_map[match.home_team.name]
            )

        if match.away_team.name in team_stats_map:
            away_stats = _dict_to_stats(
                match.away_team.name, team_stats_map[match.away_team.name]
            )

        if home_stats and away_stats:
            data_sources_used.append("Historical (10 Years)")

    return (
        training_results,
        home_stats,
        away_stats,
        league_averages,
        global_averages,
        data_sources_used,
    )


def _build_feature_batch(
    match: Match,
    home_stats: TeamStatistics,
    away_stats: TeamStatistics,
    outcomes: List[Tuple[Any, float, str]],
) -> List[Any]:
    """Build an ML features batch from suggested picks (used by ML overrides)."""
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

        feat = MLFeatureExtractor.extract_features(p, match, home_stats, away_stats)
        features_batch.append(feat)

    return features_batch


def _normalize_and_apply_probs(
    prediction: PredictionDTO, ml_probs: List[float]
) -> None:
    """Normalize ML raw probabilities and apply them to the prediction DTO.

    Kept as a module helper so it can be unit-tested independently.
    """
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


def _persist_and_cache_response(
    use_case: "GetLivePredictionsUseCase",
    filtered_results: List[MatchPredictionDTO],
    cache_key: str,
) -> None:
    """Persist live predictions and cache them for fast retrieval."""
    try:
        # 1. Ephemeral cache (short TTL for live matches)
        use_case.cache_service.set_live_matches(filtered_results, cache_key)

        # 2. Optional persistent storage (Explorer DB)
        if use_case.persistence_repository and filtered_results:
            prediction_batch = [
                {
                    "match_id": p_dto.match.id,
                    "league_id": p_dto.match.league.id,
                    "data": p_dto.model_dump(),
                    "ttl_seconds": 3600,
                }
                for p_dto in filtered_results
            ]
            use_case.persistence_repository.bulk_save_predictions(prediction_batch)
            logger.info(
                "Indexed %d live prediction matches in Explorer DB",
                len(filtered_results),
            )
    except Exception as e:
        logger.warning("Failed to persist/cache live predictions: %s", e)


async def _get_context_bundle_from_cache(
    league_id: str,
    context_bundle_cache: Optional[
        Dict[str, Optional[TrainingDataContextBundle]]
    ] = None,
) -> Optional[TrainingDataContextBundle]:
    """Resolve and memoize the contextual bundle per league for live inference."""
    if not _requires_contextual_team_statistics(league_id):
        return None

    if context_bundle_cache is not None and league_id in context_bundle_cache:
        return context_bundle_cache[league_id]

    context_bundle = await _load_contextual_training_bundle(league_id)
    if context_bundle_cache is not None:
        context_bundle_cache[league_id] = context_bundle
    return context_bundle


@dataclass
class LiveMatchPrediction:
    """Combined live match data with prediction."""

    match: Match
    prediction: Optional[Prediction]
    is_processing: bool = False
    processing_message: Optional[str] = None


class GetLivePredictionsUseCase:
    """
    Use case for getting live matches with predictions.

    Prioritizes accuracy over speed for predictions,
    while using caching to optimize response times.
    """

    PROCESSING_MESSAGE = (
        "Estamos procesando la información para darte "
        "las probabilidades con mayor precisión"
    )

    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        cache_service: CacheService,
        picks_service: PicksService,
        persistence_repository: Optional[Any] = None,
    ) -> None:
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.cache_service = cache_service
        self.picks_service = picks_service
        self.persistence_repository = persistence_repository

    async def _get_live_matches_or_cached(
        self, filter_target_leagues: bool
    ) -> Tuple[List[Match] | List[MatchPredictionDTO], bool, str, Optional[str]]:
        cache_key = "filtered" if filter_target_leagues else "all"
        cached = await self.cache_service.aget_live_matches(cache_key)
        if cached is not None:
            cached_predictions = cast(List[MatchPredictionDTO], cached)
            logger.info("Returning %d cached live matches", len(cached_predictions))
            return cached_predictions, True, cache_key, None

        matches: List[Match] = []
        source_used = "None"

        if self.data_sources.football_data_org.is_configured:
            try:
                matches = await self.data_sources.football_data_org.get_live_matches()
                if matches:
                    source_used = "Football-Data.org"
            except Exception as e:
                logger.error("Football-Data.org live fetch failed: %s", e)

        if not matches:
            # Cache empty result for short period to avoid hammering API
            await self.cache_service.aset_live_matches([], cache_key)
            return [], False, cache_key, None

        return matches, False, cache_key, source_used

    async def _prefetch_bulk_history(
        self, matches: List[Match]
    ) -> Dict[str, List[Match]]:
        bulk_history: Dict[str, List[Match]] = {}
        if not self.data_sources.football_data_org.is_configured:
            return bulk_history

        try:
            # Identify active leagues
            active_leagues = set()
            from src.infrastructure.data_sources.football_data_org import (
                COMPETITION_CODE_MAPPING,
            )

            internal_to_comp = dict(COMPETITION_CODE_MAPPING)

            for m in matches:
                lid = m.league.id
                if lid in internal_to_comp:
                    active_leagues.add(lid)

            if not active_leagues:
                return bulk_history

            logger.info("Pre-fetching history for active leagues: %s", active_leagues)
            from datetime import timedelta

            now_date = datetime.now()
            date_from = (now_date - timedelta(days=60)).strftime("%Y-%m-%d")
            date_to = now_date.strftime("%Y-%m-%d")

            tasks = [
                self.data_sources.football_data_org.get_league_matches(
                    lid, date_from, date_to, status="FINISHED"
                )
                for lid in active_leagues
            ]

            league_results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in league_results:
                if isinstance(res, list):
                    for history_match in res:
                        h_norm = self.statistics_service._normalize_name(
                            history_match.home_team.name
                        )
                        a_norm = self.statistics_service._normalize_name(
                            history_match.away_team.name
                        )

                        bulk_history.setdefault(h_norm, []).append(history_match)
                        bulk_history.setdefault(a_norm, []).append(history_match)

            logger.info("Bulk fetched history for %d teams", len(bulk_history))
        except Exception as e:
            logger.warning("Bulk fetch failed: %s", e)

        return bulk_history

    async def _prefetch_context_bundles(
        self, matches: List[Match]
    ) -> Dict[str, Optional[TrainingDataContextBundle]]:
        contextual_leagues = sorted(
            {
                match.league.id
                for match in matches
                if _requires_contextual_team_statistics(match.league.id)
            }
        )
        if not contextual_leagues:
            return {}

        bundles = await asyncio.gather(
            *[_load_contextual_training_bundle(league_id) for league_id in contextual_leagues]
        )
        return dict(zip(contextual_leagues, bundles))

    def _finalize_and_persist(
        self, results: List[MatchPredictionDTO], cache_key: str
    ) -> List[MatchPredictionDTO]:
        # Filter live statuses
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]
        filtered_results = [p for p in results if p.match.status in live_statuses]

        logger.info(
            "%d live match predictions (after filtering %d matches)",
            len(filtered_results),
            len(results) - len(filtered_results),
        )

        _persist_and_cache_response(self, filtered_results, cache_key)
        return filtered_results

    async def execute(
        self,
        filter_target_leagues: bool = True,
    ) -> List[MatchPredictionDTO]:
        """
        Get live matches with predictions.

        Args:
            filter_target_leagues: If True, only returns matches from
                                   Premier League, La Liga, Serie A, Bundesliga

        Returns:
            List of MatchPredictionDTO with predictions
        """
        # Fetch matches (or return cached if available)
        (
            matches,
            was_cached,
            cache_key,
            source_used,
        ) = await self._get_live_matches_or_cached(filter_target_leagues)
        if was_cached:
            return cast(List[MatchPredictionDTO], matches)

        if not matches:
            return []

        live_matches = cast(List[Match], matches)

        logger.info("Fetched %d live matches from %s", len(live_matches), source_used)

        # Pre-fetch bulk history for active leagues (if available)
        bulk_history = await self._prefetch_bulk_history(live_matches)
        context_bundle_cache = await self._prefetch_context_bundles(live_matches)

        # Pre-fetch pre-calculated predictions in bulk to avoid N+1 DB calls
        pre_calculated_map: dict = {}
        # Use async mongo adapter when available to prefetch pre-calculated predictions
        try:
            from src.infrastructure.repositories.async_mongo_adapter import (
                get_async_mongo_repository,
            )

            async_repo = get_async_mongo_repository()
            match_ids = [m.id for m in live_matches]
            pre_calculated_map = await async_repo.get_match_predictions_bulk(match_ids)
        except Exception as e:
            # Fallback to sync persistence repository if async adapter fails
            logger.warning("Bulk prefetch predictions (async) failed: %s", e)
            if self.persistence_repository:
                try:
                    pre_calculated_map = await asyncio.to_thread(
                        self.persistence_repository.get_match_predictions_bulk,
                        [m.id for m in live_matches],
                    )
                except Exception as e2:
                    logger.warning(
                        "Bulk prefetch predictions (threaded) failed: %s", e2
                    )

        # Generate predictions for each match
        results: List[MatchPredictionDTO] = []

        for match in live_matches:
            # Delegate per-match processing to a helper to keep execute() small
            if "start_time" not in locals():
                import time

                start_time = time.time()

            processed = await self._process_single_live_match(
                match,
                bulk_history,
                start_time,
                pre_calculated_map,
                context_bundle_cache,
            )
            results.append(processed)

        now = get_current_time()

        # Statuses that indicate a match is currently in play
        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]

        filtered_results = []
        for p_dto in results:
            # Strict filtering: Only show matches that are statistically live
            if p_dto.match.status in live_statuses:
                filtered_results.append(p_dto)

        # Cache + persist in a single helper to keep execute() small
        logger.info(
            "%d live match predictions (after filtering %d matches)",
            len(filtered_results),
            len(results) - len(filtered_results),
        )

        _persist_and_cache_response(self, filtered_results, cache_key)

        return filtered_results

    async def _generate_prediction(
        self,
        match: Match,
        bulk_history: Optional[Dict[str, List[Match]]] = None,
        context_bundle_cache: Optional[
            Dict[str, Optional[TrainingDataContextBundle]]
        ] = None,
    ) -> PredictionDTO:
        """
        Generate prediction for a single match.

        Uses all available historical data for maximum accuracy.
        """
        # Check prediction cache (async-safe)
        cached_pred = await self.cache_service.aget_predictions(match.id)
        if cached_pred is not None:
            return cast(PredictionDTO, cached_pred)

        # Collect available stats / sources
        (
            training_results,
            home_stats,
            away_stats,
            league_averages,
            global_averages,
            data_sources_used,
        ) = _determine_data_sources(
            self.cache_service,
            self.statistics_service,
            self.data_sources,
            match,
            bulk_history,
        )

        context_bundle = None
        if _requires_contextual_team_statistics(match.league.id):
            context_bundle = (
                context_bundle_cache.get(match.league.id)
                if context_bundle_cache is not None
                else None
            )
            if context_bundle is None and context_bundle_cache is None:
                context_bundle = await _load_contextual_training_bundle(match.league.id)

        if context_bundle:
            historical_matches = await self._get_aggregated_history(match, bulk_history)
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
            league_source_matches = context_bundle.target_matches or historical_matches
            league_averages = (
                self.statistics_service.calculate_league_averages(league_source_matches)
                if league_source_matches
                else None
            )
            if "Contextual International History" not in data_sources_used:
                data_sources_used.append("Contextual International History")
        # If we don't have deep stats, aggregate history and compute stats
        elif not home_stats or not away_stats:
            historical_matches = await self._get_aggregated_history(match, bulk_history)

            if not home_stats:
                home_stats = self.statistics_service.calculate_team_statistics(
                    match.home_team.name, historical_matches
                )
            if not away_stats:
                away_stats = self.statistics_service.calculate_team_statistics(
                    match.away_team.name, historical_matches
                )

            league_averages = (
                self.statistics_service.calculate_league_averages(historical_matches)
                if historical_matches
                else None
            )
            if historical_matches:
                data_sources_used.append("Aggregated History")
        else:
            # We had deep stats; still try a light aggregation for league averages
            historical_matches = await self._get_aggregated_history(match, bulk_history)
            league_averages = (
                self.statistics_service.calculate_league_averages(historical_matches)
                if historical_matches
                else None
            )

        # Generate prediction via prediction service (offload to threadpool)
        prediction = await asyncio.to_thread(
            lambda: self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages,
                global_averages=global_averages,
                data_sources=data_sources_used,
            )
        )

        # Generate Suggested Picks (offload to threadpool)
        picks_container = await asyncio.to_thread(
            lambda: self.picks_service.generate_suggested_picks(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages,
                predicted_home_goals=prediction.predicted_home_goals,
                predicted_away_goals=prediction.predicted_away_goals,
                home_win_prob=prediction.home_win_probability,
                draw_prob=prediction.draw_probability,
                away_win_prob=prediction.away_win_probability,
            )
        )

        # Convert to DTO and cache
        prediction_dto = self._prediction_to_dto(
            prediction, picks_container.suggested_picks
        )
        await self.cache_service.aset_predictions(match.id, prediction_dto)

        return prediction_dto

    async def _process_single_live_match(
        self,
        match: Match,
        bulk_history: Dict[str, List[Match]],
        start_time: float,
        pre_calculated_map: Optional[Dict[str, Any]] = None,
        context_bundle_cache: Optional[
            Dict[str, Optional[TrainingDataContextBundle]]
        ] = None,
    ) -> MatchPredictionDTO:
        """Process a single live match: try DB lookup, otherwise run realtime inference.

        Returns a MatchPredictionDTO (may contain empty prediction on failures).
        """
        try:
            # 1. ATTEMPT DB LOOKUP (Pre-calculated in Training Action)
            pre_calculated_dto = None
            # First try the bulk-prefetched map to avoid per-match DB calls
            pre_calculated_data = None
            if pre_calculated_map and match.id in pre_calculated_map:
                pre_calculated_data = pre_calculated_map.get(match.id)

            if not pre_calculated_data and self.persistence_repository:
                try:
                    pre_calculated_data = await asyncio.to_thread(
                        self.persistence_repository.get_match_prediction, match.id
                    )
                except Exception as e:
                    logger.warning("Single pre-calculated lookup failed: %s", e)

            if pre_calculated_data:
                try:
                    pre_calculated_dto = MatchPredictionDTO(**pre_calculated_data)
                    logger.info(
                        "✓ Using pre-calculated data from DB for match %s",
                        match.id,
                    )
                except Exception as parse_e:
                    logger.warning(
                        "Failed to parse pre-calculated data for %s: %s",
                        match.id,
                        parse_e,
                    )

            if pre_calculated_dto:
                # Update potentially stale live data (score, minute) while keeping
                # AI prediction
                pre_calculated_dto.match.home_goals = match.home_goals
                pre_calculated_dto.match.away_goals = match.away_goals
                pre_calculated_dto.match.status = match.status
                pre_calculated_dto.match.minute = match.minute
                return pre_calculated_dto

            # 2. EMERGENCY FALLBACK: Real-time calculation with soft timeout
            import time

            if time.time() - start_time > 20.0:  # 20s Soft Timeout
                logger.warning(
                    "⏳ Time limit reached (20s). Skipping ML for %s "
                    "to avoid API timeout.",
                    match.id,
                )
                return MatchPredictionDTO(
                    match=self._match_to_dto(match),
                    prediction=self._empty_prediction(match.id),
                )

            logger.warning(
                "⚠ Cache/DB miss for %s. Running emergency real-time inference...",
                match.id,
            )
            prediction_dto = await self._generate_prediction(
                match,
                bulk_history,
                context_bundle_cache,
            )
            match_dto = self._match_to_dto(match)

            return MatchPredictionDTO(match=match_dto, prediction=prediction_dto)
        except Exception as e:
            logger.error(
                f"Failed to generate/retrieve prediction for match {match.id}: {e}"
            )
            # Still include match without prediction to avoid breaks
            return MatchPredictionDTO(
                match=self._match_to_dto(match),
                prediction=self._empty_prediction(match.id),
            )

    async def _get_aggregated_history(
        self, match: Match, bulk_history: Optional[Dict[str, List[Match]]] = None
    ) -> List[Match]:
        """
        Get historical matches from ALL available sources and unify them.
        Identical strategy to SuggestedPicksUseCase for consistency.
        """
        import asyncio

        internal_league_code = self._get_internal_league_code(match)

        logger.info(
            "Aggregating live prediction data for %s vs %s",
            match.home_team.name,
            match.away_team.name,
        )

        tasks = []

        # 1. CSV Data Task
        if internal_league_code:
            tasks.append(self._fetch_csv_history(internal_league_code))

        # 2. OpenFootball Task
        if internal_league_code and self.data_sources.openfootball:
            tasks.append(self._fetch_openfootball_history(internal_league_code))

        # 3. Team History Task
        tasks.append(self._fetch_team_history_apis(match, bulk_history))

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_matches: List[Match] = []
        for result in results:
            if isinstance(result, list):
                all_matches.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Error in data source fetch: {result}")

        # 4. Unify
        return self._deduplicate_and_merge(all_matches)

    async def _fetch_csv_history(self, league_code: str) -> list[Match]:
        try:
            csv_history = (
                await self.data_sources.football_data_uk.get_historical_matches(
                    league_code, seasons=["2425", "2324", "2223", "2122"]
                )
            )
            return cast(list[Match], csv_history)
        except Exception as exc:
            logger.warning("Failed to fetch CSV history for %s: %s", league_code, exc)
            return []

    async def _fetch_openfootball_history(self, league_code: str) -> list[Match]:
        try:
            from src.infrastructure.data_sources.football_data_uk import (
                LEAGUES_METADATA,
            )

            if league_code in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_code]
                temp_league = League(
                    id=league_code,
                    name=meta["name"],
                    country=meta["country"],
                )
                matches = await self.data_sources.openfootball.get_matches(temp_league)
                return [m for m in matches if m.status in ["FT", "AET", "PEN"]]
        except Exception as exc:
            logger.warning("OpenFootball fetch failed for %s: %s", league_code, exc)
        return []

    async def _fetch_team_history_apis(
        self, match: Match, bulk_history: Optional[Dict[str, List[Match]]] = None
    ) -> list[Match]:
        team_matches = []

        # Optimization: Check Bulk History First
        if bulk_history:
            h_norm = self.statistics_service._normalize_name(match.home_team.name)
            a_norm = self.statistics_service._normalize_name(match.away_team.name)

            found_bulk = False
            if h_norm in bulk_history:
                team_matches.extend(bulk_history[h_norm])
                found_bulk = True
            if a_norm in bulk_history:
                team_matches.extend(bulk_history[a_norm])
                found_bulk = True

            if found_bulk:
                # logger.debug(f"Using bulk history for
                # {match.home_team.name}/{match.away_team.name}")
                return team_matches

            # Aumentamos el límite para mejorar la significancia estadística (Ley de los
            # Grandes Números)
            history_limit = 25

        # Strategy B: Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            try:
                h_hist = await self.data_sources.football_data_org.get_team_history(
                    match.home_team.name, limit=history_limit
                )
                a_hist = await self.data_sources.football_data_org.get_team_history(
                    match.away_team.name, limit=history_limit
                )
                team_matches.extend(h_hist + a_hist)
            except Exception as exc:
                logger.warning("Football-Data.org history fetch failed: %s", exc)

        return team_matches

    def _deduplicate_and_merge(self, matches: list[Match]) -> list[Match]:
        unique_map = {}
        for m in matches:
            date_key = m.match_date.strftime("%Y-%m-%d")
            h_key = "".join(filter(str.isalpha, m.home_team.name)).lower()[:10]
            a_key = "".join(filter(str.isalpha, m.away_team.name)).lower()[:10]
            key = f"{date_key}|{h_key}|{a_key}"

            if key not in unique_map:
                unique_map[key] = m
            else:
                existing = unique_map[key]
                # Priorizamos datos con estadísticas más ricas para mejorar la precisión
                # del modelo
                current_score = 0
                existing_score = 0

                if m.home_corners is not None:
                    current_score += 1
                if m.home_shots_on_target is not None:
                    current_score += 1
                if m.home_yellow_cards is not None:
                    current_score += 1

                if existing.home_corners is not None:
                    existing_score += 1
                if existing.home_shots_on_target is not None:
                    existing_score += 1
                if existing.home_yellow_cards is not None:
                    existing_score += 1

                if current_score > existing_score:
                    unique_map[key] = m

        result = list(unique_map.values())
        result.sort(key=lambda x: x.match_date, reverse=True)
        return result

    def _get_internal_league_code(self, match: Match) -> Optional[str]:
        """Map Football-Data.org competition code to internal code."""
        try:
            # Match objects from Football-Data.org already have internal league id if
            # parsed via _parse_match
            # but for safety we can check mapping
            for internal_code, org_code in COMPETITION_CODE_MAPPING.items():
                if internal_code == match.league.id:
                    return cast(str, match.league.id)
        except Exception as exc:
            logger.debug(
                "Failed to map internal league code for match %s: %s",
                getattr(match, "id", None),
                exc,
            )
        return None

    def _match_to_dto(self, match: Match) -> MatchDTO:
        """Convert Match entity to DTO."""
        from src.domain.services.team_service import TeamService

        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=match.home_team.short_name
                or TeamService.get_team_short_name(match.home_team.name),
                country=match.home_team.country,
                logo_url=match.home_team.logo_url
                or TeamService.get_team_logo(match.home_team.name),
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=match.away_team.short_name
                or TeamService.get_team_short_name(match.away_team.name),
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
            minute=match.minute,
            # Extended Stats (MatchDTO validator ensures consistency)
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
        self, prediction: Prediction, picks: list = []
    ) -> PredictionDTO:
        """Convert Prediction entity to DTO."""
        from src.application.dtos.dtos import PredictionDTO

        picks_dtos = []
        for p in picks:
            picks_dtos.append(
                SuggestedPickDTO(
                    market_type=p.market_type,
                    market_label=p.market_label,
                    probability=p.probability,
                    confidence_level=p.confidence_level,
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
            )

        # Top ML Picks = All picks with probability >= 75% (ML High Confidence tier)
        top_ml_threshold = 0.75
        top_ml_picks = [p for p in picks_dtos if p.probability >= top_ml_threshold]
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
            confidence=prediction.confidence,
            data_sources=prediction.data_sources,
            recommended_bet=prediction.recommended_bet,
            over_under_recommendation=prediction.over_under_recommendation,
            suggested_picks=picks_dtos,
            top_ml_picks=top_ml_picks,
            created_at=prediction.created_at,
        )

    def _empty_prediction(self, match_id: str) -> PredictionDTO:
        """Create an empty prediction DTO for when prediction fails."""
        return PredictionDTO(
            match_id=match_id,
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
            created_at=datetime.now(timezone("America/Bogota")),
        )
