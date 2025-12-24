"""
Football Prediction API Data Source

This module integrates with the Football Prediction API (RapidAPI) for
predictions and historical results.

API: https://football-prediction-api.p.rapidapi.com
Requires RapidAPI key.

Available markets:
- classic: Match result (1/X/2)
- over_25: Over 2.5 goals
- over_35: Over 3.5 goals
- btts: Both teams to score
- home_over_05/15: Home team goals
- away_over_05/15: Away team goals
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)


@dataclass
class FootballPredictionAPIConfig:
    """Configuration for Football Prediction API."""
    api_key: Optional[str] = None
    base_url: str = "https://football-prediction-api.p.rapidapi.com/api/v2"
    host: str = "football-prediction-api.p.rapidapi.com"
    timeout: int = 30
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.getenv("RAPIDAPI_KEY") or os.getenv("FOOTBALL_PREDICTION_API_KEY")


class FootballPredictionAPISource:
    """
    Data source for Football Prediction API.
    
    Provides:
    - Match predictions with odds
    - Past results and performance stats
    """
    
    SOURCE_NAME = "FootballPredictionAPI"
    
    def __init__(self, config: Optional[FootballPredictionAPIConfig] = None):
        self.config = config or FootballPredictionAPIConfig()
    
    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)
    
    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make authenticated request to Football Prediction API."""
        if not self.is_configured:
            logger.debug("Football Prediction API not configured (no API key)")
            return None
        
        url = f"{self.config.base_url}/{endpoint}"
        headers = {
            "X-RapidAPI-Key": self.config.api_key,
            "X-RapidAPI-Host": self.config.host,
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
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Football Prediction API HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"Football Prediction API request error: {e}")
            return None
    
    async def get_available_markets(self) -> List[str]:
        """Get list of available prediction markets."""
        data = await self._make_request("list-markets")
        
        if not data or "data" not in data:
            return []
        
        return data["data"].get("allowed_for_your_subscription", [])
    
    async def get_predictions(
        self,
        iso_date: Optional[str] = None,
        federation: str = "UEFA",
        market: str = "classic",
    ) -> List[Dict[str, Any]]:
        """
        Get predictions for matches.
        
        Args:
            iso_date: Date in ISO format (YYYY-MM-DD), defaults to today
            federation: Federation filter (UEFA, CONMEBOL, etc.)
            market: Prediction market (classic, over_25, btts, etc.)
            
        Returns:
            List of prediction data
        """
        if iso_date is None:
            iso_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        params = {
            "iso_date": iso_date,
            "federation": federation,
            "market": market,
        }
        
        data = await self._make_request("predictions", params)
        
        if not data or "data" not in data:
            return []
        
        return data["data"]
    
    async def get_past_predictions(
        self,
        iso_date: Optional[str] = None,
        federation: str = "UEFA",
        market: str = "classic",
    ) -> List[Dict[str, Any]]:
        """
        Get past predictions with results for performance analysis.
        
        Args:
            iso_date: Date in ISO format
            federation: Federation filter
            market: Prediction market
            
        Returns:
            List of past prediction data with results
        """
        if iso_date is None:
            # Get yesterday's results
            yesterday = datetime.utcnow() - timedelta(days=1)
            iso_date = yesterday.strftime("%Y-%m-%d")
        
        params = {
            "iso_date": iso_date,
            "federation": federation,
            "market": market,
        }
        
        # This endpoint returns predictions with actual results
        data = await self._make_request("predictions", params)
        
        if not data or "data" not in data:
            return []
        
        # Filter only matches with results
        results = []
        for match in data["data"]:
            if match.get("result") is not None or match.get("status") == "finished":
                results.append(match)
        
        return results
    
    async def get_finished_matches(
        self,
        days_back: int = 7,
        federation: str = "UEFA",
    ) -> List[Match]:
        """
        Get finished matches for training.
        
        Args:
            days_back: Number of days to look back
            federation: Federation filter
            
        Returns:
            List of finished Match entities
        """
        if not self.is_configured:
            logger.debug("Football Prediction API not configured, skipping")
            return []
        
        all_matches = []
        
        for i in range(1, days_back + 1):
            date = datetime.utcnow() - timedelta(days=i)
            iso_date = date.strftime("%Y-%m-%d")
            
            predictions = await self.get_past_predictions(iso_date, federation)
            
            for pred in predictions:
                try:
                    match = self._parse_prediction_to_match(pred)
                    if match and match.home_goals is not None:
                        all_matches.append(match)
                except Exception as e:
                    logger.debug(f"Error parsing prediction: {e}")
                    continue
        
        logger.info(f"Football Prediction API: fetched {len(all_matches)} finished matches")
        return all_matches
    
    def _parse_prediction_to_match(self, pred_data: dict) -> Optional[Match]:
        """Parse prediction API data into Match entity."""
        try:
            # Parse date
            start_date = pred_data.get("start_date")
            if start_date:
                try:
                    match_date = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    match_date = datetime.utcnow()
            else:
                match_date = datetime.utcnow()
            
            # Get result
            result = pred_data.get("result")
            home_goals = None
            away_goals = None
            
            if result and "-" in str(result):
                parts = str(result).split("-")
                if len(parts) == 2:
                    try:
                        home_goals = int(parts[0].strip())
                        away_goals = int(parts[1].strip())
                    except ValueError:
                        pass
            
            # Create teams
            home_team = Team(
                id=str(pred_data.get("id", "")),
                name=pred_data.get("home_team", "Unknown"),
            )
            away_team = Team(
                id=str(pred_data.get("id", "")),
                name=pred_data.get("away_team", "Unknown"),
            )
            
            # Create league
            competition = pred_data.get("competition_name", "Unknown")
            country = pred_data.get("competition_cluster", "Europe")
            
            league = League(
                id=pred_data.get("competition_name", "UNKNOWN"),
                name=competition,
                country=country,
            )
            
            return Match(
                id=str(pred_data.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
                status="FT" if home_goals is not None else "NS",
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse prediction match: {e}")
            return None
    
    async def get_prediction_for_match(
        self,
        home_team: str,
        away_team: str,
        match_date: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get prediction for a specific match.
        
        Args:
            home_team: Home team name
            away_team: Away team name
            match_date: Match date in ISO format
            
        Returns:
            Prediction data if found
        """
        predictions = await self.get_predictions(match_date)
        
        for pred in predictions:
            if (pred.get("home_team", "").lower() == home_team.lower() and
                pred.get("away_team", "").lower() == away_team.lower()):
                return pred
        
        return None
