"""
Application Use Cases Module

Use cases represent application-specific business rules and orchestrate
the flow of data between the domain layer and the infrastructure layer.
"""

from datetime import datetime
from typing import Optional
from dataclasses import dataclass
import logging

from src.domain.entities.entities import Match, League, Prediction, TeamStatistics
from src.domain.services.prediction_service import PredictionService, LeagueAverages
from src.infrastructure.data_sources.football_data_uk import (
    FootballDataUKSource,
    LEAGUES_METADATA,
)
from src.infrastructure.data_sources.api_football import APIFootballSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
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


class GetLeaguesUseCase:
    """Use case for getting available leagues."""
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
    
    async def execute(self) -> LeaguesResponseDTO:
        """Get all available leagues grouped by country."""
        leagues = self.data_sources.football_data_uk.get_available_leagues()
        
        # Get active league IDs from API-Football to filter out empty ones
        active_api_ids = set()
        api_configured = self.data_sources.api_football.is_configured
        
        if api_configured:
            try:
                active_api_ids = await self.data_sources.api_football.get_active_league_ids(days=10)
            except Exception as e:
                logger.error(f"Failed to get active leagues: {e}")
        
        from src.infrastructure.data_sources.api_football import LEAGUE_ID_MAPPING

        # Group by country
        countries_dict: dict[str, list[League]] = {}
        for league in leagues:
            # Strict Filtering:
            # If API-Football is our primary source for upcoming matches, we MUST filter by it.
            # If the league is not in the active set, we hide it.
            # If API is not configured, we strictly show nothing (since we can't get upcoming matches anyway?)
            # Or we show all? The user said: "when no data available... don't show".
            # If we have NO data source for a league, we shouldn't show it.
            
            if api_configured:
                # Check if this league code maps to an active API ID
                api_id = LEAGUE_ID_MAPPING.get(league.id)
                if not api_id or api_id not in active_api_ids:
                     # Skip this league as it has no upcoming matches
                     continue
            # If API is NOT configured, do we have another source for upcoming matches?
            # OpenFootball is mostly historical in our current impl.
            # So if API is not configured, we probably shouldn't show anything that relies on it.
            # For safety/strictness per user request:
            elif not api_configured:
                 # If strictly no mock data and no API, we have no upcoming matches.
                 # So we should probably hide everything.
                 # But this might break the app if they haven't set the key yet.
                 # However, the instruction is clear.
                 continue

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

        # Calculate league averages from historical data
        league_averages = self._calculate_league_averages(historical_matches)
        
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
    
    def _calculate_league_averages(self, matches: list[Match]) -> LeagueAverages:
        """Calculate average goals from historical matches."""
        if not matches:
            return LeagueAverages(
                avg_home_goals=1.5,
                avg_away_goals=1.1,
                avg_total_goals=2.6,
            )
        
        played_matches = [m for m in matches if m.is_played]
        if not played_matches:
            return LeagueAverages(
                avg_home_goals=1.5,
                avg_away_goals=1.1,
                avg_total_goals=2.6,
            )
        
        total_home = sum(m.home_goals for m in played_matches)
        total_away = sum(m.away_goals for m in played_matches)
        n = len(played_matches)
        
        return LeagueAverages(
            avg_home_goals=total_home / n,
            avg_away_goals=total_away / n,
            avg_total_goals=(total_home + total_away) / n,
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
        match = await self.data_sources.api_football.get_match_details(match_id)
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

        return MatchPredictionDTO(
            match=self._match_to_dto(match),
            prediction=self._prediction_to_dto(prediction),
        )

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
        
    def _create_sample_matches(
        self,
        historical_matches: list[Match],
        league: League,
        limit: int,
    ) -> list[Match]:
        """
        Create sample upcoming matches from historical teams.
        
        Used when real fixtures aren't available.
        """
        # Get unique teams from historical matches
        teams = {}
        for match in historical_matches:
            teams[match.home_team.name] = match.home_team
            teams[match.away_team.name] = match.away_team
        
        team_list = list(teams.values())
        if len(team_list) < 2:
            return []
        
        # Create sample matches
        sample_matches = []
        from datetime import timedelta
        now = datetime.utcnow()
        
        # Use last known odds if available
        odds_map = {}
        for match in historical_matches[-100:]:
            if match.home_odds:
                odds_map[match.home_team.name] = {
                    'home': match.home_odds,
                    'draw': match.draw_odds,
                    'away': match.away_odds,
                }
        
        for i in range(min(limit, len(team_list) // 2)):
            home = team_list[i * 2]
            away = team_list[i * 2 + 1]
            
            # Get odds if available
            odds = odds_map.get(home.name, {})
            
            match = Match(
                id=f"sample_{league.id}_{i}",
                home_team=home,
                away_team=away,
                league=league,
                match_date=now + timedelta(days=i + 1),
                home_odds=odds.get('home'),
                draw_odds=odds.get('draw'),
                away_odds=odds.get('away'),
            )
            sample_matches.append(match)
        
        return sample_matches
    
    def _match_to_dto(self, match: Match) -> MatchDTO:
        """Convert Match entity to DTO."""
        return MatchDTO(
            id=match.id,
            home_team=TeamDTO(
                id=match.home_team.id,
                name=match.home_team.name,
                short_name=match.home_team.short_name,
                country=match.home_team.country,
            ),
            away_team=TeamDTO(
                id=match.away_team.id,
                name=match.away_team.name,
                short_name=match.away_team.short_name,
                country=match.away_team.country,
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
    
    def _prediction_to_dto(self, prediction: Prediction) -> PredictionDTO:
        """Convert Prediction entity to DTO."""
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
