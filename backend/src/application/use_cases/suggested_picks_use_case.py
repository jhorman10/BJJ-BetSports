"""
Suggested Picks Use Case Module

Use case for generating AI-suggested betting picks for a match.
"""

import logging
from datetime import datetime
from typing import Optional
import uuid
from pytz import timezone

from src.domain.entities.entities import Match, League, Team
from src.infrastructure.cache.cache_service import CacheService
from src.domain.entities.suggested_pick import MatchSuggestedPicks, SuggestedPick
from src.domain.entities.betting_feedback import BettingFeedback
from src.domain.services.picks_service import PicksService
# Use the new AI-driven service
from src.domain.services.ai_picks_service import AIPicksService
from src.domain.services.learning_service import LearningService

from src.infrastructure.data_sources.fotmob_source import FotMobSource
from src.infrastructure.data_sources.club_elo import ClubEloSource
from src.infrastructure.data_sources.understat_source import UnderstatSource
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.exceptions import InsufficientDataException
from src.application.dtos.dtos import (
    SuggestedPickDTO,
    MatchSuggestedPicksDTO,
    BettingFeedbackRequestDTO,
    BettingFeedbackResponseDTO,
    MarketPerformanceDTO,
    LearningStatsResponseDTO,
)


logger = logging.getLogger(__name__)


