import logging
from datetime import date, datetime
from io import StringIO
from typing import Any, Dict, List, Optional

import httpx
import pandas as pd

logger = logging.getLogger(__name__)


class TennisFixtureDataSource:
    """
    Fetches upcoming tennis match fixtures from free public sources.
    Uses flashscore/sportmonks-like data or falls back to demo fixtures.
    """

    # Free tennis fixture sources
    FIXTURE_SOURCES = [
        "https://raw.githubusercontent.com/JeffSackmann/tennis/master/",
    ]

    def __init__(self, tour: str = "atp"):
        self.tour = tour
        self.base_url = "https://raw.githubusercontent.com/JeffSackmann/tennis/master/"

    def fetch_upcoming_fixtures(self) -> List[Dict]:
        """
        Fetch upcoming tennis match fixtures.
        Returns a list of match dicts with tournament, players, surface, etc.
        """
        # Try to get current year's schedule
        current_year = datetime.now().year
        fixtures = []

        try:
            # Fetch current year data to find upcoming tournaments
            filename = f"{self.tour}_matches_{current_year}.csv"
            url = f"{self.base_url}{filename}"
            logger.info(f"Fetching fixtures from {url}")

            response = httpx.get(url, follow_redirects=True, timeout=15)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))

                # Get recent matches to determine current tournament
                if "tourney_date" in df.columns:
                    df["tourney_date"] = pd.to_datetime(
                        df["tourney_date"], format="%Y%m%d", errors="coerce"
                    )
                    today = pd.Timestamp.now().normalize()

                    # Find matches in the future or very recent (within 7 days)
                    upcoming = df[df["tourney_date"] >= today - pd.Timedelta(days=7)]

                    if not upcoming.empty:
                        # Get unique tournaments
                        for _, match in upcoming.head(20).iterrows():
                            fixture = self._row_to_fixture(match)
                            if fixture:
                                fixtures.append(fixture)

            if not fixtures:
                # Fallback: generate demo fixtures for current tournaments
                fixtures = self._generate_demo_fixtures()

        except Exception as e:
            logger.warning(f"Failed to fetch live fixtures: {e}. Using demo data.")
            fixtures = self._generate_demo_fixtures()

        return fixtures

    def _row_to_fixture(self, row: Any) -> Optional[Dict]:
        """Convert a DataFrame row to a fixture dict."""
        try:
            winner = row.get("winner_name", "")
            loser = row.get("loser_name", "")

            if not winner or not loser:
                return None

            # Parse date
            tourney_date = row.get("tourney_date")
            if isinstance(tourney_date, pd.Timestamp):
                match_date = tourney_date.date()
            else:
                match_date = date.today()

            return {
                "tournament": row.get("tourney_name", "Unknown"),
                "surface": row.get("surface", "Hard"),
                "tourney_level": row.get("tourney_level", "A"),
                "round": row.get("round", "R128"),
                "match_date": match_date.isoformat(),
                "best_of": 3 if row.get("tourney_level") != "G" else 5,
                "player1": {
                    "name": winner,
                    "rank": self._safe_int(row.get("winner_rank")),
                    "rank_points": self._safe_int(row.get("winner_rank_points")),
                    "age": self._safe_float(row.get("winner_age")),
                    "hand": row.get("winner_hand", "R"),
                    "height": self._safe_int(row.get("winner_ht")),
                    "seed": self._safe_int(row.get("winner_seed")),
                },
                "player2": {
                    "name": loser,
                    "rank": self._safe_int(row.get("loser_rank")),
                    "rank_points": self._safe_int(row.get("loser_rank_points")),
                    "age": self._safe_float(row.get("loser_age")),
                    "hand": row.get("loser_hand", "R"),
                    "height": self._safe_int(row.get("loser_ht")),
                    "seed": self._safe_int(row.get("loser_seed")),
                },
            }
        except Exception as e:
            logger.error(f"Error converting row to fixture: {e}")
            return None

    def _generate_demo_fixtures(self) -> List[Dict]:
        """Generate demo fixtures for major ongoing/upcoming tournaments."""
        today = date.today()

        # Major ATP tournaments with typical surfaces
        tournaments = [
            {"name": "US Open", "surface": "Hard", "level": "G", "best_of": 5},
            {"name": "ATP Finals", "surface": "Hard", "level": "F", "best_of": 3},
            {"name": "Shanghai Masters", "surface": "Hard", "level": "M", "best_of": 3},
            {
                "name": "Paris Masters",
                "surface": "Hard (Indoor)",
                "level": "M",
                "best_of": 3,
            },
        ]

        # Top players
        players = [
            {
                "name": "Jannik Sinner",
                "rank": 1,
                "rank_points": 11830,
                "age": 23.5,
                "hand": "R",
                "height": 188,
                "seed": 1,
            },
            {
                "name": "Carlos Alcaraz",
                "rank": 2,
                "rank_points": 9875,
                "age": 22.8,
                "hand": "R",
                "height": 183,
                "seed": 2,
            },
            {
                "name": "Novak Djokovic",
                "rank": 3,
                "rank_points": 8135,
                "age": 39.0,
                "hand": "R",
                "height": 188,
                "seed": 3,
            },
            {
                "name": "Alexander Zverev",
                "rank": 4,
                "rank_points": 7075,
                "age": 28.5,
                "hand": "R",
                "height": 198,
                "seed": 4,
            },
            {
                "name": "Daniil Medvedev",
                "rank": 5,
                "rank_points": 6525,
                "age": 30.0,
                "hand": "R",
                "height": 198,
                "seed": 5,
            },
            {
                "name": "Taylor Fritz",
                "rank": 6,
                "rank_points": 5050,
                "age": 27.5,
                "hand": "R",
                "height": 193,
                "seed": 6,
            },
            {
                "name": "Casper Ruud",
                "rank": 7,
                "rank_points": 4590,
                "age": 27.0,
                "hand": "R",
                "height": 183,
                "seed": 7,
            },
            {
                "name": "Andrey Rublev",
                "rank": 8,
                "rank_points": 4220,
                "age": 28.0,
                "hand": "R",
                "height": 188,
                "seed": 8,
            },
            {
                "name": "Alex de Minaur",
                "rank": 9,
                "rank_points": 3975,
                "age": 27.0,
                "hand": "R",
                "height": 183,
                "seed": 9,
            },
            {
                "name": "Grigor Dimitrov",
                "rank": 10,
                "rank_points": 3775,
                "age": 35.0,
                "hand": "R",
                "height": 191,
                "seed": 10,
            },
            {
                "name": "Holger Rune",
                "rank": 11,
                "rank_points": 3445,
                "age": 22.5,
                "hand": "R",
                "height": 185,
                "seed": 11,
            },
            {
                "name": "Tommy Paul",
                "rank": 12,
                "rank_points": 3260,
                "age": 28.0,
                "hand": "R",
                "height": 185,
                "seed": 12,
            },
        ]

        fixtures = []

        # Generate 8 matches from different matchups
        matchups = [
            (0, 1),  # Sinner vs Alcaraz
            (2, 3),  # Djokovic vs Zverev
            (4, 5),  # Medvedev vs Fritz
            (6, 7),  # Ruud vs Rublev
            (8, 9),  # de Minaur vs Dimitrov
            (10, 11),  # Rune vs Paul
            (0, 4),  # Sinner vs Medvedev
            (1, 2),  # Alcaraz vs Djokovic
        ]

        for i, (p1_idx, p2_idx) in enumerate(matchups):
            tournament = tournaments[i % len(tournaments)]
            fixtures.append(
                {
                    "tournament": tournament["name"],
                    "surface": tournament["surface"],
                    "tourney_level": tournament["level"],
                    "round": ["R32", "R16", "QF", "SF", "F"][i % 5],
                    "match_date": today.isoformat(),
                    "best_of": tournament["best_of"],
                    "player1": players[p1_idx],
                    "player2": players[p2_idx],
                }
            )

        return fixtures

    @staticmethod
    def _safe_int(val: Any) -> Optional[int]:
        try:
            if pd.isna(val):
                return None
            return int(float(val))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        try:
            if pd.isna(val):
                return None
            return float(val)
        except (ValueError, TypeError):
            return None
