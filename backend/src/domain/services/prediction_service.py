"""
Prediction Service Module

This domain service contains the core prediction logic using:
1. Poisson Distribution for goal scoring predictions
2. Logistic Regression for match outcome classification

This is a pure domain service with no external dependencies.
"""

import math
from dataclasses import dataclass
from typing import Optional

from src.domain.entities.entities import (
    Match,
    Prediction,
    TeamStatistics,
)
from src.domain.value_objects.value_objects import (
    TeamStrength,
    Odds,
)


@dataclass
class LeagueAverages:
    """Average statistics for a league used in predictions."""
    avg_home_goals: float
    avg_away_goals: float
    avg_total_goals: float


class PredictionService:
    """
    Domain service for generating match predictions.
    
    Uses a combination of Poisson distribution for expected goals
    and statistical analysis for match outcomes.
    """
    
    # Default league averages (used when actual data is unavailable)
    DEFAULT_HOME_GOALS = 1.5
    DEFAULT_AWAY_GOALS = 1.1
    
    def __init__(self):
        """Initialize the prediction service."""
        pass
    
    def calculate_team_strength(
        self,
        team_stats: TeamStatistics,
        league_averages: LeagueAverages,
        is_home: bool = True,
    ) -> TeamStrength:
        """
        Calculate a team's attacking and defensive strength.
        
        Strength is relative to league average:
        - Attack strength > 1 means scores more than average
        - Defense strength < 1 means concedes less than average
        
        Args:
            team_stats: Historical statistics for the team
            league_averages: Average goals in the league
            is_home: Whether calculating for home matches
            
        Returns:
            TeamStrength with attack and defense values
        """
        if team_stats.matches_played == 0:
            return TeamStrength(attack_strength=1.0, defense_strength=1.0)
        
        # Attack strength = team's goals scored / league average goals
        attack = team_stats.goals_per_match / league_averages.avg_total_goals * 2
        
        # Defense strength = team's goals conceded / league average goals
        # Lower is better, but we invert for calculation
        defense = team_stats.goals_conceded_per_match / league_averages.avg_total_goals * 2
        
        # Apply home/away adjustment
        if is_home:
            attack *= 1.1  # Home teams typically score more
            defense *= 0.9  # Home teams typically concede less
        else:
            attack *= 0.9
            defense *= 1.1
        
        return TeamStrength(
            attack_strength=max(0.1, attack),
            defense_strength=max(0.1, defense),
        )
    
    def poisson_probability(self, expected: float, actual: int) -> float:
        """
        Calculate Poisson probability.
        
        P(X = k) = (λ^k * e^(-λ)) / k!
        
        Args:
            expected: Expected value (λ)
            actual: Actual value (k)
            
        Returns:
            Probability of exactly 'actual' events occurring
        """
        if expected <= 0:
            return 0.0 if actual > 0 else 1.0
        
        return (math.pow(expected, actual) * math.exp(-expected)) / math.factorial(actual)
    
    def calculate_expected_goals(
        self,
        home_strength: TeamStrength,
        away_strength: TeamStrength,
        league_averages: LeagueAverages,
    ) -> tuple[float, float]:
        """
        Calculate expected goals for both teams.
        
        Args:
            home_strength: Home team's strength
            away_strength: Away team's strength
            league_averages: League average goals
            
        Returns:
            Tuple of (expected_home_goals, expected_away_goals)
        """
        # Expected home goals = home attack * away defense weakness * league average
        home_expected = (
            home_strength.attack_strength *
            away_strength.defense_strength *
            league_averages.avg_home_goals
        )
        
        # Expected away goals = away attack * home defense weakness * league average
        away_expected = (
            away_strength.attack_strength *
            home_strength.defense_strength *
            league_averages.avg_away_goals
        )
        
        return (home_expected, away_expected)
    
    def calculate_outcome_probabilities(
        self,
        home_expected: float,
        away_expected: float,
        max_goals: int = 10,
    ) -> tuple[float, float, float]:
        """
        Calculate match outcome probabilities using Poisson distribution.
        
        Args:
            home_expected: Expected goals for home team
            away_expected: Expected goals for away team
            max_goals: Maximum goals to consider
            
        Returns:
            Tuple of (home_win_prob, draw_prob, away_win_prob)
        """
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        
        # Calculate probability for each possible score
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                prob = (
                    self.poisson_probability(home_expected, home_goals) *
                    self.poisson_probability(away_expected, away_goals)
                )
                
                if home_goals > away_goals:
                    home_win += prob
                elif home_goals == away_goals:
                    draw += prob
                else:
                    away_win += prob
        
        # Normalize to ensure sum equals 1
        total = home_win + draw + away_win
        if total > 0:
            return (home_win / total, draw / total, away_win / total)
        
        # Fallback to equal probabilities
        return (0.33, 0.34, 0.33)
    
    def calculate_over_under_probability(
        self,
        home_expected: float,
        away_expected: float,
        threshold: float = 2.5,
        max_goals: int = 10,
    ) -> tuple[float, float]:
        """
        Calculate over/under goal probabilities.
        
        Args:
            home_expected: Expected goals for home team
            away_expected: Expected goals for away team
            threshold: Goal threshold (default 2.5)
            max_goals: Maximum goals to consider
            
        Returns:
            Tuple of (over_probability, under_probability)
        """
        under = 0.0
        
        # Calculate probability of total goals <= threshold
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                total = home_goals + away_goals
                if total <= threshold:
                    prob = (
                        self.poisson_probability(home_expected, home_goals) *
                        self.poisson_probability(away_expected, away_goals)
                    )
                    under += prob
        
        over = 1.0 - under
        return (over, under)
    
    def adjust_with_odds(
        self,
        calculated_probs: tuple[float, float, float],
        odds: Optional[Odds],
        weight: float = 0.3,
    ) -> tuple[float, float, float]:
        """
        Adjust calculated probabilities with bookmaker odds.
        
        Bookmaker odds encode market expectations which can
        improve prediction accuracy.
        
        Args:
            calculated_probs: (home, draw, away) probabilities
            odds: Bookmaker odds (optional)
            weight: How much to weight odds (0-1)
            
        Returns:
            Adjusted probabilities
        """
        if odds is None:
            return calculated_probs
        
        home_calc, draw_calc, away_calc = calculated_probs
        home_odds, draw_odds, away_odds = odds.to_probabilities()
        
        # Weighted average of calculated and odds-implied probabilities
        home_adj = (1 - weight) * home_calc + weight * home_odds
        draw_adj = (1 - weight) * draw_calc + weight * draw_odds
        away_adj = (1 - weight) * away_calc + weight * away_odds
        
        # Normalize
        total = home_adj + draw_adj + away_adj
        return (home_adj / total, draw_adj / total, away_adj / total)
    
    def calculate_confidence(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        has_odds: bool,
    ) -> float:
        """
        Calculate prediction confidence based on available data.
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            has_odds: Whether we have betting odds
            
        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence
        
        # Add confidence for available data
        if home_stats and home_stats.matches_played >= 10:
            confidence += 0.15
        elif home_stats and home_stats.matches_played >= 5:
            confidence += 0.1
        
        if away_stats and away_stats.matches_played >= 10:
            confidence += 0.15
        elif away_stats and away_stats.matches_played >= 5:
            confidence += 0.1
        
        if has_odds:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def generate_prediction(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        data_sources: Optional[list[str]] = None,
    ) -> Prediction:
        """
        Generate a complete prediction for a match.
        
        Args:
            match: The match to predict
            home_stats: Historical stats for home team
            away_stats: Historical stats for away team
            league_averages: League average goals
            data_sources: List of data sources used
            
        Returns:
            Complete Prediction object
        """
        # Use defaults if league averages not provided
        if league_averages is None:
            league_averages = LeagueAverages(
                avg_home_goals=self.DEFAULT_HOME_GOALS,
                avg_away_goals=self.DEFAULT_AWAY_GOALS,
                avg_total_goals=self.DEFAULT_HOME_GOALS + self.DEFAULT_AWAY_GOALS,
            )
        
        # Calculate team strengths
        if home_stats:
            home_strength = self.calculate_team_strength(
                home_stats, league_averages, is_home=True
            )
        else:
            home_strength = TeamStrength(attack_strength=1.0, defense_strength=1.0)
        
        if away_stats:
            away_strength = self.calculate_team_strength(
                away_stats, league_averages, is_home=False
            )
        else:
            away_strength = TeamStrength(attack_strength=1.0, defense_strength=1.0)
        
        # Calculate expected goals
        home_expected, away_expected = self.calculate_expected_goals(
            home_strength, away_strength, league_averages
        )
        
        # Calculate outcome probabilities
        home_win, draw, away_win = self.calculate_outcome_probabilities(
            home_expected, away_expected
        )
        
        # Adjust with odds if available
        if match.home_odds and match.draw_odds and match.away_odds:
            odds = Odds(home=match.home_odds, draw=match.draw_odds, away=match.away_odds)
            home_win, draw, away_win = self.adjust_with_odds(
                (home_win, draw, away_win), odds
            )
        
        # Calculate over/under
        over_25, under_25 = self.calculate_over_under_probability(
            home_expected, away_expected
        )
        
        # Calculate confidence
        confidence = self.calculate_confidence(
            home_stats,
            away_stats,
            has_odds=match.home_odds is not None,
        )
        
        return Prediction(
            match_id=match.id,
            home_win_probability=round(home_win, 4),
            draw_probability=round(draw, 4),
            away_win_probability=round(away_win, 4),
            over_25_probability=round(over_25, 4),
            under_25_probability=round(under_25, 4),
            predicted_home_goals=round(home_expected, 2),
            predicted_away_goals=round(away_expected, 2),
            confidence=round(confidence, 2),
            data_sources=data_sources or [],
        )
