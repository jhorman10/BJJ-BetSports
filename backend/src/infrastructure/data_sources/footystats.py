"""
FootyStats Data Source

This module integrates with FootyStats API (footystats.org) for
detailed match statistics and historical data.

Free tier: Premier League only, 180 requests/hour.
API Documentation: https://footystats.org/api/
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)


@dataclass
class FootyStatsConfig:
    """Configuration for FootyStats API."""
    api_key: Optional[str] = None
    base_url: str = "https://api.footystats.org"
    timeout: int = 30
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("FOOTYSTATS_API_KEY")


# Mapping of our internal league codes to FootyStats league IDs
FOOTYSTATS_LEAGUE_MAPPING = {
    "E0": 2012,    # Premier League
    "SP1": 2014,   # La Liga
    "D1": 2002,    # Bundesliga  
    "I1": 2019,    # Serie A
    "F1": 2015,    # Ligue 1
}


class FootyStatsSource:
    """
    Data source for FootyStats API.
    
    Free tier limitations:
    - Premier League only
    - 180 requests per hour
    """
    
    SOURCE_NAME = "FootyStats"
    
    def __init__(self, config: Optional[FootyStatsConfig] = None):
        self.config = config or FootyStatsConfig()
        self._request_count = 0
        self._last_reset = datetime.utcnow()
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits (180/hour for free tier)."""
        now = datetime.utcnow()
        if (now - self._last_reset).total_seconds() > 3600:
            self._request_count = 0
            self._last_reset = now
        return self._request_count < 180
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make authenticated request to FootyStats."""
        if not self.is_configured:
            logger.debug("FootyStats not configured (no API key)")
            return None
        
        if not self._check_rate_limit():
            logger.warning("FootyStats rate limit reached (180/hour)")
            return None
        
        url = f"{self.config.base_url}{endpoint}"
        if params is None:
            params = {}
        params["key"] = self.config.api_key
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                self._request_count += 1
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"FootyStats HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"FootyStats request error: {e}")
            return None
    
    async def get_league_matches(
        self,
        league_code: str,
        season: Optional[str] = None,
    ) -> List[Match]:
        """
        Get matches for a league.
        
        Args:
            league_code: Our internal league code (e.g., "E0")
            season: Season year (e.g., "2024")
            
        Returns:
            List of Match entities
        """
        if league_code not in FOOTYSTATS_LEAGUE_MAPPING:
            logger.debug(f"No FootyStats mapping for league {league_code}")
            return []
        
        league_id = FOOTYSTATS_LEAGUE_MAPPING[league_code]
        
        params = {"league_id": league_id}
        if season:
            params["season_id"] = season
        
        data = await self._make_request("/league-matches", params)
        
        if not data or "data" not in data:
            return []
        
        matches = []
        for match_data in data.get("data", []):
            try:
                match = self._parse_match(match_data, league_code)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug(f"Error parsing FootyStats match: {e}")
                continue
        
        logger.info(f"FootyStats: fetched {len(matches)} matches for {league_code}")
        return matches
    
    async def get_finished_matches(
        self,
        league_codes: Optional[List[str]] = None,
    ) -> List[Match]:
        """
        Get finished matches from FootyStats.
        
        Note: Free tier only supports Premier League.
        
        Args:
            league_codes: List of our league codes to fetch
            
        Returns:
            List of finished Match entities
        """
        if not self.is_configured:
            logger.debug("FootyStats not configured, skipping")
            return []
        
        all_matches = []
        leagues_to_fetch = league_codes or ["E0"]  # Free tier: Premier League only
        
        for league_code in leagues_to_fetch:
            matches = await self.get_league_matches(league_code)
            finished = [m for m in matches if m.home_goals is not None]
            all_matches.extend(finished)
        
        return all_matches
    
    def _parse_match(self, match_data: dict, league_code: str) -> Optional[Match]:
        """Parse FootyStats match data into Match entity."""
        try:
            # Parse date
            date_unix = match_data.get("date_unix")
            if date_unix:
                match_date = datetime.fromtimestamp(date_unix)
            else:
                match_date = datetime.utcnow()
            
            # Get status
            status = match_data.get("status", "")
            is_finished = status.lower() in ["complete", "finished", "ft"]
            
            # Create teams
            home_team = Team(
                id=str(match_data.get("homeID", "")),
                name=match_data.get("home_name", "Unknown"),
            )
            away_team = Team(
                id=str(match_data.get("awayID", "")),
                name=match_data.get("away_name", "Unknown"),
            )
            
            # Create league
            league = League(
                id=league_code,
                name=match_data.get("competition_name", "Unknown"),
                country="Unknown",
            )
            
            # Get goals
            home_goals = match_data.get("homeGoalCount")
            away_goals = match_data.get("awayGoalCount")
            
            # Get additional stats if available
            home_corners = match_data.get("team_a_corners")
            away_corners = match_data.get("team_b_corners")
            home_yellow = match_data.get("team_a_yellow_cards")
            away_yellow = match_data.get("team_b_yellow_cards")
            home_red = match_data.get("team_a_red_cards")
            away_red = match_data.get("team_b_red_cards")
            
            return Match(
                id=str(match_data.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=int(home_goals) if home_goals is not None else None,
                away_goals=int(away_goals) if away_goals is not None else None,
                status="FT" if is_finished else "NS",
                home_corners=int(home_corners) if home_corners is not None else None,
                away_corners=int(away_corners) if away_corners is not None else None,
                home_yellow_cards=int(home_yellow) if home_yellow is not None else None,
                away_yellow_cards=int(away_yellow) if away_yellow is not None else None,
                home_red_cards=int(home_red) if home_red is not None else None,
                away_red_cards=int(away_red) if away_red is not None else None,
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse FootyStats match: {e}")
            return None
