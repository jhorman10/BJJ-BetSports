"""
API-Football Data Source

This module integrates with API-Football (api-football.com) for real-time
fixtures and additional statistics. Free tier: 100 requests/day.

API Documentation: https://www.api-football.com/documentation-v3
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
import logging

import httpx

from src.domain.entities.entities import Match, Team, League


logger = logging.getLogger(__name__)


@dataclass
class APIFootballConfig:
    """Configuration for API-Football."""
    api_key: Optional[str] = None
    base_url: str = "https://v3.football.api-sports.io"
    timeout: int = 30
    
    def __post_init__(self):
        # Try to get API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("API_FOOTBALL_KEY")


# Mapping of our league codes to API-Football league IDs
LEAGUE_ID_MAPPING = {
    "E0": 39,   # Premier League
    "E1": 40,   # Championship
    "SP1": 140, # La Liga
    "SP2": 141, # Segunda División
    "D1": 78,   # Bundesliga
    "D2": 79,   # 2. Bundesliga
    "I1": 135,  # Serie A
    "I2": 136,  # Serie B
    "F1": 61,   # Ligue 1
    "F2": 62,   # Ligue 2
    "N1": 88,   # Eredivisie
    "B1": 144,  # Jupiler Pro League
    "P1": 94,   # Primeira Liga
    "T1": 203,  # Super Lig
    "G1": 197,  # Super League Greece
}


class APIFootballSource:
    """
    Data source for API-Football.
    
    Provides access to real-time fixtures and additional match data.
    Requires API key (free tier: 100 requests/day).
    """
    
    SOURCE_NAME = "API-Football"
    
    def __init__(self, config: Optional[APIFootballConfig] = None):
        """Initialize the data source."""
        self.config = config or APIFootballConfig()
        self._request_count = 0
        self._last_reset = datetime.utcnow().date()
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits (100/day for free tier)."""
        today = datetime.utcnow().date()
        if today > self._last_reset:
            self._request_count = 0
            self._last_reset = today
        return self._request_count < 100
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Make authenticated request to API-Football.
        
        Args:
            endpoint: API endpoint (e.g., "/fixtures")
            params: Query parameters
            
        Returns:
            JSON response or None if failed
        """
        if not self.is_configured:
            logger.warning("API-Football not configured (no API key)")
            return None
        
        if not self._check_rate_limit():
            logger.warning("API-Football rate limit reached (100/day)")
            return None
        
        url = f"{self.config.base_url}{endpoint}"
        headers = {
            "x-rapidapi-key": self.config.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                self._request_count += 1
                
                data = response.json()
                
                if data.get("errors"):
                    logger.error(f"API-Football error: {data['errors']}")
                    return None
                
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"API-Football HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"API-Football request error: {e}")
            return None
    
    async def get_upcoming_fixtures(
        self,
        league_code: str,
        season: Optional[int] = None,
        next_n: int = 10,
    ) -> list[Match]:
        """
        Get upcoming fixtures for a league.
        
        Args:
            league_code: Our league code (e.g., "E0")
            season: Season year (e.g., 2024)
            next_n: Number of fixtures to return
            
        Returns:
            List of upcoming Match entities
        """
        if league_code not in LEAGUE_ID_MAPPING:
            logger.warning(f"League code {league_code} not mapped to API-Football")
            return []
        
        api_league_id = LEAGUE_ID_MAPPING[league_code]
        season = season or datetime.now().year
        
        # Get fixtures for next 7 days
        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        data = await self._make_request("/fixtures", {
            "league": api_league_id,
            "season": season,
            "from": from_date,
            "to": to_date,
        })
        
        if not data or not data.get("response"):
            return []
        
        matches = []
        for fixture in data["response"][:next_n]:
            try:
                match = self._parse_fixture(fixture, league_code)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug(f"Error parsing fixture: {e}")
                continue
        
        return matches
    
    def _parse_fixture(self, fixture_data: dict, league_code: str) -> Optional[Match]:
        """Parse API-Football fixture into Match entity."""
        try:
            fixture = fixture_data.get("fixture", {})
            league_data = fixture_data.get("league", {})
            teams = fixture_data.get("teams", {})
            goals = fixture_data.get("goals", {})
            
            # Parse match date
            timestamp = fixture.get("timestamp")
            match_date = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
            
            # Create league
            league = League(
                id=league_code,
                name=league_data.get("name", "Unknown"),
                country=league_data.get("country", "Unknown"),
                season=str(league_data.get("season")),
            )
            
            # Create teams
            home_team = Team(
                id=str(teams.get("home", {}).get("id", "")),
                name=teams.get("home", {}).get("name", "Unknown"),
                country=league.country,
            )
            away_team = Team(
                id=str(teams.get("away", {}).get("id", "")),
                name=teams.get("away", {}).get("name", "Unknown"),
                country=league.country,
            )
            
            # Get goals if available
            home_goals = goals.get("home")
            away_goals = goals.get("away")
            
            return Match(
                id=str(fixture.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse fixture: {e}")
            return None
    
    async def get_odds(
        self,
        fixture_id: str,
    ) -> Optional[tuple[float, float, float]]:
        """
        Get betting odds for a fixture.
        
        Args:
            fixture_id: API-Football fixture ID
            
        Returns:
            Tuple of (home_odds, draw_odds, away_odds) or None
        """
        data = await self._make_request("/odds", {
            "fixture": fixture_id,
            "bookmaker": 8,  # Bet365
        })
        
        if not data or not data.get("response"):
            return None
        
        try:
            response = data["response"][0]
            bookmakers = response.get("bookmakers", [])
            
            if not bookmakers:
                return None
            
            # Find Match Winner bet type
            for bet in bookmakers[0].get("bets", []):
                if bet.get("name") == "Match Winner":
                    values = {v["value"]: float(v["odd"]) for v in bet.get("values", [])}
                    return (
                        values.get("Home"),
                        values.get("Draw"),
                        values.get("Away"),
                    )
            
        except Exception as e:
            logger.debug(f"Error parsing odds: {e}")
        
        return None
    
    def get_remaining_requests(self) -> int:
        """Get number of remaining API requests for today."""
        today = datetime.utcnow().date()
        if today > self._last_reset:
            return 100
        return max(0, 100 - self._request_count)
