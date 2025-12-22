"""
Picks Service Module

Domain service for generating AI-suggested betting picks with smart
market prioritization based on historical performance and feedback rules.
"""

import math
from typing import Optional
from src.domain.entities.entities import Match, TeamStatistics
from src.domain.entities.suggested_pick import (
    SuggestedPick,
    MatchSuggestedPicks,
    MarketType,
    ConfidenceLevel,
)
from src.domain.entities.betting_feedback import LearningWeights
from src.domain.value_objects.value_objects import LeagueAverages


class PicksService:
    """
    Domain service for generating suggested picks.
    
    Implements the betting feedback rules:
    1. Prioritize statistical markets (corners, cards) over goals
    2. Penalize over goals when teams average < 1.5 goals/match
    3. Favor VA handicaps (+1.5/+2) for dominant teams
    4. Avoid duplicating similar markets
    5. Reduce weight for long combinations (>3 picks)
    """
    
    # Market priority weights (higher = prioritized)
    MARKET_PRIORITY = {
        MarketType.CORNERS_OVER: 1.3,
        MarketType.CORNERS_UNDER: 1.2,
        MarketType.CARDS_OVER: 1.25,
        MarketType.CARDS_UNDER: 1.15,
        MarketType.VA_HANDICAP: 1.2,
        MarketType.GOALS_OVER: 0.8,  # Penalized
        MarketType.GOALS_UNDER: 0.9,
        MarketType.TEAM_GOALS_OVER: 0.7,  # More penalized
        MarketType.TEAM_GOALS_UNDER: 0.85,
        MarketType.RESULT_1X2: 1.0,
    }
    
    # Thresholds for corner predictions
    CORNER_THRESHOLDS = [5.5, 6.5, 7.5, 8.5, 9.5, 10.5]
    
    # Thresholds for card predictions
    CARD_THRESHOLDS = [1.5, 2.5, 3.5, 4.5]
    
    # VA Handicap options
    VA_HANDICAPS = [1.0, 1.5, 2.0]
    
    def __init__(self, learning_weights: Optional[LearningWeights] = None):
        """Initialize with optional learning weights."""
        self.learning_weights = learning_weights or LearningWeights()
    
    def generate_suggested_picks(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        predicted_home_goals: float = 1.5,
        predicted_away_goals: float = 1.1,
    ) -> MatchSuggestedPicks:
        """
        Generate suggested picks for a match.
        
        Args:
            match: The match to generate picks for
            home_stats: Home team historical statistics
            away_stats: Away team historical statistics
            league_averages: League average statistics
            predicted_home_goals: Expected goals for home team
            predicted_away_goals: Expected goals for away team
            
        Returns:
            MatchSuggestedPicks with sorted recommendations
        """
        picks = MatchSuggestedPicks(match_id=match.id)
        
        if not home_stats or not away_stats:
            return picks
        
        # Check if this is a low-scoring context
        is_low_scoring = self._is_low_scoring_context(
            home_stats, away_stats, predicted_home_goals, predicted_away_goals
        )
        
        # Check for dominant team
        dominant_team = self._get_dominant_team(
            home_stats, away_stats, predicted_home_goals, predicted_away_goals
        )
        
        # Generate corners picks
        corners_picks = self._generate_corners_picks(
            home_stats, away_stats, match
        )
        for pick in corners_picks:
            picks.add_pick(pick)
        
        # Generate cards picks
        cards_picks = self._generate_cards_picks(
            home_stats, away_stats, match
        )
        for pick in cards_picks:
            picks.add_pick(pick)
        
        # Generate VA handicap picks (if dominant team exists)
        if dominant_team:
            va_picks = self._generate_va_handicap_picks(
                dominant_team, predicted_home_goals, predicted_away_goals, match
            )
            for pick in va_picks:
                picks.add_pick(pick)
        
        # Generate goals picks (with penalties if low-scoring)
        goals_picks = self._generate_goals_picks(
            predicted_home_goals, predicted_away_goals, is_low_scoring
        )
        for pick in goals_picks:
            picks.add_pick(pick)
        
        # Add combination warning if too many picks
        if len([p for p in picks.suggested_picks if p.is_recommended]) > 3:
            picks.combination_warning = (
                "⚠️ Evita combinar más de 3 picks - Mayor riesgo de fallo. "
                "Las combinadas largas (4+) fallaron por 1-2 selecciones en el historial."
            )
        
        # Check for duplicate market warning
        if picks.has_duplicate_markets():
            if picks.combination_warning:
                picks.combination_warning += (
                    " No combines over goles total + over goles por equipo."
                )
            else:
                picks.combination_warning = (
                    "⚠️ No combines over goles total + over goles por equipo."
                )
        
        return picks
    
    def _is_low_scoring_context(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        predicted_home: float,
        predicted_away: float,
    ) -> bool:
        """Check if match context suggests low scoring."""
        # Both teams average less than 1.5 goals per match
        home_avg = home_stats.goals_per_match
        away_avg = away_stats.goals_per_match
        
        if home_avg < 1.5 and away_avg < 1.5:
            return True
        
        # Predicted total is less than 2.0
        if predicted_home + predicted_away < 2.0:
            return True
        
        # High defensive strength (low goals conceded)
        home_concede = home_stats.goals_conceded_per_match
        away_concede = away_stats.goals_conceded_per_match
        
        if home_concede < 1.0 and away_concede < 1.0:
            return True
        
        return False
    
    def _get_dominant_team(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        predicted_home: float,
        predicted_away: float,
    ) -> Optional[str]:
        """
        Identify if there's a dominant team for VA handicap.
        
        Returns "home" or "away" if there's a clear favorite, None otherwise.
        """
        # Check win rates
        home_wr = home_stats.win_rate
        away_wr = away_stats.win_rate
        
        # Check goal differences
        home_gd = home_stats.goal_difference
        away_gd = away_stats.goal_difference
        
        # Check predicted goals difference
        goal_diff = predicted_home - predicted_away
        
        # Home is dominant
        if home_wr > 0.6 and home_gd > 10 and goal_diff > 0.5:
            return "home"
        
        # Away is dominant
        if away_wr > 0.6 and away_gd > 10 and goal_diff < -0.5:
            return "away"
        
        return None
    
    def _generate_corners_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
    ) -> list[SuggestedPick]:
        """Generate corner-based picks."""
        picks = []
        
        home_avg = home_stats.avg_corners_per_match
        away_avg = away_stats.avg_corners_per_match
        total_avg = home_avg + away_avg
        
        if total_avg == 0:
            return picks
        
        # Find best threshold for over corners
        for threshold in self.CORNER_THRESHOLDS:
            probability = self._poisson_over_probability(total_avg, threshold)
            
            # Apply learning weight adjustment
            adj = self.learning_weights.get_market_adjustment(MarketType.CORNERS_OVER.value)
            adjusted_prob = min(1.0, probability * adj)
            
            # Apply market priority
            priority_boost = self.MARKET_PRIORITY[MarketType.CORNERS_OVER]
            priority_score = adjusted_prob * priority_boost
            
            if adjusted_prob > 0.55:  # Only suggest if reasonable probability
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.CORNERS_OVER,
                    market_label=f"Más de {threshold} córners",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Promedio combinado: {total_avg:.1f} córners/partido. "
                             f"Local: {home_avg:.1f}, Visitante: {away_avg:.1f}",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.60,
                    priority_score=priority_score,
                )
                picks.append(pick)
                break  # Only add best threshold
        
        return picks
    
    def _generate_cards_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
    ) -> list[SuggestedPick]:
        """Generate card-based picks."""
        picks = []
        
        home_avg = home_stats.avg_yellow_cards_per_match
        away_avg = away_stats.avg_yellow_cards_per_match
        total_avg = home_avg + away_avg
        
        if total_avg == 0:
            return picks
        
        # Find best threshold
        for threshold in self.CARD_THRESHOLDS:
            probability = self._poisson_over_probability(total_avg, threshold)
            
            adj = self.learning_weights.get_market_adjustment(MarketType.CARDS_OVER.value)
            adjusted_prob = min(1.0, probability * adj)
            
            priority_boost = self.MARKET_PRIORITY[MarketType.CARDS_OVER]
            priority_score = adjusted_prob * priority_boost
            
            if adjusted_prob > 0.55:
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.CARDS_OVER,
                    market_label=f"Más de {threshold} tarjetas amarillas",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Promedio combinado: {total_avg:.1f} tarjetas/partido. "
                             f"Local: {home_avg:.1f}, Visitante: {away_avg:.1f}",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.60,
                    priority_score=priority_score,
                )
                picks.append(pick)
                break
        
        # Also generate team-specific card picks
        for team_name, team_avg, is_home in [
            (match.home_team.name, home_avg, True),
            (match.away_team.name, away_avg, False),
        ]:
            for threshold in [1.5, 2.5]:
                probability = self._poisson_over_probability(team_avg, threshold)
                adj = self.learning_weights.get_market_adjustment(MarketType.CARDS_OVER.value)
                adjusted_prob = min(1.0, probability * adj)
                
                if adjusted_prob > 0.65:  # Higher threshold for team-specific
                    confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                    risk = self._calculate_risk_level(adjusted_prob)
                    
                    pick = SuggestedPick(
                        market_type=MarketType.CARDS_OVER,
                        market_label=f"{team_name} - Más de {threshold} tarjetas",
                        probability=round(adjusted_prob, 3),
                        confidence_level=confidence,
                        reasoning=f"Promedio del equipo: {team_avg:.1f} tarjetas/partido",
                        risk_level=risk,
                        is_recommended=adjusted_prob > 0.70,
                        priority_score=adjusted_prob * self.MARKET_PRIORITY[MarketType.CARDS_OVER],
                    )
                    picks.append(pick)
                    break
        
        return picks
    
    def _generate_va_handicap_picks(
        self,
        dominant_team: str,
        predicted_home: float,
        predicted_away: float,
        match: Match,
    ) -> list[SuggestedPick]:
        """Generate VA handicap picks for dominant teams."""
        picks = []
        
        if dominant_team == "home":
            team_name = match.home_team.name
            goal_diff = predicted_home - predicted_away
        else:
            team_name = match.away_team.name
            goal_diff = predicted_away - predicted_home
        
        for handicap in self.VA_HANDICAPS:
            # Calculate probability of covering handicap
            # VA (+X) means team can lose by up to X-1 goals
            probability = self._calculate_va_probability(goal_diff, handicap)
            
            adj = self.learning_weights.get_market_adjustment(MarketType.VA_HANDICAP.value)
            adjusted_prob = min(1.0, probability * adj)
            
            priority_boost = self.MARKET_PRIORITY[MarketType.VA_HANDICAP]
            priority_score = adjusted_prob * priority_boost
            
            if adjusted_prob > 0.65:
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.VA_HANDICAP,
                    market_label=f"Hándicap VA (+{handicap}) - {team_name}",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Equipo dominante con diferencia de goles esperada de {goal_diff:.1f}. "
                             f"VA (+{handicap}) es más seguro que resultado directo.",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.70,
                    priority_score=priority_score,
                )
                picks.append(pick)
                break  # Only add best handicap option
        
        return picks
    
    def _generate_goals_picks(
        self,
        predicted_home: float,
        predicted_away: float,
        is_low_scoring: bool,
    ) -> list[SuggestedPick]:
        """Generate goals picks with penalties for low-scoring contexts."""
        picks = []
        
        total_expected = predicted_home + predicted_away
        
        # Over 2.5 goals
        over_25_prob = self._poisson_over_probability(total_expected, 2.5)
        
        # Apply learning adjustment
        adj = self.learning_weights.get_market_adjustment(MarketType.GOALS_OVER.value)
        adjusted_prob = over_25_prob * adj
        
        # Apply low-scoring penalty
        if is_low_scoring:
            adjusted_prob *= 0.75  # 25% penalty
            penalty_note = " ⚠️ Penalizado por contexto defensivo."
        else:
            penalty_note = ""
        
        adjusted_prob = min(1.0, adjusted_prob)
        
        priority_boost = self.MARKET_PRIORITY[MarketType.GOALS_OVER]
        priority_score = adjusted_prob * priority_boost
        
        confidence = SuggestedPick.get_confidence_level(adjusted_prob)
        risk = self._calculate_risk_level(adjusted_prob)
        
        pick = SuggestedPick(
            market_type=MarketType.GOALS_OVER,
            market_label="Más de 2.5 goles",
            probability=round(adjusted_prob, 3),
            confidence_level=confidence,
            reasoning=f"Goles esperados totales: {total_expected:.1f}.{penalty_note}",
            risk_level=risk + (1 if is_low_scoring else 0),  # Increase risk if low-scoring
            is_recommended=adjusted_prob > 0.65 and not is_low_scoring,
            priority_score=priority_score,
        )
        picks.append(pick)
        
        # Under 2.5 goals (favored in low-scoring context)
        under_25_prob = 1 - over_25_prob
        adj_under = self.learning_weights.get_market_adjustment(MarketType.GOALS_UNDER.value)
        adjusted_under = under_25_prob * adj_under
        
        if is_low_scoring:
            adjusted_under *= 1.1  # 10% boost
        
        adjusted_under = min(1.0, adjusted_under)
        
        if adjusted_under > 0.55:
            confidence = SuggestedPick.get_confidence_level(adjusted_under)
            risk = self._calculate_risk_level(adjusted_under)
            
            pick = SuggestedPick(
                market_type=MarketType.GOALS_UNDER,
                market_label="Menos de 2.5 goles",
                probability=round(adjusted_under, 3),
                confidence_level=confidence,
                reasoning=f"Goles esperados totales: {total_expected:.1f}. "
                         f"{'Favorecido por contexto defensivo.' if is_low_scoring else ''}",
                risk_level=risk,
                is_recommended=adjusted_under > 0.60,
                priority_score=adjusted_under * self.MARKET_PRIORITY[MarketType.GOALS_UNDER],
            )
            picks.append(pick)
        
        return picks
    
    def _poisson_over_probability(self, expected: float, threshold: float) -> float:
        """Calculate probability of over threshold using Poisson distribution."""
        if expected <= 0:
            return 0.0
        
        under_prob = 0.0
        # Sum probabilities from 0 to threshold (rounded down)
        for k in range(int(threshold) + 1):
            under_prob += (math.pow(expected, k) * math.exp(-expected)) / math.factorial(k)
        
        return 1 - under_prob
    
    def _calculate_va_probability(self, goal_diff: float, handicap: float) -> float:
        """
        Calculate probability of covering VA handicap.
        
        VA (+X) wins if: actual_diff + X > 0
        So we need actual_diff > -X
        """
        # Use normal approximation for goal difference
        std_dev = 1.3  # Typical std dev for goal difference
        
        # Need to beat -handicap threshold
        z_score = (goal_diff - (-handicap)) / std_dev
        
        # Approximate normal CDF
        return 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
    
    def _calculate_risk_level(self, probability: float) -> int:
        """Calculate risk level (1-5) from probability."""
        if probability > 0.80:
            return 1
        elif probability > 0.70:
            return 2
        elif probability > 0.60:
            return 3
        elif probability > 0.50:
            return 4
        return 5
