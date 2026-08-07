"""
OpenFootball Data Source

This module handles downloading and parsing JSON data from the OpenFootball
GitHub repository.

Repository: https://github.com/openfootball/football.json
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import httpx
from src.domain.entities.entities import League, Match, Team

logger = logging.getLogger(__name__)


# Mapping of month abbreviations to numbers
MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


# Mapping of our league codes to OpenFootball file paths (relative to season)
LEAGUE_FILE_MAPPING = {
    "E0": "en.1",
    "E1": "en.2",
    "D1": "de.1",
    "SP1": "es.1",
    "I1": "it.1",
    "F1": "fr.1",
    "B1": "be.1",
    # Add more as discovered
}


# Mapping of our league codes to OpenFootball south-america repo subdirectories
# Format: league_id -> (country_dir, file_pattern_prefix)
SOUTH_AMERICA_LEAGUE_MAPPING = {
    "COL1": ("colombia", "co1"),
    "ARG1": ("argentina", "ar1"),
    "BRA1": ("brazil", "br1"),
}


@dataclass
class OpenFootballConfig:
    """Configuration for OpenFootball data source."""

    base_url: str = (
        "https://raw.githubusercontent.com/openfootball/football.json/master"
    )
    timeout: int = 30


SOUTH_AMERICA_BASE_URL = (
    "https://raw.githubusercontent.com/openfootball/south-america/master"
)


class OpenFootballSource:
    """
    Data source for OpenFootball (GitHub).
    """

    SOURCE_NAME = "OpenFootball"

    def __init__(self, config: Optional[OpenFootballConfig] = None):
        """Initialize the data source."""
        self.config = config or OpenFootballConfig()

    def _get_season_string(self, season: Optional[str] = None) -> str:
        """
        Get season string in 'YYYY-YY' format (e.g., '2024-25').
        Default to current season based on date.
        """
        now = datetime.now()
        if not season:
            year = now.year
            # If we are in second half of year, season started this year
            if now.month >= 7:
                start_year = year
                end_year = year + 1
            else:
                start_year = year - 1
                end_year = year

            return f"{start_year}-{str(end_year)[-2:]}"

        return season

    def _get_season_year_for_south_america(self, league: League) -> str:
        """
        Get the appropriate year for south-american football.txt files.

        South American leagues use calendar-year format (e.g., 2024 for
        the 2024 season), unlike European leagues that use season format.
        """
        now = datetime.now()
        year = now.year

        # If league has explicit season, try to extract year from it
        if league.season:
            try:
                # Season format might be "2024" or "2024-25"
                if "-" in league.season:
                    year = int(league.season.split("-")[0])
                else:
                    year = int(league.season)
                return str(year)
            except (ValueError, IndexError):
                pass

        # Default: use current year (South American leagues typically current year)
        # But if we're early in the year, might still be previous year's data
        return str(year)

    def _parse_football_txt(self, content: str, league: League) -> list[Match]:
        """
        Parse football.txt format content into Match entities.

        Format example:
            = Colombia Primera A 2024

            # Date       Fri Jan 19 - Sun Dec 22 2024 (338d)

            ▪ Apertura, Matchday 1
              Fri Jan 19 2024
                18:00  Team Home            v Team Away                 0-1 (0-1)
        """
        matches = []
        lines = content.split("\n")

        # Regex to parse match lines:
        # "    18:00  Team Home            v Team Away                 0-1 (0-1)"
        # "           Team Home            v Team Away"  (no time, no score)
        # "    18:00  Team Home            v Team Away"  (time, no score)
        match_regex = re.compile(
            r"^\s*(?:(\d{1,2}:\d{2})\s+)?"  # Optional time HH:MM
            r"(.+?)\s+v\s+"  # team1 (home)
            r"(.+?)\s+"  # team2 (away)
            r"(?:(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?)?"  # Optional score FT and HT
            r"\s*$"
        )

        # Regex to parse date lines: "  Fri Jan 19 2024"
        date_regex = re.compile(
            r"^\s+[A-Z][a-z]{2}\s+"  # Day abbreviation
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"  # Month
            r"(\d{1,2})\s+"  # Day
            r"(\d{4})\s*$"  # Year
        )

        current_date = None

        for line in lines:
            # Check for date line (indented day abbreviation + month + day + year)
            date_match = date_regex.match(line)
            if date_match:
                month_str = date_match.group(1)
                day = int(date_match.group(2))
                year = int(date_match.group(3))
                month = MONTH_MAP.get(month_str, 1)
                current_date = datetime(year, month, day, tzinfo=None)
                continue

            # Check for match line (starts with optional time or " v " for home/away)
            if " v " in line and current_date:
                match_match = match_regex.match(line)
                if match_match:
                    time_str = match_match.group(1)
                    home_name = match_match.group(2).strip()
                    away_name = match_match.group(3).strip()
                    home_ft = match_match.group(4)
                    away_ft = match_match.group(5)
                    match_match.group(6)
                    match_match.group(7)

                    if not home_name or not away_name:
                        continue

                    # Parse time
                    if time_str:
                        try:
                            time_parts = time_str.split(":")
                            hour = int(time_parts[0])
                            minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                            current_date = current_date.replace(
                                hour=hour, minute=minute
                            )
                        except (ValueError, IndexError):
                            current_date = current_date.replace(hour=15, minute=0)
                    else:
                        current_date = current_date.replace(hour=15, minute=0)

                    from datetime import timezone

                    match_date = current_date.replace(tzinfo=timezone.utc)

                    # Parse scores
                    home_goals = None
                    away_goals = None
                    status = "NS"

                    if home_ft and away_ft:
                        try:
                            home_goals = int(home_ft)
                            away_goals = int(away_ft)
                            status = "FT"
                        except ValueError:
                            pass

                    home_team = Team(
                        id=home_name.lower().replace(" ", "_").replace(",", ""),
                        name=home_name,
                        country=league.country,
                    )

                    away_team = Team(
                        id=away_name.lower().replace(" ", "_").replace(",", ""),
                        name=away_name,
                        country=league.country,
                    )

                    date_part = match_date.strftime("%Y%m%d")
                    match = Match(
                        id=f"{league.id}_{date_part}_{home_team.id}_{away_team.id}",
                        home_team=home_team,
                        away_team=away_team,
                        league=league,
                        match_date=match_date,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        status=status,
                    )
                    matches.append(match)

        return matches

    @staticmethod
    def _get_previous_season(season_str: str) -> Optional[str]:
        """Compute the previous season string from a 'YYYY-YY' format.

        E.g., '2026-27' -> '2025-26', '2024-25' -> '2023-24'.
        Returns None if the input cannot be parsed.
        """
        try:
            parts = season_str.split("-")
            if len(parts) != 2:
                return None
            start_year = int(parts[0])
            end_short = int(parts[1])
            prev_start = start_year - 1
            prev_end = end_short - 1
            if prev_end < 0:
                prev_end += 100
            return f"{prev_start}-{prev_end:02d}"
        except (ValueError, IndexError):
            return None

    async def get_matches(self, league: League) -> list[Match]:
        """
        Get all matches for a league.

        Supports both the JSON format (Europe, etc.) and
        the football.txt format (South American leagues).

        Args:
            league: League entity

        Returns:
            List of matches
        """
        # First try South American leagues (football.txt format)
        if league.id in SOUTH_AMERICA_LEAGUE_MAPPING:
            return await self._get_south_america_matches(league)

        # Then try standard JSON-based leagues
        if league.id not in LEAGUE_FILE_MAPPING:
            logger.debug(f"League {league.id} not mapped in OpenFootball")
            return []

        filename = LEAGUE_FILE_MAPPING[league.id]
        season_str = self._get_season_string(league.season)

        # Build list of seasons to try: the computed/current season first,
        # then the previous season as a fallback (the GitHub repo may not
        # have published data for the upcoming season yet).
        seasons_to_try = [season_str]
        prev_season = self._get_previous_season(season_str)
        if prev_season and prev_season != season_str:
            seasons_to_try.append(prev_season)

        for try_season in seasons_to_try:
            url = f"{self.config.base_url}/{try_season}/{filename}.json"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=self.config.timeout)

                    if response.status_code == 404:
                        logger.warning(f"OpenFootball file not found: {url}")
                        continue  # Try next season

                    response.raise_for_status()
                    data = response.json()

                    matches = self._parse_matches(data, league)
                    if matches:
                        logger.info(
                            f"OpenFootball: loaded {len(matches)} matches "
                            f"from {url}"
                        )
                        return matches
                    else:
                        logger.warning(f"OpenFootball: no matches parsed from {url}")
                        continue

            except Exception as e:
                logger.error(f"Error fetching OpenFootball data from {url}: {e}")
                continue

        logger.error(
            f"OpenFootball: all seasons exhausted for {league.id} ({filename})"
        )
        return []

    async def _get_south_america_matches(self, league: League) -> list[Match]:
        """
        Fetch matches for South American leagues from openfootball/south-america.

        These leagues use football.txt format (not JSON), so we parse the
        raw text and convert season year accordingly.
        """
        country_dir, file_prefix = SOUTH_AMERICA_LEAGUE_MAPPING[league.id]

        # South American leagues use calendar year naming (e.g., 2024_co1.txt)
        season_year = self._get_season_year_for_south_america(league)

        # Try current year first, then previous years as fallback
        years_to_try = [season_year]
        try:
            year_int = int(season_year)
            for i in range(1, 4):  # Try 3 previous years
                years_to_try.append(str(year_int - i))
        except ValueError:
            pass

        for try_year in years_to_try:
            url = f"{SOUTH_AMERICA_BASE_URL}/{country_dir}/{try_year}_{file_prefix}.txt"
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, timeout=self.config.timeout)

                    if response.status_code == 404:
                        logger.debug(
                            f"OpenFootball south-america file not found: {url}"
                        )
                        continue  # Try previous year

                    response.raise_for_status()
                    content = response.text

                    matches = self._parse_football_txt(content, league)
                    if matches:
                        logger.info(
                            f"OpenFootball: loaded {len(matches)} matches "
                            f"from {url}"
                        )
                        return matches
                    else:
                        logger.warning(f"OpenFootball: no matches parsed from {url}")
                        continue

            except Exception as e:
                logger.error(
                    f"Error fetching OpenFootball south-america data from {url}: {e}"
                )
                continue

        logger.error(
            f"OpenFootball: all years exhausted for {league.id} in south-america repo"
        )
        return []

    def _parse_matches(self, data: dict, league: League) -> list[Match]:
        """Parse JSON data into Match entities."""
        matches = []

        # Data structure: { "name": "...", "matches": [ ... ] }
        match_list = data.get("matches", [])

        for item in match_list:
            try:
                # Example: {'date':'YYYY-MM-DD','team1':'Home','team2':'Away'}
                date_str = item.get("date")
                if not date_str:
                    continue

                from datetime import timezone

                dt = datetime.strptime(date_str, "%Y-%m-%d")

                # Parse time if available (format: "HH:MM" or "HH:MM:SS")
                time_str = item.get("time")
                if time_str:
                    try:
                        time_parts = time_str.split(":")
                        hour = int(time_parts[0])
                        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
                        dt = dt.replace(hour=hour, minute=minute)
                    except (ValueError, IndexError):
                        # Default to 15:00 if time parsing fails
                        dt = dt.replace(hour=15, minute=0)
                else:
                    # No time provided, default to 15:00 (typical afternoon kickoff)
                    dt = dt.replace(hour=15, minute=0)

                # Store as UTC (frontend handles display conversion)
                match_date = dt.replace(tzinfo=timezone.utc)

                home_name = item.get("team1", "Unknown")
                away_name = item.get("team2", "Unknown")

                home_team = Team(
                    id=home_name.lower().replace(" ", "_"),
                    name=home_name,
                    country=league.country,
                )

                away_team = Team(
                    id=away_name.lower().replace(" ", "_"),
                    name=away_name,
                    country=league.country,
                )

                # Score parsing
                score = item.get("score")
                home_goals = None
                away_goals = None
                status = "NS"

                if score and score.get("ft"):
                    home_goals = score["ft"][0]
                    away_goals = score["ft"][1]
                    status = "FT"

                date_part = match_date.strftime("%Y%m%d")
                match = Match(
                    id=f"{league.id}_{date_part}_{home_team.id}_{away_team.id}",
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_date=match_date,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    status=status,
                )
                matches.append(match)

            except Exception as e:
                logger.debug(f"Error parsing match item: {e}")
                continue

        return matches
