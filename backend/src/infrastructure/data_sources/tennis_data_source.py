import logging
from io import StringIO

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class TennisDataSource:
    """
    Data source for tennis match data from Jeff Sackmann's GitHub repositories.
    """

    ATP_BASE_URL = (
        "https://raw.githubusercontent.com/jegqwll/tennis_atp_2000_2025/main/"
    )
    WTA_BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/"

    def __init__(self, tour: str = "atp"):
        """
        Initialize the data source.

        Args:
            tour: 'atp' or 'wta'
        """
        if tour not in ["atp", "wta"]:
            raise ValueError("Tour must be 'atp' or 'wta'")

        self.tour = tour
        self.base_url = self.ATP_BASE_URL if tour == "atp" else self.WTA_BASE_URL

    def fetch_matches_by_year(self, year: int) -> pd.DataFrame:
        """
        Fetch match data for a specific year.

        Args:
            year: The year to fetch data for (e.g., 2023).

        Returns:
            DataFrame containing match data.
        """
        filename = f"{self.tour}_matches_{year}.csv"
        url = f"{self.base_url}{filename}"

        try:
            logger.info(f"Fetching {url}")
            response = httpx.get(url, follow_redirects=True)
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))
            logger.info(f"Loaded {len(df)} matches for {year}")
            return df
        except Exception as e:
            logger.error(f"Failed to fetch data for {year}: {e}")
            return pd.DataFrame()

    def fetch_matches_range(self, start_year: int, end_year: int) -> pd.DataFrame:
        """
        Fetch match data for a range of years.

        Args:
            start_year: Start year (inclusive).
            end_year: End year (inclusive).

        Returns:
            DataFrame containing combined match data.
        """
        dfs = []
        for year in range(start_year, end_year + 1):
            df = self.fetch_matches_by_year(year)
            if not df.empty:
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        return pd.concat(dfs, ignore_index=True)

    def fetch_combined_data(self) -> pd.DataFrame:
        """Fetch the pre-computed combined CSV (2000-2025)."""
        url = f"{self.base_url}{self.tour}_matches_combined.csv"
        try:
            logger.info(f"Fetching combined data from {url}")
            response = httpx.get(url, follow_redirects=True)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            logger.info(f"Loaded {len(df)} combined matches")
            return df
        except Exception as e:
            logger.warning(
                f"Combined CSV not available: {e}. Falling back to range fetch."
            )
            return pd.DataFrame()

    def fetch_latest_matches(self, n_matches: int = 100) -> pd.DataFrame:
        """
        Fetch the most recent matches from the current year and potentially last year.

        Args:
            n_matches: Approximate number of matches to fetch.

        Returns:
            DataFrame containing recent matches.
        """
        from datetime import datetime

        current_year = datetime.now().year

        # Try current year first
        df = self.fetch_matches_by_year(current_year)

        # If not enough, fetch previous year
        if len(df) < n_matches:
            prev_df = self.fetch_matches_by_year(current_year - 1)
            if not prev_df.empty:
                df = pd.concat([prev_df, df], ignore_index=True)

        # Sort by date descending and take top N
        if not df.empty and "tourney_date" in df.columns:
            df["tourney_date"] = pd.to_datetime(
                df["tourney_date"], format="%Y%m%d", errors="coerce"
            )
            df = df.sort_values("tourney_date", ascending=False).head(n_matches)

        return df
