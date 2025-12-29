"""
Football-Data.co.uk Data Source

This module handles downloading and parsing CSV data from Football-Data.co.uk.
The site provides free historical football data including results and betting odds.

Data Source: https://www.football-data.co.uk/
"""

import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
import logging

import httpx
import pandas as pd
from io import StringIO

from src.domain.entities.entities import Match, Team, League, TeamStatistics
from src.domain.constants import LEAGUES_METADATA
from src.domain.services.statistics_service import StatisticsService


logger = logging.getLogger(__name__)


@dataclass
class FootballDataConfig:
    """Configuration for Football-Data.co.uk data source."""
    base_url: str = "https://www.football-data.co.uk"
    timeout: int = 30


# Mapping of league codes to Football-Data.co.uk CSV paths
LEAGUE_CSV_PATHS = {
    # England
    "E0": "england/premier-league",    # Premier League
    "E1": "england/championship",       # Championship
    "E_FA": "england/fa-cup",           # FA Cup (Placeholder)
    "E2": "england/league-one",         # League One
    "E3": "england/league-two",         # League Two
    
    # Spain
    "SP1": "spain/la-liga",             # La Liga
    "SP2": "spain/segunda",             # Segunda Division
    "SP_C": "spain/copa-del-rey",       # Copa del Rey (Placeholder)
    
    # Germany
    "D1": "germany/bundesliga",         # Bundesliga
    "D2": "germany/bundesliga-2",       # 2. Bundesliga
    
    # Italy
    "I1": "italy/serie-a",              # Serie A
    "I2": "italy/serie-b",              # Serie B
    
    # France
    "F1": "france/ligue-1",             # Ligue 1
    "F2": "france/ligue-2",             # Ligue 2
    
    # Netherlands
    "N1": "netherlands/eredivisie",     # Eredivisie
    "N2": "netherlands/eerste-divisie", # Eerste Divisie (Placeholder)
    
    # Belgium
    "B1": "belgium/jupiler-league",     # Jupiler Pro League
    "B2": "belgium/challenger-pro",     # Challenger Pro League (Placeholder)
    
    # Portugal
    "P1": "portugal/primeira-liga",     # Primeira Liga
    "P2": "portugal/liga-portugal-2",   # Liga Portugal 2 (Placeholder)
    
    # Turkey
    "T1": "turkey/super-lig",           # Super Lig
    "T2": "turkey/1-lig",               # 1. Lig (Placeholder)
    
    # Greece
    "G1": "greece/super-league",        # Super League
    "G2": "greece/super-league-2",      # Super League 2 (Placeholder)

    # Scotland
    "SC0": "scotland/premiership",      # Premiership
    "SC1": "scotland/championship",     # Championship

    # International (Europe & Americas)
    "UCL": "international/champions-league",   # Champions League
    "UEL": "international/europa-league",      # Europa League
    "UECL": "international/conference-league", # Conference League
    "EURO": "international/euro-championship", # Euro Championship
    "LIB": "international/libertadores",       # Copa Libertadores (Placeholder)
    "SUD": "international/sudamericana",       # Copa Sudamericana (Placeholder)
}




