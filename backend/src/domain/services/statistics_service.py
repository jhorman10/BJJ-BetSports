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
        
        # Stats accumulators
        total_corners = 0
        total_yellows = 0
        total_reds = 0
        
        for match in matches:
            if not match.is_played:
                continue
            
            # Extract team names (case insensitive)
            home_name = match.home_team.name.lower()
            away_name = match.away_team.name.lower()
            target_name = team_name.lower()

            is_home = home_name == target_name
            is_away = away_name == target_name
            
            # Robust fuzzy matching
            if not (is_home or is_away):
                # check target in match names
                cond1_home = target_name in home_name
                cond1_away = target_name in away_name
                
                # check match names in target (e.g. "Chelsea" in "Chelsea FC")
                # We filter out very short strings to avoid false positives with abbreviations like "FC"
                cond2_home = (len(home_name) > 3 and home_name in target_name)
                cond2_away = (len(away_name) > 3 and away_name in target_name)
                
                if cond1_home or cond2_home:
                    is_home = True
                elif cond1_away or cond2_away:
                    is_away = True
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            
            # Goals
            h_goals = match.home_goals if match.home_goals is not None else 0
            a_goals = match.away_goals if match.away_goals is not None else 0
            
            # Accumulate Stats (if available)
            if is_home:
                if match.home_corners is not None: total_corners += match.home_corners
                if match.home_yellow_cards is not None: total_yellows += match.home_yellow_cards
                if match.home_red_cards is not None: total_reds += match.home_red_cards
            else:
                if match.away_corners is not None: total_corners += match.away_corners
                if match.away_yellow_cards is not None: total_yellows += match.away_yellow_cards
                if match.away_red_cards is not None: total_reds += match.away_red_cards
            
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
            total_corners=total_corners,
            total_yellow_cards=total_yellows,
            total_red_cards=total_reds,
        )

    def calculate_league_averages(self, matches: List[Match]) -> LeagueAverages:
        """
        Calculate average stats for the league from historical matches.
        
        Args:
            matches: List of matches to analyze
            
        Returns:
            LeagueAverages object with calculated means
        """
        from src.domain.value_objects.value_objects import LeagueAverages
        
        total_home = 0
        total_away = 0
        count = 0
        
        for m in matches:
            if m.is_played:
                # Use strict extraction to avoid NoneType errors
                h = m.home_goals if m.home_goals is not None else 0
                a = m.away_goals if m.away_goals is not None else 0
                total_home += h
                total_away += a
                count += 1
                
        if count == 0:
            # Fallback to defaults if no history
            return LeagueAverages(
                avg_home_goals=1.5,
                avg_away_goals=1.1,
                avg_total_goals=2.6
            )
            
        avg_home = total_home / count
        avg_away = total_away / count
        
        return LeagueAverages(
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            avg_total_goals=avg_home + avg_away
        )
