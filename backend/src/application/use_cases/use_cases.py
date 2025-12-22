"""
Application Use Cases Module

Use cases represent application-specific business rules and orchestrate
the flow of data between the domain layer and the infrastructure layer.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass
import logging
import asyncio

from src.domain.entities.entities import Match, League, Prediction, TeamStatistics
from src.domain.services.prediction_service import PredictionService
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
                matches = await self.data_sources.football_data_uk.get_historical_matches(
                    league_id, 
                    seasons=["2425"]
                )
                return len(matches) >= 5
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
    
    async def execute(self, league_id: str, limit: int = 10) -> PredictionsResponseDTO:
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
        # 1. Try Football-Data.co.uk (CSV) - Preferred for stats
        historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
            league_id,
            seasons=["2425", "2324"],
        )
        
        # 2. If no data, try OpenFootball (JSON) - Fallback
        # Note: We need a League entity, which we created above ('league')
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
        upcoming_matches = await self._get_upcoming_matches(league_id, limit)
        
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
            
            # Data Sufficiency Filter:
            # Both teams must have played at least 3 matches to generate a reliable prediction
            if home_stats.matches_played < 3 or away_stats.matches_played < 3:
                continue
            
            # Generate prediction
            prediction = self.prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages,
                data_sources=data_sources_used,
            )
            
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
            
            prediction_dto = self._prediction_to_dto(prediction)
            
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
            generated_at=datetime.utcnow(),
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

    def _prediction_to_dto(self, prediction: Prediction) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO
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

        # 2. Get historical data for context (for stats)
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
        
        # 3. Calculate stats using whatever history we found (or empty list)
        home_stats = self.statistics_service.calculate_team_statistics(match.home_team.name, historical_matches)
        away_stats = self.statistics_service.calculate_team_statistics(match.away_team.name, historical_matches)
        
        # 4. Generate prediction
        prediction = self.prediction_service.generate_prediction(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=None, # Will use defaults
            data_sources=[APIFootballSource.SOURCE_NAME] + ([FootballDataUKSource.SOURCE_NAME] if historical_matches else []),
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
            prediction=self._prediction_to_dto(prediction),
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

    def _prediction_to_dto(self, prediction: Prediction) -> PredictionDTO:
         from src.application.dtos.dtos import PredictionDTO
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
            created_at=prediction.created_at,
        )
        

