"""
Football-Data.co.uk Data Source

This module handles downloading and parsing CSV data from Football-Data.co.uk.
The site provides free historical football data including results and betting odds.

Data Source: https://www.football-data.co.uk/
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Any, Callable
from dataclasses import dataclass
import logging
import functools

import httpx
from io import StringIO

from src.domain.entities.entities import Match, Team, League, TeamStatistics
from src.domain.constants import LEAGUES_METADATA
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.team_service import TeamService


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


    # International (Europe & Americas)
    "UCL": "international/champions-league",   # Champions League
    "UEL": "international/europa-league",      # Europa League
    "UECL": "international/conference-league", # Conference League
    "EURO": "international/euro-championship", # Euro Championship
    "LIB": "international/libertadores",       # Copa Libertadores (Placeholder)
    "SUD": "international/sudamericana",       # Copa Sudamericana (Placeholder)
}





def retry_async(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator for async functions.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    if i == retries - 1:
                        logger.error(f"Failed {func.__name__} after {retries} retries: {e}")
                        raise
                    logger.warning(f"Retry {i+1}/{retries} for {func.__name__} due to {e}. Waiting {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    # Non-retriable exception
                    logger.error(f"Non-retriable error in {func.__name__}: {e}")
                    raise
            return None
        return wrapper
    return decorator


class FootballDataUKSource:
    """
    Data source for Football-Data.co.uk.
    
    Provides access to historical match results and betting odds.
    """
    
    SOURCE_NAME = "Football-Data.co.uk"
    
    # Whitelist of league codes known to provide valid .csv files at /mmz4281/{season}/{code}.csv
    # Excludes Cups (UCL, UEL) and unsupported partial leagues (P2, etc.) to prevent 404s/Redirects.
    SUPPORTED_LEAGUES = {
        "E0", "E1", "E2", "E3",  # England
        "SP1", "SP2",            # Spain
        "D1", "D2",              # Germany
        "I1", "I2",              # Italy
        "F1", "F2",              # France
        "N1",                    # Netherlands (N2 often missing)
        "B1",                    # Belgium (B2 often missing)
        "P1",                    # Portugal (P2 redirects to SP2 - Invalid)
        "SC0", "SC1",            # Scotland (Prem, Div 1) - Optional, adding just in case
        "T1",                    # Turkey
        "G1",                    # Greece
    }
    
    def __init__(self, config: Optional[FootballDataConfig] = None):
        """Initialize the data source."""
        self.config = config or FootballDataConfig()
        self._cache: dict[str, tuple[Any, datetime]] = {}  # Any instead of pd.DataFrame for lazy import
    
    def _get_csv_url(self, league_code: str, season: str) -> str:
        """
        Construct CSV URL for a league and season.
        """
        # Football-Data.co.uk URL pattern: /mmz4281/{season}/{league_code}.csv
        return f"{self.config.base_url}/mmz4281/{season}/{league_code}.csv"

    def _get_current_season(self, date: Optional[datetime] = None) -> str:
        """
        Calculate the current football-data.co.uk season code.
        Format: "2425" for 2024-2025.
        Season changes in August.
        """
        if date is None:
            date = datetime.now()
            
        year = date.year
        if date.month >= 8:
            # August to December: current year + next year
            start = year % 100
            end = (year + 1) % 100
        else:
            # January to July: previous year + current year
            start = (year - 1) % 100
            end = year % 100
            
        return f"{start:02d}{end:02d}"

    @retry_async(retries=3, delay=1.0)
    async def download_csv(
        self,
        league_code: str,
        season: str,
        force_refresh: bool = False,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Optional[tuple[Any, datetime]]:
        """
        Download and parse CSV data for a league.
        
        Args:
            league_code: League code
            season: Season code (e.g., "2324")
            force_refresh: If True, ignore cache and re-download
            client: Optional httpx client to reuse
            
        Returns:
            Tuple of (DataFrame, timestamp) or None if failed
        """
        try:
            # Lazy import pandas (only when actually downloading data)
            import pandas as pd
        except ImportError:
            # Handle API-ONLY mode (no pandas installed)
            import os
            if os.getenv("API_ONLY_MODE", "false").lower() == "true":
                logger.warning(f"Skipping CSV download for {league_code} (Pandas not available in API-ONLY mode).")
                return None
            else:
                raise ImportError("Pandas is required for CSV processing but is not installed.")
        
        cache_key = f"{league_code}_{season}"
        
        if not force_refresh and cache_key in self._cache:
            return self._cache[cache_key]
        
        url = self._get_csv_url(league_code, season)
        
        try:
            if client:
                response = await client.get(url, timeout=self.config.timeout)
            else:
                async with httpx.AsyncClient() as new_client:
                    response = await new_client.get(url, timeout=self.config.timeout)

            response.raise_for_status()
            
            if not response.text or len(response.text.strip()) < 10:
                logger.warning(f"Empty or malformed response from {url}")
                return None
                
            # Parse CSV (CPU-bound, offload to thread)
            loop = asyncio.get_running_loop()
            df = await loop.run_in_executor(
                None, 
                lambda: pd.read_csv(
                    StringIO(response.text),
                    encoding='utf-8',
                    on_bad_lines='skip',
                )
            )
            
            # Basic cleanup
            df.columns = [c.strip() for c in df.columns]
            df = df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam'], how='any')
            
            now = datetime.now(timezone.utc)
            self._cache[cache_key] = (df, now)
            
            # Diagnostic Log: Check latest date in CSV
            latest_date = "Unknown"
            if 'Date' in df.columns and not df.empty:
                try:
                    latest_date = df['Date'].iloc[-1]
                except: pass
            
            logger.info(f"Downloaded {len(df)} matches from {url}. Latest match date in CSV: {latest_date}")
            return (df, now)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"CSV not found (404) for {url}. This season might not be available yet.")
                return None
            raise # Let retry decorator handle other status codes
        except Exception as e:
            logger.error(f"Error processing CSV from {url}: {e}")
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
        df: Any,  # DataFrame, but using Any for lazy import
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
        # Lazy import pandas
        import pandas as pd
        
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
                home_team_name = str(row['HomeTeam'])
                away_team_name = str(row['AwayTeam'])

                home_team = Team(
                    id=home_team_name.lower().replace(" ", "_"),
                    name=home_team_name,
                    country=league.country,
                    logo_url=TeamService.get_team_logo(home_team_name)
                )
                
                away_team = Team(
                    id=away_team_name.lower().replace(" ", "_"),
                    name=away_team_name,
                    country=league.country,
                    logo_url=TeamService.get_team_logo(away_team_name)
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

                # EXTENDED STATS (Shots, Target, Fouls)
                # HS = Home Shots, AS = Away Shots
                home_shots = int(row['HS']) if 'HS' in row and pd.notna(row['HS']) else None
                away_shots = int(row['AS']) if 'AS' in row and pd.notna(row['AS']) else None

                # HST = Home Shots on Target, AST = Away Shots on Target
                home_shots_on_target = int(row['HST']) if 'HST' in row and pd.notna(row['HST']) else None
                away_shots_on_target = int(row['AST']) if 'AST' in row and pd.notna(row['AST']) else None

                # HF = Home Fouls, AF = Away Fouls
                home_fouls = int(row['HF']) if 'HF' in row and pd.notna(row['HF']) else None
                away_fouls = int(row['AF']) if 'AF' in row and pd.notna(row['AF']) else None

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
                    home_total_shots=home_shots,
                    away_total_shots=away_shots,
                    home_shots_on_target=home_shots_on_target,
                    away_shots_on_target=away_shots_on_target,
                    home_fouls=home_fouls,
                    away_fouls=away_fouls,
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
        force_refresh: bool = False,
    ) -> list[Match]:
        """
        Get historical matches for a league.
        
        Args:
            league_code: League code (e.g., "E0")
            seasons: List of season codes or None for current season
            force_refresh: Whether to force re-download of data
            
        Returns:
            List of Match entities
        """
        if seasons is None:
            # Dynamic season calculation with fallback
            current_season = self._get_current_season()
            
            # Previous season calculation
            try:
                # Format is "2425" -> 2024
                start_year = int(current_season[:2])
                prev_start = (start_year - 1) % 100
                prev_season = f"{prev_start:02d}{start_year:02d}"
                seasons = [current_season, prev_season]
            except Exception:
                seasons = [current_season, "2324"]
                
            logger.info(f"Targeting seasons for {league_code}: {seasons}")
        
        if league_code not in LEAGUES_METADATA:
            logger.warning(f"Unknown league code: {league_code}")
            return []
            
        # Check if this source supports this league
        if league_code not in self.SUPPORTED_LEAGUES:
            # Silent return or debug to avoid spamming warnings for expected unsupported leagues (like Cups)
            logger.debug(f"Skipping {league_code}: Not in Football-Data.co.uk supported whitelist")
            return []
        
        meta = LEAGUES_METADATA[league_code]
        league = League(
            id=league_code,
            name=meta["name"],
            country=meta["country"],
            season=seasons[0] if seasons else None,
        )
        
        all_matches = []
        
        # Use a shared client for all requests to improve performance
        async with httpx.AsyncClient() as client:
            tasks = [self.download_csv(league_code, season, force_refresh=force_refresh, client=client) for season in seasons]
            results = await asyncio.gather(*tasks)

        has_current_data = False
        
        for i, result in enumerate(results):
            season_code = seasons[i]
            if result is not None:
                df, timestamp = result
                if not df.empty:
                    matches = self.parse_matches(df, league, timestamp)
                    all_matches.extend(matches)
                    if i == 0: # Current season
                        has_current_data = True
                        logger.info(f"Successfully loaded {len(matches)} matches for {league_code} season {season_code}")
            else:
                if i == 0:
                    logger.warning(f"Failed to load current season ({season_code}) for {league_code}. Falling back to historical data only.")
        
        if not all_matches:
            logger.error(f"No matches found for {league_code} in seasons {seasons}")
            
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
            if code in self.SUPPORTED_LEAGUES:
                leagues.append(League(
                    id=code,
                    name=meta["name"],
                    country=meta["country"],
                ))
        return leagues
