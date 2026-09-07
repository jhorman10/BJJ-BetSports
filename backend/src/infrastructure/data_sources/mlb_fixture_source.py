import logging
from typing import Optional, List, Dict
from datetime import datetime, date, timedelta
import httpx

logger = logging.getLogger(__name__)


class MLBFixtureSource:
    """
    Fetches upcoming MLB game fixtures from statsapi.mlb.com.
    Falls back to demo data when API is unavailable.
    """

    SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"
    ROSTER_URL = "https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"

    # MLB team IDs for demo data
    TEAM_IDS = {
        "NYY": 147, "BOS": 111, "LAD": 119, "HOU": 117,
        "ATL": 144, "NYM": 121, "PHI": 143, "CHC": 112,
        "STL": 138, "SD": 135, "SEA": 136, "MIN": 142,
        "TOR": 141, "BAL": 110, "CLE": 114, "TEX": 140,
        "SF": 137, "TB": 139, "MIA": 146, "CHW": 4,
        "KC": 118, "MIL": 158, "CIN": 113, "DET": 116,
        "OAK": 133, "PIT": 134, "COL": 115, "WSH": 120,
        "ARI": 109, "LAA": 108,
    }

    def __init__(self):
        self._cache: Optional[List[Dict]] = None
        self._cache_date: Optional[date] = None

    def get_upcoming_games(self, days: int = 7, team: Optional[str] = None) -> List[Dict]:
        """
        Get upcoming MLB games for the next N days.
        Returns a list of game dicts with teams, pitchers, venue, etc.
        """
        today = date.today()
        end_date = today + timedelta(days=days)

        try:
            games = self._fetch_from_api(today, end_date, team)
            if games:
                return games
        except Exception as e:
            logger.warning(f"Failed to fetch from MLB API: {e}")

        # Fallback to demo data
        return self._generate_demo_fixtures(days, team)

    def get_series(self, days: int = 14, team: Optional[str] = None) -> List[List[Dict]]:
        """
        Get upcoming games grouped into series.
        """
        games = self.get_upcoming_games(days=days, team=team)
        return self._group_into_series(games)

    def _fetch_from_api(self, start: date, end: date, team: Optional[str] = None) -> List[Dict]:
        """Fetch schedule from MLB Stats API."""
        params = {
            "sportId": 1,
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "hydrate": "probablePitcher,team",
        }
        if team and team.upper() in self.TEAM_IDS:
            params["teamId"] = self.TEAM_IDS[team.upper()]

        response = httpx.get(self.SCHEDULE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        games = []
        for date_entry in data.get("dates", []):
            for game in date_entry.get("games", []):
                fixture = self._parse_game(game)
                if fixture:
                    games.append(fixture)

        return games

    def _parse_game(self, game: dict) -> Optional[Dict]:
        """Parse a game from the MLB Stats API response."""
        try:
            teams = game.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})

            home_team = home.get("team", {})
            away_team = away.get("team", {})

            # Parse probable pitchers
            home_pitcher = home.get("probablePitcher", {})
            away_pitcher = away.get("probablePitcher", {})

            game_date = game.get("gameDate", "")
            if game_date:
                dt = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
                game_date_str = dt.date().isoformat()
                time_str = dt.strftime("%H:%M")
            else:
                game_date_str = date.today().isoformat()
                time_str = "19:00"

            return {
                "game_id": str(game.get("gamePk", "")),
                "date": game_date_str,
                "time": time_str,
                "home_team": home_team.get("abbreviation", home_team.get("name", "")),
                "away_team": away_team.get("abbreviation", away_team.get("name", "")),
                "home_team_name": home_team.get("name", ""),
                "away_team_name": away_team.get("name", ""),
                "venue": game.get("venue", {}).get("name", ""),
                "day_night": "night" if "18:00" <= time_str <= "23:59" else "day",
                "home_pitcher_name": home_pitcher.get("fullName"),
                "away_pitcher_name": away_pitcher.get("fullName"),
                "series_id": f"{away_team.get('abbreviation', '')}@{home_team.get('abbreviation', '')}_{game_date_str}",
            }
        except Exception as e:
            logger.error(f"Error parsing game: {e}")
            return None

    def _group_into_series(self, games: List[Dict]) -> List[List[Dict]]:
        """Group games by series (same matchup)."""
        series_map: Dict[str, List[Dict]] = {}
        for game in games:
            matchup = tuple(sorted([game["home_team"], game["away_team"]]))
            key = f"{matchup[0]}_vs_{matchup[1]}"
            if key not in series_map:
                series_map[key] = []
            series_map[key].append(game)
        return list(series_map.values())

    def _generate_demo_fixtures(self, days: int = 7, team: Optional[str] = None) -> List[Dict]:
        """Generate demo MLB fixtures with realistic matchups."""
        today = date.today()

        # Top MLB matchups with probable pitchers
        matchups = [
            {
                "home": {"abbr": "NYY", "name": "New York Yankees", "pitcher": "Gerrit Cole"},
                "away": {"abbr": "BOS", "name": "Boston Red Sox", "pitcher": "Brayan Bello"},
                "venue": "Yankee Stadium",
            },
            {
                "home": {"abbr": "LAD", "name": "Los Angeles Dodgers", "pitcher": "Yoshinobu Yamamoto"},
                "away": {"abbr": "SF", "name": "San Francisco Giants", "pitcher": "Logan Webb"},
                "venue": "Dodger Stadium",
            },
            {
                "home": {"abbr": "HOU", "name": "Houston Astros", "pitcher": "Framber Valdez"},
                "away": {"abbr": "TEX", "name": "Texas Rangers", "pitcher": "Nathan Eovaldi"},
                "venue": "Minute Maid Park",
            },
            {
                "home": {"abbr": "ATL", "name": "Atlanta Braves", "pitcher": "Spencer Strider"},
                "away": {"abbr": "PHI", "name": "Philadelphia Phillies", "pitcher": "Zack Wheeler"},
                "venue": "Truist Park",
            },
            {
                "home": {"abbr": "NYM", "name": "New York Mets", "pitcher": "Kodai Senga"},
                "away": {"abbr": "CHC", "name": "Chicago Cubs", "pitcher": "Justin Steele"},
                "venue": "Citi Field",
            },
            {
                "home": {"abbr": "SEA", "name": "Seattle Mariners", "pitcher": "Luis Castillo"},
                "away": {"abbr": "OAK", "name": "Oakland Athletics", "pitcher": "JP Sears"},
                "venue": "T-Mobile Park",
            },
            {
                "home": {"abbr": "STL", "name": "St. Louis Cardinals", "pitcher": "Sonny Gray"},
                "away": {"abbr": "MIL", "name": "Milwaukee Brewers", "pitcher": "Corbin Burnes"},
                "venue": "Busch Stadium",
            },
            {
                "home": {"abbr": "BAL", "name": "Baltimore Orioles", "pitcher": "Corbin Burnes"},
                "away": {"abbr": "CLE", "name": "Cleveland Guardians", "pitcher": "Shane Bieber"},
                "venue": "Camden Yards",
            },
            {
                "home": {"abbr": "TOR", "name": "Toronto Blue Jays", "pitcher": "Kevin Gausman"},
                "away": {"abbr": "MIN", "name": "Minnesota Twins", "pitcher": "Pablo Lopez"},
                "venue": "Rogers Centre",
            },
            {
                "home": {"abbr": "SD", "name": "San Diego Padres", "pitcher": "Yu Darvish"},
                "away": {"abbr": "ARI", "name": "Arizona Diamondbacks", "pitcher": "Zac Gallen"},
                "venue": "Petco Park",
            },
        ]

        games = []
        for i, matchup in enumerate(matchups):
            game_date = today + timedelta(days=i % days)
            is_night = i % 3 != 0
            games.append({
                "game_id": f"demo_{i+1}",
                "date": game_date.isoformat(),
                "time": "19:05" if is_night else "13:05",
                "home_team": matchup["home"]["abbr"],
                "away_team": matchup["away"]["abbr"],
                "home_team_name": matchup["home"]["name"],
                "away_team_name": matchup["away"]["name"],
                "venue": matchup["venue"],
                "day_night": "night" if is_night else "day",
                "home_pitcher_name": matchup["home"]["pitcher"],
                "away_pitcher_name": matchup["away"]["pitcher"],
                "series_id": f"{matchup['away']['abbr']}@{matchup['home']['abbr']}_{game_date.isoformat()}",
            })

        return games