class GetSuggestedPicksUseCase:
    """Use case for getting AI-suggested picks for a match."""
    
    def __init__(
        self,
        data_sources,  # DataSources from use_cases.py
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        learning_service: LearningService,
        cache_service: CacheService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.learning_service = learning_service
        self.learning_service = learning_service
        self.cache_service = cache_service
        self.odds_api = None # TheOddsAPISource removed
        # Initialize new sources if not passed in data_sources (fallback)
        self.club_elo = getattr(data_sources, "club_elo", None) or ClubEloSource()
        self.understat = getattr(data_sources, "understat", None) or UnderstatSource()
        self.fotmob = getattr(data_sources, "fotmob", None) or FotMobSource()
        
        # Upgrade to AI Picks Service
        self.picks_service = AIPicksService(
            learning_weights=learning_service.get_learning_weights()
        )
    
    async def execute(
        self, 
        match_id: str,
        match_data: Optional[Match] = None,
        pre_fetched_history: Optional[list[Match]] = None
    ) -> Optional[MatchSuggestedPicksDTO]:
        """
        Generate suggested picks for a match. Guaranteed to use real data.
        """
        try:
            # 1. Get match details (always returns a Match if reconstructible)
            match = match_data if match_data else await self._get_match(match_id)
            if not match:
                logger.warning(f"Match {match_id} could not be identified after fallbacks.")
                from src.utils.time_utils import get_current_time
                return MatchSuggestedPicksDTO(
                    match_id=match_id,
                    suggested_picks=[],
                    combination_warning="Partido no encontrado o datos insuficientes.",
                    generated_at=get_current_time()
                )
            
            # 1.5 Fetch Global Averages
            global_avg_data = self.cache_service.get("global_statistical_averages")
            global_averages = None
            if global_avg_data:
                from src.domain.value_objects.value_objects import LeagueAverages
                global_averages = LeagueAverages(**global_avg_data)

            # 2. Get historical matches (Aggregated: CSV + OpenFootball + APIs)
            if pre_fetched_history is not None:
                historical_matches = pre_fetched_history
                data_sources_used = ["Bulk Pre-fetch"]
            else:
                historical_matches = await self._get_historical_matches(match)
                data_sources_used = ["Historical Data"]
            
            # 3. Calculate team statistics
            # These will containMP=0 if no history found, but service handles it.
            home_stats = self.statistics_service.calculate_team_statistics(
                match.home_team.name,
                historical_matches,
            )
            away_stats = self.statistics_service.calculate_team_statistics(
                match.away_team.name,
                historical_matches,
            )
            
            # 4. Calculate League Averages (REAL data from aggregated history)
            league_averages = self.statistics_service.calculate_league_averages(historical_matches)
            
            # 4. Enrich with new sources (Best effort, no blocking)
            highlights_url = None
            rt_odds = None
            home_elo, away_elo = None, None
            try:
                # Get real-time odds (Now integrated from Match details via ESPN)
                # If match has odds, we use them as "rt_odds" format for the prediction service
                if match.home_odds and match.away_odds:
                    # Construct odds dictionary in format expected by PredictionService/PicksService
                    # The Service expects a dictionary where keys might be bookmakers or outcomes?
                    # The original code produced: {outcome_name: price} e.g. {"Arsenal": 1.5, "Chelsea": 4.0}
                    # To be compatible, we should use Team Names.
                    rt_odds = {
                        match.home_team.name: match.home_odds,
                        match.away_team.name: match.away_odds
                    }
                    if match.draw_odds:
                        rt_odds["Draw"] = match.draw_odds
                
                # Get Elo from ClubElo
                home_elo, away_elo = await self.club_elo.get_elo_for_match(match.home_team.name, match.away_team.name)
                
            except Exception as e:
                logger.warning(f"Secondary data enrichment failed: {e}")

            # Define sources used
            prediction_sources = ["Historical Data"]
            if pre_fetched_history: prediction_sources.append("Bulk Context")
            if self.data_sources.football_data_org.is_configured:
                prediction_sources.append("Football-Data.org")
            if rt_odds:
                prediction_sources.append("The Odds API")
            if home_elo:
                prediction_sources.append("ClubElo")
            # Check if stats imply FotMob usage (corners available)
            if home_stats and home_stats.matches_with_corners > 0:
                prediction_sources.append("FotMob")

            # 5. Generate prediction
            prediction = self.prediction_service.generate_prediction(
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
            
            # 6. Generate suggested picks
            suggested_picks_container = self.picks_service.generate_suggested_picks(
                match=match,
                home_stats=home_stats if home_stats and home_stats.matches_played > 0 else None,
                away_stats=away_stats if away_stats and away_stats.matches_played > 0 else None,
                league_averages=league_averages,
                predicted_home_goals=prediction.predicted_home_goals,
                predicted_away_goals=prediction.predicted_away_goals,
                home_win_prob=prediction.home_win_probability,
                draw_prob=prediction.draw_probability,
                away_win_prob=prediction.away_win_probability,
            )
            
            # 7. Convert to DTO
            from src.application.use_cases.live_predictions_use_case import GetLivePredictionsUseCase
            # Leverage existing mapping logic from live predictions for consistency
            temp_use_case = GetLivePredictionsUseCase(
                self.data_sources, self.prediction_service, self.statistics_service, None, self.picks_service
            )
            
            # Populate DTO
            picks_dtos = []
            for pick in suggested_picks_container.suggested_picks:
                from src.application.dtos.dtos import SuggestedPickDTO
                picks_dtos.append(SuggestedPickDTO(
                    market_type=pick.market_type,
                    market_label=pick.market_label,
                    probability=pick.probability,
                    confidence_level=pick.confidence_level,
                    reasoning=pick.reasoning,
                    risk_level=pick.risk_level,
                    is_recommended=pick.is_recommended,
                    priority_score=pick.priority_score,
                    is_ml_confirmed=pick.is_ml_confirmed,
                    ml_confidence=pick.ml_confidence,
                    suggested_stake=pick.suggested_stake,
                    kelly_percentage=pick.kelly_percentage,
                    clv_beat=getattr(pick, 'clv_beat', False),
                    expected_value=pick.expected_value,
                    opening_odds=pick.odds,
                    closing_odds=getattr(pick, 'closing_odds', 0.0)
                ))

            # Build Prediction DTO (optional for internal consistency)
            from src.application.dtos.dtos import PredictionDTO
            pred_dto = PredictionDTO(
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
                generated_at=get_current_time()
            )
            
        except InsufficientDataException as e:
            logger.info(f"Skipping prediction for {match_id}: {e}")
            from src.utils.time_utils import get_current_time
            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=[],
                combination_warning=f"Datos insuficientes: {str(e)}",
                highlights_url=highlights_url,
                real_time_odds=rt_odds,
                generated_at=get_current_time()
            )
        except Exception as e:
            logger.error(f"Error in suggested picks execution for {match_id}: {e}", exc_info=True)
            # Return empty DTO instead of None to avoid 500 validation error
            from src.utils.time_utils import get_current_time
            return MatchSuggestedPicksDTO(
                match_id=match_id,
                suggested_picks=[],
                combination_warning=f"Error inesperado al generar picks.",
                generated_at=get_current_time()
            )
    
    async def _get_match(self, match_id: str) -> Optional[Match]:
        """Get match details from available sources with cache fallbacks."""
        # 1. Optimization: If ID is synthetic (contains underscores), skip external APIs
        if "_" in match_id:
            return self._reconstruct_match_from_id(match_id)

        # 2. Try Football-Data.org regular fetch
        if self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(match_id)
            if match:
                return match
        # This is vital when the account is suspended/limited but we already fetched the list
        try:
            from src.infrastructure.cache.cache_service import get_cache_service
            cache = get_cache_service()
            for key in ["filtered", "all"]:
                live_preds = cache.get_live_matches(key)
                if live_preds:
                    # live_preds is List[MatchPredictionDTO]
                    for lp in live_preds:
                        if str(lp.match.id) == str(match_id):
                            logger.info(f"✓ Found match {match_id} in live_matches cache fallback")
                            # Convert DTO back to Entity (minimal version)
                            from src.domain.entities.entities import League, Team
                            return Match(
                                id=lp.match.id,
                                home_team=Team(id=lp.match.home_team.id, name=lp.match.home_team.name),
                                away_team=Team(id=lp.match.away_team.id, name=lp.match.away_team.name),
                                league=League(id=lp.match.league.id, name=lp.match.league.name, country=lp.match.league.country),
                                match_date=lp.match.match_date,
                                status=lp.match.status or "NS"
                            )
        except Exception as e:
            logger.warning(f"Live matches cache fallback failed for {match_id}: {e}")

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
            # Let's look at the specific ID: B1_20260207_sporting_charleroi_cercle_brugge
            # sporting_charleroi (2 words)
            # cercle_brugge (2 words)
            
            # We can't perfectly separate them without knowing the teams.
            # However, we can return a "Skeleton Match" and let the History Aggregator 
            # find the real teams using the fuzzy search on the Combined string or specific history fetch.
            
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
                season=str(match_date.year) # Approx
            )
            
            home_team = Team(id=f"synthetic_{home_slug}", name=home_name, country="Unknown")
            away_team = Team(id=f"synthetic_{away_slug}", name=away_name, country="Unknown")
            
            logger.info(f"Reconstructed synthetic match from ID: {home_name} vs {away_name}")
            
            return Match(
                id=match_id,
                league=league,
                home_team=home_team,
                away_team=away_team,
                match_date=match_date,
                status="NS", # Not Started assumed
                home_goals=None,
                away_goals=None
            )
            
        except Exception as e:
            logger.warning(f"Failed to reconstruct match from ID {match_id}: {e}")
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
        
        logger.info(f"Aggregating data for {match.home_team.name} vs {match.away_team.name} (League: {internal_league_code})")
        
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
                logger.warning(f"Error in data source fetch: {result}")
                
        # 4. Unify and Deduplicate
        unified_matches = self._deduplicate_and_merge(all_matches)
        logger.info(f"Data Aggregation: {len(all_matches)} raw matches -> {len(unified_matches)} unique unified matches")
        
        return unified_matches

    async def _fetch_csv_history(self, league_code: str) -> list[Match]:
        try:
            return await self.data_sources.football_data_uk.get_historical_matches(
                league_code,
                seasons=["2425", "2324"],
            )
        except Exception:
            return []

    async def _fetch_openfootball_history(self, league_code: str) -> list[Match]:
        try:
            from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
            if league_code in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_code]
                temp_league = League(
                    id=league_code,
                    name=meta["name"],
                    country=meta["country"],
                )
                matches = await self.data_sources.openfootball.get_matches(temp_league)
                return [m for m in matches if m.status in ["FT", "AET", "PEN"]]
        except Exception:
            pass
        return []

    async def _fetch_team_history_apis(self, match: Match) -> list[Match]:
        """Fetch history specifically for the two teams from APIs."""
        team_matches = []
        
        # Strategy A: Football-Data.org
        # Strategy B: Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            try:
                # Football-Data.org uses names for history fetch in this project's implementation
                h_hist = await self.data_sources.football_data_org.get_team_history(match.home_team.name, limit=10)
                a_hist = await self.data_sources.football_data_org.get_team_history(match.away_team.name, limit=10)
                team_matches.extend(h_hist + a_hist)
            except Exception as e:
                logger.warning(f"Football-Data.org history fetch failed: {e}")
                
        # Strategy C: FotMob (Best for Corners/Cards in minor leagues)
        if self.fotmob and self.fotmob.is_configured:
            try:
                h_hist = await self.fotmob.get_team_history(match.home_team.name, limit=5)
                a_hist = await self.fotmob.get_team_history(match.away_team.name, limit=5)
                team_matches.extend(h_hist + a_hist)
            except Exception as e:
                logger.warning(f"FotMob history fetch failed: {e}")

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
                    if m.home_shots_on_target is not None and existing.home_shots_on_target is None:
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
                is_ml_confirmed=getattr(p, 'is_ml_confirmed', False),
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
        new_adjustment = self.learning_service.get_market_adjustment(request.market_type)
        
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
            default=datetime.now(timezone('America/Bogota'))
        )
        
        return LearningStatsResponseDTO(
            market_performances=performance_dtos,
            total_feedback_count=total_count,
            last_updated=last_updated,
        )


