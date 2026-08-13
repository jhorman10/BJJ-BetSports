"""
Football-Data.org Data Source

This module integrates with Football-Data.org free API tier for
additional league data, standings, and team information.

API Documentation: https://www.football-data.org/documentation/api
Free tier: 10 requests/minute
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from src.domain.entities.entities import League, Match, Team

logger = logging.getLogger(__name__)


@dataclass
class FootballDataOrgConfig:
    """Configuration for Football-Data.org."""

    api_key: Optional[str] = None
    base_url: str = "https://api.football-data.org/v4"
    timeout: int = 30
    min_wait_seconds: float = 6.5  # Optimized for Free Tier (10 req/min = 1 per 6s)

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = os.getenv("FOOTBALL_DATA_ORG_KEY")

        # Allow overriding rate limit via env var (e.g. set to 0.5 for paid plans)
        env_wait = os.getenv("FOOTBALL_DATA_ORG_WAIT_SECONDS")
        if env_wait:
            try:
                self.min_wait_seconds = float(env_wait)
            except ValueError:
                pass


# Mapping of our league codes to Football-Data.org competition codes
COMPETITION_CODE_MAPPING = {
    "E0": "PL",  # Premier League
    "E1": "ELC",  # Championship
    "SP1": "PD",  # La Liga
    "D1": "BL1",  # Bundesliga
    "I1": "SA",  # Serie A
    "F1": "FL1",  # Ligue 1
    "N1": "DED",  # Eredivisie
    "P1": "PPL",  # Primeira Liga
    "UCL": "CL",  # UEFA Champions League
    "UEL": "EL",  # UEFA Europa League
    "EURO": "EC",  # European Championship
    "WC": "WC",  # World Cup
}


class FootballDataOrgSource:
    """
    Data source for Football-Data.org.

    Provides access to league standings, team data, and match schedules.
    Free tier: 10 requests/minute.
    """

    SOURCE_NAME = "Football-Data.org"

    def __init__(self, config: Optional[FootballDataOrgConfig] = None) -> None:
        """Initialize the data source."""
        self.config = config or FootballDataOrgConfig()
        self._request_times: list[datetime] = []
        self._memory_cache: dict[str, dict[str, Any]] = {}
        self._last_request_time: Optional[datetime] = None
        self._blocked_until: Optional[datetime] = None
        self._lock: Optional[asyncio.Lock] = None

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.config.api_key)

    async def _wait_strict(self) -> None:
        """
        Strict rate limiting: 10 req/min = 1 req every 6 seconds.
        Uses a Lock to ensure task safety in async contexts.
        """
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            now = datetime.utcnow()

            # Check global block first
            if self._blocked_until and now < self._blocked_until:
                wait_time = (self._blocked_until - now).total_seconds()
                if wait_time > 0:
                    logger.warning(
                        "Global 429 Block Active. Sleeping %.2fs...", wait_time
                    )
                    await asyncio.sleep(wait_time)
                    now = datetime.utcnow()

            if self._last_request_time:
                elapsed = (now - self._last_request_time).total_seconds()
                required_wait = self.config.min_wait_seconds

                if elapsed < required_wait:
                    wait_time = required_wait - elapsed
                    logger.debug(
                        "Rate Limit: Waiting %.2fs to respect %.2fs gap",
                        wait_time,
                        required_wait,
                    )
                    await asyncio.sleep(wait_time)

            self._last_request_time = datetime.utcnow()

    async def _make_request(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        use_cache: bool = True,
        ttl_seconds: int = 86400,
    ) -> Optional[dict[str, Any]]:
        """
        Make authenticated request with Multi-Level Caching:
        1. Memory Cache (Session)
        2. DB Cache (Persistent)
        3. Real API Call (Rate Limited)
        """
        if not self.is_configured:
            logger.warning("Football-Data.org not configured (no API key)")
            return None

        cache_key = f"{endpoint}:{json.dumps(params, sort_keys=True) if params else ''}"
        if use_cache and cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        repo = None
        if use_cache:
            try:
                from src.infrastructure.repositories.async_mongo_adapter import (
                    get_async_mongo_repository,
                )

                repo = get_async_mongo_repository()
                cached_data = await repo.get_cached_response(endpoint, params)
                if isinstance(cached_data, dict):
                    self._memory_cache[cache_key] = cached_data
                    return cached_data
            except Exception as e:
                logger.warning("DB Cache read failed: %s", e)

        await self._wait_strict()

        url = f"{self.config.base_url}{endpoint}"
        # is_configured (checked above) guarantees the API key is present.
        assert self.config.api_key is not None
        headers: dict[str, str] = {"X-Auth-Token": self.config.api_key}

        max_retries = 3
        backoff = 60

        for attempt in range(max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=self.config.timeout,
                    )

                    if response.status_code == 429:
                        if attempt < max_retries:
                            retry_after = int(
                                response.headers.get("Retry-After", backoff)
                            )
                            logger.warning(
                                "429 Too Many Requests — sleeping %s s",
                                retry_after,
                            )
                            self._blocked_until = datetime.utcnow() + timedelta(
                                seconds=retry_after
                            )
                            await asyncio.sleep(retry_after)
                            continue
                        return None

                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        return None

                    self._memory_cache[cache_key] = data
                    if use_cache and repo:
                        try:
                            await repo.save_cached_response(
                                endpoint, data, params, ttl_seconds
                            )
                        except Exception as e:
                            logger.debug(
                                "Failed to persist cached response async: %s", e
                            )

                    return data

            except Exception as e:
                logger.error("Request failed: %s", e)
                if attempt < max_retries:
                    await asyncio.sleep(5)
                else:
                    return None
        return None

    async def get_competitions(self) -> list[dict[str, Any]]:
        """Get list of available competitions."""
        data = await self._make_request("/competitions", ttl_seconds=604800)
        if not data:
            return []
        competitions = data.get("competitions")
        if not isinstance(competitions, list):
            return []
        return [
            competition for competition in competitions if isinstance(competition, dict)
        ]

    async def get_league_teams(self, league_code: str) -> list[Team]:
        """Get teams for a league."""
        if league_code not in COMPETITION_CODE_MAPPING:
            return []

        comp_code = COMPETITION_CODE_MAPPING[league_code]
        data = await self._make_request(
            f"/competitions/{comp_code}/teams",
            ttl_seconds=604800,
        )

        if not data or not data.get("teams"):
            return []

        teams: list[Team] = []
        for team_data in data["teams"]:
            teams.append(
                Team(
                    id=str(team_data.get("id")),
                    name=team_data.get("name", "Unknown"),
                    short_name=team_data.get("shortName"),
                    country=team_data.get("area", {}).get("name"),
                )
            )

        return teams

    async def get_upcoming_matches(
        self, league_code: str, matchday: Optional[int] = None
    ) -> list[Match]:
        """Get scheduled matches for a league."""
        if league_code not in COMPETITION_CODE_MAPPING:
            return []

        comp_code = COMPETITION_CODE_MAPPING[league_code]
        params: dict[str, str | int] = {"status": "SCHEDULED,TIMED,IN_PLAY,LIVE"}
        if matchday:
            params["matchday"] = matchday

        data = await self._make_request(
            f"/competitions/{comp_code}/matches",
            params,
            ttl_seconds=3600,
        )
        if not data or not data.get("matches"):
            return []

        competition = data.get("competition", {})
        league = League(
            id=league_code,
            name=competition.get("name", "Unknown"),
            country=competition.get("area", {}).get("name", "Unknown"),
        )

        matches: list[Match] = []
        for match_data in data["matches"]:
            try:
                match = self._parse_match(match_data, league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug("Error parsing match: %s", e)

        return matches

    async def get_league_matches(
        self,
        league_code: str,
        date_from: str,
        date_to: str,
        status: Optional[str] = None,
    ) -> list[Match]:
        """Get all matches for a league within a date range (batch fetch)."""
        if league_code not in COMPETITION_CODE_MAPPING:
            return []

        comp_code = COMPETITION_CODE_MAPPING[league_code]
        params = {"dateFrom": date_from, "dateTo": date_to}
        if status:
            params["status"] = status

        data = await self._make_request(
            f"/competitions/{comp_code}/matches",
            params,
            ttl_seconds=3600,
        )
        if not data or not data.get("matches"):
            return []

        competition = data.get("competition", {})
        league = League(
            id=league_code,
            name=competition.get("name", "Unknown"),
            country=competition.get("area", {}).get("name", "Unknown"),
        )

        matches: list[Match] = []
        for match_data in data["matches"]:
            try:
                match = self._parse_match(match_data, league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug("Error parsing bulk match: %s", e)

        return matches

    def _parse_match(self, match_data: dict, league: League) -> Optional[Match]:
        """Parse Football-Data.org match into Match entity."""
        try:
            home_team_data = match_data.get("homeTeam", {})
            away_team_data = match_data.get("awayTeam", {})

            home_team = Team(
                id=str(home_team_data.get("id", "")),
                name=home_team_data.get("name", "Unknown"),
                short_name=home_team_data.get("shortName"),
                country=league.country,
            )

            away_team = Team(
                id=str(away_team_data.get("id", "")),
                name=away_team_data.get("name", "Unknown"),
                short_name=away_team_data.get("shortName"),
                country=league.country,
            )

            utc_date = match_data.get("utcDate", "")
            match_date = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))

            score = match_data.get("score", {}).get("fullTime", {})
            home_goals = score.get("home")
            away_goals = score.get("away")

            return Match(
                id=str(match_data.get("id", "")),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
                status=match_data.get("status", "NS"),
            )

        except Exception as e:
            logger.debug("Failed to parse match: %s", e)
            return None

    async def get_finished_matches(
        self,
        date_from: str,
        date_to: str,
        league_codes: Optional[list[str]] = None,
    ) -> list[Match]:
        """Get finished matches within a date range (chunks to avoid limits)."""
        all_matches: list[Match] = []

        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d")

        chunk_days = 10
        current = start

        comp_filter = None
        if league_codes:
            comp_codes = [
                COMPETITION_CODE_MAPPING[lc]
                for lc in league_codes
                if lc in COMPETITION_CODE_MAPPING
            ]
            if comp_codes:
                comp_filter = ",".join(comp_codes)

        while current < end:
            chunk_end = min(current + timedelta(days=chunk_days), end)

            params = {
                "status": "FINISHED",
                "dateFrom": current.strftime("%Y-%m-%d"),
                "dateTo": chunk_end.strftime("%Y-%m-%d"),
            }

            if comp_filter:
                params["competitions"] = comp_filter

            data = await self._make_request("/matches", params)

            if data and data.get("matches"):
                for match_data in data["matches"]:
                    try:
                        competition = match_data.get("competition", {})
                        comp_code = competition.get("code", "")

                        league_code = None
                        for internal, external in COMPETITION_CODE_MAPPING.items():
                            if external == comp_code:
                                league_code = internal
                                break

                        if not league_code:
                            continue

                        league = League(
                            id=league_code,
                            name=competition.get("name", "Unknown"),
                            country=competition.get("area", {}).get("name", "Unknown"),
                        )

                        match = self._parse_match(match_data, league)
                        if match:
                            all_matches.append(match)
                    except Exception as e:
                        logger.debug("Error parsing finished match: %s", e)

            current = chunk_end + timedelta(days=1)

        logger.info(
            "Football-Data.org: fetched %d finished matches (%s to %s)",
            len(all_matches),
            date_from,
            date_to,
        )
        return all_matches

    async def get_standings(self, league_code: str) -> Optional[list[dict[str, Any]]]:
        """Get current standings for a league."""
        if league_code not in COMPETITION_CODE_MAPPING:
            return None

        comp_code = COMPETITION_CODE_MAPPING[league_code]
        data = await self._make_request(f"/competitions/{comp_code}/standings")
        if not data:
            return None
        standings = data.get("standings")
        if not isinstance(standings, list):
            return None
        return [standing for standing in standings if isinstance(standing, dict)]

    async def get_match_details(self, match_id: str) -> Optional[Match]:
        """Get details for a specific match."""
        data = await self._make_request(f"/matches/{match_id}")
        if not data:
            return None

        try:
            competition = data.get("competition", {})
            comp_code = competition.get("code")
            league_code = "Unknown"
            for internal, external in COMPETITION_CODE_MAPPING.items():
                if external == comp_code:
                    league_code = internal
                    break

            league = League(
                id=league_code,
                name=competition.get("name", "Unknown"),
                country=competition.get("area", {}).get("name", "Unknown"),
            )

            return self._parse_match(data, league)

        except Exception as e:
            logger.error("Error parsing match details from football-data.org: %s", e)
            return None

    async def get_team_history(self, team_name: str, limit: int = 5) -> list[Match]:
        """Get last N finished matches for a specific team."""
        if not self.is_configured:
            return []

        search_data = await self._make_request("/teams", {"name": team_name})
        if not search_data or not search_data.get("teams"):
            logger.warning("Team %s not found in Football-Data.org", team_name)
            return []

        team_id = None
        for team in search_data["teams"]:
            if team.get("name", "").lower() == team_name.lower():
                team_id = team["id"]
                break

        if not team_id:
            team_id = search_data["teams"][0]["id"]

        params = {"status": "FINISHED", "limit": limit}
        data = await self._make_request(
            f"/teams/{team_id}/matches",
            params,
        )
        if not data or not data.get("matches"):
            return []

        matches: list[Match] = []
        for fixture in data["matches"]:
            try:
                league_code = "UNKNOWN"
                comp_code = fixture.get("competition", {}).get("code")
                if comp_code:
                    for k, v in COMPETITION_CODE_MAPPING.items():
                        if v == comp_code:
                            league_code = k
                            break

                league = League(
                    id=league_code,
                    name=fixture.get("competition", {}).get("name", "Unknown"),
                    country="Unknown",
                    season=str(fixture.get("season", {}).get("startDate", "")[:4]),
                )

                match = self._parse_match(fixture, league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug("Error parsing team history match: %s", e)
                continue

        return matches

    async def get_live_matches(self) -> list[Match]:
        """Get all live matches globally."""
        if not self.is_configured:
            return []

        await self._wait_strict()

        data = await self._make_request("/matches", {"status": "LIVE"})
        if not data or not data.get("matches"):
            data = await self._make_request("/matches", {"status": "IN_PLAY"})

        if not data or not data.get("matches"):
            return []

        matches: list[Match] = []
        for match_data in data["matches"]:
            try:
                competition = match_data.get("competition", {})
                comp_code = competition.get("code")

                league_code = "UNKNOWN"
                for internal, external in COMPETITION_CODE_MAPPING.items():
                    if external == comp_code:
                        league_code = internal
                        break

                league = League(
                    id=league_code,
                    name=competition.get("name", "Unknown"),
                    country=competition.get("area", {}).get("name", "Unknown"),
                )

                match = self._parse_match(match_data, league)
                if match:
                    matches.append(match)
            except Exception as e:
                logger.debug("Error parsing live match: %s", e)
                continue

        logger.info("Football-Data.org: Found %d live matches", len(matches))
        return matches
