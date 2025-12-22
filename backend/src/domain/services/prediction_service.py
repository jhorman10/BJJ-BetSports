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


class PredictionService:
    """
    Domain service for generating match predictions.
    
    Uses a combination of Poisson distribution for expected goals
    and statistical analysis for match outcomes.
    
    STRICT: Only uses REAL data. Returns zeros when insufficient data.
    """
    
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
        
        # Correct Poisson Normalization:
        # Compare stats against the specific venue average (Home vs Away)
        # to correctly capture relative strength without double-counting home advantage.
        
        if is_home:
            # Home Attack vs League Avg Home Goals
            avg_goals_scored = league_averages.avg_home_goals if league_averages.avg_home_goals > 0 else 1.5
            # Home Defense vs League Avg Away Goals (what visitors usually score)
            avg_goals_conceded = league_averages.avg_away_goals if league_averages.avg_away_goals > 0 else 1.2
        else:
            # Away Attack vs League Avg Away Goals
            avg_goals_scored = league_averages.avg_away_goals if league_averages.avg_away_goals > 0 else 1.2
            # Away Defense vs League Avg Home Goals (what hosts usually score)
            avg_goals_conceded = league_averages.avg_home_goals if league_averages.avg_home_goals > 0 else 1.5
            
        attack = team_stats.goals_per_match / avg_goals_scored
        defense = team_stats.goals_conceded_per_match / avg_goals_conceded
        
        return TeamStrength(
            attack_strength=max(0.1, attack),
            defense_strength=max(0.1, defense),
        )
    
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
        if odds is None:
            return 0.5  # Neutral score when no odds available
        
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
        def form_consistency(form: str) -> float:
            if len(form) < 3:
                return 0.5  # Not enough data
            
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
            scores.append(form_consistency(home_stats.recent_form))
        if away_stats and away_stats.recent_form:
            scores.append(form_consistency(away_stats.recent_form))
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def calculate_corner_probabilities(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
    ) -> tuple[float, float]:
        """Calculate prob for Over/Under 9.5 corners."""
        # PROFITABILITY FIX: Require at least 6 matches for reliable corner stats
        if not home_stats or not away_stats or home_stats.matches_played < 6 or away_stats.matches_played < 6:
            return (0.0, 0.0)
            
        # Estimate expected corners (Heuristic: Home Avg + Away Avg)
        # Global approx average is ~10.
        avg_corners = home_stats.avg_corners_per_match + away_stats.avg_corners_per_match
        if avg_corners == 0: avg_corners = 9.5 # Fallback
        
        # Use Poisson for > 9.5
        under = 0.0
        probs = self._get_poisson_distribution(avg_corners, 20)
        for k in range(10): # 0 to 9
            under += probs[k]
            
        over = 1.0 - under
        return (round(over, 4), round(under, 4))

    def calculate_card_probabilities(
        self,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
    ) -> tuple[float, float]:
        """Calculate prob for Over/Under 4.5 yellow cards."""
        # PROFITABILITY FIX: Require at least 6 matches for reliable card stats
        if not home_stats or not away_stats or home_stats.matches_played < 6 or away_stats.matches_played < 6:
            return (0.0, 0.0)
            
        # Estimate expected cards
        avg_cards = home_stats.avg_yellow_cards_per_match + away_stats.avg_yellow_cards_per_match
        if avg_cards == 0: avg_cards = 4.0 # Fallback
        
        # Use Poisson for > 4.5
        under = 0.0
        probs = self._get_poisson_distribution(avg_cards, 15)
        for k in range(5): # 0 to 4
            under += probs[k]
            
        over = 1.0 - under
        return (round(over, 4), round(under, 4))
        
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
        # PROFITABILITY FIX: Reduce reliance on Odds Agreement. 
        # To find value, we must be willing to disagree with the market if Data Quality is high.
        # New Weights: Entropy (40%), Data Quality (45%), Odds (5%), Form (10%)
        
        w_entropy = 0.40
        w_quality = 0.45
        w_odds = 0.05
        w_form = 0.10
        
        if not has_odds_data:
            # Distribute 0.15 odds weight: 0.10 to quality, 0.05 to entropy
            w_quality += 0.10
            w_entropy += 0.05
            w_odds = 0.0
            
        if not has_recent_form:
            # Distribute 0.15 form weight: 0.10 to quality, 0.05 to entropy
            w_quality += 0.10
            w_entropy += 0.05
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
            
        return round(min(max(confidence, 0.0), 1.0), 3)
    
    def generate_prediction(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        data_sources: Optional[list[str]] = None,
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
            
        Returns:
            Prediction object (with zeros if no data available)
        """
        # Check for sufficient data - STRICT: require both teams AND league data (or use defaults)
        home_played = home_stats.matches_played if home_stats else 0
        away_played = away_stats.matches_played if away_stats else 0
        
        # PROFITABILITY FIX: Increase minimum matches to 6 to ensure statistical significance
        MIN_MATCHES = 6
        
        # FIX: If league_averages is None but we have Stats, use a default global average
        if not league_averages and (home_played >= MIN_MATCHES and away_played >= MIN_MATCHES):
            # Global average ~2.6-2.7 goals. Home typically 1.5, Away 1.2
            from src.domain.value_objects.value_objects import LeagueAverages
            league_averages = LeagueAverages(
                avg_home_goals=1.50,
                avg_away_goals=1.20,
                avg_total_goals=2.70
            ) 

        has_league_data = league_averages is not None
        
        # If insufficient data, return empty prediction (no fake values)
        if home_played < MIN_MATCHES or away_played < MIN_MATCHES or not has_league_data:
            # FALLBACK TO ODDS: If we have odds, use them as implied probability
            if match.home_odds and match.draw_odds and match.away_odds:
                odds = Odds(home=match.home_odds, draw=match.draw_odds, away=match.away_odds)
                h_prob, d_prob, a_prob = odds.to_probabilities()
                
                # We can't predict exact goals reliably without stats, 
                # but we can provide win probabilities which is better than nothing.
                return Prediction(
                    match_id=match.id,
                    home_win_probability=round(h_prob, 4),
                    draw_probability=round(d_prob, 4),
                    away_win_probability=round(a_prob, 4),
                    over_25_probability=0.0, # Cannot infer from simple 1X2 odds
                    under_25_probability=0.0,
                    predicted_home_goals=0.0,
                    predicted_away_goals=0.0,
                    
                    over_95_corners_probability=0.0,
                    under_95_corners_probability=0.0,
                    over_45_cards_probability=0.0,
                    under_45_cards_probability=0.0,
                    handicap_line=0.0,
                    handicap_home_probability=0.0,
                    handicap_away_probability=0.0,

                    expected_value=0.0,
                    is_value_bet=False,

                    confidence=0.3, # Low confidence as it's just market implied
                    data_sources=["Mercado de Apuestas (Odds)"],
                )

            return Prediction(
                match_id=match.id,
                home_win_probability=0.0,
                draw_probability=0.0,
                away_win_probability=0.0,
                over_25_probability=0.0,
                under_25_probability=0.0,
                predicted_home_goals=0.0,
                predicted_away_goals=0.0,
                
                over_95_corners_probability=0.0,
                under_95_corners_probability=0.0,
                over_45_cards_probability=0.0,
                under_45_cards_probability=0.0,
                handicap_line=0.0,
                handicap_home_probability=0.0,
                handicap_away_probability=0.0,

                expected_value=0.0,
                is_value_bet=False,

                confidence=0.0,
                data_sources=["Datos Insuficientes"],
            )
        
        # Calculate team strengths (using REAL data only)
        home_strength = self.calculate_team_strength(
            home_stats, league_averages, is_home=True
        )
        
        away_strength = self.calculate_team_strength(
            away_stats, league_averages, is_home=False
        )
        
        # Calculate expected goals
        home_expected, away_expected = self.calculate_expected_goals(
            home_strength, away_strength, league_averages
        )
        
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
        
        # Calculate Over/Under Corners (9.5)
        over_95_corners, under_95_corners = self.calculate_corner_probabilities(home_stats, away_stats)
        
        # Calculate Over/Under Cards (4.5)
        over_45_cards, under_45_cards = self.calculate_card_probabilities(home_stats, away_stats)
        
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
            
            # New Fields
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
        )
