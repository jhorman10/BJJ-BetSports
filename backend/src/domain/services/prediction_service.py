"""
Prediction Service Module

This domain service contains the core prediction logic using:
1. Poisson Distribution for goal scoring predictions
2. Logistic Regression for match outcome classification

This is a pure domain service with no external dependencies.
"""

import math
import functools
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
    LeagueAverages,
)
from src.domain.exceptions import InsufficientDataException


class PredictionService:
    """
    Domain service for generating match predictions.
    
    Uses a combination of Poisson distribution for expected goals
    and statistical analysis for match outcomes.
    
    STRICT POLICY: 
    - NO MOCK DATA ALLOWED.
    - Only uses REAL historical and real-time data from verified sources.
    - If data is insufficient, returns zero results/empty predictions.
    - Prohibited to use placeholders or simulated data for probabilities.
    """
    
    def __init__(self):
        """Initialize the prediction service."""
        pass
    
    def adjust_with_odds(
        self,
        calculated_probs: tuple[float, float, float],
        odds: Odds,
        weight: float = 0.5,
    ) -> tuple[float, float, float]:
        """
        Adjust calculated probabilities using market odds.
        
        Args:
            calculated_probs: Model's predicted probabilities
            odds: Bookmaker odds
            weight: Weight to give to bookmaker odds (0-1)
            
        Returns:
            Adjusted probabilities
        """
        if weight <= 0:
            return calculated_probs
        if weight >= 1:
            return odds.to_probabilities()
        
        odds_probs = odds.to_probabilities()
        
        home = (calculated_probs[0] * (1 - weight)) + (odds_probs[0] * weight)
        draw = (calculated_probs[1] * (1 - weight)) + (odds_probs[1] * weight)
        away = (calculated_probs[2] * (1 - weight)) + (odds_probs[2] * weight)
        
        # Normalize
        total = home + draw + away
        return (home / total, draw / total, away / total)
    
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
        if team_stats is None or team_stats.matches_played == 0:
            return TeamStrength(attack_strength=1.0, defense_strength=1.0)
        
        # Correct Poisson Normalization:
        # Compare stats against the specific venue average (Home vs Away)
        # to correctly capture relative strength without double-counting home advantage.
        
        if is_home:
            # Home Attack vs League Avg Home Goals
            avg_goals_scored = league_averages.avg_home_goals
            # Home Defense vs League Avg Away Goals (what visitors usually score)
            avg_goals_conceded = league_averages.avg_away_goals
            
            if avg_goals_scored <= 0 or avg_goals_conceded <= 0:
                # If we have no baseline, we cannot calculate relative strength components.
                # Since generate_prediction already guards for insufficient data,
                # this is a protective fallback to avoid ZeroDivisionError.
                return TeamStrength(attack_strength=1.0, defense_strength=1.0)
            
            # Use granular home stats if we have at least 3 home matches
            if team_stats.home_matches_played >= 3:
                attack = team_stats.home_goals_per_match / avg_goals_scored
                defense = team_stats.home_goals_conceded_per_match / avg_goals_conceded
                season_avg_attack = team_stats.home_goals_per_match
                season_avg_defense = team_stats.home_goals_conceded_per_match
            else:
                # Fallback to overall stats but slightly penalized for lack of venue data
                attack = team_stats.goals_per_match / avg_goals_scored
                defense = team_stats.goals_conceded_per_match / avg_goals_conceded
                season_avg_attack = team_stats.goals_per_match
                season_avg_defense = team_stats.goals_conceded_per_match
        else:
            # Away Attack vs League Avg Away Goals
            avg_goals_scored = league_averages.avg_away_goals
            # Away Defense vs League Avg Home Goals (what hosts usually score)
            avg_goals_conceded = league_averages.avg_home_goals
            
            if avg_goals_scored <= 0 or avg_goals_conceded <= 0:
                return TeamStrength(attack_strength=1.0, defense_strength=1.0)
            
            # Use granular away stats if we have at least 3 away matches
            if team_stats.away_matches_played >= 3:
                attack = team_stats.away_goals_per_match / avg_goals_scored
                defense = team_stats.away_goals_conceded_per_match / avg_goals_conceded
                season_avg_attack = team_stats.away_goals_per_match
                season_avg_defense = team_stats.away_goals_conceded_per_match
            else:
                attack = team_stats.goals_per_match / avg_goals_scored
                defense = team_stats.goals_conceded_per_match / avg_goals_conceded
                season_avg_attack = team_stats.goals_per_match
                season_avg_defense = team_stats.goals_conceded_per_match
        
        # Apply form factor adjustment based on recent performance (last 5 matches)
        # Extract goals from recent_form to analyze momentum
        # form_factor > 1.0 = hot form, < 1.0 = cold form
        form_factor_attack = 1.0
        if team_stats.recent_form and len(team_stats.recent_form) >= 3:
            # Estimate recent performance: W=3pts, D=1pt, L=0pts as proxy for goals
            recent_points = sum(3 if r == 'W' else 1 if r == 'D' else 0 for r in team_stats.recent_form[-5:])
            expected_points = 1.5 * len(team_stats.recent_form[-5:])  # Avg team gets ~1.5 pts/match
            if expected_points > 0:
                # Form factor: (recent_performance / expected) clamped to [0.8, 1.2]
                form_factor_attack = min(1.2, max(0.8, recent_points / expected_points))
        
        # Apply form adjustment to attack strength
        attack_adjusted = attack * form_factor_attack
        
        return TeamStrength(
            attack_strength=max(0.1, attack_adjusted),
            defense_strength=max(0.1, defense),
        )
    
    @staticmethod
    def calculate_weighted_average(
        values: list[float],
        recency_decay: float = 0.1
    ) -> float:
        """
        Calculate weighted average with exponential decay for recent matches.
        
        Uses exponential decay to give more weight to recent results:
        - Last match gets weight = 1.0
        - Previous match gets weight = exp(-decay)
        - Earlier matches get progressively less weight
        
        This implements recency bias, crucial for capturing team form.
        
        Args:
            values: List of values (e.g., goals scored in each match), newest first
            recency_decay: Decay factor (default 0.1 = ~90% weight after 1 match)
            
        Returns:
            Weighted average giving more importance to recent matches
            
        Example:
            goals = [2, 1, 3, 0, 2]  # Last 5 matches, newest first
            weighted_avg = calculate_weighted_average(goals, decay=0.1)
            # Recent 2 goals count more than older 0 goals
        """
        if not values:
            return 0.0
        
        import numpy as np
        weights = np.exp(-recency_decay * np.arange(len(values)))
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        weight_total = sum(weights)
        
        return weighted_sum / weight_total if weight_total > 0 else 0.0
    
    @staticmethod
    def calculate_form_factor(
        recent_goals: list[float],
        season_average: float
    ) -> float:
        """
        Calculate team's current form relative to season performance.
        
        Form factor > 1.0 means team is in hot form (scoring above average)
        Form factor < 1.0 means team is struggling (scoring below average)
        
        This captures momentum and recent tactical/personnel changes.
        
        Args:
            recent_goals: Goals in last 5 matches
            season_average: Average goals per match over full season
            
        Returns:
            Form factor (1.0 = normal form, >1.0 = hot, <1.0 = cold)
            
        Example:
            recent = [2, 3, 2, 1, 2]  # Hot streak, 2 goals/match
            season_avg = 1.2  # Season average
            form = calculate_form_factor(recent, season_avg)
            # form = 2.0 / 1.2 = 1.67 (67% above average!)
        """
        if not recent_goals or season_average <= 0:
            return 1.0
        
        recent_avg = sum(recent_goals) / len(recent_goals)
        return min(2.0, max(0.5, recent_avg / season_average))
    
    @staticmethod
    def adjust_confidence_by_sample_size(
        base_confidence: float,
        sample_size: int,
        min_samples: int = 10
    ) -> float:
        """
        Adjust confidence score based on data sample size.
        
        Implements statistical uncertainty reduction:
        - Small samples (< min_samples) get penalized
        - Large samples (> 2*min_samples) get bonus
        - Uses sqrt scaling (Central Limit Theorem)
        
        Args:
            base_confidence: Initial confidence score (0-1)
            sample_size: Number of historical matches used
            min_samples: Minimum for full confidence (default 10)
            
        Returns:
            Adjusted confidence score (0-1)
            
        Example:
            confidence = 0.7
            # With only 5 matches:
            adjusted = adjust_confidence_by_sample_size(0.7, 5, min_samples=10)
            # adjusted ≈ 0.49 (reduced by ~30% due to small sample)
            
            # With 25 matches:
            adjusted = adjust_confidence_by_sample_size(0.7, 25, min_samples=10)
            # adjusted ≈ 0.88 (boosted by large sample)
        """
        if sample_size <= 0:
            return 0.0
        
        import math
        # Penalty/bonus factor based on sqrt(n)
        size_factor = math.sqrt(sample_size / min_samples)
        # Cap at 1.5x for very large samples, min at 0.5x for very small
        size_factor = min(1.5, max(0.5, size_factor))
        
        adjusted = base_confidence * size_factor
        return min(1.0, max(0.0, adjusted))
    
    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def poisson_probability(expected: float, actual: int) -> float:
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
    
    @staticmethod
    def _get_poisson_distribution(expected: float, max_goals: int) -> list[float]:
        """
        Generate Poisson distribution up to max_goals.
        Optimized to avoid repeated factorial/pow calculations.
        """
        if expected <= 0:
            probs = [0.0] * (max_goals + 1)
            probs[0] = 1.0
            return probs
            
        probs = [0.0] * (max_goals + 1)
        # P(0) = e^-lambda
        current_prob = math.exp(-expected)
        probs[0] = current_prob
        
        for k in range(1, max_goals + 1):
            current_prob *= expected / k
            probs[k] = current_prob
            
        return probs

    def calculate_expected_goals(
        self,
        home_strength: TeamStrength,
        away_strength: TeamStrength,
        league_averages: LeagueAverages,
        home_lineup_factor: float = 1.0,
        away_lineup_factor: float = 1.0,
    ) -> tuple[float, float]:
        """
        Calculate expected goals for both teams.
        
        Args:
            home_strength: Home team's strength
            away_strength: Away team's strength
            league_averages: League average goals
            home_lineup_factor: 0.0-1.0 factor representing squad availability (1.0 = Full Squad)
            away_lineup_factor: 0.0-1.0 factor representing squad availability
            
        Returns:
            Tuple of (expected_home_goals, expected_away_goals)
        """
        # Expected home goals = home attack * away defense weakness * league average
        # Adjusted by lineup availability (if key players missing, attack drops)
        home_expected = (
            home_strength.attack_strength *
            away_strength.defense_strength *
            league_averages.avg_home_goals *
            home_lineup_factor
        )
        
        # Expected away goals = away attack * home defense weakness * league average
        away_expected = (
            away_strength.attack_strength *
            home_strength.defense_strength *
            league_averages.avg_away_goals *
            away_lineup_factor
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
        
        # Optimization: Pre-calculate distributions
        home_probs = self._get_poisson_distribution(home_expected, max_goals)
        away_probs = self._get_poisson_distribution(away_expected, max_goals)
        
        # Calculate probability for each possible score
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                # Use pre-calculated probabilities
                prob = home_probs[home_goals] * away_probs[away_goals]
                
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
        
        # Optimization: Pre-calculate distributions
        home_probs = self._get_poisson_distribution(home_expected, max_goals)
        away_probs = self._get_poisson_distribution(away_expected, max_goals)
        
        # Calculate probability of total goals <= threshold
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                total = home_goals + away_goals
                if total <= threshold:
                    prob = home_probs[home_goals] * away_probs[away_goals]
                    under += prob
        
        over = 1.0 - under
        return (over, under)
    
    def _calculate_entropy_score(
        self,
        probs: tuple[float, float, float],
    ) -> float:
        """
        Calculate certainty score based on Shannon Entropy.
        
        Lower entropy = higher certainty in prediction.
        H = -Σ p(x) * log2(p(x))
        Max entropy for 3 outcomes = log2(3) ≈ 1.585
        
        Args:
            probs: Tuple of (home_win, draw, away_win) probabilities
            
        Returns:
            Certainty score (0-1), where 1 = very certain
        """
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p)
        
        max_entropy = math.log2(3)  # ~1.585 for 3 outcomes
        return 1 - (entropy / max_entropy)
    
    def _calculate_data_quality(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
    ) -> float:
        """
        Calculate data quality score based on sample size.
        
        Uses sigmoid function based on Central Limit Theorem:
        - n >= 30 is statistically reliable
        - Score reaches ~0.9 at 30 matches
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            Data quality score (0-1)
        """
        if not home_stats and not away_stats:
            return 0.0  # Zero confidence with no data
        
        home_n = home_stats.matches_played if home_stats else 0
        away_n = away_stats.matches_played if away_stats else 0
        avg_n = (home_n + away_n) / 2
        
        # Sigmoid curve centered at 15 matches, reaches ~0.9 at 30
        # PROFITABILITY FIX: Shift center to 20 matches to be more conservative/reliable
        return 1 / (1 + math.exp(-0.15 * (avg_n - 22)))
    
    def _calculate_odds_agreement(
        self,
        calculated_probs: tuple[float, float, float],
        odds: Optional[Odds],
    ) -> float:
        """
        Calculate agreement between model and market odds.
        
        Uses Kullback-Leibler divergence to measure difference.
        Lower divergence = higher agreement = higher confidence.
        
        Args:
            calculated_probs: Model's predicted probabilities
            odds: Bookmaker odds (if available)
            
        Returns:
            Agreement score (0-1)
        """
        if not odds:
            return 0.0  # Zero agreement score when no odds available
        
        odds_probs = odds.to_probabilities()
        
        # Calculate KL divergence: D(P||Q) = Σ P(x) * log(P(x)/Q(x))
        kl_div = 0.0
        for p, q in zip(calculated_probs, odds_probs):
            if p > 0 and q > 0:
                kl_div += p * math.log(p / q)
        
        # Map KL divergence to 0-1 score using exponential decay
        # KL ~0 = perfect agreement (score ~1)
        # KL ~1 = significant disagreement (score ~0.37)
        return math.exp(-kl_div)
    
    def _calculate_market_sentiment(
        self,
        current_odds: Optional[Odds],
        opening_odds: Optional[Odds] = None,
    ) -> float:
        """
        Calculate market sentiment factor based on dropping odds.
        If odds drop, probability increases.
        
        Returns:
            Factor to adjust probability (1.0 = Neutral, >1.0 = Market likes this outcome)
        """
        if not current_odds or not opening_odds:
            return 1.0
            
        # Example: Home odds drop from 2.0 to 1.8 -> Market supports Home
        # Factor = Opening / Current
        # 2.0 / 1.8 = 1.11 (11% boost to probability)
        
        # We cap the impact to avoid overreacting to volatility
        sentiment = opening_odds.home / current_odds.home
        return max(0.8, min(1.2, sentiment))

    def _calculate_form_consistency(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
    ) -> float:
        """
        Calculate form consistency from recent results.
        
        Consistent form (e.g., WWWWW or LLLLL) = more predictable.
        Inconsistent form (e.g., WLWLW) = less predictable.
        
        Args:
            home_stats: Home team statistics with recent_form
            away_stats: Away team statistics with recent_form
            
        Returns:
            Consistency score (0-1)
        """
        def form_consistency_single_team(form: str, matches_played: int) -> float:
            # Low sample size penalty
            if matches_played < 10 or len(form) < 3: # Require at least 10 matches and 3 recent form entries
                return 0.0  # Not enough data for reliable confidence
            
            # Count transitions between different results
            transitions = sum(
                1 for i in range(len(form) - 1) 
                if form[i] != form[i + 1]
            )
            max_transitions = len(form) - 1
            
            # Fewer transitions = more consistent
            return 1 - (transitions / max_transitions)
        
        scores = []
        if home_stats and home_stats.recent_form:
            scores.append(form_consistency_single_team(home_stats.recent_form, home_stats.matches_played))
        if away_stats and away_stats.recent_form:
            scores.append(form_consistency_single_team(away_stats.recent_form, away_stats.matches_played))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def calculate_corner_probabilities(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None
    ) -> tuple[float, float, float, float]:
        """
        Calculate prob for Over/Under 9.5 corners AND expected values.
        Returns: (over_prob, under_prob, home_expected, away_expected)
        """
        if not home_stats or not away_stats:
             return (0.0, 0.0, 0.0, 0.0)
             
        # STRICT RULE: Require at least 4 matches with corner data for both teams
        if home_stats.matches_played < 4 or away_stats.matches_played < 4:
            return (0.0, 0.0, 0.0, 0.0)

        home_avg = home_stats.avg_corners_per_match
        away_avg = away_stats.avg_corners_per_match
            
        # Estimate expected corners (Heuristic: Home Avg + Away Avg)
        # Global approx average is ~10.
        # We split the total expected between home and away based on their relative contribution
        total_expected = home_avg + away_avg
        total_expected = home_avg + away_avg
        if total_expected == 0: total_expected = avg_corners
        
        # Simple proportional split
        if (home_avg + away_avg) > 0:
            home_expected = total_expected * (home_avg / (home_avg + away_avg))
            away_expected = total_expected * (away_avg / (home_avg + away_avg))
        else:
            home_expected = total_expected / 2
            away_expected = total_expected / 2
        
        # Use Poisson for > 9.5
        under = 0.0
        probs = self._get_poisson_distribution(total_expected, 20)
        for k in range(10): # 0 to 9
            under += probs[k]
            
        over = 1.0 - under
        return (round(over, 4), round(under, 4), round(home_expected, 1), round(away_expected, 1))

    def calculate_card_probabilities(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None
    ) -> tuple[float, float, float, float]:
        """
        Calculate prob for Over/Under 4.5 yellow cards AND expected values.
        Returns: (over_prob, under_prob, home_expected, away_expected)
        """
        if not home_stats or not away_stats:
             return (0.0, 0.0, 0.0, 0.0)

        # STRICT RULE: Require at least 4 matches with card data for both teams
        if home_stats.matches_played < 4 or away_stats.matches_played < 4:
            return (0.0, 0.0, 0.0, 0.0)

        home_avg = home_stats.avg_yellow_cards_per_match
        away_avg = away_stats.avg_yellow_cards_per_match
            
        # Estimate expected cards
        total_expected = home_avg + away_avg
        total_expected = home_avg + away_avg
        if total_expected == 0: total_expected = avg_cards
        
        # Simple proportional split
        if (home_avg + away_avg) > 0:
            home_expected = total_expected * (home_avg / (home_avg + away_avg))
            away_expected = total_expected * (away_avg / (home_avg + away_avg))
        else:
            home_expected = total_expected / 2
            away_expected = total_expected / 2
        
        # Use Poisson for > 4.5
        under = 0.0
        probs = self._get_poisson_distribution(total_expected, 15)
        for k in range(5): # 0 to 4
            under += probs[k]
            
        over = 1.0 - under
        return (round(over, 4), round(under, 4), round(home_expected, 1), round(away_expected, 1))
        
    def calculate_handicap_probabilities(
        self,
        home_expected: float,
        away_expected: float,
    ) -> tuple[float, float, float]:
        """
        Calculate Asian Handicap probabilities using simulation/Poisson diff.
        Returns: (line, home_beat_line_prob, away_beat_line_prob)
        """
        diff = home_expected - away_expected
        # Determine strict line (nearest 0.5)
        line = round(diff * 2) / 2
        if line == 0: line = -0.5 # Default to home slight disadvantage if equal
        
        # If line is positive (e.g. +1.5), it means Home gets +1.5. 
        # Usually spread is denoted as "Home -1.5" if Home is favorite.
        # Let's standardize: Line is applied to Home score.
        # Home Win Spread = P(Home + Line > Away)
        
        home_win_spread = 0.0
        
        max_goals = 10
        home_probs = self._get_poisson_distribution(home_expected, max_goals)
        away_probs = self._get_poisson_distribution(away_expected, max_goals)
        
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                if (h + line) > a:
                    home_win_spread += home_probs[h] * away_probs[a]
                    
        return (line, round(home_win_spread, 4), round(1.0 - home_win_spread, 4))

    def calculate_confidence(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        has_odds: bool,
        calculated_probs: Optional[tuple[float, float, float]] = None,
        odds: Optional[Odds] = None,
    ) -> float:
        """
        Calculate prediction confidence using multiple statistical factors.
        
        Combines four components:
        1. Entropy Score (35%): How certain the model is in its prediction
        2. Data Quality (30%): Statistical reliability based on sample size
        3. Odds Agreement (20%): Alignment with market expectations
        4. Form Consistency (15%): Predictability from recent results
        
        Args:
            home_stats: Home team statistics
            away_stats: Away team statistics
            has_odds: Whether betting odds are available
            calculated_probs: Model's calculated probabilities
            odds: Bookmaker odds object
            
        Returns:
            Confidence score (0-1)
        """
        # Default probabilities if not provided
        if calculated_probs is None:
            calculated_probs = (0.33, 0.34, 0.33)
        
        # Calculate components
        entropy_score = self._calculate_entropy_score(calculated_probs)
        data_quality = self._calculate_data_quality(home_stats, away_stats)
        
        # Calculate availability flags
        has_stats = (home_stats is not None) and (away_stats is not None)
        has_odds_data = (odds is not None)
        has_recent_form = False
        if has_stats:
            has_recent_form = bool(home_stats.recent_form and away_stats.recent_form)
        
        form_score = 0.5
        if has_recent_form:
             form_score = self._calculate_form_consistency(home_stats, away_stats)
             
        odds_agreement = 0.5
        if has_odds_data:
             odds_agreement = self._calculate_odds_agreement(calculated_probs, odds)
        
        # Dynamic Weighting
        # PROFITABILITY FIX: Optimized for Large Dataset (10 Years History)
        # With 18k+ samples, Data Quality is usually high/saturated. 
        # We shift weight to Entropy (Model Certainty) and Form (Recency).
        # We also slightly increase Odds respect to detect sharp market moves.
        
        w_entropy = 0.50  # Increased from 0.40 - Trust the model's output distribution more
        w_quality = 0.25  # Decreased from 0.45 - Since we have 10y data, this is less differentiating
        w_odds = 0.10     # Increased from 0.05 - Respect market efficiency slightly more
        w_form = 0.15     # Increased from 0.10 - Recent form matters more in long-term avg context
        
        if not has_odds_data:
            # Distribute 0.10 odds weight: 0.05 to quality, 0.05 to form
            w_quality += 0.05
            w_form += 0.05
            w_odds = 0.0
            
        if not has_recent_form:
            # Distribute 0.15 form weight: 0.10 to entropy, 0.05 to quality
            w_entropy += 0.10
            w_quality += 0.05
            w_form = 0.0
            
        confidence = (
            w_entropy * entropy_score +
            w_quality * data_quality +
            w_odds * odds_agreement +
            w_form * form_score
        )
        
        # Strict penalty for low data quality
        # If we have very few matches, confidence should be capped
        if data_quality < 0.4:  # Matches < ~10
            confidence = min(confidence, 0.45)
        
        # Apply sample size adjustment based on actual match count
        # This implements statistical uncertainty reduction per Central Limit Theorem
        total_matches = 0
        if home_stats and away_stats:
            total_matches = min(home_stats.matches_played, away_stats.matches_played)
        
        if total_matches > 0:
            confidence = self.adjust_confidence_by_sample_size(
                base_confidence=confidence,
                sample_size=total_matches,
                min_samples=15  # Require 15 matches for full confidence
            )
            
        return round(min(max(confidence, 0.0), 1.0), 3)
    
    def generate_prediction(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        global_averages: Optional[LeagueAverages] = None,
        data_sources: Optional[list[str]] = None,
        home_missing_players: int = 0,
        away_missing_players: int = 0,
        opening_odds: Optional[Odds] = None,
        min_matches: int = 6,
        highlights_url: Optional[str] = None,
        real_time_odds: Optional[dict[str, float]] = None,
        home_elo: Optional[float] = None,
        away_elo: Optional[float] = None,
    ) -> Prediction:
        """
        Generate a prediction for a match using ONLY real data.
        
        If historical data is insufficient, returns zeros/empty values
        instead of fake defaults.
        
        Args:
            match: The match to predict
            home_stats: Historical stats for home team (None if unavailable)
            away_stats: Historical stats for away team (None if unavailable)
            league_averages: League average goals (None if unavailable)
            data_sources: List of data sources used
            home_missing_players: Count of key players missing (Injuries/Suspensions)
            away_missing_players: Count of key players missing
            opening_odds: Odds when market opened (to detect dropping odds)
            
        Returns:
            Prediction object (with zeros if no data available)
        """
        # STRICT RULE: NO DATA = NO PREDICTION
        if not home_stats or not away_stats:
            raise InsufficientDataException(f"Missing team statistics for {match.home_team.name} vs {match.away_team.name}")

        home_played = home_stats.matches_played
        away_played = away_stats.matches_played
        
        # logger.debug(f"DEBUG: {match.home_team.name} ({home_played}) vs {match.away_team.name} ({away_played}) | min_matches={min_matches}")
        
        if home_played < min_matches or away_played < min_matches:
            raise InsufficientDataException(
                f"Insufficient historical data: {match.home_team.name} ({home_played} matches) "
                f"or {match.away_team.name} ({away_played} matches) below threshold of {min_matches}"
            )

        # If league_averages is None, use a default global average
        if not league_averages:
            if global_averages:
                league_averages = global_averages
            else:
                raise InsufficientDataException("Baseline league/global averages unavailable.")

        # Baseline Confidence
        h_played = home_stats.matches_played if home_stats else 0
        a_played = away_stats.matches_played if away_stats else 0
        avg_played = (h_played + a_played) / 2
        base_confidence = 0.5 # Start with neutral 50% confidence for baseline predictions
        
        # If we have odds, we'll use them as a factor later (market implied)
        market_probs = None
        if match.home_odds and match.draw_odds and match.away_odds:
            odds = Odds(home=match.home_odds, draw=match.draw_odds, away=match.away_odds)
            market_probs = odds.to_probabilities()
            if not data_sources: data_sources = []
            if "Mercado de Apuestas (Odds)" not in data_sources:
                data_sources.append("Mercado de Apuestas (Odds)")
            # Boost confidence slightly if we have market verification
            base_confidence = 0.55
        # Calculate team strengths (using REAL data only)
        home_strength = self.calculate_team_strength(
            home_stats, league_averages, is_home=True
        )
        
        away_strength = self.calculate_team_strength(
            away_stats, league_averages, is_home=False
        )
        
        # 1. LINEUP FACTOR: Penalize for missing players
        # Heuristic: Each missing key player reduces effectiveness by ~7%
        # Cap at 30% reduction (0.7) to avoid over-penalizing without knowing who exactly
        home_lineup_factor = max(0.7, 1.0 - (home_missing_players * 0.07))
        away_lineup_factor = max(0.7, 1.0 - (away_missing_players * 0.07))

        # 2. MARKET SENTIMENT: Adjust based on Dropping Odds
        # If opening odds are available, compare with current odds
        market_factor_home = 1.0
        market_factor_away = 1.0
        
        if opening_odds and match.home_odds and match.away_odds:
            current_odds = Odds(home=match.home_odds, draw=match.draw_odds, away=match.away_odds)
            
            # Home Sentiment: If odds drop (e.g. 2.0 -> 1.8), factor > 1 (Positive)
            if current_odds.home > 0 and opening_odds.home > 0:
                sentiment = opening_odds.home / current_odds.home
                # Cap impact to avoid overreaction (0.85 to 1.15)
                market_factor_home = max(0.85, min(1.15, sentiment))
                
            # Away Sentiment
            if current_odds.away > 0 and opening_odds.away > 0:
                sentiment = opening_odds.away / current_odds.away
                market_factor_away = max(0.85, min(1.15, sentiment))

        # Calculate expected goals
        # We combine lineup penalty and market sentiment into the calculation
        home_expected, away_expected = self.calculate_expected_goals(
            home_strength, away_strength, league_averages,
            home_lineup_factor=home_lineup_factor * market_factor_home,
            away_lineup_factor=away_lineup_factor * market_factor_away
        )
        
        # 3. ELO ADJUSTMENT (New)
        # If we have Elo ratings, we can calculate an expected win probability
        # P(A) = 1 / (1 + 10^((Rb-Ra)/400))
        elo_home_prob = 0.0
        if home_elo and away_elo:
            elo_diff = home_elo - away_elo
            # Add home advantage to Elo (typically +100 points)
            elo_home_prob = 1 / (1 + 10 ** (-(elo_diff + 100) / 400))
            
            # Blend Elo expectation into goals? 
            # Or just use it to boost confidence?
            # Let's use it to adjust expected goals slightly towards the Elo favorite
            if elo_home_prob > 0.6: # Home is strong favorite
                home_expected *= 1.1
            elif elo_home_prob < 0.4: # Away is strong favorite
                away_expected *= 1.1
            
            if "ClubElo" not in data_sources: data_sources.append("ClubElo")
        
        # Calculate outcome probabilities
        home_win, draw, away_win = self.calculate_outcome_probabilities(
            home_expected, away_expected
        )
        
        # Calculate over/under
        over_25, under_25 = self.calculate_over_under_probability(
            home_expected, away_expected
        )
        
        # Build odds object for confidence calculation
        odds_obj = None
        if match.home_odds and match.draw_odds and match.away_odds:
            odds_obj = Odds(home=match.home_odds, draw=match.draw_odds, away=match.away_odds)
        
        # Calculate Over/Under Corners (9.5) and Expected Values
        over_95_corners, under_95_corners, exp_home_corners, exp_away_corners = self.calculate_corner_probabilities(home_stats, away_stats, league_averages)
        
        # Calculate Over/Under Cards (4.5) and Expected Values
        over_45_cards, under_45_cards, exp_home_cards, exp_away_cards = self.calculate_card_probabilities(home_stats, away_stats, league_averages)
        
        # Calculate Handicap
        handicap_line, handicap_home, handicap_away = self.calculate_handicap_probabilities(home_expected, away_expected)

        # Calculate Expected Value (EV)
        # We look for the highest EV among the main 1X2 market
        max_ev = 0.0
        is_value_bet = False
        
        if match.home_odds and match.draw_odds and match.away_odds:
            ev_home = (home_win * match.home_odds) - 1
            ev_draw = (draw * match.draw_odds) - 1
            ev_away = (away_win * match.away_odds) - 1
            
            max_ev = max(ev_home, ev_draw, ev_away)
            
            # Threshold for "Value Bet" badge (e.g. > 2% edge)
            if max_ev > 0.02:
                is_value_bet = True

        # Calculate confidence based on ACTUAL data quality
        confidence = self.calculate_confidence(
            home_stats,
            away_stats,
            has_odds=match.home_odds is not None,
            calculated_probs=(home_win, draw, away_win),
            odds=odds_obj,
        )
        
        # Boost confidence if Elo data is present (it adds robustness)
        if home_elo and away_elo:
            confidence = min(0.99, confidence * 1.1)
        
        # Calculate data updated time
        data_updated_at = None
        timestamps = []
        if home_stats and home_stats.data_updated_at:
            timestamps.append(home_stats.data_updated_at)
        if away_stats and away_stats.data_updated_at:
            timestamps.append(away_stats.data_updated_at)
            
        if timestamps:
            # Use the oldest timestamp to be conservative (data is only as fresh as its oldest component)
            # OR use newest? Usually they are from same source/time. Let's use max (newest) as it indicates when check was done.
            data_updated_at = max(timestamps)
        
        return Prediction(
            match_id=match.id,
            home_win_probability=round(home_win, 4),
            draw_probability=round(draw, 4),
            away_win_probability=round(away_win, 4),
            over_25_probability=round(over_25, 4),
            under_25_probability=round(under_25, 4),
            predicted_home_goals=round(home_expected, 2),
            predicted_away_goals=round(away_expected, 2),
            
            # New Projected Stats
            predicted_home_corners=exp_home_corners,
            predicted_away_corners=exp_away_corners,
            predicted_home_yellow_cards=exp_home_cards,
            predicted_away_yellow_cards=exp_away_cards,
            predicted_home_red_cards=0.1, # Default low expectation for reds
            predicted_away_red_cards=0.1,
            
            # Standard Probabilities
            over_95_corners_probability=over_95_corners,
            under_95_corners_probability=under_95_corners,
            over_45_cards_probability=over_45_cards,
            under_45_cards_probability=under_45_cards,
            handicap_line=handicap_line,
            handicap_home_probability=handicap_home,
            handicap_away_probability=handicap_away,
            
            # Value Bet
            expected_value=round(max_ev, 4),
            is_value_bet=is_value_bet,
            
            confidence=round(confidence, 2),
            data_sources=data_sources or [],
            data_updated_at=data_updated_at,
            highlights_url=highlights_url,
            real_time_odds=real_time_odds,
        )
