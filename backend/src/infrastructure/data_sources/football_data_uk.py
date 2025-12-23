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

# League metadata
LEAGUES_METADATA = {
    "E0": {"name": "Premier League", "country": "England"},
    "E1": {"name": "Championship", "country": "England"},
    "E_FA": {"name": "FA Cup", "country": "England"},
    "SP1": {"name": "La Liga", "country": "Spain"},
    "SP2": {"name": "Segunda División", "country": "Spain"},
    "SP_C": {"name": "Copa del Rey", "country": "Spain"},
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
    "UCL": {"name": "Champions League", "country": "International"},
    "UEL": {"name": "Europa League", "country": "International"},
    "UECL": {"name": "Conference League", "country": "International"},
    "EURO": {"name": "Euro Championship", "country": "International"},
    "LIB": {"name": "Copa Libertadores", "country": "International"},
    "SUD": {"name": "Copa Sudamericana", "country": "International"},
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
    
    def _normalize_name(self, name: str) -> str:
        """Normalize team name for comparison."""
        # Remove common prefixes/suffixes
        remove = ["fc", "cf", "as", "sc", "ac", "inter", "real", "sporting", "club", "de", "le", "la"]
        
        cleaned = name.lower()
        for word in remove:
            # Remove isolated occurrences
            cleaned = cleaned.replace(f" {word} ", " ")
            if cleaned.startswith(f"{word} "):
                cleaned = cleaned[len(word)+1:]
            if cleaned.endswith(f" {word}"):
                cleaned = cleaned[:-len(word)-1]
                
        return cleaned.strip().replace(" ", "")

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
        
        # New stats for picks
        total_corners = 0
        total_yellow_cards = 0
        total_red_cards = 0
        
        recent_results = []
        
        target_norm = self._normalize_name(team_name)
        
        for match in matches:
            if not match.is_played:
                continue
            
            home_norm = self._normalize_name(match.home_team.name)
            away_norm = self._normalize_name(match.away_team.name)
            
            # Check for match (exact normalized or containment if substantial)
            is_home = target_norm == home_norm or (len(target_norm) > 3 and target_norm in home_norm) or (len(home_norm) > 3 and home_norm in target_norm)
            is_away = target_norm == away_norm or (len(target_norm) > 3 and target_norm in away_norm) or (len(away_norm) > 3 and away_norm in target_norm)
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            
            # Get stats based on role
            goals_for = match.home_goals if is_home else match.away_goals
            goals_against = match.away_goals if is_home else match.home_goals
            
            # Robustly handle None goals
            if goals_for is None or goals_against is None:
                continue
                
            goals_scored += goals_for
            goals_conceded += goals_against
            
            if goals_for > goals_against:
                wins += 1
                if is_home:
                    home_wins += 1
                else:
                    away_wins += 1
                recent_results.append('W')
            elif goals_for < goals_against:
                losses += 1
                recent_results.append('L')
            else:
                draws += 1
                recent_results.append('D')
                
            # Accumulate corners/cards
            if match.home_corners is not None and match.away_corners is not None:
                total_corners += match.home_corners if is_home else match.away_corners
                
            # Accumulate cards
            y_cards = match.home_yellow_cards if is_home else match.away_yellow_cards
            r_cards = match.home_red_cards if is_home else match.away_red_cards
            
            if y_cards is not None:
                total_yellow_cards += y_cards
            if r_cards is not None:
                total_red_cards += r_cards
        
        # Get last 5 results for form
        recent_form = ''.join(recent_results[-5:]) if recent_results else ""
        
        # Calculate data freshness
        timestamps = [m.data_fetched_at for m in matches if hasattr(m, 'data_fetched_at') and m.data_fetched_at]
        last_updated = max(timestamps) if timestamps else None
        
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
            total_corners=total_corners,
            total_yellow_cards=total_yellow_cards,
            total_red_cards=total_red_cards,
            recent_form=recent_form,
            data_updated_at=last_updated,
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
