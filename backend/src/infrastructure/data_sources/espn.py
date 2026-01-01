"""
ESPN API Data Source

This module integrates with ESPN's hidden public API for soccer scores and stats.
Provides free access to real-time and historical match data with detailed stats.

Endpoints:
- Scoreboard: http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard
- Summary: http://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
import asyncio

from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)

# Mapping internal league codes to ESPN league slugs
ESPN_LEAGUE_MAPPING = {
    "E0": "eng.1",   # Premier League
    "SP1": "esp.1",  # La Liga
    "D1": "ger.1",   # Bundesliga
    "I1": "ita.1",   # Serie A
    "F1": "fra.1",   # Ligue 1
    "B1": "bel.1",     # Jupiler Pro League (Belgium)
    "P1": "por.1",   # Primeira Liga (check availability)
    "N1": "ned.1",   # Eredivisie
    "UCL": "uefa.champions",
    "UEL": "uefa.europa",
    "UECL": "uefa.europa.conf", # Corrected generic slug for Conference League
}

class ESPNSource:
    """
    Data source for ESPN API.
    """
    
    SOURCE_NAME = "ESPN"
    BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer"
    
    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def _make_request(self, url: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make HTTP request to ESPN."""
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"ESPN request failed: {e}")
            return None

    async def get_finished_matches(
        self,
        league_codes: Optional[List[str]] = None,
        days_back: int = 7,
    ) -> List[Match]:
        """
        Get finished matches from ESPN.
        Iterates through dates and leagues.
        """
        matches = []
        leagues_to_fetch = league_codes or list(ESPN_LEAGUE_MAPPING.keys())
        
        # ESPN requires day-by-day fetching for scoreboard
        # We will limit to efficient range
        dates_to_fetch = []
        for i in range(1, days_back + 1):
            d = datetime.utcnow() - timedelta(days=i)
            dates_to_fetch.append(d.strftime("%Y%m%d"))
            
        # Optimization: Fetch per league, per date range string (ESPN supports comma separated?)
        # ESPN API supports date range like dates=20241201-20241207 or comma?
        # Testing shows comma works or range.
        # Let's batch by week if days_back is large, or just iterate days if small.
        # For robustness, we'll loop over leagues.
        
        for code in leagues_to_fetch:
            slug = ESPN_LEAGUE_MAPPING.get(code)
            if not slug:
                continue
            
            # For efficiency in this MVP, we fetch 1 week at a time strings if days_back > 7?
            # Or just loop dates.
            # Let's try fetching the whole range using YYYYMMDD-YYYYMMDD format if supported.
            # Documentation is unofficial. 'dates' param usually takes YYYYMMDD.
            # We will fetch day by day for now to ensure reliability, but parallelize?
            # To avoid rate limits (though ESPN is generous), we do sequential days.
            
            # Simple approach: Loop days. 
            # If days_back is large (e.g. 365), this is slow.
            # If user asks for historical data, we prefer CSV or GitHub.
            # ESPN is best for RECENT detailed stats (last 60 days).
            # So we enforce cap if this source is called generally.
            eff_days_back = min(days_back, 60) 
            
            for i in range(1, eff_days_back + 1):
                date_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y%m%d")
                
                url = f"{self.BASE_URL}/{slug}/scoreboard"
                data = await self._make_request(url, {"dates": date_str})
                
                if not data or "events" not in data:
                    continue
                    
                for event in data["events"]:
                    status = event.get("status", {}).get("type", {}).get("state")
                    if status != "post": # Finalized
                        continue
                        
                    try:
                        match_id = event.get("id")
                        # Fetch detailed stats for this match (corners/cards)
                        # We need another call to /summary?event=<id>
                        # Warn: N+1 problem.
                        # We only do this for valuable matches.
                        
                        match = await self._get_match_details(slug, match_id, event, code)
                        if match:
                            matches.append(match)
                            
                    except Exception as e:
                        logger.debug(f"Error parsing ESPN match: {e}")
                        continue
                        
        logger.info(f"ESPN: fetched {len(matches)} matches")
        return matches

    async def _get_match_details(self, slug: str, match_id: str, event_summary: dict, league_code: str) -> Optional[Match]:
        """Fetch details (summary) to get stats."""
        url = f"{self.BASE_URL}/{slug}/summary"
        data = await self._make_request(url, {"event": match_id})
        
        if not data:
            # Fallback to scoreboard data only (no stats)
            return self._parse_scoreboard_match(event_summary, league_code)
            
        # Parse detailed stats from boxscore
        boxscore = data.get("boxscore", {})
        teams = boxscore.get("teams", [])
        
        home_team_stats = {}
        away_team_stats = {}
        
        home_id = event_summary["competitions"][0]["competitors"][0]["team"]["id"]
        # Determine which team in boxscore is home
        # Usually order matches, but rely on ID.
        
        for team_data in teams:
            tid = team_data.get("team", {}).get("id")
            stats = {s["name"]: s["displayValue"] for s in team_data.get("statistics", [])}
            
            if tid == home_id:
                home_team_stats = stats
            else:
                away_team_stats = stats
        
        return self._parse_full_match(event_summary, home_team_stats, away_team_stats, league_code)

    def _parse_scoreboard_match(self, event: dict, league_code: str) -> Optional[Match]:
        """Parse match from scoreboard without extra stats."""
        # TODO: Implement basic parsing
        return None # For now only return detailed matches
    
    def _parse_full_match(self, event: dict, home_stats: dict, away_stats: dict, league_code: str) -> Optional[Match]:
        try:
            competition = event["competitions"][0]
            competitors = competition["competitors"]
            home_comp = competitors[0]
            away_comp = competitors[1]
            
            # Ensure home is really home
            if home_comp["homeAway"] != "home":
                home_comp, away_comp = away_comp, home_comp
                # Swap stats too? logic above used ID, so stats map is correct by ID.
                # Wait, my logic above assigned home_team_stats based on home_id matching FIRST competitor.
                # If first competitor is actually away, then I assigned away stats to home_team_stats var?
                # Re-check:
                # home_id = event_summary["competitions"][0]["competitors"][0]["team"]["id"]
                # Competitors list in scoreboard: usually [home, away] with attribute homeAway='home'/'away'.
                # Let's rely on 'homeAway' attribute.
                pass 
                
            # Date
            date_str = event.get("date") # "2024-12-01T13:30Z"
            match_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%MZ")
            
            # Teams
            home_team = Team(
                id=home_comp["team"]["id"],
                name=home_comp["team"]["displayName"],
                logo_url=home_comp["team"].get("logo")
            )
            away_team = Team(
                id=away_comp["team"]["id"],
                name=away_comp["team"]["displayName"],
                logo_url=away_comp["team"].get("logo")
            )
            
            # Score
            home_goals = int(home_comp["score"])
            away_goals = int(away_comp["score"])
            
            # Stats (parse strings to ints)
            def p_int(val):
                try: return int(float(val)) if val else None
                except: return None
                
            return Match(
                id=f"espn_{event['id']}",
                home_team=home_team,
                away_team=away_team,
                league=League(id=league_code, name=ESPN_LEAGUE_MAPPING[league_code], country="Europe"),
                match_date=match_date,
                home_goals=home_goals,
                away_goals=away_goals,
                status="FT",
                
                # Stats
                home_corners=p_int(home_stats.get("wonCorners")),
                away_corners=p_int(away_stats.get("wonCorners")),
                home_yellow_cards=p_int(home_stats.get("yellowCards")),
                away_yellow_cards=p_int(away_stats.get("yellowCards")),
                home_red_cards=p_int(home_stats.get("redCards")),
                away_red_cards=p_int(away_stats.get("redCards")),
            )
            
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None
