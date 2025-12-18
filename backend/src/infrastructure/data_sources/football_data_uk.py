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
    "E2": "england/league-one",         # League One
    "E3": "england/league-two",         # League Two
    
    # Spain
    "SP1": "spain/la-liga",             # La Liga
    "SP2": "spain/segunda",             # Segunda Division
    
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

    # Europe
    "UCL": "europe/champions-league",   # Champions League
    "UEL": "europe/europa-league",      # Europa League
    "UECL": "europe/conference-league", # Conference League
    "EURO": "europe/euro-championship", # Euro Championship
}

# League metadata
LEAGUES_METADATA = {
    "E0": {"name": "Premier League", "country": "England"},
    "E1": {"name": "Championship", "country": "England"},
    "SP1": {"name": "La Liga", "country": "Spain"},
    "SP2": {"name": "Segunda División", "country": "Spain"},
    "D1": {"name": "Bundesliga", "country": "Germany"},
    "D2": {"name": "2. Bundesliga", "country": "Germany"},
    "I1": {"name": "Serie A", "country": "Italy"},
    "I2": {"name": "Serie B", "country": "Italy"},
    "F1": {"name": "Ligue 1", "country": "France"},
    "F2": {"name": "Ligue 2", "country": "France"},
    "N1": {"name": "Eredivisie", "country": "Netherlands"},
    "N2": {"name": "Eerste Divisie", "country": "Netherlands"},
    "B1": {"name": "Jupiler Pro League", "country": "Belgium"},
    "B2": {"name": "Challenger Pro League", "country": "Belgium"},
    "P1": {"name": "Primeira Liga", "country": "Portugal"},
    "P2": {"name": "Liga Portugal 2", "country": "Portugal"},
    "T1": {"name": "Süper Lig", "country": "Turkey"},
    "T2": {"name": "1. Lig", "country": "Turkey"},
    "G1": {"name": "Super League", "country": "Greece"},
    "G2": {"name": "Super League 2", "country": "Greece"},
    "SC0": {"name": "Premiership", "country": "Scotland"},
    "SC1": {"name": "Championship", "country": "Scotland"},
    "UCL": {"name": "Champions League", "country": "Europe"},
    "UEL": {"name": "Europa League", "country": "Europe"},
    "UECL": {"name": "Conference League", "country": "Europe"},
    "EURO": {"name": "Euro Championship", "country": "Europe"},
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
        self._cache: dict[str, pd.DataFrame] = {}
    
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
    ) -> Optional[pd.DataFrame]:
        """
        Download and parse CSV data for a league.
        
        Args:
            league_code: League code
            season: Season code (e.g., "2324")
            
        Returns:
            DataFrame with match data or None if failed
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
                
                self._cache[cache_key] = df
                logger.info(f"Downloaded {len(df)} matches from {url}")
                return df
                
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error downloading {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date from CSV format."""
        formats = ["%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        return None
    
    def parse_matches(
        self,
        df: pd.DataFrame,
        league: League,
    ) -> list[Match]:
        """
        Parse DataFrame into Match entities.
        
        Args:
            df: DataFrame from CSV
            league: League entity
            
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
        for season in seasons:
            df = await self.download_csv(league_code, season)
            if df is not None:
                matches = self.parse_matches(df, league)
                all_matches.extend(matches)
        
        return all_matches
    
    def calculate_team_statistics(
        self,
        team_name: str,
        matches: list[Match],
    ) -> TeamStatistics:
        """
        Calculate statistics for a team from match history.
        
        Args:
            team_name: Team name
            matches: List of historical matches
            
        Returns:
            TeamStatistics for the team
        """
        team_id = None
        matches_played = 0
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        home_wins = 0
        away_wins = 0
        recent_results = []
        
        for match in matches:
            if not match.is_played:
                continue
            
            is_home = match.home_team.name.lower() == team_name.lower()
            is_away = match.away_team.name.lower() == team_name.lower()
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            
            if is_home:
                goals_scored += match.home_goals
                goals_conceded += match.away_goals
                
                if match.home_goals > match.away_goals:
                    wins += 1
                    home_wins += 1
                    recent_results.append('W')
                elif match.home_goals < match.away_goals:
                    losses += 1
                    recent_results.append('L')
                else:
                    draws += 1
                    recent_results.append('D')
            else:
                goals_scored += match.away_goals
                goals_conceded += match.home_goals
                
                if match.away_goals > match.home_goals:
                    wins += 1
                    away_wins += 1
                    recent_results.append('W')
                elif match.away_goals < match.home_goals:
                    losses += 1
                    recent_results.append('L')
                else:
                    draws += 1
                    recent_results.append('D')
        
        # Get last 5 results for form
        recent_form = ''.join(recent_results[-5:]) if recent_results else ""
        
        return TeamStatistics(
            team_id=team_id or team_name.lower().replace(" ", "_"),
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            home_wins=home_wins,
            away_wins=away_wins,
            recent_form=recent_form,
        )
    
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
