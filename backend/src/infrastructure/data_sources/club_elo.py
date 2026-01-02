"""
ClubElo Data Source

Fetches football Elo ratings from api.clubelo.com.
Provides a global, objective measure of team strength.
"""

import logging
import aiohttp
import io
from datetime import datetime, timedelta
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class ClubEloSource:
    BASE_URL = "http://api.clubelo.com"
    _cache: Dict[str, float] = {}
    _last_fetch: datetime = None
    
    async def get_elo_for_match(self, home_team: str, away_team: str) -> tuple[Optional[float], Optional[float]]:
        """
        Get Elo ratings for home and away teams.
        Returns (home_elo, away_elo).
        """
        await self._ensure_cache()
        
        h_elo = self._find_team_elo(home_team)
        a_elo = self._find_team_elo(away_team)
        
        return h_elo, a_elo

    async def _ensure_cache(self):
        """Fetch and cache the latest Elo ratings (once per day)."""
        now = datetime.now()
        if self._last_fetch and (now - self._last_fetch) < timedelta(hours=24):
            return

        try:
            # Lazy import pandas (only when fetching data)
            import pandas as pd
            
            # Fetch current ratings for all teams
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.BASE_URL}/{now.strftime('%Y-%m-%d')}") as response:
                    if response.status == 200:
                        content = await response.text()
                        # Parse CSV
                        df = pd.read_csv(io.StringIO(content))
                        # Cache: {TeamName: Elo}
                        self._cache = dict(zip(df['Club'], df['Elo']))
                        self._last_fetch = now
                        logger.info(f"Fetched {len(self._cache)} ClubElo ratings")
                    else:
                        logger.warning(f"Failed to fetch ClubElo: {response.status}")
        except Exception as e:
            logger.error(f"Error fetching ClubElo data: {e}")

    def _find_team_elo(self, team_name: str) -> Optional[float]:
        """Fuzzy search for team name in Elo cache."""
        if not self._cache:
            return None
            
        # 1. Direct match
        if team_name in self._cache:
            return self._cache[team_name]
            
        # 2. Normalized match
        normalized_input = team_name.lower().replace(" ", "")
        
        # Try to find best match
        # This is a simple heuristic, could be improved with Levenshtein
        for club, elo in self._cache.items():
            normalized_club = club.lower().replace(" ", "")
            if normalized_input == normalized_club:
                return elo
            if normalized_input in normalized_club or normalized_club in normalized_input:
                # Only accept if length difference is small to avoid false positives
                if abs(len(normalized_input) - len(normalized_club)) < 4:
                    return elo
                    
        return None