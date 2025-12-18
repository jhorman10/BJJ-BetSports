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


class GetLeaguesUseCase:
    """Use case for getting available leagues."""
    
    def __init__(self, data_sources: DataSources):
        self.data_sources = data_sources
    
    async def execute(self) -> LeaguesResponseDTO:
        """Get all available leagues grouped by country."""
        leagues = self.data_sources.football_data_uk.get_available_leagues()
        
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
            countries.append(CountryDTO(
                name=country_name,
                code=country_name[:3].upper(),
                leagues=league_dtos,
            ))
        
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
    ):
        self.data_sources = data_sources
        self.prediction_service = prediction_service
    
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
        
        # Get historical data from Football-Data.co.uk
        historical_matches = await self.data_sources.football_data_uk.get_historical_matches(
            league_id,
            seasons=["2425", "2324"],
        )
        
        # Calculate league averages from historical data
        league_averages = self._calculate_league_averages(historical_matches)
        
        # Get upcoming fixtures
        upcoming_matches = await self._get_upcoming_matches(league_id, limit)
        
        # If no upcoming matches from APIs, create mock upcoming matches
        # from the most recent unplayed historical data
        if not upcoming_matches:
            upcoming_matches = self._create_sample_matches(historical_matches, league, limit)
        
        # Generate predictions
        predictions = []
        data_sources_used = [FootballDataUKSource.SOURCE_NAME]
        
        if self.data_sources.api_football.is_configured:
            data_sources_used.append(APIFootballSource.SOURCE_NAME)
        if self.data_sources.football_data_org.is_configured:
            data_sources_used.append(FootballDataOrgSource.SOURCE_NAME)
        
        for match in upcoming_matches[:limit]:
            # Get team statistics
            home_stats = self.data_sources.football_data_uk.calculate_team_statistics(
                match.home_team.name,
                historical_matches,
            )
            away_stats = self.data_sources.football_data_uk.calculate_team_statistics(
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
        
        return []
    
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
