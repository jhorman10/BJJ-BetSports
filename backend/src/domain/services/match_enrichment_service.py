"""
Match Enrichment Service

This service provides logic to merge match data from multiple sources.
It helps fill in missing statistics (corners, cards, shots) by finding the 
same match in different data sources (e.g., CSV vs API).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from src.domain.entities.entities import Match, Team, League
from src.domain.services.statistics_service import StatisticsService

logger = logging.getLogger(__name__)

class MatchEnrichmentService:
    """
    Service for enriching and merging match data from multiple sources.
    """
    
    def __init__(self, statistics_service: StatisticsService = None):
        self.statistics_service = statistics_service or StatisticsService()

    def merge_matches(self, primary_matches: List[Match], secondary_matches: List[Match]) -> List[Match]:
        """
        Merge two lists of matches. 
        If a match exists in both, prefer the one with more detailed statistics.
        """
        merged_map = {}
        
        # Helper to create a deduplication key
        def get_match_key(m: Match) -> str:
            date_str = m.match_date.strftime("%Y-%m-%d")
            # Use normalized names for better matching across sources
            h_norm = self.statistics_service._normalize_name(m.home_team.name)
            a_norm = self.statistics_service._normalize_name(m.away_team.name)
            return f"{date_str}|{h_norm}|{a_norm}"

        # 1. Add all primary matches
        for m in primary_matches:
            key = get_match_key(m)
            merged_map[key] = m
            
        # 2. Add secondary matches if they provide better data or are new
        for m in secondary_matches:
            key = get_match_key(m)
            if key in merged_map:
                existing = merged_map[key]
                # Merge logic: if secondary has stats that primary lacks, update primary
                self._enrich_match(existing, m)
            else:
                merged_map[key] = m
                
        return list(merged_map.values())

    def _enrich_match(self, base: Match, source: Match):
        """
        Enrich base match with data from source match if available.
        """
        # Goals (sanity check, usually should match)
        if base.home_goals is None: base.home_goals = source.home_goals
        if base.away_goals is None: base.away_goals = source.away_goals
        
        # Corners (High value for picks)
        if base.home_corners is None: base.home_corners = source.home_corners
        if base.away_corners is None: base.away_corners = source.away_corners
        
        # Yellow Cards
        if base.home_yellow_cards is None: base.home_yellow_cards = source.home_yellow_cards
        if base.away_yellow_cards is None: base.away_yellow_cards = source.away_yellow_cards
        
        # Red Cards
        if base.home_red_cards is None: base.home_red_cards = source.home_red_cards
        if base.away_red_cards is None: base.away_red_cards = source.away_red_cards
        
        # Shots (Advanced stats)
        if hasattr(base, 'home_shots_on_target') and hasattr(source, 'home_shots_on_target'):
            if base.home_shots_on_target is None: base.home_shots_on_target = source.home_shots_on_target
        if hasattr(base, 'away_shots_on_target') and hasattr(source, 'away_shots_on_target'):
            if base.away_shots_on_target is None: base.away_shots_on_target = source.away_shots_on_target

    def find_match_overlap(self, target: Match, candidates: List[Match]) -> Optional[Match]:
        """
        Find a specific match in a list of candidates.
        Uses fuzzy name matching and date proximity.
        """
        target_date = target.match_date.date()
        target_h = self.statistics_service._normalize_name(target.home_team.name)
        target_a = self.statistics_service._normalize_name(target.away_team.name)
        
        for cand in candidates:
            # Allow 1 day difference for timezone shifts in different sources
            if abs((cand.match_date.date() - target_date).days) <= 1:
                cand_h = self.statistics_service._normalize_name(cand.home_team.name)
                cand_a = self.statistics_service._normalize_name(cand.away_team.name)
                
                if target_h == cand_h and target_a == cand_a:
                    return cand
                    
        return None
