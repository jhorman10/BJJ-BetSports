"""
Training Data Service

Orchestrates the fetching, merging, and enrichment of training data
from multiple sources (GitHub, CSV, API-Football, ESPN, etc.).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional, cast

from src.application.use_cases.use_cases import DataSources
from src.core.constants import DEFAULT_LEAGUES
from src.domain.constants import (
    ALL_INTERNATIONAL_TOURNAMENTS,
    NATIONAL_TEAM_TOURNAMENTS,
)
from src.domain.entities.entities import League, Match, TrainingDataContextBundle
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.team_competition_context_resolver import (
    TeamCompetitionContext,
    TeamCompetitionContextResolver,
)
from src.utils.time_utils import COLOMBIA_TZ, get_current_time

logger = logging.getLogger(__name__)


class TrainingDataService:
    """
    Application service for orchestrating training data collection.
    """

    def __init__(
        self,
        data_sources: DataSources,
        enrichment_service: MatchEnrichmentService,
        context_resolver: Optional[TeamCompetitionContextResolver] = None,
    ) -> None:
        self.data_sources = data_sources
        self.enrichment_service = enrichment_service
        self.context_resolver = context_resolver or TeamCompetitionContextResolver()

    async def _fetch_github_matches(
        self, leagues: List[str], start_date: Optional[str], days_back: Optional[int]
    ) -> List[Match]:
        """Fetch matches from the GitHub dataset with the same semantics as the
        original inline implementation. Returns empty list on failure."""
        try:
            from src.infrastructure.data_sources.github_dataset import (
                LocalGithubDataSource,
            )

            gh_data = LocalGithubDataSource()
            gh_start_dt = None
            if start_date:
                try:
                    gh_start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError as e:
                    logger.debug(f"GitHub date parsing skipped (invalid format): {e}")
            elif days_back:
                gh_start_dt = get_current_time() - timedelta(days=days_back)

            github_matches = await gh_data.get_finished_matches(
                league_codes=leagues, date_from=gh_start_dt
            )
            return cast(List[Match], github_matches)
        except Exception as e:
            logger.warning(f"GitHub Dataset fetch failed: {e}")
            return []

    async def _fetch_csv_for_league(
        self, lid: str, force_refresh: bool, days_back: Optional[int]
    ) -> List[Match]:
        """Fetch CSV/historical matches for a single league and apply backfill
        when CSV appears stale."""
        try:
            matches = await self.data_sources.football_data_uk.get_historical_matches(
                lid, seasons=None, force_refresh=force_refresh
            )

            if matches:
                matches.sort(key=lambda x: x.match_date)
                last_match_date = matches[-1].match_date

                if last_match_date.tzinfo is None:
                    last_match_date = COLOMBIA_TZ.localize(last_match_date)

                now = get_current_time()
                days_lag = (now - last_match_date).days

                if days_lag > 3:
                    logger.warning(
                        "CSV data for %s is stale (%d days). " "Triggering backfill...",
                        lid,
                        days_lag,
                    )
                    start_backfill = last_match_date + timedelta(days=1)
                    gap_matches = await self._backfill_gap(lid, start_backfill, now)
                    if gap_matches:
                        logger.info(
                            "Backfilled %d matches for %s", len(gap_matches), lid
                        )
                        matches.extend(gap_matches)

            return matches or []
        except Exception as e:
            logger.error(f"Error fetching CSV/Backfill for {lid}: {e}")
            return []

    async def _fetch_football_data_org_matches(
        self, leagues: List[str], days_back: Optional[int]
    ) -> List[Match]:
        try:
            if self.data_sources.football_data_org.is_configured:
                start_dt = get_current_time() - timedelta(days=days_back or 550)
                api_fb_matches = (
                    await self.data_sources.football_data_org.get_finished_matches(
                        date_from=start_dt.strftime("%Y-%m-%d"),
                        date_to=get_current_time().strftime("%Y-%m-%d"),
                        league_codes=leagues,
                    )
                )
                if api_fb_matches:
                    logger.info(
                        f"Football-Data.org: loaded {len(api_fb_matches)} matches"
                    )
                return api_fb_matches or []
        except Exception as e:
            logger.warning(f"Football-Data.org fetch failed: {e}")
        return []

    async def _fetch_espn_matches(self, leagues: List[str]) -> List[Match]:
        try:
            from src.infrastructure.data_sources.espn import ESPNSource

            espn = ESPNSource()
            espn_matches = await espn.get_finished_matches(
                league_codes=leagues, days_back=60
            )
            return espn_matches or []
        except Exception as e:
            logger.warning(f"ESPN fetch failed for training data: {e}")
            return []

    async def _fetch_openfootball_matches(self, leagues: List[str]) -> List[Match]:
        open_football_matches: List[Match] = []
        try:
            from src.infrastructure.data_sources.football_data_uk import (
                LEAGUES_METADATA,
            )
            from src.infrastructure.data_sources.openfootball import OpenFootballSource

            open_fb = OpenFootballSource()
            for league_code in leagues:
                # Use correct country from LEAGUES_METADATA
                country = "Europe"
                if league_code in LEAGUES_METADATA:
                    country = LEAGUES_METADATA[league_code].get("country", "Europe")
                league_entity = League(
                    id=league_code, name=league_code, country=country
                )
                of_matches = await open_fb.get_matches(league_entity)
                open_football_matches.extend(of_matches)
            if open_football_matches:
                logger.info(
                    f"OpenFootball: loaded {len(open_football_matches)} matches"
                )
            return open_football_matches
        except Exception as e:
            logger.warning(f"OpenFootball fetch failed for training data: {e}")
            return []

    def _get_sortable_date(self, m: Match) -> datetime:
        dt = m.match_date
        if dt.tzinfo is None:
            return cast(datetime, COLOMBIA_TZ.localize(dt))
        return cast(datetime, dt)

    async def fetch_contextual_training_data(
        self,
        leagues: List[str],
        days_back: Optional[int] = None,
        start_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> TrainingDataContextBundle:
        """Return an explicit target/support bundle for contextual training flows."""
        target_matches = await self.fetch_comprehensive_training_data(
            leagues=leagues,
            days_back=days_back,
            start_date=start_date,
            force_refresh=force_refresh,
        )

        if not target_matches or not self._requires_contextual_bundle(leagues):
            return self._build_domestic_training_bundle(leagues, target_matches)

        support_candidates = await self._fetch_contextual_support_candidates(
            leagues=leagues,
            days_back=days_back,
            start_date=start_date,
            force_refresh=force_refresh,
        )
        candidate_matches = self.enrichment_service.merge_matches(
            list(target_matches), support_candidates
        )
        return self._build_international_training_bundle(
            leagues=leagues,
            target_matches=target_matches,
            candidate_matches=candidate_matches,
        )

    def _requires_contextual_bundle(self, leagues: List[str]) -> bool:
        return any(league_id in ALL_INTERNATIONAL_TOURNAMENTS for league_id in leagues)

    async def _fetch_contextual_support_candidates(
        self,
        leagues: List[str],
        days_back: Optional[int],
        start_date: Optional[str],
        force_refresh: bool,
    ) -> List[Match]:
        support_leagues = sorted(set(DEFAULT_LEAGUES).union(leagues))
        return await self.fetch_comprehensive_training_data(
            leagues=support_leagues,
            days_back=days_back,
            start_date=start_date,
            force_refresh=force_refresh,
        )

    def _build_domestic_training_bundle(
        self, leagues: List[str], target_matches: List[Match]
    ) -> TrainingDataContextBundle:
        sorted_target_matches = sorted(target_matches, key=self._get_sortable_date)
        return TrainingDataContextBundle(
            target_matches=sorted_target_matches,
            support_matches=[],
            support_matches_by_team={},
            coverage_report={
                "mode": "domestic",
                "requested_league_ids": tuple(leagues),
                "target_match_count": len(sorted_target_matches),
                "support_match_count": 0,
                "team_count": 0,
                "teams": {},
            },
        )

    def _build_international_training_bundle(
        self,
        leagues: List[str],
        target_matches: List[Match],
        candidate_matches: List[Match],
    ) -> TrainingDataContextBundle:
        sorted_target_matches = sorted(target_matches, key=self._get_sortable_date)
        target_match_keys = {
            self._build_match_key(match) for match in sorted_target_matches
        }
        target_matches_by_team = self._group_target_matches_by_team(
            sorted_target_matches
        )

        support_matches_by_team: dict[str, List[Match]] = {}
        support_match_map: dict[str, Match] = {}
        team_reports: dict[str, dict[str, Any]] = {}

        for normalized_team_name, team_target_matches in target_matches_by_team.items():
            anchor_match = max(team_target_matches, key=self._get_sortable_date)
            context = self.context_resolver.resolve(
                normalized_team_name, anchor_match, candidate_matches
            )
            team_support_matches = [
                match
                for match in candidate_matches
                if self._match_contains_team(normalized_team_name, match)
                and self._build_match_key(match) not in target_match_keys
                and self._match_is_valid_support(match, context)
            ]
            team_support_matches.sort(key=self._get_sortable_date)

            support_matches_by_team[normalized_team_name] = team_support_matches
            for match in team_support_matches:
                support_match_map.setdefault(self._build_match_key(match), match)

            team_reports[normalized_team_name] = {
                "participant_type": context.participant_type,
                "base_competition_id": context.base_competition_id,
                "support_competition_ids": context.support_competition_ids,
                "target_match_count": len(team_target_matches),
                "support_match_count": len(team_support_matches),
                "confidence": context.confidence,
                "evidence": context.evidence,
            }

        support_matches = sorted(
            support_match_map.values(), key=self._get_sortable_date
        )
        return TrainingDataContextBundle(
            target_matches=sorted_target_matches,
            support_matches=support_matches,
            support_matches_by_team=support_matches_by_team,
            coverage_report={
                "mode": "international",
                "requested_league_ids": tuple(leagues),
                "target_match_count": len(sorted_target_matches),
                "support_match_count": len(support_matches),
                "team_count": len(target_matches_by_team),
                "teams": team_reports,
            },
        )

    def _group_target_matches_by_team(
        self, target_matches: List[Match]
    ) -> dict[str, List[Match]]:
        grouped_matches: dict[str, List[Match]] = {}
        for match in target_matches:
            for team_name in (match.home_team.name, match.away_team.name):
                normalized_team_name = StatisticsService.normalize_team_name(team_name)
                grouped_matches.setdefault(normalized_team_name, []).append(match)
        return grouped_matches

    def _match_contains_team(self, normalized_team_name: str, match: Match) -> bool:
        return normalized_team_name in {
            StatisticsService.normalize_team_name(match.home_team.name),
            StatisticsService.normalize_team_name(match.away_team.name),
        }

    def _match_is_valid_support(
        self, match: Match, context: TeamCompetitionContext
    ) -> bool:
        if context.participant_type == "national_team":
            return match.league.id in NATIONAL_TEAM_TOURNAMENTS

        relevant_competitions = set(context.support_competition_ids)
        if context.base_competition_id:
            relevant_competitions.add(context.base_competition_id)
        return match.league.id in relevant_competitions

    def _build_match_key(self, match: Match) -> str:
        return "|".join(
            [
                match.match_date.strftime("%Y-%m-%d"),
                StatisticsService.normalize_team_name(match.home_team.name),
                StatisticsService.normalize_team_name(match.away_team.name),
                match.league.id,
            ]
        )

    async def fetch_comprehensive_training_data(
        self,
        leagues: List[str],
        days_back: Optional[int] = None,
        start_date: Optional[str] = None,
        force_refresh: bool = False,
    ) -> List[Match]:
        """
        Fetch and unify data from ALL sources for training.
        """
        logger.info(f"Orchestrating comprehensive training data for leagues: {leagues}")

        # Buckets for different sources
        gh_matches = await self._fetch_github_matches(leagues, start_date, days_back)

        # CSV source (sequential per-league to respect rate limits during backfill)
        results = []
        for lid in leagues:
            res = await self._fetch_csv_for_league(lid, force_refresh, days_back)
            results.append(res)
        csv_matches = []
        for res in results:
            csv_matches.extend(res or [])

        api_fb_matches = await self._fetch_football_data_org_matches(leagues, days_back)
        espn_matches = await self._fetch_espn_matches(leagues)
        open_football_matches = await self._fetch_openfootball_matches(leagues)

        # --- UNIFY & ENRICH ---
        all_matches = gh_matches
        all_matches = self.enrichment_service.merge_matches(all_matches, csv_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, api_fb_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, espn_matches)
        all_matches = self.enrichment_service.merge_matches(
            all_matches, open_football_matches
        )

        # Sort by standardized date
        all_matches.sort(key=self._get_sortable_date)

        # Final filtering
        if start_date:
            try:
                start_dt = COLOMBIA_TZ.localize(
                    datetime.strptime(start_date, "%Y-%m-%d")
                )
                all_matches = [
                    m for m in all_matches if self._get_sortable_date(m) >= start_dt
                ]
            except ValueError as e:
                logger.debug(f"Start date parsing skipped (invalid format): {e}")
        elif days_back:
            start_dt = get_current_time().replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - timedelta(days=days_back)
            all_matches = [
                m for m in all_matches if self._get_sortable_date(m) >= start_dt
            ]

        logger.info(f"Unification complete: {len(all_matches)} total training matches")
        return all_matches

    async def _backfill_gap(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        """
        Fetch matches from fallback sources (Football-Data.org, OpenFootball)
        to fill gap between static CSVs and today.
        """
        # Try Football-Data.org first (best recent coverage)
        backfilled = await self._backfill_via_football_data_org(
            league_code, start_date, end_date
        )
        if backfilled:
            return backfilled

        # Fallback: try OpenFootball for historical seasons
        backfilled = await self._backfill_via_openfootball(
            league_code, start_date, end_date
        )
        return backfilled

    async def _backfill_via_football_data_org(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        try:
            if self.data_sources.football_data_org.is_configured:
                logger.info(
                    "Backfilling %s via Football-Data.org from %s to %s...",
                    league_code,
                    start_date.date(),
                    end_date.date(),
                )
                fd_matches = (
                    await self.data_sources.football_data_org.get_finished_matches(
                        date_from=start_date.strftime("%Y-%m-%d"),
                        date_to=end_date.strftime("%Y-%m-%d"),
                        league_codes=[league_code],
                    )
                )
                typed_matches = cast(List[Match], fd_matches)
                if typed_matches:
                    logger.info(
                        "✓ Found %d backfill matches in Football-Data.org for %s",
                        len(typed_matches),
                        league_code,
                    )
                    return typed_matches
                else:
                    logger.info(
                        f"No matches found in Football-Data.org for {league_code} gap."
                    )
            else:
                logger.info(
                    "Skipping Football-Data.org backfill for %s: "
                    "API key not configured.",
                    league_code,
                )
        except Exception as e:
            logger.warning(
                f"Backfill source Football-Data.org failed for {league_code}: {e}"
            )
        return []

    async def _backfill_via_openfootball(
        self, league_code: str, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        try:
            from src.domain.entities.entities import League
            from src.infrastructure.data_sources.football_data_uk import (
                LEAGUES_METADATA,
            )

            if league_code in LEAGUES_METADATA:
                meta = LEAGUES_METADATA[league_code]
                league = League(
                    id=league_code, name=meta["name"], country=meta["country"]
                )

                of_matches = await self.data_sources.openfootball.get_matches(league)

                relevant_matches = []
                for m in of_matches:
                    m_date = m.match_date
                    if m_date.tzinfo is None and start_date.tzinfo:
                        m_date = COLOMBIA_TZ.localize(m_date)
                    if start_date <= m_date <= end_date:
                        relevant_matches.append(m)

                if relevant_matches:
                    logger.info(
                        "✓ Found %d backfill matches in OpenFootball for %s",
                        len(relevant_matches),
                        league_code,
                    )
                    return relevant_matches
        except Exception as e:
            logger.warning(
                f"Backfill source OpenFootball failed for {league_code}: {e}"
            )
        return []
