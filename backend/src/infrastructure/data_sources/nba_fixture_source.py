import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class NBAFixtureSource:
    """
    Fetches upcoming NBA game fixtures from ESPN API.
    Falls back to demo data when API is unavailable.
    """

    SCOREBOARD_URL = (
        "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    )

    def __init__(self) -> None:
        self._cache: Optional[List[Dict]] = None
        self._cache_date: Optional[date] = None

    def get_upcoming_games(
        self, days: int = 7, team: Optional[str] = None
    ) -> List[Dict]:
        """
        Get upcoming NBA games for the next N days.
        Returns a list of game dicts with teams, venue, etc.
        """
        today = date.today()

        try:
            games = self._fetch_from_api(today, days, team)
            if games:
                return games
        except Exception as e:
            logger.warning(f"Failed to fetch from ESPN API: {e}")

        # Fallback to demo data
        return self._generate_demo_fixtures(days, team)

    def _fetch_from_api(
        self, start: date, days: int, team: Optional[str] = None
    ) -> List[Dict]:
        """Fetch schedule from ESPN API."""
        games = []
        for i in range(days):
            target_date = start + timedelta(days=i)
            try:
                response = httpx.get(
                    self.SCOREBOARD_URL,
                    params={"dates": target_date.strftime("%Y%m%d")},
                    timeout=15,
                )
                response.raise_for_status()
                data = response.json()

                for event in data.get("events", []):
                    game = self._parse_event(event, target_date)
                    if game:
                        if team and team.upper() not in (
                            game["home_team"],
                            game["away_team"],
                        ):
                            continue
                        games.append(game)
            except Exception as e:
                logger.warning(f"Failed to fetch ESPN for {target_date}: {e}")

        return games

    def _parse_event(self, event: dict, target_date: date) -> Optional[Dict]:
        """Parse a single event from ESPN."""
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

            # Parse date/time
            date_str = event.get("date", "")
            if date_str:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                game_date = dt.date().isoformat()
                time_str = dt.strftime("%H:%M")
            else:
                game_date = target_date.isoformat()
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
            }
        except Exception as e:
            logger.error(f"Error parsing event: {e}")
            return None

    def _generate_demo_fixtures(
        self, days: int = 7, team: Optional[str] = None
    ) -> List[Dict]:
        """Generate demo NBA fixtures with realistic matchups."""
        today = date.today()

        matchups: list[dict[str, Any]] = [
            {
                "home": {"abbr": "LAL", "name": "Los Angeles Lakers"},
                "away": {"abbr": "BOS", "name": "Boston Celtics"},
                "venue": "Crypto.com Arena",
            },
            {
                "home": {"abbr": "GSW", "name": "Golden State Warriors"},
                "away": {"abbr": "DEN", "name": "Denver Nuggets"},
                "venue": "Chase Center",
            },
            {
                "home": {"abbr": "MIL", "name": "Milwaukee Bucks"},
                "away": {"abbr": "PHI", "name": "Philadelphia 76ers"},
                "venue": "Fiserv Forum",
            },
            {
                "home": {"abbr": "MIA", "name": "Miami Heat"},
                "away": {"abbr": "NYK", "name": "New York Knicks"},
                "venue": "Kaseya Center",
            },
            {
                "home": {"abbr": "PHX", "name": "Phoenix Suns"},
                "away": {"abbr": "LAC", "name": "LA Clippers"},
                "venue": "Footprint Center",
            },
            {
                "home": {"abbr": "CLE", "name": "Cleveland Cavaliers"},
                "away": {"abbr": "OKC", "name": "Oklahoma City Thunder"},
                "venue": "Rocket Mortgage FieldHouse",
            },
            {
                "home": {"abbr": "DAL", "name": "Dallas Mavericks"},
                "away": {"abbr": "MIN", "name": "Minnesota Timberwolves"},
                "venue": "American Airlines Center",
            },
            {
                "home": {"abbr": "ATL", "name": "Atlanta Hawks"},
                "away": {"abbr": "BKN", "name": "Brooklyn Nets"},
                "venue": "State Farm Arena",
            },
            {
                "home": {"abbr": "SAC", "name": "Sacramento Kings"},
                "away": {"abbr": "MEM", "name": "Memphis Grizzlies"},
                "venue": "Golden 1 Center",
            },
            {
                "home": {"abbr": "IND", "name": "Indiana Pacers"},
                "away": {"abbr": "CHI", "name": "Chicago Bulls"},
                "venue": "Gainbridge Fieldhouse",
            },
        ]

        games = []
        for i, matchup in enumerate(matchups):
            game_date = today + timedelta(days=i % days)
            hour = 19 if i % 3 != 0 else 13
            games.append(
                {
                    "game_id": f"demo_{i+1}",
                    "date": game_date.isoformat(),
                    "time": f"{hour}:00",
                    "home_team": matchup["home"]["abbr"],
                    "away_team": matchup["away"]["abbr"],
                    "home_team_name": matchup["home"]["name"],
                    "away_team_name": matchup["away"]["name"],
                    "venue": matchup["venue"],
                }
            )

        return games
