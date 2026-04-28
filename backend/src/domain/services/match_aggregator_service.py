"""
Match Aggregator Service

This domain service is responsible for:
1. Fetching historical matches from all available data sources
    (UK, Org, Open) in parallel.
2. Fetching upcoming matches from all available data sources.
3. Merging and deduplicating match data, prioritizing the richest sources.
4. Implementing strict aggregation rules as per project standards.
5. Enforcing Data Sanity (Refactoring Rule 13).
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Coroutine, List

from src.domain.constants import ALL_INTERNATIONAL_TOURNAMENTS
from src.domain.entities.entities import League, Match
from src.infrastructure.data_sources.espn import ESPNSource
from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.infrastructure.data_sources.openfootball import OpenFootballSource
from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
from src.utils.time_utils import get_current_time

logger = logging.getLogger(__name__)


class MatchAggregatorService:
    def __init__(
        self,
        football_data_uk: FootballDataUKSource,
        football_data_org: FootballDataOrgSource,
        openfootball: OpenFootballSource,
        thesportsdb: TheSportsDBClient,
        espn: ESPNSource,
    ):
        self.football_data_uk = football_data_uk
        self.football_data_org = football_data_org
        self.openfootball = openfootball
        self.thesportsdb = thesportsdb
        self.espn = espn

    async def get_aggregated_history(
        self, league_id: str, seasons: List[str]
    ) -> List[Match]:
        """
        Fetch historical matches from ALL sources in parallel, merge them,
        and validate sanity.
        """
        logger.info("Aggregating history for %s from all sources...", league_id)

        # Define parallel tasks
        tasks: List[Coroutine[Any, Any, Any]] = []

        # 1. Football-Data.co.uk (Primary)
        tasks.append(
            self.football_data_uk.get_historical_matches(
                league_id,
                seasons=seasons,
            )
        )

        # 2. Football-Data.org (Secondary)
        if self.football_data_org.is_configured:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)
            tasks.append(
                self.football_data_org.get_finished_matches(
                    date_from=start_date.strftime("%Y-%m-%d"),
                    date_to=end_date.strftime("%Y-%m-%d"),
                    league_codes=[league_id],
                )
            )
        else:
            tasks.append(asyncio.sleep(0))

        # 3. ESPN (Support for UCL/International)
        if self.espn:
            # ESPN is great for recent history of UCL
            tasks.append(
                self.espn.get_finished_matches(
                    league_codes=[league_id],
                    days_back=120,  # Get last 4 months for UCL context
                )
            )
        else:
            tasks.append(asyncio.sleep(0))

        # 4. OpenFootball (Fallback)
        from src.infrastructure.data_sources.football_data_uk import LEAGUES_METADATA

        if self.openfootball and league_id in LEAGUES_METADATA:
            meta = LEAGUES_METADATA[league_id]
            league_entity = League(
                id=league_id, name=meta["name"], country=meta["country"]
            )
            tasks.append(self.openfootball.get_matches(league_entity))
        else:
            tasks.append(asyncio.sleep(0))

        # Execute
        results = await asyncio.gather(*tasks, return_exceptions=True)

        uk_matches: List[Match] = results[0] if isinstance(results[0], list) else []
        org_matches: List[Match] = results[1] if isinstance(results[1], list) else []
        espn_matches: List[Match] = results[2] if isinstance(results[2], list) else []
        open_matches: List[Match] = results[3] if isinstance(results[3], list) else []

        if isinstance(results[0], Exception):
            logger.warning("UK Source Error: %s", results[0])
        if isinstance(results[2], Exception):
            logger.warning("ESPN Source Error: %s", results[2])

        # Merge
        merged_matches = self._merge_matches(
            uk_matches, org_matches, open_matches, espn_matches
        )

        # Validate Sanity (Rule 13)
        valid_matches = []
        rejected_count = 0
        for m in merged_matches:
            if self._is_data_sane(m):
                valid_matches.append(m)
            else:
                rejected_count += 1

        if rejected_count > 0:
            logger.warning(
                "Rejected %s matches due to Data Sanity violations (Outliers).",
                rejected_count,
            )

        return valid_matches

    def _is_data_sane(self, match: Match) -> bool:
        """
        Rule 13: Data Sanity / Outlier Detection.
        Returns False if match data implies corruption or absurdity.
        """
        # 1. Goal Sanity
        total_goals = (match.home_goals or 0) + (match.away_goals or 0)
        if total_goals > 20:  # Example threshold: >20 goals is likely bad data
            return False

        # 2. Score Sanity (Negative scores)
        if (match.home_goals is not None and match.home_goals < 0) or (
            match.away_goals is not None and match.away_goals < 0
        ):
            return False

        # 3. Date sanity (Future date for finished match?)
        # if match.status == "FT" and match.match_date > datetime.now(...) # Handled
        # elsewhere usually

        return True

    def _merge_matches(
        self,
        uk: List[Match],
        org: List[Match],
        open_src: List[Match],
        espn_src: List[Match],
    ) -> List[Match]:
        """
        Merge strategy: UK > Org > ESPN > Open.
        CRITICAL REFACTOR: Performs Deep Merge (Enrichment) instead of
        simple deduplication.
        If a match exists, we fill in missing fields (Corners, Cards,
        Referee) from secondary sources.
        """
        merged = {}
        from src.domain.services.statistics_service import StatisticsService

        def get_merge_key(m: Match) -> str:
            # Robust key generation using normalized names
            date_str = m.match_date.strftime("%Y%m%d")
            h_norm = StatisticsService.normalize_team_name(m.home_team.name)
            a_norm = StatisticsService.normalize_team_name(m.away_team.name)
            return f"{date_str}_{h_norm}_{a_norm}"

        def enrich_match(target: Match, source: Match) -> None:
            # Fill missing core stats
            if target.home_corners is None and source.home_corners is not None:
                target.home_corners = source.home_corners
            if target.away_corners is None and source.away_corners is not None:
                target.away_corners = source.away_corners

            if (
                target.home_yellow_cards is None
                and source.home_yellow_cards is not None
            ):
                target.home_yellow_cards = source.home_yellow_cards
            if (
                target.away_yellow_cards is None
                and source.away_yellow_cards is not None
            ):
                target.away_yellow_cards = source.away_yellow_cards

            if target.home_red_cards is None and source.home_red_cards is not None:
                target.home_red_cards = source.home_red_cards
            if target.away_red_cards is None and source.away_red_cards is not None:
                target.away_red_cards = source.away_red_cards

            # Fill Extended Stats
            if target.home_total_shots is None and source.home_total_shots is not None:
                target.home_total_shots = source.home_total_shots
            if target.away_total_shots is None and source.away_total_shots is not None:
                target.away_total_shots = source.away_total_shots

            # Fill Referee if missing
            if not target.referee and source.referee:
                target.referee = source.referee

        def process_list(matches: List[Match] | None, source_tag: str) -> int:
            count = 0
            if not matches:
                return count
            for m in matches:
                # Basic validation
                if m.status not in ["FT", "AET", "PEN", "FINISHED", "post"]:
                    continue
                if not m.match_date:
                    continue

                key = get_merge_key(m)

                if key not in merged:
                    merged[key] = m
                    count += 1
                else:
                    # EXISTING MATCH FOUND -> ENRICH IT (Rule 2A)
                    enrich_match(merged[key], m)

            return count

        # Process in order of priority (Primary creates the base, Secondary fills gaps)
        c_uk = process_list(uk or [], "UK")
        c_org = process_list(org or [], "Org")
        c_espn = process_list(espn_src or [], "ESPN")
        c_open = process_list(open_src or [], "Open")

        logger.info(
            "Merged History: UK=%s, Org=%s, ESPN=%s, Open=%s. Unique Total=%s",
            c_uk,
            c_org,
            c_espn,
            c_open,
            len(merged),
        )
        return list(merged.values())

    async def get_upcoming_matches(
        self, league_id: str, limit: int = 20
    ) -> List[Match]:
        """
        Fetch upcoming matches from available sources.
        """
        # Tournament leagues play less frequently, need more days_ahead
        days_ahead = 30 if league_id in ALL_INTERNATIONAL_TOURNAMENTS else 7

        # 1. Try ESPN (Primary - Has Odds)
        try:
            matches = await self.espn.get_upcoming_matches(
                league_id, days_ahead=days_ahead
            )
            if matches:
                return self._sort_and_limit(matches, limit)
        except Exception as e:
            logger.warning(f"ESPN upcoming fetch failed for {league_id}: {e}")

        # 2. Try Football-Data.org
        if self.football_data_org.is_configured:
            matches = await self.football_data_org.get_upcoming_matches(league_id)
            if matches:
                return self._sort_and_limit(matches, limit)

        # 3. Try TheSportsDB
        try:
            matches = await self.thesportsdb.get_upcoming_fixtures(
                league_id, next_n=limit
            )
            if matches:
                return self._sort_and_limit(matches, limit)
        except Exception as e:
            logger.debug(f"TheSportsDB upstream fetch error: {e}")

        # 4. Try OpenFootball
        try:
            from src.infrastructure.data_sources.football_data_uk import (
                LEAGUES_METADATA,
            )

            if self.openfootball and league_id in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_id]
                league_entity = League(
                    id=league_id, name=meta["name"], country=meta["country"]
                )
                matches = await self.openfootball.get_matches(league_entity)
                upcoming = [m for m in matches if m.status == "NS"]
                if upcoming:
                    return self._sort_and_limit(upcoming, limit)
        except Exception as e:
            logger.debug(f"OpenFootball upstream fetch error: {e}")

        return []

    def _sort_and_limit(self, matches: List[Match], limit: int) -> List[Match]:
        """Helper to strict sort by date and limit. Includes Sanity Check."""
        now = get_current_time()
        valid = []
        for m in matches:
            # Sanity Check for Upcoming
            odds_sane = True
            # Check odds if present (e.g. < 1.01) - Not always available in 'Match'
            # entity here, usually later in Enrichment

            m_date = m.match_date
            if m_date.tzinfo is None:
                from pytz import timezone as pytz_tz

                tz = pytz_tz("America/Bogota")
                m_date = tz.localize(m_date)
            else:
                m_date = m_date.astimezone(now.tzinfo)

            if m_date > now and odds_sane:
                valid.append(m)

        valid.sort(key=lambda x: x.match_date)
        return valid[:limit]
