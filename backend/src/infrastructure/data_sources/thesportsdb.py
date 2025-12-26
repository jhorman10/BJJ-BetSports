"""
TheSportsDB Data Source

This module integrates with TheSportsDB (thesportsdb.com) for team details,
league info, and basic match data.

API Documentation: https://www.thesportsdb.com/api/v1/json/3/
"""

import os
import logging
import httpx
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from src.domain.entities.entities import Team, League, Match

logger = logging.getLogger(__name__)

@dataclass
class TheSportsDBConfig:
    """Configuration for TheSportsDB."""
    api_key: Optional[str] = None
    base_url: str = "https://www.thesportsdb.com/api/v1/json/3"
    timeout: int = 30
    
    def __post_init__(self):
        if self.api_key is None:
            # '3' is a common free tier key for testing 
            self.api_key = os.getenv("THESPORTSDB_KEY", "3")

class TheSportsDBClient:
    """
    Client for TheSportsDB API.
    """
    
    SOURCE_NAME = "TheSportsDB"
    
    def __init__(self, config: Optional[TheSportsDBConfig] = None):
        self.config = config or TheSportsDBConfig()
        
    async def _make_request(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """Make request to TheSportsDB."""
        url = f"{self.config.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"TheSportsDB request error: {e}")
            return None

    async def search_team(self, team_name: str) -> Optional[Team]:
        """Search for a team by name."""
        data = await self._make_request(f"/searchteams.php?t={team_name}")
        
        if not data or not data.get("teams"):
            return None
            
        team_data = data["teams"][0]
        
        return Team(
            id=team_data.get("idTeam"),
            name=team_data.get("strTeam"),
            short_name=team_data.get("strTeamShort"),
            country=team_data.get("strCountry"),
            logo_url=team_data.get("strBadge")
        )

    async def get_league_details(self, league_name: str) -> Optional[League]:
        """Get league details."""
        # Note: TheSportsDB search is loose, might need mapping
        data = await self._make_request(f"/search_all_leagues.php?c=England&s=Soccer") # Example specific query
        # Ideally we search by exact league name if possible or map IDs
        
        # For now, let's just implement basic team search as that's the main value add (logos/info)
    async def get_upcoming_fixtures(self, league_id: str, next_n: int = 15) -> list[Match]:
        """
        Get upcoming fixtures for a league.
        
        Args:
           league_id: Internal league ID (e.g., 'E0')
           next_n: Number of matches to return
           
        Returns:
            List of upcoming Match objects
        """
        # Map internal ID to TheSportsDB ID
        # Values from: https://www.thesportsdb.com/api/v1/json/3/all_leagues.php
        INTERNAL_TO_TSDB = {
            "E0": "4328", # Premier League
            "SP1": "4335", # La Liga
            "SP1": "4335", # La Liga
            "D1": "4331", # Bundesliga
            "F1": "4334", # Ligue 1
            "D1": "4331", # Bundesliga
            "F1": "4334", # Ligue 1
            "P1": "4344", # Primeira Liga
            "N1": "4337", # Eredivisie
            "SC0": "4330", # Scottish Premiership (Ross County etc)
            "T1": "4359", # Super Lig (Turkey)
            "G1": "4392", # Super League (Greece)
        }
        
        tsdb_id = INTERNAL_TO_TSDB.get(league_id)
        if not tsdb_id:
            logger.warning(f"No TheSportsDB mapping for league {league_id}")
            return []
            
        # Endpoint: eventsnextleague.php?id=4328
        data = await self._make_request(f"/eventsnextleague.php?id={tsdb_id}")
        
        if not data or not data.get("events"):
            return []
            
        matches = []
        for event in data["events"]:
            try:
                # Parse date/time
                # Format: "2024-12-21" "12:30:00"
                date_str = event.get("dateEvent")
                time_str = event.get("strTime")
                
                match_date = datetime.utcnow() # Default
                if date_str and time_str:
                    try:
                        match_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                         # Attempt fallback without seconds
                         try:
                             match_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                         except ValueError:
                             pass

                # Create basic Team objects (we usually need IDs but here we only have names)
                # We can fetch IDs later or map them if essential. For basic display, names work.
                # However, our system relies on Team entities.
                # We'll use a placeholder ID or try to derive it.
                
                home_team = Team(
                    id=event.get("idHomeTeam") or "unknown",
                    name=event.get("strHomeTeam"),
                    logo_url=None # Not provided in this endpoint
                )
                
                away_team = Team(
                    id=event.get("idAwayTeam") or "unknown",
                    name=event.get("strAwayTeam"),
                    logo_url=None
                )
                
                # Create rudimentary league object
                league = League(
                    id=league_id, # Keep internal ID
                    name=event.get("strLeague"),
                    country="Unknown", # API might not provide this here
                )
                
                match = Match(
                    id=event.get("idEvent"),
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_date=match_date,
                    status="NS", # It's 'upcoming' endpoint
                    home_goals=None,
                    away_goals=None
                )
                matches.append(match)
                
            except Exception as e:
                logger.error(f"Error parsing TheSportsDB event: {e}")
                continue
                
        # Limit results
        return matches[:next_n]

    async def get_match_details(self, match_id: str) -> Optional[Match]:
        """Get match details by ID."""
        # Endpoint: lookupevent.php?id=441613
        data = await self._make_request(f"/lookupevent.php?id={match_id}")
        
        if not data or not data.get("events"):
            return None
            
        event = data["events"][0]
        
        try:
             # Parse date/time
            date_str = event.get("dateEvent")
            time_str = event.get("strTime")
            
            match_date = datetime.utcnow()
            if date_str and time_str:
                try:
                    match_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                except ValueError:
                     try:
                         match_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                     except ValueError:
                         pass

            home_team = Team(
                id=event.get("idHomeTeam") or "unknown",
                name=event.get("strHomeTeam"),
                logo_url=None
            )
            
            away_team = Team(
                id=event.get("idAwayTeam") or "unknown",
                name=event.get("strAwayTeam"),
                logo_url=None
            )
            
            league = League(
                id=event.get("idLeague"), # Use External ID if internal mapping unclear
                name=event.get("strLeague"),
                country="Unknown",
                season=event.get("strSeason")
            )
            
            return Match(
                id=event.get("idEvent"),
                home_team=home_team,
                away_team=away_team,
                league=league,
                match_date=match_date,
                status="NS" if not event.get("intHomeScore") else "FT", # Simplified status
                home_goals=int(event.get("intHomeScore")) if event.get("intHomeScore") else None,
                away_goals=int(event.get("intAwayScore")) if event.get("intAwayScore") else None,
            )
        except Exception as e:
            logger.error(f"Error parsing TheSportsDB match details: {e}")
            return None

    async def get_past_events(self, league_id: str, max_events: int = 50) -> list[Match]:
        """
        Get past/finished events for a league.
        
        Args:
            league_id: Internal league ID (e.g., 'E0')
            max_events: Maximum number of events to return
            
        Returns:
            List of finished Match objects with results
        """
        # Map internal ID to TheSportsDB ID
        INTERNAL_TO_TSDB = {
            "E0": "4328",   # Premier League
            "SP1": "4335",  # La Liga
            "D1": "4331",   # Bundesliga
            "F1": "4334",   # Ligue 1
            "F1": "4334",   # Ligue 1
            "P1": "4344",   # Primeira Liga
            "N1": "4337",   # Eredivisie
            "SC0": "4330",  # Scottish Premiership
            "T1": "4359",   # Super Lig (Turkey)
            "G1": "4392",   # Super League (Greece)
        }
        
        tsdb_id = INTERNAL_TO_TSDB.get(league_id)
        if not tsdb_id:
            logger.debug(f"No TheSportsDB mapping for league {league_id}")
            return []
            
        # Endpoint: eventspastleague.php?id=4328
        data = await self._make_request(f"/eventspastleague.php?id={tsdb_id}")
        
        if not data or not data.get("events"):
            return []
            
        matches = []
        for event in data["events"][:max_events]:
            try:
                # Only include finished matches with scores
                home_score = event.get("intHomeScore")
                away_score = event.get("intAwayScore")
                
                if home_score is None or away_score is None:
                    continue
                
                # Parse date/time
                date_str = event.get("dateEvent")
                time_str = event.get("strTime") or "00:00:00"
                
                match_date = datetime.utcnow()
                if date_str:
                    try:
                        match_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            match_date = datetime.strptime(date_str, "%Y-%m-%d")
                        except ValueError:
                            pass

                home_team = Team(
                    id=event.get("idHomeTeam") or "unknown",
                    name=event.get("strHomeTeam"),
                    logo_url=event.get("strHomeTeamBadge")
                )
                
                away_team = Team(
                    id=event.get("idAwayTeam") or "unknown",
                    name=event.get("strAwayTeam"),
                    logo_url=event.get("strAwayTeamBadge")
                )
                
                league = League(
                    id=league_id,
                    name=event.get("strLeague"),
                    country="Unknown",
                    season=event.get("strSeason")
                )
                
                match = Match(
                    id=event.get("idEvent"),
                    home_team=home_team,
                    away_team=away_team,
                    league=league,
                    match_date=match_date,
                    status="FT",
                    home_goals=int(home_score),
                    away_goals=int(away_score),
                )
                matches.append(match)
                
            except Exception as e:
                logger.debug(f"Error parsing TheSportsDB past event: {e}")
                continue
                
        logger.info(f"TheSportsDB: fetched {len(matches)} past events for {league_id}")
        return matches
