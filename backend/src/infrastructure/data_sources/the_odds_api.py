"""
The Odds API Data Source

Provides real-time betting odds from multiple bookmakers.
Free tier: 500 requests per month.
API Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)

# Mapping of our league codes to The Odds API sport keys
SPORT_KEY_MAPPING = {
    "E0": "soccer_epl",               # Premier League
    "E1": "soccer_efl_championship",  # Championship
    "SP1": "soccer_spain_la_liga",    # La Liga
    "D1": "soccer_germany_bundesliga",# Bundesliga
    "I1": "soccer_italy_serie_a",     # Serie A
    "F1": "soccer_france_ligue_1",    # Ligue 1
    "N1": "soccer_netherlands_eredivisie", # Eredivisie
    "P1": "soccer_portugal_primeira_liga", # Primeira Liga
    "UCL": "soccer_uefa_champions_league",
    "UEL": "soccer_uefa_europa_league",
}

class TheOddsAPISource:
    """
    Data source for The Odds API.
    """
    
    SOURCE_NAME = "The Odds API"
    BASE_URL = "https://api.the-odds-api.com/v4/sports"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("THE_ODDS_API_KEY")
        self._client = httpx.AsyncClient(timeout=30.0)
    
    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[Any]:
        if not self.is_configured:
            logger.warning("The Odds API not configured (no API key)")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        query_params = {"apiKey": self.api_key}
        if params:
            query_params.update(params)
            
        try:
            response = await self._client.get(url, params=query_params)
            # Check for remaining requests in headers
            remaining = response.headers.get("x-requests-remaining")
            if remaining:
                logger.debug(f"The Odds API remaining requests: {remaining}")
                
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"The Odds API request failed: {e}")
            return None

    async def get_odds(
        self,
        league_code: str,
        regions: str = "eu,us",
        markets: str = "h2h",
        odds_format: str = "decimal"
    ) -> List[Dict[str, Any]]:
        """
        Get odds for a specific league.
        """
        sport_key = SPORT_KEY_MAPPING.get(league_code)
        if not sport_key:
            logger.warning(f"League code {league_code} not mapped to The Odds API")
            return []
            
        endpoint = f"/{sport_key}/odds"
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }
        
        data = await self._make_request(endpoint, params)
        return data if data else []

    def map_to_match(self, odds_item: Dict[str, Any], league_code: str) -> Match:
        """
        Maps a JSON item from The Odds API to our internal Match entity.
        Note: This is partially mapped as The Odds API focus is on odds, not full results.
        """
        # Parse start time
        commence_time = odds_item.get("commence_time")
        if commence_time:
             # Format: 2021-12-01T12:00:00Z
             match_date = datetime.strptime(commence_time, "%Y-%m-%dT%H:%M:%SZ")
        else:
             match_date = datetime.now()

        # Best Odds Extraction (Simplified - picks the first bookmaker for now)
        home_odds = None
        draw_odds = None
        away_odds = None
        
        bookmakers = odds_item.get("bookmakers", [])
        if bookmakers:
            # We can pick a specific one or the best one
            # For simplicity, we take the first available
            for bm in bookmakers:
                market = next((m for m in bm.get("markets", []) if m["key"] == "h2h"), None)
                if market:
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome["name"]
                        price = outcome["price"]
                        if name == odds_item["home_team"]:
                            home_odds = price
                        elif name == odds_item["away_team"]:
                            away_odds = price
                        else:
                            draw_odds = price
                    break

        return Match(
            id=odds_item.get("id", ""),
            home_team=Team(id="", name=odds_item.get("home_team", "Unknown")),
            away_team=Team(id="", name=odds_item.get("away_team", "Unknown")),
            league=League(id=league_code, name=odds_item.get("sport_title", "Unknown")),
            match_date=match_date,
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            status="NS" # Not Started
        )