class FootballDataUKSource:
    """
    Data source for Football-Data.co.uk.
    
    Provides access to historical match results and betting odds.
    """
    
    SOURCE_NAME = "Football-Data.co.uk"
    
    def __init__(self, config: Optional[FootballDataConfig] = None):
        """Initialize the data source."""
        self.config = config or FootballDataConfig()
        self._cache: dict[str, tuple[pd.DataFrame, datetime]] = {}
    
    def _get_csv_url(self, league_code: str, season: str) -> str:
        """
        Construct CSV URL for a league and season.
        
        Args:
            league_code: League code (e.g., "E0" for Premier League)
            season: Season in format "2324" for 2023-2024
            
        Returns:
            Full URL to the CSV file
        """
        # Football-Data.co.uk URL pattern: /mmz4281/{season}/{league_code}.csv
        return f"{self.config.base_url}/mmz4281/{season}/{league_code}.csv"
    
    async def download_csv(
        self,
        league_code: str,
        season: str,
    ) -> Optional[tuple[pd.DataFrame, datetime]]:
        """
        Download and parse CSV data for a league.
        
        Args:
            league_code: League code
            season: Season code (e.g., "2324")
            
        Returns:
            Tuple of (DataFrame, timestamp) or None if failed
        """
        cache_key = f"{league_code}_{season}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        url = self._get_csv_url(league_code, season)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                
                # Parse CSV
                df = pd.read_csv(
                    StringIO(response.text),
                    encoding='utf-8',
                    on_bad_lines='skip',
                )
                
                now = datetime.utcnow()
                self._cache[cache_key] = (df, now)
                logger.info(f"Downloaded {len(df)} matches from {url}")
                return (df, now)
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error downloading {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from CSV format and localize to COLOMBIA_TZ."""
        from src.utils.time_utils import COLOMBIA_TZ
        formats = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return COLOMBIA_TZ.localize(dt)
            except (ValueError, TypeError):
                continue
        return None
    
    def parse_matches(
        self,
        df: pd.DataFrame,
        league: League,
        fetch_time: Optional[datetime] = None,
    ) -> list[Match]:
        """
        Parse DataFrame into Match entities.
        
        Args:
            df: DataFrame from CSV
            league: League entity
            fetch_time: Time when data was fetched
            
        Returns:
            List of Match entities
        """
        matches = []
        
        # Expected columns
        required_cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']
        
        if not all(col in df.columns for col in required_cols):
            logger.warning(f"Missing required columns in data. Available: {df.columns.tolist()}")
            return matches
        
        for idx, row in df.iterrows():
            try:
                # Parse date
                match_date = self._parse_date(str(row['Date']))
                if not match_date:
                    continue
                
                # Create teams
                home_team = Team(
                    id=f"{league.id}_{row['HomeTeam']}".replace(" ", "_").lower(),
                    name=str(row['HomeTeam']),
                    country=league.country,
                )
                away_team = Team(
                    id=f"{league.id}_{row['AwayTeam']}".replace(" ", "_").lower(),
                    name=str(row['AwayTeam']),
                    country=league.country,
                )
                
                # Get goals (handle NaN for unplayed matches)
                home_goals = int(row['FTHG']) if pd.notna(row.get('FTHG')) else None
                away_goals = int(row['FTAG']) if pd.notna(row.get('FTAG')) else None
                
                # Get betting odds (different bookmakers use different column names)
                home_odds = None
                draw_odds = None
                away_odds = None
                
                # Try common odds columns (B365 = Bet365, BW = Betway, etc.)
                odds_cols = [
                    ('B365H', 'B365D', 'B365A'),
                    ('BWH', 'BWD', 'BWA'),
                    ('IWH', 'IWD', 'IWA'),
                    ('PSH', 'PSD', 'PSA'),
                    ('WHH', 'WHD', 'WHA'),
                ]
                
                for h, d, a in odds_cols:
                    if h in row and pd.notna(row[h]):
                        home_odds = float(row[h])
                        draw_odds = float(row[d]) if pd.notna(row[d]) else None
                        away_odds = float(row[a]) if pd.notna(row[a]) else None
                        break
                
                # Parse Stats (Corners, Cards)
                # HC = Home Corners, AC = Away Corners
                home_corners = int(row['HC']) if 'HC' in row and pd.notna(row['HC']) else None
                away_corners = int(row['AC']) if 'AC' in row and pd.notna(row['AC']) else None
                
                # HY = Home Yellows, AY = Away Yellows
                home_yellow = int(row['HY']) if 'HY' in row and pd.notna(row['HY']) else None
                away_yellow = int(row['AY']) if 'AY' in row and pd.notna(row['AY']) else None
                
                # HR = Home Reds, AR = Away Reds
                home_red = int(row['HR']) if 'HR' in row and pd.notna(row['HR']) else None
                away_red = int(row['AR']) if 'AR' in row and pd.notna(row['AR']) else None

                match = Match(
                    id=f"{league.id}_{match_date.strftime('%Y%m%d')}_{home_team.id}_{away_team.id}",
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_date=match_date,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    home_odds=home_odds,
                    draw_odds=draw_odds,
                    away_odds=away_odds,
                    home_corners=home_corners,
                    away_corners=away_corners,
                    home_yellow_cards=home_yellow,
                    away_yellow_cards=away_yellow,
                    home_red_cards=home_red,
                    away_red_cards=away_red,
                    data_fetched_at=fetch_time,
                )
                matches.append(match)
                
            except Exception as e:
                logger.debug(f"Error parsing row {idx}: {e}")
                continue
        
        return matches
    
    async def get_historical_matches(
        self,
        league_code: str,
        seasons: Optional[list[str]] = None,
    ) -> list[Match]:
        """
        Get historical matches for a league.
        
        Args:
            league_code: League code (e.g., "E0")
            seasons: List of season codes or None for current season
            
        Returns:
            List of Match entities
        """
        if seasons is None:
            # Default to current and previous season
            seasons = ["2425", "2324"]
        
        if league_code not in LEAGUES_METADATA:
            logger.warning(f"Unknown league code: {league_code}")
            return []
        
        meta = LEAGUES_METADATA[league_code]
        league = League(
            id=league_code,
            name=meta["name"],
            country=meta["country"],
            season=seasons[0] if seasons else None,
        )
        
        all_matches = []
        tasks = [self.download_csv(league_code, season) for season in seasons]
        all_matches = []
        for result in await asyncio.gather(*tasks):
            if result is not None:
                df, timestamp = result
                matches = self.parse_matches(df, league, timestamp)
                all_matches.extend(matches)
        
        return all_matches
    
    def calculate_team_statistics(
        self,
        team_name: str,
        matches: list[Match],
    ) -> TeamStatistics:
        """
        Calculate statistics for a team from match history.
        Delegates to StatisticsService.
        """
        return StatisticsService.calculate_team_statistics(team_name, matches)
    
    def get_available_leagues(self) -> list[League]:
        """Get list of available leagues."""
        leagues = []
        for code, meta in LEAGUES_METADATA.items():
            leagues.append(League(
                id=code,
                name=meta["name"],
                country=meta["country"],
            ))
        return leagues
