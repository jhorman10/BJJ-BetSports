"""
Suggested Picks Use Case Module

Use case for generating AI-suggested betting picks for a match.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from pytz import timezone

if TYPE_CHECKING:
    from src.application.use_cases.use_cases import DataSources

from src.application.dtos.dtos import (
    BettingFeedbackRequestDTO,
    BettingFeedbackResponseDTO,
    LearningStatsResponseDTO,
    MarketPerformanceDTO,
    MatchSuggestedPicksDTO,
    SuggestedPickDTO,
    TopMLPicksDTO,
)
from src.domain.entities.betting_feedback import BettingFeedback
from src.domain.entities.entities import League, Match, Team
from src.domain.entities.suggested_pick import MatchSuggestedPicks
from src.domain.exceptions import InsufficientDataException

# Use the new AI-driven service
from src.domain.services.ai_picks_service import AIPicksService
from src.domain.services.learning_service import LearningService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.infrastructure.cache.cache_service import CacheService
from src.infrastructure.data_sources.club_elo import ClubEloSource

logger = logging.getLogger(__name__)


class GetSuggestedPicksUseCase:
    """Use case for getting AI-suggested picks for a match."""

    def __init__(
        self,
        data_sources: "DataSources",  # DataSources from use_cases.py
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        learning_service: LearningService,
        cache_service: CacheService,
    ) -> None:
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.learning_service = learning_service
        self.cache_service = cache_service
        self.odds_api = None  # TheOddsAPISource removed
        # Initialize new sources if not passed in data_sources (fallback)
        self.club_elo = getattr(data_sources, "club_elo", None) or ClubEloSource()

        # Upgrade to AI Picks Service
        self.picks_service = AIPicksService(
            learning_weights=learning_service.learning_weights
        )

    async def execute(
        self,
        match_id: str,
        match_data: Optional[Match] = None,
        pre_fetched_history: Optional[list[Match]] = None,
    ) -> Optional[MatchSuggestedPicksDTO]:
        """
        Generate suggested picks for a match. Guaranteed to use real data.
        """
        try:
            from src.application.use_cases.use_cases import (
                _build_match_team_statistics,
                _load_contextual_training_bundle,
            )

            # 1. Get match details (always returns a Match if reconstructible)
            match = match_data if match_data else await self._get_match(match_id)
            if not match:
                logger.warning(
                    f"Match {match_id} could not be identified after fallbacks."
                )
                from src.utils.time_utils import get_current_time

                return MatchSuggestedPicksDTO(
                    match_id=match_id,
                    suggested_picks=[],
                    combination_warning="Partido no encontrado o datos insuficientes.",
                    generated_at=get_current_time(),
                )

            context_bundle = await _load_contextual_training_bundle(match.league.id)

            # 1.5 Fetch Global Averages (async-safe)
            global_avg_data = await self.cache_service.aget(
                "global_statistical_averages"
            )
            global_averages = None
            if global_avg_data:
                from src.domain.value_objects.value_objects import LeagueAverages

                global_averages = LeagueAverages(**global_avg_data)

            # 2. Get historical matches (Aggregated: CSV + OpenFootball + APIs)
            if pre_fetched_history is not None:
                historical_matches = pre_fetched_history
                _data_sources_used = ["Bulk Pre-fetch"]
            else:
                historical_matches = await self._get_historical_matches(match)
                _data_sources_used = ["Historical Data"]

            # 3. Calculate team statistics
            # These will contain MP=0 if no history found, but service handles it.
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

            # 4. Calculate League Averages (REAL data from aggregated history)
            league_source_matches = (
                context_bundle.target_matches if context_bundle else historical_matches
            )
            league_averages = self.statistics_service.calculate_league_averages(
                league_source_matches
            )
            if (
                context_bundle
                and "Contextual International History" not in _data_sources_used
            ):
                _data_sources_used.append("Contextual International History")

            # 4. Enrich with new sources (Best effort, no blocking)
            highlights_url = None
            rt_odds = None
            home_elo, away_elo = None, None
            try:
                # Get real-time odds (Now integrated from Match details via ESPN)
                # If match has odds, we use them as "rt_odds" format for the prediction
                # service
                if match.home_odds and match.away_odds:
                    # Construct odds dictionary in format expected by
                    # PredictionService/PicksService
                    # The Service expects a dictionary where keys might be bookmakers or
                    # outcomes?
                    # The original code produced: {outcome_name: price} e.g. {"Arsenal":
                    # 1.5, "Chelsea": 4.0}
                    # To be compatible, we should use Team Names.
                    rt_odds = {
                        match.home_team.name: match.home_odds,
                        match.away_team.name: match.away_odds,
                    }
                    if match.draw_odds:
                        rt_odds["Draw"] = match.draw_odds

                # Get Elo from ClubElo
                home_elo, away_elo = await self.club_elo.get_elo_for_match(
                    match.home_team.name, match.away_team.name
                )

            except Exception as e:
                logger.warning("Secondary data enrichment failed: %s", e)

            # Define sources used
            prediction_sources = list(_data_sources_used)
            if not prediction_sources:
                prediction_sources = ["Historical Data"]
            if pre_fetched_history and "Bulk Context" not in prediction_sources:
                prediction_sources.append("Bulk Context")
            if self.data_sources.football_data_org.is_configured:
                prediction_sources.append("Football-Data.org")
            if rt_odds:
                prediction_sources.append("The Odds API")
            if home_elo:
                prediction_sources.append("ClubElo")
            # 5. Generate prediction (offload CPU/blocking work to threadpool)
            prediction = await asyncio.to_thread(
                lambda: self.prediction_service.generate_prediction(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=league_averages,
                    global_averages=global_averages,
                    data_sources=prediction_sources,
                    highlights_url=highlights_url,
                    real_time_odds=rt_odds,
                    home_elo=home_elo,
                    away_elo=away_elo,
                )
            )

            # 6. Generate suggested picks (offload to threadpool)
            suggested_picks_container = await asyncio.to_thread(
                lambda: self.picks_service.generate_suggested_picks(
                    match=match,
                    home_stats=(
                        home_stats
                        if home_stats and home_stats.matches_played > 0
                        else None
                    ),
                    away_stats=(
                        away_stats
                        if away_stats and away_stats.matches_played > 0
                        else None
                    ),
                    league_averages=league_averages,
                    predicted_home_goals=prediction.predicted_home_goals,
                    predicted_away_goals=prediction.predicted_away_goals,
                    home_win_prob=prediction.home_win_probability,
                    draw_prob=prediction.draw_probability,
                    away_win_prob=prediction.away_win_probability,
                )
            )

            # 7. Convert to DTO
            # Populate DTO
            picks_dtos = []
            for pick in suggested_picks_container.suggested_picks:
                from src.application.dtos.dtos import SuggestedPickDTO

                picks_dtos.append(
                    SuggestedPickDTO(
                        market_type=pick.market_type,
                        market_label=pick.market_label,
                        probability=pick.probability,
                        confidence_level=pick.confidence_level,
                        reasoning=pick.reasoning,
                        risk_level=pick.risk_level,
                        is_recommended=pick.is_recommended,
                        priority_score=pick.priority_score,
                        is_ml_confirmed=pick.is_ml_confirmed,
                        is_ia_confirmed=getattr(pick, "is_ia_confirmed", False),
                        ml_confidence=pick.ml_confidence,
                        suggested_stake=pick.suggested_stake,
                        kelly_percentage=pick.kelly_percentage,
                        clv_beat=getattr(pick, "clv_beat", False),
                        expected_value=pick.expected_value,
                        opening_odds=pick.odds,
                        closing_odds=getattr(pick, "closing_odds", 0.0),
                    )
                )

            # Build Prediction DTO (optional for internal consistency)
            from src.application.dtos.dtos import PredictionDTO

            _pred_dto = PredictionDTO(
                match_id=match.id,
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
                created_at=prediction.created_at,
            )

            from src.utils.time_utils import get_current_time

            return MatchSuggestedPicksDTO(
                match_id=match.id,
                suggested_picks=picks_dtos,
                highlights_url=highlights_url,
                real_time_odds=rt_odds,
                generated_at=get_current_time(),
            )

        except InsufficientDataException as e:
            logger.info("Skipping prediction for %s: %s", match_id, e)
            from src.utils.time_utils import get_current_time

            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=[],
                combination_warning=f"Datos insuficientes: {str(e)}",
                highlights_url=highlights_url,
                real_time_odds=rt_odds,
                generated_at=get_current_time(),
            )
        except Exception as e:
            logger.error(
                "Error in suggested picks execution for %s: %s",
                match_id,
                e,
                exc_info=True,
            )
            # Return empty DTO instead of None to avoid 500 validation error
            from src.utils.time_utils import get_current_time

            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=[],
                combination_warning="Error inesperado al generar picks.",
                generated_at=get_current_time(),
            )

    async def _get_match(self, match_id: str) -> Optional[Match]:
        """Get match details from available sources with cache fallbacks."""
        # 1. Optimization: If ID is synthetic (contains underscores), skip external APIs
        if "_" in match_id:
            return self._reconstruct_match_from_id(match_id)

        # 2. Try Football-Data.org regular fetch
        if self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(
                match_id
            )
            if match:
                return match
        # This is vital when the account is suspended/limited but we already fetched the
        # list
        try:
            # Use injected cache_service (async-safe wrapper present)
            cache = self.cache_service
            for key in ["filtered", "all"]:
                live_preds = await cache.aget_live_matches(key)
                if live_preds:
                    # live_preds is List[MatchPredictionDTO]
                    for lp in live_preds:
                        if str(lp.match.id) == str(match_id):
                            logger.info(
                                "✓ Found match %s in live_matches cache fallback",
                                match_id,
                            )
                            # Convert DTO back to Entity (minimal version)
                            from src.domain.entities.entities import League, Team

                            return Match(
                                id=lp.match.id,
                                home_team=Team(
                                    id=lp.match.home_team.id,
                                    name=lp.match.home_team.name,
                                ),
                                away_team=Team(
                                    id=lp.match.away_team.id,
                                    name=lp.match.away_team.name,
                                ),
                                league=League(
                                    id=lp.match.league.id,
                                    name=lp.match.league.name,
                                    country=lp.match.league.country,
                                ),
                                match_date=lp.match.match_date,
                                status=lp.match.status or "NS",
                            )
        except Exception as e:
            logger.warning("Live matches cache fallback failed for %s: %s", match_id, e)

        # Final Fallback: Reconstruct from ID if it follows our custom format
        # Format: {LeagueCode}_{YYYYMMDD}_{Home}_{Away}
        return self._reconstruct_match_from_id(match_id)

    def _reconstruct_match_from_id(self, match_id: str) -> Optional[Match]:
        """
        Reconstruct a Match object from a synthetic ID string.
        Format expected: LEAGUE_DATE_HOME_AWAY
        """
        try:
            parts = match_id.split("_")
            if len(parts) < 4:
                return None

            league_code = parts[0]
            date_str = parts[1]
            # Teams might contain underscores, so we join the middle parts carefully
            # Usually strict format, but let's assume home/away are at the end?
            # Actually, standard format used in this project seems to be:
            # ID = f"{league.id}_{date_str}_{home_slug}_{away_slug}"
            # This is ambiguous if slugs have underscores.
            # But usually we can assume the first 2 parts are fixed.

            # Let's try to infer names.
            # If we split by "_", and we know League and Date are first two.
            # The rest is Home and Away.
            # This is tricky without a separator.
            # BUT, we can just use the slug as the name for lookup purposes.
            # The Stats Service handles fuzzy matching usually.

            # Heuristic: Split remaining into two halves? No.
            # Let's look at the specific ID:
            # B1_20260207_sporting_charleroi_cercle_brugge
            # sporting_charleroi (2 words)
            # cercle_brugge (2 words)

            # We can't perfectly separate them without knowing the teams.
            # However, we can return a "Skeleton Match" and let the History Aggregator
            # find the real teams using the fuzzy search on the Combined string or
            # specific history fetch.

            # Actually, let's look at how the ID was likely constructed.
            # If we assume the middle is the split... no.

            # BETTER APPROACH:
            # We use the raw parts as "Home" and "Away" candidates in a generic way
            # OR we try to find these team slugs in our database/constants.

            # For now, let's make a best effort split.
            # parts[0] = B1
            # parts[1] = 20260207
            # parts[2:] = [sporting, charleroi, cercle, brugge]

            rest = parts[2:]
            mid = len(rest) // 2
            home_slug = "_".join(rest[:mid])
            away_slug = "_".join(rest[mid:])

            # Format Name from slug: sporting_charleroi -> Sporting Charleroi
            home_name = home_slug.replace("_", " ").title()
            away_name = away_slug.replace("_", " ").title()

            match_date = datetime.strptime(date_str, "%Y%m%d")

            league = League(
                id=league_code,
                name=f"League {league_code}",
                country="Unknown",
                season=str(match_date.year),  # Approx
            )

            home_team = Team(
                id=f"synthetic_{home_slug}", name=home_name, country="Unknown"
            )
            away_team = Team(
                id=f"synthetic_{away_slug}", name=away_name, country="Unknown"
            )

            logger.info(
                "Reconstructed synthetic match from ID: %s vs %s",
                home_name,
                away_name,
            )

            return Match(
                id=match_id,
                league=league,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                status="NS",  # Not Started assumed
                home_goals=None,
                away_goals=None,
            )

        except Exception as e:
            logger.warning("Failed to reconstruct match from ID %s: %s", match_id, e)
            return None

    async def _get_historical_matches(self, match: Match) -> list[Match]:
        """
        Get historical matches from ALL available sources and unify them.

        Strategy: Aggregation & Unification
        1. Fetch CSV Data (Rich stats, historical depth)
        2. Fetch OpenFootball (Basic stats, high availability)
        3. Fetch API Team History (Recent form, specific team focus)
        4. Merge and Deduplicate, preferring entries with more stats.
        """
        import asyncio

        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING

        # Determine internal league code
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        internal_league_code = None

        from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA

        if match.league.id in LEAGUES_METADATA:
            internal_league_code = match.league.id
        else:
            try:
                lid = int(match.league.id)
                if lid in api_id_to_code:
                    internal_league_code = api_id_to_code[lid]
            except (ValueError, TypeError):
                pass

        logger.info(
            "Aggregating data for %s vs %s (League: %s)",
            match.home_team.name,
            match.away_team.name,
            internal_league_code,
        )

        tasks = []

        # 1. CSV Data Task
        if internal_league_code:
            tasks.append(self._fetch_csv_history(internal_league_code))

        # 2. OpenFootball Task
        if internal_league_code and self.data_sources.openfootball:
            tasks.append(self._fetch_openfootball_history(internal_league_code))

        # 3. Team History Task (Football-Data.org & Others)
        tasks.append(self._fetch_team_history_apis(match))

        # Execute all fetches in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_matches = []
        for result in results:
            if isinstance(result, list):
                all_matches.extend(result)
            elif isinstance(result, Exception):
                logger.warning("Error in data source fetch: %s", result)

        # 4. Unify and Deduplicate
        unified_matches = self._deduplicate_and_merge(all_matches)
        logger.info(
            "Data Aggregation: %s raw matches -> %s unique unified matches",
            len(all_matches),
            len(unified_matches),
        )

        return unified_matches

    async def _fetch_csv_history(self, league_code: str) -> list[Match]:
        try:
            csv_history = (
                await self.data_sources.football_data_uk.get_historical_matches(
                    league_code, seasons=["2425", "2324"]
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
    ) -> List[Match]:
        """Fetch history specifically for the two teams from APIs."""
        team_matches = []

        # Strategy A: Football-Data.org
        # Strategy B: Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            try:
                # Football-Data.org uses names for history fetch in this project's
                # implementation
                h_hist = await self.data_sources.football_data_org.get_team_history(
                    match.home_team.name, limit=10
                )
                a_hist = await self.data_sources.football_data_org.get_team_history(
                    match.away_team.name, limit=10
                )
                team_matches.extend(h_hist + a_hist)
            except Exception as e:
                logger.warning("Football-Data.org history fetch failed: %s", e)

        return team_matches

    def _deduplicate_and_merge(self, matches: list[Match]) -> list[Match]:
        """
        Deduplicate matches based on Date and Teams.
        Merge strategy: Keep the instance with the most statistical data.
        """
        unique_map = {}

        for m in matches:
            # Create a normalized key: YYYY-MM-DD|HOME|AWAY
            # Using simple string cleaning for fuzzy match robustness
            date_key = m.match_date.strftime("%Y-%m-%d")
            h_key = "".join(filter(str.isalpha, m.home_team.name)).lower()[:10]
            a_key = "".join(filter(str.isalpha, m.away_team.name)).lower()[:10]
            key = f"{date_key}|{h_key}|{a_key}"

            if key not in unique_map:
                unique_map[key] = m
            else:
                existing = unique_map[key]
                # MERGE LOGIC: Replace if 'm' has better stats than 'existing'

                # Check 1: Does new one have corners? (Crucial for picks)
                new_has_stats = m.home_corners is not None
                old_has_stats = existing.home_corners is not None

                if new_has_stats and not old_has_stats:
                    unique_map[key] = m  # Upgrade!
                elif new_has_stats and old_has_stats:
                    # Both have stats, maybe prefer CSV (Football-Data.co.uk) over API?
                    # Usually CSV is cleaner. But let's assume they are similar.
                    # Maybe check for shots?
                    if (
                        m.home_shots_on_target is not None
                        and existing.home_shots_on_target is None
                    ):
                        unique_map[key] = m

        # Sort by date descending
        result = list(unique_map.values())
        result.sort(key=lambda x: x.match_date, reverse=True)
        return result

    def _to_dto(self, picks: MatchSuggestedPicks) -> MatchSuggestedPicksDTO:
        """Convert domain object to DTO."""
        pick_dtos = [
            SuggestedPickDTO(
                market_type=p.market_type.value,
                market_label=p.market_label,
                probability=p.probability,
                confidence_level=p.confidence_level.value,
                reasoning=p.reasoning,
                risk_level=p.risk_level,
                is_recommended=p.is_recommended,
                priority_score=p.priority_score,
                is_ml_confirmed=getattr(p, "is_ml_confirmed", False),
                is_ia_confirmed=getattr(p, "is_ia_confirmed", False),
            )
            for p in picks.suggested_picks
        ]

        return MatchSuggestedPicksDTO(
            match_id=picks.match_id,
            suggested_picks=pick_dtos,
            combination_warning=picks.combination_warning,
            generated_at=picks.generated_at,
        )


class RegisterFeedbackUseCase:
    """Use case for registering betting feedback."""

    def __init__(self, learning_service: LearningService):
        self.learning_service = learning_service

    def execute(self, request: BettingFeedbackRequestDTO) -> BettingFeedbackResponseDTO:
        """
        Register betting feedback and update learning weights.

        Args:
            request: Feedback request with bet outcome

        Returns:
            Response with new confidence adjustment
        """
        # Create feedback entity
        feedback = BettingFeedback(
            bet_id=str(uuid.uuid4()),
            match_id=request.match_id,
            market_type=request.market_type,
            prediction=request.prediction,
            actual_outcome=request.actual_outcome,
            was_correct=request.was_correct,
            odds=request.odds,
            stake=request.stake,
        )

        # Register with learning service
        self.learning_service.register_feedback(feedback)

        # Get new adjustment
        new_adjustment = self.learning_service.get_market_adjustment(
            request.market_type
        )

        return BettingFeedbackResponseDTO(
            success=True,
            message=f"Feedback registered for {request.market_type}",
            market_type=request.market_type,
            new_confidence_adjustment=new_adjustment,
        )


class GetLearningStatsUseCase:
    """Use case for getting learning statistics."""

    def __init__(self, learning_service: LearningService):
        self.learning_service = learning_service

    def execute(self) -> LearningStatsResponseDTO:
        """
        Get all learning statistics.

        Returns:
            Response with market performance data
        """
        all_stats = self.learning_service.get_all_stats()

        performance_dtos = [
            MarketPerformanceDTO(
                market_type=perf.market_type,
                total_predictions=perf.total_predictions,
                correct_predictions=perf.correct_predictions,
                success_rate=perf.success_rate,
                avg_odds=perf.avg_odds,
                total_profit_loss=perf.total_profit_loss,
                confidence_adjustment=perf.confidence_adjustment,
                last_updated=perf.last_updated,
            )
            for perf in all_stats.values()
        ]

        total_count = sum(p.total_predictions for p in all_stats.values())
        last_updated = max(
            (p.last_updated for p in all_stats.values()),
            default=datetime.now(timezone("America/Bogota")),
        )

        return LearningStatsResponseDTO(
            market_performances=performance_dtos,
            total_feedback_count=total_count,
            last_updated=last_updated,
        )


class GetTopMLPicksUseCase:
    """Use case for retrieving the top ML picks across all leagues."""

    def __init__(self, persistence_repository: Any) -> None:
        self.persistence_repository = persistence_repository

    async def execute(
        self, limit: int = 50, league_id: Optional[str] = None
    ) -> Optional["TopMLPicksDTO"]:
        """
        Synthesize top picks from predictions.

        Args:
            limit: Max number of picks to return
            league_id: Optional filter to calculate top picks for specific league only
        """
        try:
            # 1. Get predictions (All or League Specific)
            if league_id:
                active_preds = self.persistence_repository.get_league_predictions(
                    league_id
                )
            else:
                active_preds = self.persistence_repository.get_all_active_predictions()

            from src.application.dtos.dtos import SuggestedPickDTO, TopMLPicksDTO

            # 2. Extract best pick from each prediction
            unique_match_picks = []

            for pred_data in active_preds:
                if "prediction" in pred_data:
                    payload = pred_data["prediction"]
                elif "data" in pred_data:
                    payload = pred_data["data"]
                else:
                    payload = pred_data
                if not isinstance(payload, dict):
                    continue

                prediction = payload.get("prediction", {})
                match_info = payload.get("match", {})

                # Check match date (ensure only future matches)
                from src.utils.time_utils import get_current_time

                now = get_current_time()  # Returns Bogota time

                match_date_str = match_info.get("match_date")
                if match_date_str:
                    try:
                        # Fallback for dateutil missing
                        m_date = None
                        try:
                            # Try standard ISO first
                            m_date = match_date_str.replace("Z", "+00:00")
                            m_date = datetime.fromisoformat(m_date)
                        except (ValueError, AttributeError) as e:
                            logger.warning(
                                "Could not parse date %s: %s",
                                match_date_str,
                                e,
                            )
                            continue
                        if m_date.tzinfo is None:
                            # Prefer the runtime tzinfo; otherwise use the
                            # project fallback timezone helper.
                            from src.utils.time_utils import COLOMBIA_TZ

                            m_date = cast(datetime, COLOMBIA_TZ.localize(m_date))
                        else:
                            m_date = m_date.astimezone(now.tzinfo)

                        from datetime import timedelta

                        # Statuses that indicate a match is currently in play
                        live_statuses = ["1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"]

                        # Allow if:
                        # 1. It's in the future
                        # 2. It's currently marked as live
                        # 3. It's PAUSED/HALFTIME etc.
                        if match_info.get("status") in ["FT", "AET", "PEN", "FINISHED"]:
                            continue

                        is_recent = (now - m_date) < timedelta(minutes=150)

                        if (
                            m_date <= now
                            and match_info.get("status") not in live_statuses
                            and not is_recent
                        ):
                            continue  # Skip past and finished matches
                    except Exception as e:
                        logger.warning("Error parsing date %s: %s", match_date_str, e)

                picks = prediction.get("suggested_picks", [])

                home_name = match_info.get("home_team", {}).get("name", "")
                away_name = match_info.get("away_team", {}).get("name", "")
                match_label = f"{home_name} vs {away_name}"
                _match_id = match_info.get("id")

                # Local sorting to find the best pick for THIS match
                match_picks_objects = []
                for p in picks:
                    if isinstance(p, dict):
                        # Enrich reasoning with match info for the global list
                        base_reasoning = p.get("reasoning", "")
                        p["reasoning"] = f"[{match_label}] {base_reasoning}"

                        dto = SuggestedPickDTO(**p)
                        match_picks_objects.append(dto)

                if not match_picks_objects:
                    continue

                # Sort match specific picks
                match_picks_objects.sort(
                    key=lambda x: (
                        getattr(x, "is_ia_confirmed", False),
                        getattr(x, "is_ml_confirmed", False),
                        x.priority_score,
                        x.probability,
                    ),
                    reverse=True,
                )

                # Take the BEST one
                best_pick = match_picks_objects[0]
                unique_match_picks.append(best_pick)

            # 3. Sort unified picks (best from each match)
            # Primary: IA Confirmed (Absolute Best)
            # Secondary: ML Confirmed (High Confidence)
            # Tertiary: Priority Score (Expected Value + ML Confidence)
            # Quaternary: Probability
            unique_match_picks.sort(
                key=lambda x: (
                    getattr(x, "is_ia_confirmed", False),  # True (1) > False (0)
                    getattr(x, "is_ml_confirmed", False),
                    x.priority_score,
                    x.probability,
                ),
                reverse=True,
            )

            # 4. Limit
            top_picks = unique_match_picks[:limit]

            from src.utils.time_utils import get_current_time

            return TopMLPicksDTO(picks=top_picks, generated_at=get_current_time())

        except Exception as e:
            logger.error("Error generating Top ML Picks: %s", e, exc_info=True)
            return None