class GetTopMLPicksUseCase:
    """Use case for retrieving the top ML picks across all leagues."""
    
    def __init__(self, persistence_repository):
        self.persistence_repository = persistence_repository
        
    async def execute(self, limit: int = 50) -> Optional['TopMLPicksDTO']:
        """
        Synthesize top picks from all active predictions.
        """
        try:
            # 1. Get all active predictions from DB
            active_preds = self.persistence_repository.get_all_active_predictions()
            
            all_picks = []
            
            from src.application.dtos.dtos import SuggestedPickDTO, TopMLPicksDTO
            
            # 2. Extract picks from each prediction
            for pred_data in active_preds:
                # pred_data is the JSON dict stored in 'match_predictions.data'
                # Structure: { match: {...}, prediction: { suggested_picks: [...] } }
                
                prediction = pred_data.get("prediction", {})
                match_info = pred_data.get("match", {})
                picks = prediction.get("suggested_picks", [])
                
                match_label = f"{match_info.get('home_team', {}).get('name', '')} vs {match_info.get('away_team', {}).get('name', '')}"
                match_id = match_info.get("id")
                
                for p in picks:
                    # Filter out low value picks?
                    # Let's keep all and sort by priority/probability
                    
                    # Ensure it's a valid pick object/dict
                    if isinstance(p, dict):
                         # Enrich reasoning with match info for the global list
                         base_reasoning = p.get("reasoning", "")
                         p["reasoning"] = f"[{match_label}] {base_reasoning}"
                         
                         dto = SuggestedPickDTO(**p)
                         all_picks.append(dto)
            
            # 3. Sort picks
            # Primary: Priority Score (Expected Value + ML Confidence)
            # Secondary: Probability
            all_picks.sort(key=lambda x: (x.priority_score, x.probability), reverse=True)
            
            # 4. Limit
            top_picks = all_picks[:limit]
            
            from src.utils.time_utils import get_current_time
            return TopMLPicksDTO(
                picks=top_picks,
                generated_at=get_current_time()
            )
            
        except Exception as e:
            logger.error(f"Error generating Top ML Picks: {e}", exc_info=True)
            return None
