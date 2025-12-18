"""
Statistics Service Module

This module provides logic to calculate TeamStatistics from a list of Match entities.
It is source-agnostic, meaning it can process matches from any data source.
"""

from typing import List
from src.domain.entities.entities import Match, TeamStatistics


class StatisticsService:
    """Service for calculating team statistics."""

    def calculate_team_statistics(
        self,
        team_name: str,
        matches: List[Match],
    ) -> TeamStatistics:
        """
        Calculate statistics for a team from match history.
        
        Args:
            team_name: Team name
            matches: List of historical matches
            
        Returns:
            TeamStatistics for the team
        """
        team_id = None
        matches_played = 0
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        home_wins = 0
        away_wins = 0
        recent_results = []
        
        for match in matches:
            if not match.is_played:
                continue
            
            # Extract team names (case insensitive)
            home_name = match.home_team.name.lower()
            away_name = match.away_team.name.lower()
            target_name = team_name.lower()

            is_home = home_name == target_name
            is_away = away_name == target_name
            
            # Simple substring check if exact match fails (helps with naming variations)
            if not (is_home or is_away):
                if target_name in home_name:
                    is_home = True
                elif target_name in away_name:
                    is_away = True
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            
            # Goals
            h_goals = match.home_goals if match.home_goals is not None else 0
            a_goals = match.away_goals if match.away_goals is not None else 0
            
            if is_home:
                goals_scored += h_goals
                goals_conceded += a_goals
                
                if h_goals > a_goals:
                    wins += 1
                    home_wins += 1
                    recent_results.append('W')
                elif h_goals < a_goals:
                    losses += 1
                    recent_results.append('L')
                else:
                    draws += 1
                    recent_results.append('D')
            else:
                goals_scored += a_goals
                goals_conceded += h_goals
                
                if a_goals > h_goals:
                    wins += 1
                    away_wins += 1
                    recent_results.append('W')
                elif a_goals < h_goals:
                    losses += 1
                    recent_results.append('L')
                else:
                    draws += 1
                    recent_results.append('D')
        
        # Get last 5 results for form
        recent_form = ''.join(recent_results[-5:]) if recent_results else ""
        
        return TeamStatistics(
            team_id=team_id or team_name.lower().replace(" ", "_"),
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            home_wins=home_wins,
            away_wins=away_wins,
            recent_form=recent_form,
        )
