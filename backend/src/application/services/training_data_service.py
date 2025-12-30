"""
Training Data Service

Orchestrates the fetching, merging, and enrichment of training data 
from multiple sources (GitHub, CSV, API-Football, ESPN, etc.).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.domain.entities.entities import Match
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.application.use_cases.use_cases import DataSources
from src.utils.time_utils import get_current_time, COLOMBIA_TZ

logger = logging.getLogger(__name__)

class TrainingDataService:
    """
    Application service for orchestrating training data collection.
    """

    def __init__(self, data_sources: DataSources, enrichment_service: MatchEnrichmentService):
        self.data_sources = data_sources
        self.enrichment_service = enrichment_service

    async def fetch_comprehensive_training_data(
        self, 
        leagues: List[str], 
        days_back: Optional[int] = None, 
        start_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[Match]:
        """
        Fetch and unify data from ALL sources for training.
        """
        logger.info(f"Orchestrating comprehensive training data for leagues: {leagues}")
        
        # Buckets for different sources
        csv_matches = []
        api_fb_matches = []
        fd_org_matches = []
        gh_matches = []
        espn_matches = []
        
        # 1. GitHub Dataset (Massive historical base)
        try:
            from src.infrastructure.data_sources.github_dataset import LocalGithubDataSource
            gh_data = LocalGithubDataSource()
            gh_start_dt = None
            if days_back:
                gh_start_dt = get_current_time() - timedelta(days=days_back)
            elif start_date:
                try: gh_start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                except ValueError: pass
            gh_matches = await gh_data.get_finished_matches(league_codes=leagues, date_from=gh_start_dt)
        except Exception as e:
            logger.warning(f"GitHub Dataset fetch failed: {e}")

        # 2. CSV source (Rich historical stats)
        for league_id in leagues:
            try:
                # Use dynamic seasons logic inside get_historical_matches
                matches = await self.data_sources.football_data_uk.get_historical_matches(
                    league_id, 
                    seasons=None, 
                    force_refresh=force_refresh
                )
                
                # --- BACKFILL STRATEGY ---
                # Check if CSV data is stale (older than 3 days)
                if matches:
                    # Sort to find latest date
                    matches.sort(key=lambda x: x.match_date)
                    last_match_date = matches[-1].match_date
                    
                    # Ensure timezone awareness for comparison
                    if last_match_date.tzinfo is None:
                        last_match_date = COLOMBIA_TZ.localize(last_match_date)
                        
                    now = get_current_time()
                    days_lag = (now - last_match_date).days
                    
                    if days_lag > 3:
                        logger.warning(f"CSV data for {league_id} is stale ({days_lag} days lag). Triggering backfill...")
                        start_backfill = last_match_date + timedelta(days=1)
                        gap_matches = await self._backfill_gap(league_id, start_backfill, now)
                        if gap_matches:
                            logger.info(f"Backfilled {len(gap_matches)} matches for {league_id} from API-Football")
                            matches.extend(gap_matches)
                
                csv_matches.extend(matches)
            except Exception as e:
                logger.error(f"Error fetching CSV/Backfill for {league_id}: {e}")

        # 3. API-Football (Highest detail stats)
        # DISABLED PER USER REQUEST for local training optimization
        # try:
        #     from src.infrastructure.data_sources.api_football import APIFootballSource
        #     api_fb = APIFootballSource()
        #     if api_fb.is_configured:
        #         today = get_current_time()
        #         date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        #         api_fb_matches = await api_fb.get_finished_matches(date_from, today.strftime("%Y-%m-%d"), leagues)
        # except Exception: pass

        # 4. ESPN (Detailed recent stats)
        try:
            from src.infrastructure.data_sources.espn import ESPNSource
            espn = ESPNSource()
            espn_matches = await espn.get_finished_matches(league_codes=leagues, days_back=30)
        except Exception: pass

        # 5. Football-Data.org (High coverage base)
        try:
            from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
            fd_org = FootballDataOrgSource()
            if fd_org.is_configured:
                today = get_current_time()
                date_from = (today - timedelta(days=60)).strftime("%Y-%m-%d")
                fd_org_matches = await fd_org.get_finished_matches(date_from, today.strftime("%Y-%m-%d"), leagues)
        except Exception: pass

        # --- UNIFY & ENRICH ---
        all_matches = gh_matches
        all_matches = self.enrichment_service.merge_matches(all_matches, fd_org_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, csv_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, api_fb_matches)
        all_matches = self.enrichment_service.merge_matches(all_matches, espn_matches)

        # Sort by date (standardized)
        def get_sortable_date(m):
            dt = m.match_date
            return COLOMBIA_TZ.localize(dt) if dt.tzinfo is None else dt

        all_matches.sort(key=get_sortable_date)
        
        # Final filtering
        if start_date:
            try:
                start_dt = COLOMBIA_TZ.localize(datetime.strptime(start_date, "%Y-%m-%d"))
                all_matches = [m for m in all_matches if get_sortable_date(m) >= start_dt]
            except ValueError: pass
        elif days_back:
            start_dt = get_current_time().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back)
            all_matches = [m for m in all_matches if get_sortable_date(m) >= start_dt]

        logger.info(f"Unification complete: {len(all_matches)} total training matches")
        return all_matches

    async def _backfill_gap(self, league_code: str, start_date: datetime, end_date: datetime) -> List[Match]:
        """
        Fetch matches from API-Football to fill gap between static CSVs and today.
        """
        return [] # DISABLED PER USER REQUEST
        # try:
        #     from src.infrastructure.data_sources.api_football import APIFootballSource
        #     api_fb = APIFootballSource()
        #     if not api_fb.is_configured:
        #         return []
        #         
        #     return await api_fb.get_finished_matches(
        #         date_from=start_date.strftime("%Y-%m-%d"),
        #         date_to=end_date.strftime("%Y-%m-%d"),
        #         league_codes=[league_code]
        #     )
        # except Exception as e:
        #     logger.warning(f"Backfill failed for {league_code}: {e}")
        #     return []
