"""
BDFutbol Data Source

This module integrates with BDFutbol API v2.0 (api.bdfutbol.com) for
historical Spanish and European football data.

API Documentation: https://api.bdfutbol.com/
Uses HTTP Basic Auth with username and password from BDFutbol account.

Supported leagues:
- 1a: Primera División (La Liga)
- 2a: Segunda División
- eng: Premier League
- ger: Bundesliga
- ita: Serie A
- fra: Ligue 1
- por: Primeira Liga
- hol: Eredivisie
- bra: Brasilerao
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import httpx

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)


@dataclass
class BDFutbolConfig:
    """Configuration for BDFutbol API."""
    username: Optional[str] = None
    password: Optional[str] = None
    base_url: str = "http://api.bdfutbol.com/v2"
    timeout: int = 30
    
    def __post_init__(self):
        if self.username is None:
            self.username = os.getenv("BDFUTBOL_USERNAME")
        if self.password is None:
            self.password = os.getenv("BDFUTBOL_PASSWORD")


# Mapping of our internal league codes to BDFutbol category codes
BDFUTBOL_CATEGORY_MAPPING = {
    "E0": "eng",   # Premier League
    "SP1": "1a",   # La Liga
    "SP2": "2a",   # Segunda División
    "D1": "ger",   # Bundesliga
    "I1": "ita",   # Serie A
    "F1": "fra",   # Ligue 1
    "P1": "por",   # Primeira Liga
    "N1": "hol",   # Eredivisie
}

# Reverse mapping for league names
CATEGORY_TO_NAME = {
    "1a": "La Liga",
    "2a": "Segunda División",
    "eng": "Premier League",
    "ger": "Bundesliga",
    "ita": "Serie A",
    "fra": "Ligue 1",
    "por": "Primeira Liga",
    "hol": "Eredivisie",
    "bra": "Brasilerao",
}


class BDFutbolSource:
    """
    Data source for BDFutbol API v2.0.
    
    Provides historical data for Spanish and major European leagues.
    Requires BDFutbol account credentials.
    """
    
    SOURCE_NAME = "BDFutbol"
    
    def __init__(self, config: Optional[BDFutbolConfig] = None):
        self.config = config or BDFutbolConfig()
    
    @property
    def is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.config.username and self.config.password)
    
    async def _make_request(
        self,
        params: dict,
    ) -> Optional[dict]:
        """Make authenticated request to BDFutbol API."""
        if not self.is_configured:
            logger.debug("BDFutbol not configured (no credentials)")
            return None
        
        auth = (self.config.username, self.config.password)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.config.base_url,
                    params=params,
                    auth=auth,
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                data = response.json()
                
                # Check API status
                if data.get("status") != 1:
                    error_msg = data.get("text", "Unknown error")
                    logger.warning(f"BDFutbol API error: {error_msg}")
                    return None
                
                return data
                
        except httpx.HTTPStatusError as e:
            logger.error(f"BDFutbol HTTP error: {e}")
            return None
        except Exception as e:
            logger.error(f"BDFutbol request error: {e}")
            return None
    
    async def get_season_results(
        self,
        category: str,
        season: str,
    ) -> List[Match]:
        """
        Get all results for a season.
        
        Args:
            category: BDFutbol category code ('1a', '2a', 'eng', etc.)
            season: Season format 'yyyy-yy' (e.g., '2024-25')
            
        Returns:
            List of Match entities with results
        """
        params = {
            "tip": "res",
            "cat": category,
            "temp": season,
        }
        
        data = await self._make_request(params)
        
        if not data:
            return []
        
        matches = []
        for match_data in data.get("result", []):
            try:
                match = self._parse_match(match_data, category)
                if match and match.home_goals is not None:
                    matches.append(match)
            except Exception as e:
                logger.debug(f"Error parsing BDFutbol match: {e}")
                continue
        
        logger.info(f"BDFutbol: fetched {len(matches)} matches for {category} {season}")
        return matches
    
    async def get_finished_matches(
        self,
        league_codes: Optional[List[str]] = None,
        seasons: Optional[List[str]] = None,
    ) -> List[Match]:
        """
        Get finished matches from BDFutbol for specified leagues.
        
        Args:
            league_codes: List of our internal league codes (e.g., ["SP1", "E0"])
            seasons: List of seasons to fetch (e.g., ["2024-25", "2023-24"])
            
        Returns:
            List of finished Match entities
        """
        if not self.is_configured:
            logger.debug("BDFutbol not configured, skipping")
            return []
        
        all_matches = []
        leagues_to_fetch = league_codes or ["SP1", "SP2"]  # Default: Spanish leagues
        seasons_to_fetch = seasons or ["2024-25", "2023-24"]
        
        for league_code in leagues_to_fetch:
            category = BDFUTBOL_CATEGORY_MAPPING.get(league_code)
            if not category:
                continue
                
            for season in seasons_to_fetch:
                matches = await self.get_season_results(category, season)
                all_matches.extend(matches)
        
        return all_matches
    
    async def get_standings(
        self,
        category: str,
        season: str,
    ) -> Optional[dict]:
        """
        Get standings for a season.
        
        Args:
            category: BDFutbol category code
            season: Season format 'yyyy-yy'
            
        Returns:
            Standings data
        """
        params = {
            "tip": "cla",
            "cat": category,
            "temp": season,
        }
        
        data = await self._make_request(params)
        return data.get("result") if data else None
    
    def _parse_match(self, match_data: dict, category: str) -> Optional[Match]:
        """Parse BDFutbol match data into Match entity."""
        try:
            # Parse date (format: dd/mm/yyyy)
            fecha_str = match_data.get("fecha")
            if fecha_str:
                try:
                    match_date = datetime.strptime(fecha_str, "%d/%m/%Y")
                except ValueError:
                    match_date = datetime.utcnow()
            else:
                match_date = datetime.utcnow()
            
            # Map category to league code
            league_code = None
            for code, cat in BDFUTBOL_CATEGORY_MAPPING.items():
                if cat == category:
                    league_code = code
                    break
            league_code = league_code or category.upper()
            
            # Create teams
            home_team = Team(
                id=str(match_data.get("id_local", "")),
                name=match_data.get("nombre_local", "Unknown"),
            )
            away_team = Team(
                id=str(match_data.get("id_visitante", "")),
                name=match_data.get("nombre_visitante", "Unknown"),
            )
            
            # Create league
            league_name = CATEGORY_TO_NAME.get(category, category)
            league = League(
                id=league_code,
                name=league_name,
                country="Spain" if category in ["1a", "2a"] else "Europe",
            )
            
            # Get goals
            home_goals = match_data.get("goles_local")
            away_goals = match_data.get("goles_visitante")
            
            return Match(
                id=str(match_data.get("id_partido", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=int(home_goals) if home_goals is not None else None,
                away_goals=int(away_goals) if away_goals is not None else None,
                status="FT" if home_goals is not None else "NS",
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse BDFutbol match: {e}")
            return None
