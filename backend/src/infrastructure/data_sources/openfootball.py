"""
OpenFootball Data Source

This module handles downloading and parsing JSON data from the OpenFootball GitHub repository.
Repository: https://github.com/openfootball/football.json
"""

import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

import httpx
from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)


@dataclass
class OpenFootballConfig:
    """Configuration for OpenFootball data source."""
    base_url: str = "https://raw.githubusercontent.com/openfootball/football.json/master"
    timeout: int = 30


# Mapping of our league codes to OpenFootball file paths (relative to season)
LEAGUE_FILE_MAPPING = {
    "E0": "en.1",
    "E1": "en.2",
    "D1": "de.1",
    "SP1": "es.1",
    "I1": "it.1",
    "F1": "fr.1",
    "B1": "be.1",
    # Add more as discovered
}


class OpenFootballSource:
    """
    Data source for OpenFootball (GitHub).
    """

    SOURCE_NAME = "OpenFootball"

    def __init__(self, config: Optional[OpenFootballConfig] = None):
        """Initialize the data source."""
        self.config = config or OpenFootballConfig()

    def _get_season_string(self, season: Optional[str] = None) -> str:
        """
        Get season string in 'YYYY-YY' format (e.g., '2024-25').
        Default to current season based on date.
        """
        now = datetime.now()
        if not season:
            year = now.year
            # If we are in second half of year, season started this year
            if now.month >= 7:
                start_year = year
                end_year = year + 1
            else:
                start_year = year - 1
                end_year = year
            
            return f"{start_year}-{str(end_year)[-2:]}"
        
        return season

    async def get_matches(self, league: League) -> list[Match]:
        """
        Get all matches for a league.
        
        Args:
            league: League entity
            
        Returns:
            List of matches
        """
        if league.id not in LEAGUE_FILE_MAPPING:
            logger.debug(f"League {league.id} not mapped in OpenFootball")
            return []

        filename = LEAGUE_FILE_MAPPING[league.id]
        season_str = self._get_season_string(league.season)
        
        # URL pattern: {base}/{season}/{filename}.json
        url = f"{self.config.base_url}/{season_str}/{filename}.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.config.timeout)
                
                if response.status_code == 404:
                    logger.warning(f"OpenFootball file not found: {url}")
                    return []
                    
                response.raise_for_status()
                data = response.json()
                
                return self._parse_matches(data, league)
                
        except Exception as e:
            logger.error(f"Error fetching OpenFootball data from {url}: {e}")
            return []

    def _parse_matches(self, data: dict, league: League) -> list[Match]:
        """Parse JSON data into Match entities."""
        matches = []
        
        # Data structure: { "name": "...", "matches": [ ... ] }
        match_list = data.get("matches", [])
        
        for item in match_list:
            try:
                # { "date": "2024-08-16", "team1": "...", "team2": "...", "score": { ... } }
                date_str = item.get("date")
                if not date_str:
                    continue
                    
                from src.utils.time_utils import COLOMBIA_TZ
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                match_date = COLOMBIA_TZ.localize(dt)
                
                # Check if authorized time is present
                if item.get("time"):
                    # Combine date and time if needed (simple implementation just uses date)
                    pass

                home_name = item.get("team1", "Unknown")
                away_name = item.get("team2", "Unknown")
                
                home_team = Team(
                    id=home_name.lower().replace(" ", "_"),
                    name=home_name,
                    country=league.country
                )
                
                away_team = Team(
                    id=away_name.lower().replace(" ", "_"),
                    name=away_name,
                    country=league.country
                )
                
                # Score parsing
                score = item.get("score")
                home_goals = None
                away_goals = None
                status = "NS"
                
                if score and score.get("ft"):
                    home_goals = score["ft"][0]
                    away_goals = score["ft"][1]
                    status = "FT"
                
                match = Match(
                    id=f"{league.id}_{match_date.strftime('%Y%m%d')}_{home_team.id}_{away_team.id}",
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_date=match_date,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    status=status
                )
                matches.append(match)
                
            except Exception as e:
                logger.debug(f"Error parsing match item: {e}")
                continue
                
        return matches
