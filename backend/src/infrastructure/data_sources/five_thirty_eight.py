"""
FiveThirtyEight SPI Data Source

Provides historical Soccer Power Index (SPI) data for teams and matches.
Data Source: https://github.com/fivethirtyeight/data/tree/master/soccer-spi
"""

import logging
import pandas as pd
from io import StringIO
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)

class FiveThirtyEightSource:
    """
    Data source for FiveThirtyEight SPI data.
    """
    
    SOURCE_NAME = "FiveThirtyEight"
    CSV_URL = "https://projects.fivethirtyeight.com/soccer-api/club/spi_matches.csv"
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=60.0)
        self._df = None

    async def _download_data(self):
        """
        Downloads the latest SPI matches CSV.
        """
        if self._df is not None:
            return
            
        try:
            logger.info("Downloading FiveThirtyEight SPI data...")
            response = await self._client.get(self.CSV_URL)
            response.raise_for_status()
            
            # Use StringIO and pandas to parse
            self._df = pd.read_csv(StringIO(response.text))
            logger.info(f"Successfully loaded {len(self._df)} matches from FiveThirtyEight")
        except Exception as e:
            logger.error(f"Failed to download FiveThirtyEight data: {e}")
            raise

    async def get_team_spi(self, team_name: str) -> Optional[float]:
        """
        Get the latest SPI for a team.
        """
        await self._download_data()
        if self._df is None:
            return None
            
        # Filter for the team (fuzzy match might be needed)
        from src.domain.services.statistics_service import StatisticsService
        stats_service = StatisticsService()
        
        team_norm = stats_service._normalize_name(team_name)
        
        # We look for the latest occurrence of the team
        # The CSV has columns: team1, team2, spi1, spi2, etc.
        # We need to check both team1 and team2
        team1_matches = self._df[self._df['team1'].apply(lambda x: stats_service._normalize_name(str(x)) == team_norm)]
        team2_matches = self._df[self._df['team2'].apply(lambda x: stats_service._normalize_name(str(x)) == team_norm)]
        
        latest_spi = None
        latest_date = None
        
        if not team1_matches.empty:
            last_row = team1_matches.iloc[-1]
            latest_spi = last_row['spi1']
            latest_date = last_row['date']
            
        if not team2_matches.empty:
            last_row = team2_matches.iloc[-1]
            if latest_date is None or last_row['date'] > latest_date:
                latest_spi = last_row['spi2']
                
        return float(latest_spi) if latest_spi is not None else None
