import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# NBA team abbreviation mapping
NBA_TEAMS = {
    "ATL": "ATL",
    "BOS": "BOS",
    "BKN": "BKN",
    "CHA": "CHA",
    "CHI": "CHI",
    "CLE": "CLE",
    "DAL": "DAL",
    "DEN": "DEN",
    "DET": "DET",
    "GSW": "GSW",
    "HOU": "HOU",
    "IND": "IND",
    "LAC": "LAC",
    "LAL": "LAL",
    "MEM": "MEM",
    "MIA": "MIA",
    "MIL": "MIL",
    "MIN": "MIN",
    "NOP": "NOP",
    "NYK": "NYK",
    "OKC": "OKC",
    "ORL": "ORL",
    "PHI": "PHI",
    "PHX": "PHX",
    "POR": "POR",
    "SAC": "SAC",
    "SAS": "SAS",
    "TOR": "TOR",
    "UTA": "UTA",
    "WAS": "WAS",
}

# ESPN team abbreviation to full name
ESPN_TEAM_NAMES = {
    "ATL": "Hawks",
    "BOS": "Celtics",
    "BKN": "Nets",
    "CHA": "Hornets",
    "CHI": "Bulls",
    "CLE": "Cavaliers",
    "DAL": "Mavericks",
    "DEN": "Nuggets",
    "DET": "Pistons",
    "GSW": "Warriors",
    "HOU": "Rockets",
    "IND": "Pacers",
    "LAC": "Clippers",
    "LAL": "Lakers",
    "MEM": "Grizzlies",
    "MIA": "Heat",
    "MIL": "Bucks",
    "MIN": "Timberwolves",
    "NOP": "Pelicans",
    "NYK": "Knicks",
    "OKC": "Thunder",
    "ORL": "Magic",
    "PHI": "76ers",
    "PHX": "Suns",
    "POR": "Trail Blazers",
    "SAC": "Kings",
    "SAS": "Spurs",
    "TOR": "Raptors",
    "UTA": "Jazz",
    "WAS": "Wizards",
}


class NBADataSource:
    """
    Data source for NBA historical data from ESPN API.
    Fetches game logs, team stats, and standings.
    """

    SCOREBOARD_URL = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    )
    TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams"
    STANDINGS_URL = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/standings"
    )

    def __init__(self, cache_dir: str = "backend/data/cache/nba"):
        self.cache_dir = cache_dir
        self._standings_cache: Optional[Dict] = None

    def _safe_int(self, val: Any) -> int:
        """Safely convert a value to int, returning 0 on failure."""
        try:
            if val is None:
                return 0
            return int(float(val))
        except (ValueError, TypeError):
            return 0

    def _safe_float(self, val: Any) -> float:
        """Safely convert a value to float, returning 0.0 on failure."""
        try:
            if val is None:
                return 0.0
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    def fetch_scoreboard(self, days: int = 7) -> List[Dict]:
        """Fetch upcoming games from ESPN scoreboard API."""
        games = []
        today = date.today()
        for i in range(days):
            target_date = today + timedelta(days=i)
            try:
                response = httpx.get(
                    self.SCOREBOARD_URL,
                    params={"dates": target_date.strftime("%Y%m%d")},
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()
                for event in data.get("events", []):
                    game = self._parse_scoreboard_event(event)
                    if game:
                        games.append(game)
            except Exception as e:
                logger.warning(f"Failed to fetch scoreboard for {target_date}: {e}")
        return games

    def _parse_scoreboard_event(self, event: dict) -> Optional[Dict]:
        """Parse a single event from ESPN scoreboard."""
        try:
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            comp = competitions[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                return None

            home = next(
                (c for c in competitors if c.get("homeAway") == "home"), competitors[0]
            )
            away = next(
                (c for c in competitors if c.get("homeAway") == "away"), competitors[1]
            )

            home_team = home.get("team", {})
            away_team = away.get("team", {})

            # Parse date
            date_str = event.get("date", "")
            if date_str:
                from datetime import datetime

                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                game_date = dt.date().isoformat()
                time_str = dt.strftime("%H:%M")
            else:
                game_date = date.today().isoformat()
                time_str = "19:00"

            return {
                "game_id": event.get("id", ""),
                "date": game_date,
                "time": time_str,
                "home_team": home_team.get("abbreviation", ""),
                "away_team": away_team.get("abbreviation", ""),
                "home_team_name": home_team.get("displayName", ""),
                "away_team_name": away_team.get("displayName", ""),
                "venue": comp.get("venue", {}).get("fullName", ""),
                "status": event.get("status", {}).get("type", {}).get("name", ""),
            }
        except Exception as e:
            logger.error(f"Error parsing scoreboard event: {e}")
            return None

    def fetch_standings(self) -> Dict[str, Dict]:
        """Fetch current NBA standings."""
        if self._standings_cache:
            return self._standings_cache

        try:
            response = httpx.get(self.STANDINGS_URL, timeout=15)
            response.raise_for_status()
            data = response.json()

            standings = {}
            for conference in data.get("children", []):
                for team_entry in conference.get("standings", {}).get("entries", []):
                    team = team_entry.get("team", {})
                    abbrev = team.get("abbreviation", "")
                    stats = {
                        s["name"]: s.get("value", 0)
                        for s in team_entry.get("stats", [])
                    }
                    standings[abbrev] = {
                        "abbreviation": abbrev,
                        "name": team.get("displayName", ""),
                        "wins": self._safe_int(stats.get("wins", 0)),
                        "losses": self._safe_int(stats.get("losses", 0)),
                        "win_pct": self._safe_float(stats.get("winPercent", 0.5)),
                        "points_for": self._safe_float(
                            stats.get("avgPointsFor", 112.0)
                        ),
                        "points_against": self._safe_float(
                            stats.get("avgPointsAgainst", 112.0)
                        ),
                    }
            self._standings_cache = standings
            return standings
        except Exception as e:
            logger.warning(f"Failed to fetch standings: {e}")
            return {}

    def get_team_stats(
        self, team: str, date_range: Optional[List[date]] = None
    ) -> dict:
        """
        Get aggregate team stats for feature extraction.
        Returns offense and defense averages.
        """
        standings = self.fetch_standings()
        team_data = standings.get(team.upper(), {})

        return {
            "team": team.upper(),
            "wins": team_data.get("wins", 0),
            "losses": team_data.get("losses", 0),
            "win_pct": team_data.get("win_pct", 0.5),
            "pts_scored_per_game": team_data.get("points_for", 112.0),
            "pts_allowed_per_game": team_data.get("points_against", 112.0),
            "off_rating": team_data.get("points_for", 112.0),
            "def_rating": team_data.get("points_against", 112.0),
        }

    @staticmethod
    def normalize_team(abbr: str) -> str:
        """Normalize team abbreviation to standard format."""
        return NBA_TEAMS.get(abbr.upper(), abbr.upper())
