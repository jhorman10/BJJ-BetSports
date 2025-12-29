"""
Application Use Cases Module

Use cases represent application-specific business rules and orchestrate
the flow of data between the domain layer and the infrastructure layer.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from pytz import timezone
import logging
import asyncio

from src.domain.entities.entities import Match, League, Prediction, TeamStatistics
from src.domain.services.prediction_service import PredictionService
from src.domain.services.picks_service import PicksService
from src.domain.value_objects.value_objects import LeagueAverages
from src.infrastructure.data_sources.football_data_uk import (
    FootballDataUKSource,
    LEAGUES_METADATA,
)
from src.infrastructure.data_sources.api_football import APIFootballSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.application.dtos.dtos import (
    TeamDTO,
    LeagueDTO,
    MatchDTO,
    PredictionDTO,
    MatchPredictionDTO,
    CountryDTO,
    LeaguesResponseDTO,
    PredictionsResponseDTO,
)


logger = logging.getLogger(__name__)


@dataclass
class DataSources:
    """Container for all data sources."""
    football_data_uk: FootballDataUKSource
    api_football: APIFootballSource
    football_data_org: FootballDataOrgSource
    openfootball: OpenFootballSource
    thesportsdb: TheSportsDBClient


class GetLeaguesUseCase:
    """Use case for getting available leagues."""
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
    
    async def execute(self) -> LeaguesResponseDTO:
        """Get all available leagues grouped by country."""
        leagues = self.data_sources.football_data_uk.get_available_leagues()
        
        # Filter leagues by data sufficiency (>= 5 matches in current season)
        # We do this concurrently to minimize latency
        async def check_league_sufficiency(league_id: str) -> bool:
            try:
                # Use default seasons (current + previous) to ensure we have data 
                # even if new season just started (using past data for stats)
                matches = await self.data_sources.football_data_uk.get_historical_matches(
                    league_id, 
                    seasons=None 
                )
                
                # Count only FINISHED matches (matches with goals)
                # This filters out leagues that only have fixtures but no results yet
                finished_matches = [m for m in matches if m.home_goals is not None]
                return len(finished_matches) >= 5
            except Exception:
                return False

        # Run checks in parallel
        results = await asyncio.gather(*[check_league_sufficiency(l.id) for l in leagues])
        
        # Filter the leagues list
        active_leagues = [
            league for league, is_sufficient in zip(leagues, results) 
            if is_sufficient
        ]
        
        # Update generic leagues list to only include sufficient ones
        leagues = active_leagues

        # Get active league IDs from API-Football to filter out empty ones
        active_api_ids = set()
        api_configured = self.data_sources.api_football.is_configured
        
        if api_configured:
            try:
                active_api_ids = await self.data_sources.api_football.get_active_league_ids(days=10)
            except Exception as e:
                logger.error(f"Failed to get active leagues from API-Football: {e}")
        
        # Get active codes from Football-Data.org
        active_org_codes = set()
        org_configured = self.data_sources.football_data_org.is_configured
        
        if org_configured:
            try:
                from src.infrastructure.data_sources.football_data_org import COMPETITION_CODE_MAPPING
                # Create reverse mapping: "PL" -> "E0"
                org_code_to_internal = {v: k for k, v in COMPETITION_CODE_MAPPING.items()}
                
                competitions = await self.data_sources.football_data_org.get_competitions()
                for comp in competitions:
                    code = comp.get("code")
                    if code in org_code_to_internal:
                        active_org_codes.add(org_code_to_internal[code])
            except Exception as e:
                logger.error(f"Failed to get active leagues from Football-Data.org: {e}")

        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING

        # Group by country
        countries_dict: dict[str, list[League]] = {}
        for league in leagues:
            is_active = False
            
            # Check API-Football validity
            if api_configured:
                api_id = LEAGUE_ID_MAPPING.get(league.id)
                if api_id and api_id in active_api_ids:
                    is_active = True
            
            # Check Football-Data.org validity (if not already found active)
            if not is_active and org_configured:
                if league.id in active_org_codes:
                    is_active = True
            
            # Relaxed Filtering Logic:
            # We show ALL leagues that we know about (from CSV metadata).
            # We try to mark them as 'active' for API usage if possible, but we don't hide them.

            if api_configured:
                api_id = LEAGUE_ID_MAPPING.get(league.id)
                if api_id and api_id in active_api_ids:
                    is_active = True
            
            if not is_active and org_configured:
                if league.id in active_org_codes:
                    is_active = True
            
            # Use 'is_active' logic to potentially tag leagues in the future, 
            # but for now we include EVERYTHING from 'leagues' (which comes from metadata).

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
            countries.append(CountryDTO(
                name=country_name,
                code=country_name[:3].upper(),
                leagues=league_dtos,
            ))
        
        return LeaguesResponseDTO(
            countries=countries,
            total_leagues=len(leagues),
        )


from src.domain.services.statistics_service import StatisticsService

class GetPredictionsUseCase:
    """Use case for getting match predictions."""
    
    def __init__(
        self,
        data_sources: DataSources,
        prediction_service: PredictionService,
        statistics_service: StatisticsService,
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
        self.statistics_service = statistics_service
        self.picks_service = PicksService()
    
    async def execute(self, league_id: str, limit: int = 20) -> PredictionsResponseDTO:
        """
        Get predictions for upcoming matches in a league.
        
        Args:
            league_id: League identifier
            limit: Maximum matches to return
            
        Returns:
            Predictions response with match predictions
        """
        # Get league metadata
        if league_id not in LEAGUES_METADATA:
            raise ValueError(f"Unknown league: {league_id}")
        
        meta = LEAGUES_METADATA[league_id]
        league = League(
            id=league_id,
            name=meta["name"],
            country=meta["country"],
        )
        
        # Get historical data
        # 1. Dynamic Season Calculation
        # Instead of hardcoding "2425", we calculate based on current date
        now = datetime.now(timezone('America/Bogota'))
        current_year = now.year
        
        # Football seasons usually run from July to June
        if now.month < 7:
            # We are in the second half of a season (e.g. Feb 2025 -> 24/25)
            s1_start = current_year - 1
            s1_end = current_year
            s2_start = current_year - 2
            s2_end = current_year - 1
        else:
            # We are in the first half of a season (e.g. Sep 2025 -> 25/26)
            s1_start = current_year
            s1_end = current_year + 1
            s2_start = current_year - 1
            s2_end = current_year
            
        current_season = f"{str(s1_start)[-2:]}{str(s1_end)[-2:]}"
        prev_season = f"{str(s2_start)[-2:]}{str(s2_end)[-2:]}"
        seasons = [current_season, prev_season]
        
        logger.info(f"Fetching historical matches for {league_id} - Seasons: {seasons}")
        
        # 1. Try Football-Data.co.uk (CSV) - Preferred for stats
        historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
            league_id,
            seasons=seasons,
        )
        
        # 2. If no data, try OpenFootball (JSON) - Fallback
        if not historical_matches:
            logger.info(f"No CSV data for {league_id}, trying OpenFootball...")
            try:
                open_matches = await self.data_sources.openfootball.get_matches(league)
                # Filter for played matches only
                historical_matches = [m for m in open_matches if m.status in ["FT", "AET", "PEN"]]
            except Exception as e:
                logger.warning(f"Failed to fetch OpenFootball history: {e}")

        # Calculate league averages from historical data using the service
        league_averages = self.statistics_service.calculate_league_averages(historical_matches)
        
        # Get upcoming fixtures
        upcoming_matches = await self._get_upcoming_matches(league_id, limit=1000)
        
        # Strict Date Filter: Only show matches in the future
        now = datetime.now(timezone('America/Bogota'))
        upcoming_matches = [m for m in upcoming_matches if m.match_date > now]
        
        if not upcoming_matches:
            logger.info(f"No upcoming future matches found for {league_id}")
            return PredictionsResponseDTO(
                league=LeagueDTO(
                    id=league_id,
                    name=meta["name"],
                    country=meta["country"],
                ),
                predictions=[],
                generated_at=datetime.now(timezone('America/Bogota'))
            )
        
        # Build predictions
        predictions = []
        data_sources_used = [FootballDataUKSource.SOURCE_NAME]
        
        if self.data_sources.api_football.is_configured:
            data_sources_used.append(APIFootballSource.SOURCE_NAME)
        if self.data_sources.football_data_org.is_configured:
            data_sources_used.append(FootballDataOrgSource.SOURCE_NAME)
        if self.data_sources.openfootball:
             data_sources_used.append(OpenFootballSource.SOURCE_NAME)
        
        for match in upcoming_matches[:limit]:
            # Get team statistics using the generic service
            home_stats = self.statistics_service.calculate_team_statistics(
                match.home_team.name,
                historical_matches,
            )
            away_stats = self.statistics_service.calculate_team_statistics(
                match.away_team.name,
                historical_matches,
            )
            
            # Generate prediction
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages,
                data_sources=data_sources_used,
            )
            
            # Generate suggested picks
            suggested_picks = self.picks_service.generate_suggested_picks(
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
            
            # Filter: Check if we actually have something to show
            is_valid_prediction = (prediction.home_win_probability + prediction.draw_probability + prediction.away_win_probability) > 0
            has_picks = len(suggested_picks.suggested_picks) > 0
            
            if not (is_valid_prediction or has_picks):
                logger.debug(f"Skipping match {match.id} due to lack of prediction/picks")
                continue
            
            # Convert to DTOs
            match_dto = self._match_to_dto(match)
            
            # Inject projected stats (historical averages) for upcoming matches
            if match.status in ["NS", "TIMED", "SCHEDULED"]:
                if home_stats and home_stats.matches_played > 0:
                    match_dto.home_corners = int(round(home_stats.avg_corners_per_match))
                    match_dto.home_yellow_cards = int(round(home_stats.avg_yellow_cards_per_match))
                    match_dto.home_red_cards = int(round(home_stats.avg_red_cards_per_match))
                if away_stats and away_stats.matches_played > 0:
                    match_dto.away_corners = int(round(away_stats.avg_corners_per_match))
                    match_dto.away_yellow_cards = int(round(away_stats.avg_yellow_cards_per_match))
                    match_dto.away_red_cards = int(round(away_stats.avg_red_cards_per_match))
            
            prediction_dto = self._prediction_to_dto(prediction, suggested_picks.suggested_picks)
            
            predictions.append(MatchPredictionDTO(
                match=match_dto,
                prediction=prediction_dto,
            ))
        
        return PredictionsResponseDTO(
            league=LeagueDTO(
                id=league.id,
                name=league.name,
                country=league.country,
            ),
            predictions=predictions,
            generated_at=datetime.now(timezone('America/Bogota')),
        )
    

    
    async def _get_upcoming_matches(
        self,
        league_id: str,
        limit: int,
    ) -> list[Match]:
        """Get upcoming matches from available sources."""
        # Try API-Football first if configured
        if self.data_sources.api_football.is_configured:
            matches = await self.data_sources.api_football.get_upcoming_fixtures(
                league_id,
                next_n=limit,
            )
            if matches:
                return matches
        
        # Try Football-Data.org
        if self.data_sources.football_data_org.is_configured:
            matches = await self.data_sources.football_data_org.get_upcoming_matches(
                league_id,
            )
            if matches:
                return matches[:limit]

        # Try TheSportsDB (Free fallback)
        try:
            matches = await self.data_sources.thesportsdb.get_upcoming_fixtures(league_id, next_n=limit)
            if matches:
                 return matches
        except Exception as e:
             logger.warning(f"TheSportsDB fetch failed: {e}")
        
        # Try OpenFootball
        # We need league entity for mapping
        try:
            from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA
            if league_id in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_id]
                league_entity = League(id=league_id, name=meta["name"], country=meta["country"])
                matches = await self.data_sources.openfootball.get_matches(league_entity)
                
                # Filter for upcoming only (NS)
                upcoming = [m for m in matches if m.status == "NS"]
                if upcoming:
                    # Sort by date
                    upcoming.sort(key=lambda x: x.match_date)
                    return upcoming[:limit]
        except Exception as e:
            logger.error(f"OpenFootball fetch failed: {e}")
            
        return []
        
    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country),
            away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
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

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                 )
                 for p in picks
             ]

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
            suggested_picks=pick_dtos,
            created_at=prediction.created_at,
        )


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
        self.picks_service = PicksService()

    async def execute(self, match_id: str) -> MatchPredictionDTO:
        # 1. Get match details
        match = None
        
        # Try API-Football first (if configured)
        if self.data_sources.api_football.is_configured:
            match = await self.data_sources.api_football.get_match_details(match_id)
            
        # Try Football-Data.org if not found/configured
        if not match and self.data_sources.football_data_org.is_configured:
            match = await self.data_sources.football_data_org.get_match_details(match_id)
            
        # Try TheSportsDB if not found
        if not match:
            try:
                match = await self.data_sources.thesportsdb.get_match_details(match_id)
            except Exception:
                pass
            
        if not match:
            return None

        if not match:
            return None

        # 2. Check Training Cache for Historical Prediction (Consistency)
        try:
            from src.infrastructure.cache import get_training_cache
            from src.application.dtos.dtos import SuggestedPickDTO
            
            training_cache = get_training_cache()
            training_results = training_cache.get_training_results()
            
            if training_results and 'match_history' in training_results:
                # O(N) lookup but N=18k is fast enough for single request. 
                # Optimized: convert to dict if frequent, but for now linear scan is <10ms.
                # Actually, filtering by ID is cleaner.
                history_item = next((m for m in training_results['match_history'] if m['match_id'] == match_id), None)
                
                if history_item:
                    # Found in history! Map to PredictionDTO
                    logger.info(f"Serving cached historical prediction for match {match_id}")
                    
                    # Synthesize SuggestedPickDTOs from History PickDetails
                    picks_dtos = []
                    if 'picks' in history_item:
                        for p in history_item['picks']:
                            # PickDetail -> SuggestedPickDTO
                            prob = p.get('probability', 0.5)
                            conf = p.get('confidence', 0.5)
                            
                            # Estimate risk/confidence text
                            conf_level = "MEDIA"
                            if prob > 0.7: conf_level = "ALTA"
                            elif prob < 0.4: conf_level = "BAJA"
                            
                            risk = int((1 - prob) * 10)
                            if risk < 1: risk = 1
                            
                            picks_dtos.append(SuggestedPickDTO(
                                market_type=p.get('market_type', 'unknown'),
                                market_label=p.get('market_label', 'Unknown Pick'),
                                probability=prob,
                                confidence_level=conf_level,
                                reasoning="Resultado Verificado en Backtest",
                                risk_level=risk,
                                is_recommended=True, # All history picks were "suggested"
                                priority_score=prob * p.get('expected_value', 1.0)
                            ))

                    # Parse prediction values
                    pred_dto = PredictionDTO(
                        match_id=match_id,
                        home_win_probability=history_item.get('home_win_probability', 0.0),
                        draw_probability=history_item.get('draw_probability', 0.0),
                        away_win_probability=history_item.get('away_win_probability', 0.0),
                        over_25_probability=0.0, # Not stored yet, but less critical than Win Probs
                        under_25_probability=0.0,
                        predicted_home_goals=history_item.get('predicted_home_goals', 0.0),
                        predicted_away_goals=history_item.get('predicted_away_goals', 0.0),
                        confidence=history_item.get('confidence', 0.0),
                        data_sources=[
                            "GitHub Dataset (2000-2025)",
                            "API-Football",
                            "ESPN",
                            "Football-Data.co.uk"
                        ], # Explicitly list sources used in Training
                        recommended_bet="See Picks",
                        over_under_recommendation="See Picks",
                        suggested_picks=picks_dtos,
                        created_at=datetime.now(timezone('America/Bogota')), # Placeholder
                    )
                    
                    # Update probabilities if we can infer them from picks or if added to history later
                    # For now, we return what we have. The UI mostly cares about 'suggested_picks' and exact score.
                    
                    return MatchPredictionDTO(
                        match=self._match_to_dto(match),
                        prediction=pred_dto
                    )
        except Exception as e:
            logger.warning(f"Error reading training cache for match details: {e}")

        # 3. Get historical data for context (for stats) - Standard Fallback
        historical_matches = []
        
        # Try to map API-Football league ID to our internal code
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING
        
        # Create reverse mapping: {39: "E0", ...}
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        
        internal_league_code = None
        try:
            # API ID is usually string in Match entity, mapping values are int
            lid = int(match.league.id)
            if lid in api_id_to_code:
                internal_league_code = api_id_to_code[lid]
        except (ValueError, TypeError):
            pass
            
        if internal_league_code:
            # We found a mapping! Now we can fetch historical data.
            # 2a. Try Football-Data.co.uk (CSV)
            try:
                historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
                    internal_league_code,
                    seasons=["2425", "2324"], # Fetch current and last season
                )
            except Exception as e:
                logger.warning(f"Failed to fetch CSV history details: {e}")
                
            # 2b. If no CSV data, try OpenFootball
            if not historical_matches and self.data_sources.openfootball:
                try:
                    # Construct a league entity with the internal ID for OpenFootball lookup
                    # (OpenFootballSource uses league.id to find the file)
                    from src.domain.entities.entities import League
                    temp_league = League(
                        id=internal_league_code, 
                        name=match.league.name, 
                        country=match.league.country, 
                        season=match.league.season
                    )
                    open_matches = await self.data_sources.openfootball.get_matches(temp_league)
                    historical_matches = [m for m in open_matches if m.status in ["FT", "AET", "PEN"]]
                except Exception as e:
                    logger.warning(f"Failed to fetch OpenFootball history details: {e}")
        
        # 4. Calculate stats using whatever history we found (or empty list)
        home_stats = self.statistics_service.calculate_team_statistics(match.home_team.name, historical_matches)
        away_stats = self.statistics_service.calculate_team_statistics(match.away_team.name, historical_matches)
        
        # 5. Generate prediction
        prediction = self.prediction_service.generate_prediction(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=None, # Will use defaults
            data_sources=[APIFootballSource.SOURCE_NAME] + ([FootballDataUKSource.SOURCE_NAME] if historical_matches else []),
        )

        # Generate suggested picks
        suggested_picks = self.picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=None,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            home_win_prob=prediction.home_win_probability,
            draw_prob=prediction.draw_probability,
            away_win_prob=prediction.away_win_probability,
        )
        
        # Enhanced Match DTO with projected stats if NS
        match_dto = self._match_to_dto(match)
        if match.status in ["NS", "TIMED", "SCHEDULED"] and historical_matches:
             # Inject projected stats (averages) for UI display
             if home_stats and  home_stats.matches_played > 0:
                 match_dto.home_corners = int(round(home_stats.avg_corners_per_match))
                 match_dto.home_yellow_cards = int(round(home_stats.avg_yellow_cards_per_match))
                 match_dto.home_red_cards = int(round(home_stats.avg_red_cards_per_match))
             
             if away_stats and away_stats.matches_played > 0:
                 match_dto.away_corners = int(round(away_stats.avg_corners_per_match))
                 match_dto.away_yellow_cards = int(round(away_stats.avg_yellow_cards_per_match))
                 match_dto.away_red_cards = int(round(away_stats.avg_red_cards_per_match))

        return MatchPredictionDTO(
            match=match_dto,
            prediction=self._prediction_to_dto(prediction, suggested_picks.suggested_picks),
        )

    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now (should be in mapper)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country, logo_url=match.home_team.logo_url),
            away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country, logo_url=match.away_team.logo_url),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
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

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         # Same logic as above, but keeping it inside the class for now
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                 )
                 for p in picks
             ]

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
            suggested_picks=pick_dtos,
            created_at=prediction.created_at,
        )
        


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
        self.picks_service = PicksService()
        
    async def execute(self, team_name: str) -> list[MatchPredictionDTO]:
        """
        Get matches for a specific team with predictions.
        
        Args:
            team_name: Name of the team to search for
            
        Returns:
            List of MatchPredictionDTOs
        """
        # 1. Get matches
        matches = await self.data_sources.api_football.get_team_matches(team_name)
        
        if not matches:
            return []
            
        match_prediction_dtos = []
        
        # 2. Setup helpers for historical data
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING
        api_id_to_code = {v: k for k, v in LEAGUE_ID_MAPPING.items()}
        
        # Process each match
        for match in matches:
            try:
                # 3. Try to get historical context
                historical_matches = []
                internal_league_code = None
                
                try:
                    # Try to map league ID
                    if match.league.id and match.league.id.isdigit():
                        lid = int(match.league.id)
                        if lid in api_id_to_code:
                            internal_league_code = api_id_to_code[lid]
                except Exception:
                    pass
                    
                if internal_league_code:
                    try:
                        # Fetch history (cached by service potentially)
                        historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
                            internal_league_code,
                            seasons=["2425", "2324"], 
                        )
                    except Exception:
                        pass
                
                # 4. Calculate stats
                home_stats = self.statistics_service.calculate_team_statistics(match.home_team.name, historical_matches)
                away_stats = self.statistics_service.calculate_team_statistics(match.away_team.name, historical_matches)
                
                # 5. Generate prediction
                prediction = self.prediction_service.generate_prediction(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=None,
                    data_sources=["API-Football", "Football-Data.co.uk"] if historical_matches else ["API-Football"],
                )
                
                # Generate suggested picks
                suggested_picks = self.picks_service.generate_suggested_picks(
                    match=match,
                    home_stats=home_stats,
                    away_stats=away_stats,
                    league_averages=None,
                    predicted_home_goals=prediction.predicted_home_goals,
                    predicted_away_goals=prediction.predicted_away_goals,
                    home_win_prob=prediction.home_win_probability,
                    draw_prob=prediction.draw_probability,
                    away_win_prob=prediction.away_win_probability,
                )
                
                # 6. Create DTOs
                match_dto = self._match_to_dto(match)
                
                # Inject projected stats if NS
                if match.status in ["NS", "TIMED", "SCHEDULED"] and historical_matches:
                     if home_stats and home_stats.matches_played > 0:
                         match_dto.home_corners = int(round(home_stats.avg_corners_per_match))
                         match_dto.home_yellow_cards = int(round(home_stats.avg_yellow_cards_per_match))
                         match_dto.home_red_cards = int(round(home_stats.avg_red_cards_per_match))
                     if away_stats and away_stats.matches_played > 0:
                         match_dto.away_corners = int(round(away_stats.avg_corners_per_match))
                         match_dto.away_yellow_cards = int(round(away_stats.avg_yellow_cards_per_match))
                         match_dto.away_red_cards = int(round(away_stats.avg_red_cards_per_match))
                
                prediction_dto = self._prediction_to_dto(prediction, suggested_picks.suggested_picks)
                
                match_prediction_dtos.append(MatchPredictionDTO(
                    match=match_dto,
                    prediction=prediction_dto
                ))
                
            except Exception as e:
                logger.warning(f"Error processing team match {match.id}: {e}")
                continue

        return match_prediction_dtos
        
    def _match_to_dto(self, match: Match) -> MatchDTO:
        # Duplicated helper for now to avoid cross-cutting refactor
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country, logo_url=match.home_team.logo_url),
            away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country, logo_url=match.away_team.logo_url),
            league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
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

    def _prediction_to_dto(self, prediction: Prediction, picks: list = None) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO, SuggestedPickDTO
         
         pick_dtos = []
         if picks:
             pick_dtos = [
                 SuggestedPickDTO(
                     market_type=p.market_type.value if hasattr(p.market_type, 'value') else p.market_type,
                     market_label=p.market_label,
                     probability=p.probability,
                     confidence_level=p.confidence_level.value if hasattr(p.confidence_level, 'value') else p.confidence_level,
                     reasoning=p.reasoning,
                     risk_level=p.risk_level,
                     is_recommended=p.is_recommended,
                     priority_score=p.priority_score,
                 )
                 for p in picks
             ]

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
            suggested_picks=pick_dtos,
            created_at=prediction.created_at,
        )



class GetGlobalLiveMatchesUseCase:
    """
    Use case for getting all live matches globally from ALL available sources.
    
    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data or simulated matches allowed.
    - Aggregates and deduplicates data to provide the most complete picture.
    """
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
        
    async def execute(self) -> list[MatchDTO]:
        """
        Execute the use case.
        
        Returns:
            List of unique live matches from all sources.
        """
        tasks = []
        
        # 1. API-Football (Primary)
        if self.data_sources.api_football.is_configured:
            tasks.append(self.data_sources.api_football.get_live_matches())
            
        # 2. Football-Data.org (Secondary)
        if self.data_sources.football_data_org.is_configured:
            tasks.append(self.data_sources.football_data_org.get_live_matches())
            
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"Error fetching live matches from source: {res}")
                
        def _calculate_richness(m: Match) -> int:
            """Calculate how many extended statistics a match has."""
            score = 0
            if m.home_corners is not None: score += 1
            if m.home_yellow_cards is not None: score += 1
            if m.home_red_cards is not None: score += 1
            if m.home_shots_on_target is not None: score += 1
            if m.home_total_shots is not None: score += 1
            if m.home_possession: score += 1
            if m.home_fouls is not None: score += 1
            if m.home_offsides is not None: score += 1
            if m.minute: score += 1
            if m.events: score += 1
            return score

        for match in all_matches:
            # Create a simple unique key
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                # Prefer the match with more data richness
                existing = unique_matches[key]
                if _calculate_richness(match) > _calculate_richness(existing):
                    unique_matches[key] = match
        
        # Convert to DTOs
        # Helper reuse (technical debt: duplication)
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        dtos = []
        for match in unique_matches.values():
             dtos.append(MatchDTO(
                id=match.id,
                home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country, logo_url=match.home_team.logo_url),
                away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country, logo_url=match.away_team.logo_url),
                league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
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
                # Extended Stats (MatchDTO validator handles consistency, but we pass them here)
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
            ))
            
        return dtos


class GetGlobalDailyMatchesUseCase:
    """
    Use case for getting all daily matches from ALL available sources.
    
    STRICT POLICY:
    - ONLY returns REAL data from external APIs.
    - NO mock data allowed.
    """
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
        
    async def execute(self, date_str: Optional[str] = None) -> list[MatchDTO]:
        """Get daily matches combined."""
        tasks = []
        
        # 1. API-Football
        if self.data_sources.api_football.is_configured:
            tasks.append(self.data_sources.api_football.get_daily_matches(date_str))
            
        # 2. Football-Data.org (Need to implement get_matches with date range)
        # Currently no direct 'get_daily_matches', but we can assume 'upcoming' covers today if scheduled
        # Skipping to avoid complexity for now, relying on API-Football for strict daily list
        # or we could add specific date query to football_data_org but it has strict rate limits.
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_matches = []
        for res in results:
            if isinstance(res, list):
                all_matches.extend(res)
                
        def _calculate_richness(m: Match) -> int:
            score = 0
            if m.home_corners is not None: score += 1
            if m.home_yellow_cards is not None: score += 1
            if m.home_red_cards is not None: score += 1
            if m.home_shots_on_target is not None: score += 1
            if m.home_total_shots is not None: score += 1
            if m.home_possession: score += 1
            return score

        # Deduplication (same logic)
        unique_matches = {}
        for match in all_matches:
            key = f"{match.home_team.name.lower()}-{match.away_team.name.lower()}"
            if key not in unique_matches:
                unique_matches[key] = match
            else:
                existing = unique_matches[key]
                if _calculate_richness(match) > _calculate_richness(existing):
                    unique_matches[key] = match

        # Map to DTOs
        from src.application.dtos.dtos import TeamDTO, LeagueDTO
        dtos = []
        for match in unique_matches.values():
             dtos.append(MatchDTO(
                id=match.id,
                home_team=TeamDTO(id=match.home_team.id, name=match.home_team.name, country=match.home_team.country, logo_url=match.home_team.logo_url),
                away_team=TeamDTO(id=match.away_team.id, name=match.away_team.name, country=match.away_team.country, logo_url=match.away_team.logo_url),
                league=LeagueDTO(id=match.league.id, name=match.league.name, country=match.league.country, season=match.league.season),
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
                # Extended Stats (MatchDTO validator handles consistency)
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
            ))
            
        return dtos
