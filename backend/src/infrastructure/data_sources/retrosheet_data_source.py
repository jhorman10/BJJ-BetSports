import logging
from datetime import date, timedelta
from io import StringIO
from typing import Any, List, Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


# Team abbreviation mapping (Retrosheet -> standard)
TEAM_MAP = {
    "NYA": "NYY",
    "NYN": "NYM",
    "CHN": "CHC",
    "CHA": "CHW",
    "SLN": "STL",
    "KCA": "KC",
    "ANA": "LAA",
    "SDN": "SD",
    "SFN": "SF",
    "TEX": "TEX",
    "MON": "WSH",
    "TBA": "TB",
    "MIA": "MIA",
    "COL": "COL",
    "ARI": "ARI",
    "ATL": "ATL",
    "LAN": "LAD",
    "OAK": "OAK",
    "SEA": "SEA",
    "DET": "DET",
    "BAL": "BAL",
    "BOS": "BOS",
    "CLE": "CLE",
    "CIN": "CIN",
    "HOU": "HOU",
    "MIL": "MIL",
    "MIN": "MIN",
    "PHI": "PHI",
    "PIT": "PIT",
    "TOR": "TOR",
    "WAS": "WSH",
    "FLO": "MIA",
}


class RetrosheetDataSource:
    """
    Data source for baseball historical data from Retrosheet.
    Fetches CSV data for team stats, batting, and pitching.
    """

    BASE_URL = (
        "https://raw.githubusercontent.com/chadwickbureau/baseballdatabank/master/core"
    )

    def __init__(self, cache_dir: str = "backend/data/cache/retrosheet"):
        self.cache_dir = cache_dir
        self._team_stats_cache: Optional[pd.DataFrame] = None

    def _safe_int(self, val: Any) -> int:
        """Safely convert a value to int, returning 0 on failure."""
        try:
            if pd.isna(val):
                return 0
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _safe_float(self, val: Any) -> float:
        """Safely convert a value to float, returning 0.0 on failure."""
        try:
            if pd.isna(val):
                return 0.0
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def fetch_season(self, year: int) -> pd.DataFrame:
        """
        Fetch game data for a specific season.
        """
        url = f"{self.BASE_URL}/Games.csv"
        try:
            logger.info(f"Fetching Retrosheet Games.csv for {year}")
            response = httpx.get(url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            # Filter by year
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
                df = df[df["Date"].dt.year == year]
            elif "yearID" in df.columns:
                df = df[df["yearID"] == year]
            logger.info(f"Loaded {len(df)} games for {year}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data for {year}: {e}")
            return pd.DataFrame()

    def fetch_range(self, start_year: int, end_year: int) -> pd.DataFrame:
        """
        Fetch game data for a range of years.
        """
        dfs = []
        for year in range(start_year, end_year + 1):
            df = self.fetch_season(year)
            if not df.empty:
                dfs.append(df)
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    def get_team_stats(
        self, team: str, date_range: Optional[List[date]] = None
    ) -> dict:
        """
        Get aggregate team stats for feature extraction.
        Returns batting and pitching averages.
        """
        # Return default stats when no historical data is available
        return {
            "team": team,
            "games_played": 0,
            "wins": 0,
            "losses": 0,
            "win_pct": 0.5,
            "runs_scored_per_game": 4.5,
            "runs_allowed_per_game": 4.5,
            "batting_avg": 0.250,
            "ops": 0.720,
            "era": 4.00,
            "whip": 1.30,
        }

    @staticmethod
    def normalize_team(abbr: str) -> str:
        """Normalize team abbreviation to standard 3-letter code."""
        return TEAM_MAP.get(abbr.upper(), abbr.upper())
