"""
Live Predictions Use Case Module

Use case for generating predictions for live matches,
combining real-time data with historical statistics.
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass
from pytz import timezone
import logging

from src.domain.entities.entities import Match, Prediction, TeamStatistics
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.picks_service import PicksService
from src.infrastructure.cache.cache_service import CacheService
from src.infrastructure.data_sources.football_data_uk import (
    FootballDataUKSource,
    LEAGUES_METADATA,
)
from src.infrastructure.data_sources.football_data_org import (
    FootballDataOrgSource,
    COMPETITION_CODE_MAPPING,
)
from src.infrastructure.data_sources.fotmob_source import FotMobSource
from src.infrastructure.repositories.persistence_repository import PersistenceRepository
from src.application.dtos.dtos import (
    TeamDTO,
    LeagueDTO,
    MatchDTO,
    PredictionDTO,
    MatchPredictionDTO,
    SuggestedPickDTO,
)
from src.application.use_cases.use_cases import DataSources
from src.utils.time_utils import get_current_time


logger = logging.getLogger(__name__)


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
    
    PROCESSING_MESSAGE = "Estamos procesando la información para darte las probabilidades con mayor precisión"
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
        cache_service: CacheService,
        picks_service: PicksService,
        persistence_repository: Optional[PersistenceRepository] = None,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.cache_service = cache_service
        self.picks_service = picks_service
        self.persistence_repository = persistence_repository
        self.fotmob = data_sources.fotmob or FotMobSource()
    
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
        # Check cache first
        cache_key = "filtered" if filter_target_leagues else "all"
        cached = self.cache_service.get_live_matches(cache_key)
        if cached is not None:
            logger.info(f"Returning {len(cached)} cached live matches")
            return cached
        
        # Get live matches
        # Get live matches
        matches = []
        source_used = "None"

        # Priority 1: FotMob (Rich Stats: Corners, Cards, etc.)
        if self.fotmob:
             try:
                 matches = await self.fotmob.get_live_matches()
                 if matches:
                     source_used = "FotMob"
             except Exception as e:
                 logger.error(f"FotMob live fetch failed: {e}")

        # Priority 2: Football-Data.org (Official Fallback, but fewer stats)
        if not matches and self.data_sources.football_data_org.is_configured:
            try:
                matches = await self.data_sources.football_data_org.get_live_matches()
                if matches:
                    source_used = "Football-Data.org"
            except Exception as e:
                logger.error(f"Football-Data.org live fetch failed: {e}")
        
        if not matches:
            # Cache empty result for short period to avoid hammering API
            self.cache_service.set_live_matches([], cache_key)
            return []
        
        logger.info(f"Fetched {len(matches)} live matches from {source_used}")
        
        # Generate predictions for each match
        results: List[MatchPredictionDTO] = []
        
        for match in matches:
            try:
                # 1. ATTEMPT DB LOOKUP (Pre-calculated in Training Action)
                pre_calculated_dto = None
                if self.persistence_repository:
                    pre_calculated_data = self.persistence_repository.get_match_prediction(match.id)
                    if pre_calculated_data:
                         try:
                             pre_calculated_dto = MatchPredictionDTO(**pre_calculated_data)
                             logger.info(f"✓ Using pre-calculated data from DB for match {match.id}")
                         except Exception as parse_e:
                             logger.warning(f"Failed to parse pre-calculated data for {match.id}: {parse_e}")

                if pre_calculated_dto:
                    # Update potentially stale live data (score, minute) while keeping AI prediction
                    pre_calculated_dto.match.home_goals = match.home_goals
                    pre_calculated_dto.match.away_goals = match.away_goals
                    pre_calculated_dto.match.status = match.status
                    pre_calculated_dto.match.minute = match.minute
                    results.append(pre_calculated_dto)
                    continue

                # 2. EMERGENCY FALLBACK: Real-time calculation
                logger.warning(f"⚠ Cache/DB miss for {match.id}. Running emergency real-time inference...")
                prediction_dto = await self._generate_prediction(match)
                match_dto = self._match_to_dto(match)
                
                results.append(MatchPredictionDTO(
                    match=match_dto,
                    prediction=prediction_dto,
                ))
            except Exception as e:
                logger.error(f"Failed to generate/retrieve prediction for match {match.id}: {e}")
                # Still include match without prediction to avoid breaks
                results.append(MatchPredictionDTO(
                    match=self._match_to_dto(match),
                    prediction=self._empty_prediction(match.id),
                ))
        
        # Cache results
        self.cache_service.set_live_matches(results, cache_key)
        logger.info(f"Generated {len(results)} live match predictions")
        
        return results
    
    async def _generate_prediction(self, match: Match) -> PredictionDTO:
        """
        Generate prediction for a single match.
        
        Uses all available historical data for maximum accuracy.
        """
        # Check prediction cache
        cached_pred = self.cache_service.get_predictions(match.id)
        if cached_pred is not None:
            return cached_pred
        
        # Get internal league code
        internal_code = self._get_internal_league_code(match)
        
        # 1. Try to get deep stats from Unified Cache (10 years)
        training_results = self.cache_service.get("ml_training_result_data")
        
        home_stats = None
        away_stats = None
        data_sources_used = [FootballDataOrgSource.SOURCE_NAME]

        # Fetch Global Averages (Universal Baseline)
        global_avg_data = self.cache_service.get("global_statistical_averages")
        global_averages = None
        if global_avg_data:
            from src.domain.value_objects.value_objects import LeagueAverages
            global_averages = LeagueAverages(**global_avg_data)
        
        if training_results and 'team_stats' in training_results:
            team_stats_map = training_results['team_stats']
            
            # Helper to convert dict to entity
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
                    recent_form=raw.get("recent_form", "")
                )

            # Look up home/away
            if match.home_team.name in team_stats_map:
                home_stats = _dict_to_stats(match.home_team.name, team_stats_map[match.home_team.name])
            
            if match.away_team.name in team_stats_map:
                away_stats = _dict_to_stats(match.away_team.name, team_stats_map[match.away_team.name])
                
            if home_stats and away_stats:
                data_sources_used.append("Historical (10 Years)")
                # Use simplified league averages if we have deep stats, or fetch?
                # Calculating league avg from 18k matches is expensive if not cached. 
                # Use default safely or fetch small history for it.
                league_averages = None 

        # 2. Fallback to shallow fetch (API-Football) if no training stats
        # 2. Fallback to aggregated fetch (CSV + OpenFootball + APIs)
        if not home_stats or not away_stats:
             historical_matches = await self._get_aggregated_history(match)
             
             if not home_stats:
                 home_stats = self.statistics_service.calculate_team_statistics(
                    match.home_team.name,
                    historical_matches,
                 )
             if not away_stats:
                 away_stats = self.statistics_service.calculate_team_statistics(
                    match.away_team.name,
                    historical_matches,
                 )
             
             league_averages = self.statistics_service.calculate_league_averages(historical_matches) if historical_matches else None
             if historical_matches:
                 data_sources_used.append("Aggregated History")
                 # Check if we have rich stats (likely from FotMob in minor leagues)
                 if any(m.home_corners is not None for m in historical_matches):
                     data_sources_used.append("FotMob")
        else:
             # We used deep stats, but maybe we still want league averages from recent data?
             historical_matches = await self._get_aggregated_history(match)
             league_averages = self.statistics_service.calculate_league_averages(historical_matches) if historical_matches else None

        
        prediction = self.prediction_service.generate_prediction(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            global_averages=global_averages,
            data_sources=data_sources_used,
        )
        
        # Generate Suggested Picks
        picks_container = self.picks_service.generate_suggested_picks(
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
        
        # Convert to DTO
        prediction_dto = self._prediction_to_dto(prediction, picks_container.picks)
        
        # Cache the prediction
        self.cache_service.set_predictions(match.id, prediction_dto)
        
        return prediction_dto
    
    async def _get_aggregated_history(self, match: Match) -> List[Match]:
        """
        Get historical matches from ALL available sources and unify them.
        Identical strategy to SuggestedPicksUseCase for consistency.
        """
        import asyncio
        from src.infrastructure.data_sources.football_data_org import COMPETITION_CODE_MAPPING
        
        internal_league_code = self._get_internal_league_code(match)
        
        logger.info(f"Aggregating live prediction data for {match.home_team.name} vs {match.away_team.name}")
        
        tasks = []
        
        # 1. CSV Data Task
        if internal_league_code:
            tasks.append(self._fetch_csv_history(internal_league_code))
            
        # 2. OpenFootball Task
        if internal_league_code and self.data_sources.openfootball:
            tasks.append(self._fetch_openfootball_history(internal_league_code))
            
        # 3. Team History Task
        tasks.append(self._fetch_team_history_apis(match))
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for result in results:
            if isinstance(result, list):
                all_matches.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Error in data source fetch: {result}")
                
        # 4. Unify
        return self._deduplicate_and_merge(all_matches)

    async def _fetch_csv_history(self, league_code: str) -> list[Match]:
        try:
            return await self.data_sources.football_data_uk.get_historical_matches(
                league_code,
                seasons=["2425", "2324", "2223", "2122"],
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
        team_matches = []
        # Aumentamos el límite para mejorar la significancia estadística (Ley de los Grandes Números)
        HISTORY_LIMIT = 25
        
        # Strategy C: FotMob
        if self.fotmob and self.fotmob.is_configured:
            try:
                h_hist = await self.fotmob.get_team_history(match.home_team.name, limit=10)
                a_hist = await self.fotmob.get_team_history(match.away_team.name, limit=10)
                team_matches.extend(h_hist + a_hist)
            except Exception:
                pass

        # Strategy B: Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            try:
                h_hist = await self.data_sources.football_data_org.get_team_history(match.home_team.name, limit=HISTORY_LIMIT)
                a_hist = await self.data_sources.football_data_org.get_team_history(match.away_team.name, limit=HISTORY_LIMIT)
                team_matches.extend(h_hist + a_hist)
            except Exception:
                pass
                
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
                # Priorizamos datos con estadísticas más ricas para mejorar la precisión del modelo
                current_score = 0
                existing_score = 0
                
                if m.home_corners is not None: current_score += 1
                if m.home_shots_on_target is not None: current_score += 1
                if m.home_yellow_cards is not None: current_score += 1
                
                if existing.home_corners is not None: existing_score += 1
                if existing.home_shots_on_target is not None: existing_score += 1
                if existing.home_yellow_cards is not None: existing_score += 1
                
                if current_score > existing_score:
                    unique_map[key] = m
        
        result = list(unique_map.values())
        result.sort(key=lambda x: x.match_date, reverse=True)
        return result
    
    def _get_internal_league_code(self, match: Match) -> Optional[str]:
        """Map Football-Data.org competition code to internal code."""
        try:
            # Match objects from Football-Data.org already have internal league id if parsed via _parse_match
            # but for safety we can check mapping
            for internal_code, org_code in COMPETITION_CODE_MAPPING.items():
                if internal_code == match.league.id:
                    return internal_code
        except Exception:
            pass
        return None
    
    def _match_to_dto(self, match: Match) -> MatchDTO:
        """Convert Match entity to DTO."""
        from src.domain.services.team_service import TeamService
        
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=match.home_team.short_name,
                country=match.home_team.country,
                logo_url=match.home_team.logo_url or TeamService.get_team_logo(match.home_team.name),
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=match.away_team.short_name,
                country=match.away_team.country,
                logo_url=match.away_team.logo_url or TeamService.get_team_logo(match.away_team.name),
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
    
    def _prediction_to_dto(self, prediction: Prediction, picks: list = []) -> PredictionDTO:
        """Convert Prediction entity to DTO."""
        
        picks_dtos = []
        for pick in picks:
             picks_dtos.append(SuggestedPickDTO(
                 market_type=pick.market_type,
                 market_label=pick.market_label,
                 probability=pick.probability,
                 confidence_level=pick.confidence_level,
                 reasoning=pick.reasoning,
                 risk_level=pick.risk_level,
                 is_recommended=pick.is_recommended,
                 priority_score=pick.priority_score
             ))

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
            created_at=datetime.now(timezone('America/Bogota')),
        )
