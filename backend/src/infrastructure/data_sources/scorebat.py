"""
ScoreBat Video API Data Source

Provides free football highlights and goals from major leagues.
API Documentation: https://www.scorebat.com/video-api/v3/
"""

import logging
from typing import Optional, List, Dict, Any
import os
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class ScoreBatSource:
    """
    Data source for ScoreBat Video API.
    """
    
    SOURCE_NAME = "ScoreBat"
    FEED_URL = "https://www.scorebat.com/video-api/v3/feed/"
    
    def __init__(self, api_token: Optional[str] = None):
        """
        ScoreBat V3 uses a token in the URL or sometimes no token for a public feed.
        We'll use a token if provided.
        """
        self.api_token = api_token or os.getenv("SCOREBAT_TOKEN")
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def get_highlights(self) -> List[Dict[str, Any]]:
        """
        Fetches the latest highlights feed.
        """
        url = self.FEED_URL
        if self.api_token:
            url += f"?token={self.api_token}"
            
        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("response", [])
        except Exception as e:
            logger.error(f"ScoreBat request failed: {e}")
            return []

    def find_match_highlights(self, home_team: str, away_team: str, highlights: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Fuzzy match for team names to find highlights for a specific match.
        """
        from src.domain.services.statistics_service import StatisticsService
        stats_service = StatisticsService()
        
        home_norm = stats_service._normalize_name(home_team)
        away_norm = stats_service._normalize_name(away_team)
        
        for item in highlights:
            side1 = stats_service._normalize_name(item.get("side1", {}).get("name", ""))
            side2 = stats_service._normalize_name(item.get("side2", {}).get("name", ""))
            
            # Simple match - team names should appear in the feed sides
            if (home_norm in side1 or home_norm in side2) and (away_norm in side1 or away_norm in side2):
                return item
                
        return None
