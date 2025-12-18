"""
Football-Data.org Data Source

This module integrates with Football-Data.org free API tier for
additional league data, standings, and team information.

API Documentation: https://www.football-data.org/documentation/api
Free tier: 10 requests/minute
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import logging
import asyncio

import httpx

from src.domain.entities.entities import Match, Team, League


logger = logging.getLogger(__name__)


@dataclass
class FootballDataOrgConfig:
    """Configuration for Football-Data.org."""
    api_key: Optional[str] = None
    base_url: str = "https://api.football-data.org/v4"
    timeout: int = 30
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")


# Mapping of our league codes to Football-Data.org competition codes
COMPETITION_CODE_MAPPING = {
    "E0": "PL",   # Premier League
    "E1": "ELC",  # Championship
    "SP1": "PD",  # La Liga
    "D1": "BL1",  # Bundesliga
    "I1": "SA",   # Serie A
    "F1": "FL1",  # Ligue 1
    "N1": "DED",  # Eredivisie
    "P1": "PPL",  # Primeira Liga
}


class FootballDataOrgSource:
    """
    Data source for Football-Data.org.
    
    Provides access to league standings, team data, and match schedules.
    Free tier: 10 requests/minute.
    """
    
    SOURCE_NAME = "Football-Data.org"
    
    def __init__(self, config: Optional[FootballDataOrgConfig] = None):
        """Initialize the data source."""
        self.config = config or FootballDataOrgConfig()
        self._request_times: list[datetime] = []
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)
    
    async def _wait_for_rate_limit(self):
        """Wait if necessary to respect rate limit (10 req/min)."""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old request times
        self._request_times = [t for t in self._request_times if t > minute_ago]
        
        if len(self._request_times) >= 10:
            # Wait until oldest request is more than a minute old
            wait_time = (self._request_times[0] + timedelta(minutes=1) - now).total_seconds()
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Make authenticated request to Football-Data.org.
        
        Args:
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response or None if failed
        """
        if not self.is_configured:
            logger.warning("Football-Data.org not configured (no API key)")
            return None
        
        await self._wait_for_rate_limit()
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "X-Auth-Token": self.config.api_key,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout,
                )
                
                self._request_times.append(datetime.utcnow())
                
                if response.status_code == 429:
                    logger.warning("Football-Data.org rate limit hit")
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Football-Data.org HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Football-Data.org request error: {e}")
            return None
    
    async def get_competitions(self) -> list[dict]:
        """Get list of available competitions."""
        data = await self._make_request("/competitions")
        
        if not data:
            return []
        
        return data.get("competitions", [])
    
    async def get_league_teams(self, league_code: str) -> list[Team]:
        """
        Get teams for a league.
        
        Args:
            league_code: Our league code
            
        Returns:
            List of Team entities
        """
        if league_code not in COMPETITION_CODE_MAPPING:
            return []
        
        comp_code = COMPETITION_CODE_MAPPING[league_code]
        data = await self._make_request(f"/competitions/{comp_code}/teams")
        
        if not data or not data.get("teams"):
            return []
        
        teams = []
        for team_data in data["teams"]:
            teams.append(Team(
                id=str(team_data.get("id")),
                name=team_data.get("name", "Unknown"),
                short_name=team_data.get("shortName"),
                country=team_data.get("area", {}).get("name"),
            ))
        
        return teams
    
    async def get_upcoming_matches(
        self,
        league_code: str,
        matchday: Optional[int] = None,
    ) -> list[Match]:
        """
        Get scheduled matches for a league.
        
        Args:
            league_code: Our league code
            matchday: Specific matchday or None for upcoming
            
        Returns:
            List of Match entities
        """
        if league_code not in COMPETITION_CODE_MAPPING:
            return []
        
        comp_code = COMPETITION_CODE_MAPPING[league_code]
        params = {"status": "SCHEDULED"}
        
        if matchday:
            params["matchday"] = matchday
        
        data = await self._make_request(f"/competitions/{comp_code}/matches", params)
        
        if not data or not data.get("matches"):
            return []
        
        # Get competition info
        competition = data.get("competition", {})
        league = League(
            id=league_code,
            name=competition.get("name", "Unknown"),
            country=competition.get("area", {}).get("name", "Unknown"),
        )
        
        matches = []
        for match_data in data["matches"]:
            try:
                match = self._parse_match(match_data, league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug(f"Error parsing match: {e}")
        
        return matches
    
    def _parse_match(self, match_data: dict, league: League) -> Optional[Match]:
        """Parse Football-Data.org match into Match entity."""
        try:
            home_team_data = match_data.get("homeTeam", {})
            away_team_data = match_data.get("awayTeam", {})
            
            home_team = Team(
                id=str(home_team_data.get("id", "")),
                name=home_team_data.get("name", "Unknown"),
                short_name=home_team_data.get("shortName"),
                country=league.country,
            )
            
            away_team = Team(
                id=str(away_team_data.get("id", "")),
                name=away_team_data.get("name", "Unknown"),
                short_name=away_team_data.get("shortName"),
                country=league.country,
            )
            
            # Parse date
            utc_date = match_data.get("utcDate", "")
            match_date = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
            
            # Get score if available
            score = match_data.get("score", {}).get("fullTime", {})
            home_goals = score.get("home")
            away_goals = score.get("away")
            
            return Match(
                id=str(match_data.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse match: {e}")
            return None
    
    async def get_standings(self, league_code: str) -> Optional[dict]:
        """
        Get current standings for a league.
        
        Args:
            league_code: Our league code
            
        Returns:
            Standings data or None
        """
        if league_code not in COMPETITION_CODE_MAPPING:
            return None
        
        comp_code = COMPETITION_CODE_MAPPING[league_code]
        data = await self._make_request(f"/competitions/{comp_code}/standings")
        
        if not data:
            return None
        
        return data.get("standings", [])
