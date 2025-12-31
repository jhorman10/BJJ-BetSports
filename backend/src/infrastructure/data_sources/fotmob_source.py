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
        try:
            url = f"{self.BASE_URL}/searchSuggest?term={team_name}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # Look in squad/team suggestions
                    for item in data:
                        if isinstance(item, dict) and "name" in item:
                             # Simple fuzzy check
                             if team_name.lower() in item["name"].lower():
                                 return item["id"]
                        if "team" in data and isinstance(data["team"], list):
                             if data["team"]: return data["team"][0]["id"]
                    return None
        except Exception:
            return None
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