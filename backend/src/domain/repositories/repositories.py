"""
Domain Repository Interfaces Module

These are abstract interfaces that define how the domain layer accesses data.
Concrete implementations are provided in the infrastructure layer.
This follows the Dependency Inversion Principle (DIP).
"""

from abc import ABC, abstractmethod
from typing import Optional
from datetime import datetime

from src.domain.entities.entities import (
    Team,
    League,
    Match,
    TeamStatistics,
)


class LeagueRepository(ABC):
    """Abstract repository for league operations."""
    
    @abstractmethod
    async def get_all_leagues(self) -> list[League]:
        """Get all available leagues."""
        pass
    
    @abstractmethod
    async def get_league_by_id(self, league_id: str) -> Optional[League]:
        """Get a specific league by ID."""
        pass
    
    @abstractmethod
    async def get_leagues_by_country(self, country: str) -> list[League]:
        """Get all leagues for a specific country."""
        pass


class TeamRepository(ABC):
    """Abstract repository for team operations."""
    
    @abstractmethod
    async def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Get a specific team by ID."""
        pass
    
    @abstractmethod
    async def get_teams_by_league(self, league_id: str) -> list[Team]:
        """Get all teams in a league."""
        pass
    
    @abstractmethod
    async def get_team_statistics(
        self,
        team_id: str,
        season: Optional[str] = None,
    ) -> Optional[TeamStatistics]:
        """Get statistics for a team."""
        pass


class MatchRepository(ABC):
    """Abstract repository for match operations."""
    
    @abstractmethod
    async def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get a specific match by ID."""
        pass
    
    @abstractmethod
    async def get_upcoming_matches(
        self,
        league_id: str,
        limit: int = 10,
    ) -> list[Match]:
        """Get upcoming matches for a league."""
        pass
    
    @abstractmethod
    async def get_historical_matches(
        self,
        league_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Match]:
        """Get historical matches for a league."""
        pass
    
    @abstractmethod
    async def get_head_to_head(
        self,
        team1_id: str,
        team2_id: str,
        limit: int = 10,
    ) -> list[Match]:
        """Get head-to-head matches between two teams."""
        pass
    
    @abstractmethod
    async def get_team_matches(
        self,
        team_id: str,
        limit: int = 20,
    ) -> list[Match]:
        """Get recent matches for a team."""
        pass
