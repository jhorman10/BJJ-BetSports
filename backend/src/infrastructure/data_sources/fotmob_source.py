"""
FotMob Data Source

Unofficial integration with FotMob API to fetch detailed match statistics
(Corners, Cards, xG, Shots) which are essential for high-quality picks.
"""

import logging
import aiohttp
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.domain.entities.entities import Match, Team, League

logger = logging.getLogger(__name__)

class FotMobSource:
    BASE_URL = "https://www.fotmob.com/api"
    
    def __init__(self):
        self.is_configured = True # Always available (free)

    # Mapping of FotMob League IDs to Internal Codes
    FOTMOB_LEAGUE_MAPPING = {
        47: "E0",   # Premier League
        48: "E1",   # Championship
        87: "SP1",  # La Liga
        54: "D1",   # Bundesliga
        55: "I1",   # Serie A
        53: "F1",   # Ligue 1
        57: "N1",   # Eredivisie
        61: "P1",   # Primeira Liga
        42: "UCL",  # Champions League
        73: "UEL",  # Europa League
        50: "EURO", # Euro
        77: "WC",   # World Cup
    }

    async def get_live_matches(self) -> List[Match]:
        """
        Fetch all currently live matches with detailed stats.
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/matches/live"
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    matches = []
                    
                    # FotMob returns { "leagues": [ { "matches": [...] } ] }
                    if not data or "leagues" not in data:
                        return []
                        
                    for league_group in data.get("leagues", []):
                        league_id = league_group.get("id")
                        internal_code = self.FOTMOB_LEAGUE_MAPPING.get(league_id)
                        
                        # Even if unmapped, we might want to return it for display?
                        # For now, let's keep unmapped as "UNKNOWN" or just skip if logic requires known league
                        # User wants visual stats, so we should allow unknown leagues.
                        
                        league_name = league_group.get("name", "Unknown League")
                        country_name = league_group.get("ccode", "World")
                        
                        for match_data in league_group.get("matches", []):
                            # We might need to fetch details for stats if they aren't in the list
                            # Often the 'list' view has minimal stats.
                            # Let's inspect the list item structure via one detail fetch or assumption.
                            # FotMob live list usually has score/time but NOT corners/cards details.
                            # We need to fetch details for each live match to get the corners/cards.
                            
                            match_id = match_data.get("id")
                            if not match_id: continue
                            
                            # Parallel fetch details for live matches (usually number of live games is manageable < 50)
                            # to avoid sequential slowness.
                            # We can collect IDs and fetch later or fetch here. 
                            # Let's verify _get_match_details use.
                            pass # Logic moved to parallel block below
                            
                    # Collect all match IDs first
                    live_match_ids = []
                    for league in data.get("leagues", []):
                        for m in league.get("matches", []):
                            if m.get("id"):
                                live_match_ids.append(str(m.get("id")))

                    if not live_match_ids:
                        return []
                        
                    # Fetch details in parallel
                    tasks = [self._get_match_details(session, mid) for mid in live_match_ids]
                    details_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for details in details_results:
                        if isinstance(details, dict):
                            # We need to map basic info from details mostly
                            # The details object usually contains 'general' which has league info too
                            general = details.get("general", {})
                            league_id = general.get("leagueId")
                            internal_code = self.FOTMOB_LEAGUE_MAPPING.get(league_id, "UNKNOWN")
                            
                            # Create Match
                            # We need to construct a 'basic_info' dict that _map_to_match expects
                            # OR refactor _map_to_match.
                            # Let's adapt _map_to_match to handle the full details object if passed as both args
                            
                            # Synthesize basic info from details for _map_to_match compatibility
                            basic_info = {
                                "id": general.get("matchId"),
                                "status": {"utcTime": general.get("matchTimeUTC"), "finished": False}, 
                                "home": {"name": general.get("homeTeam", {}).get("name")},
                                "away": {"name": general.get("awayTeam", {}).get("name")},
                                "scoreStr": details.get("header", {}).get("scoreStr")
                            }
                            
                            match_entity = self._map_to_match(basic_info, details)
                            if match_entity:
                                # Patch League info
                                match_entity.league.id = internal_code
                                match_entity.league.name = general.get("leagueName", "Unknown")
                                # Try to get score from header if _map didn't get it (status varies)
                                if match_entity.home_goals == 0 and match_entity.away_goals == 0:
                                     # Try extracting from string again if needed
                                     pass
                                     
                                matches.append(match_entity)
                    
                    return matches
        except Exception as e:
            logger.error(f"Error fetching live matches from FotMob: {e}")
            return []

    async def get_team_history(self, team_name: str, limit: int = 5) -> List[Match]:
        """
        Fetch detailed historical matches for a team including Corners and Cards.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Search for Team ID
                team_id = await self._search_team_id(session, team_name)
                if not team_id:
                    return []

                # 2. Get Team Fixtures (Results)
                matches_data = await self._get_team_fixtures(session, team_id)
                
                # Filter finished matches
                finished = [m for m in matches_data if m.get("status", {}).get("finished")]
                
                # Sort by date desc and take limit
                recent = sorted(finished, key=lambda x: x.get("status", {}).get("utcTime") or "", reverse=True)[:limit]
                
                # 3. Fetch Details for each match in parallel (to get stats)
                tasks = [self._get_match_details(session, str(m["id"])) for m in recent]
                details_list = await asyncio.gather(*tasks, return_exceptions=True)
                
                matches = []
                for i, details in enumerate(details_list):
                    if isinstance(details, dict):
                        match_entity = self._map_to_match(recent[i], details)
                        if match_entity:
                            matches.append(match_entity)
                            
                return matches
        except Exception as e:
            logger.warning(f"FotMob history fetch failed for {team_name}: {e}")
            return []

    async def _search_team_id(self, session, team_name: str) -> Optional[int]:
        """
        Search for a team ID using name with fallback cleaning strategies.
        """
        def clean_name(n: str) -> str:
            remove = ["fc", "cf", "as", "sc", "ac", "afc", "inter", "real", "sporting", "cd"]
            cleaned = n.lower()
            for w in remove:
                cleaned = cleaned.replace(f" {w} ", " ")
                if cleaned.endswith(f" {w}"): cleaned = cleaned[:-len(w)-1]
                if cleaned.startswith(f"{w} "): cleaned = cleaned[len(w)+1:]
            return cleaned.strip()

        async def try_search(term: str) -> Optional[int]:
            try:
                url = f"{self.BASE_URL}/searchSuggest?term={term}"
                async with session.get(url) as response:
                    if response.status != 200: return None
                    data = await response.json()
                    
                    # 1. Check 'team' top hit
                    if "team" in data and isinstance(data["team"], list) and data["team"]:
                         return data["team"][0]["id"]

                    # 2. Check general suggestions
                    for item in data:
                        if isinstance(item, dict) and "name" in item:
                            res_name = item["name"].lower()
                            in_term = term.lower()
                            # Bidirectional check: 'man city' in 'manchester city' (No)
                            # 'manchester city' in 'man city' (No)
                            # 'aston villa' in 'aston villa fc' (Yes)
                            if in_term in res_name or res_name in in_term:
                                return item["id"]
                    return None
            except Exception:
                return None

        # 1. Try Exact/Original Name
        tid = await try_search(team_name)
        if tid: return tid
        
        # 2. Try Cleaned Name (Remove FC, etc)
        cleaned = clean_name(team_name)
        if cleaned != team_name.lower():
            tid = await try_search(cleaned)
            if tid: return tid
            
        # 3. Try First Word (Desperate fallback for 'Manchester City' -> 'Manchester' -> might match Utd? Risky.
        # Better: Try 3 chars? No.
        # Let's rely on cleaned name.
        
        return None

    async def _get_team_fixtures(self, session, team_id: int) -> List[Dict]:
        try:
            url = f"{self.BASE_URL}/teams?id={team_id}&tab=fixtures"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("fixtures", {}).get("allFixtures", {}).get("fixtures", [])
        except Exception:
            return []
        return []

    async def _get_match_details(self, session, match_id: str) -> Optional[Dict]:
        try:
            url = f"{self.BASE_URL}/matchDetails?matchId={match_id}"
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
        except Exception:
            return None
        return None

    def _map_to_match(self, basic_info: Dict, details: Dict) -> Optional[Match]:
        try:
            # Extract Stats
            content = details.get("content", {})
            stats_wrapper = content.get("stats", {}).get("Periods", {}).get("All", {}).get("stats", [])
            
            home_stats = {}
            away_stats = {}
            
            for stat_group in stats_wrapper:
                for stat in stat_group.get("stats", []):
                    name = stat.get("title", "").lower()
                    vals = stat.get("stats", []) # [home_val, away_val]
                    if len(vals) == 2:
                        if "corner" in name:
                            home_stats["corners"] = int(vals[0])
                            away_stats["corners"] = int(vals[1])
                        elif "yellow card" in name:
                            home_stats["yellow"] = int(vals[0])
                            away_stats["yellow"] = int(vals[1])
                        elif "red card" in name:
                            home_stats["red"] = int(vals[0])
                            away_stats["red"] = int(vals[1])
                        elif "possession" in name:
                            home_stats["possession"] = int(vals[0])
                            away_stats["possession"] = int(vals[1])
            
            # Basic Info
            status_obj = basic_info.get("status", {})
            date_str = status_obj.get("utcTime")
            match_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")) if date_str else datetime.now()
            
            home_name = basic_info.get("home", {}).get("name", "Unknown")
            away_name = basic_info.get("away", {}).get("name", "Unknown")
            
            score_str = status_obj.get("scoreStr", "0 - 0")
            try:
                parts = score_str.split(" - ")
                h_goals = int(parts[0])
                a_goals = int(parts[1])
            except:
                h_goals, a_goals = 0, 0

            return Match(
                id=str(basic_info.get("id")),
                league=League(id="fotmob_gen", name="FotMob League", country="World"),
                home_team=Team(id=f"fot_{home_name}", name=home_name),
                away_team=Team(id=f"fot_{away_name}", name=away_name),
                match_date=match_date,
                status="FT",
                home_goals=h_goals,
                away_goals=a_goals,
                home_corners=home_stats.get("corners"),
                away_corners=away_stats.get("corners"),
                home_yellow_cards=home_stats.get("yellow"),
                away_yellow_cards=away_stats.get("yellow"),
                home_red_cards=home_stats.get("red"),
                away_red_cards=away_stats.get("red"),
                home_possession=home_stats.get("possession"),
                away_possession=away_stats.get("possession")
            )
        except Exception:
            return None