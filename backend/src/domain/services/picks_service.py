"""
Picks Service Module

Domain service for generating AI-suggested betting picks with smart
market prioritization based on historical performance and feedback rules.
"""

import math
import functools
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
    
    def __init__(
        self, 
        learning_weights: Optional[LearningWeights] = None,
        context_analyzer: Optional['ContextAnalyzer'] = None,
        confidence_calculator: Optional['ConfidenceCalculator'] = None
    ):
        """Initialize with optional learning, context, and confidence services."""
        from src.domain.services.context_analyzer import ContextAnalyzer
        from src.domain.services.confidence_calculator import ConfidenceCalculator
        
        self.learning_weights = learning_weights or LearningWeights()
        self.context_analyzer = context_analyzer or ContextAnalyzer()
        self.confidence_calculator = confidence_calculator or ConfidenceCalculator()
    
    def generate_suggested_picks(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        predicted_home_goals: float = 0.0,
        predicted_away_goals: float = 0.0,
        home_win_prob: float = 0.0,
        draw_prob: float = 0.0,
        away_win_prob: float = 0.0,
    ) -> MatchSuggestedPicks:
        """
        Generate suggested picks for a match using ONLY REAL DATA.
        Ahora potenciado con Contexto y Confianza Granular.
        """
        picks = MatchSuggestedPicks(match_id=match.id)
        
        # Analyze Context
        context = self.context_analyzer.analyze_match_context(match, home_stats, away_stats)
        
        # RELAXED: We attempt to generate picks even with partial data
        # but we track data quality to adjust confidence
        has_home_stats = home_stats is not None and home_stats.matches_played > 0
        has_away_stats = away_stats is not None and away_stats.matches_played > 0
        has_prediction_data = predicted_home_goals > 0 or predicted_away_goals > 0
        
        # Check if this is a low-scoring context
        is_low_scoring = False
        if has_home_stats and has_away_stats:
            is_low_scoring = self._is_low_scoring_context(
                home_stats, away_stats, predicted_home_goals, predicted_away_goals
            )
        
        if has_home_stats and has_away_stats:
            corners_picks = self._generate_corners_picks(home_stats, away_stats, match)
            for pick in corners_picks:
                picks.add_pick(pick)
        
            # Generate cards picks
            cards_picks = self._generate_cards_picks(home_stats, away_stats, match)
            for pick in cards_picks:
                picks.add_pick(pick)
            
            # Generate red card pick
            red_card_pick = self._generate_red_cards_pick(home_stats, away_stats, match)
            if red_card_pick:
                picks.add_pick(red_card_pick)
        
        # 4. Prediction-based picks (Winner/Goals)
        # We can generate winner picks if we have probability (even from odds), 
        # but Goals picks require goal stats.
        if home_win_prob > 0:
            # Generate VA handicap picks (needs win prob)
            va_picks = self._generate_va_handicap_picks_v2(
                match, predicted_home_goals, predicted_away_goals, 
                home_win_prob, away_win_prob
            )
            for pick in va_picks:
                picks.add_pick(pick)
            
            # Generate winner pick
            winner_pick = self._generate_winner_pick(
                match, home_win_prob, draw_prob, away_win_prob
            )
            if winner_pick:
                picks.add_pick(winner_pick)
        
        # Only generate goals picks if we actually have goal predictions
        if has_prediction_data:
            # Generate goals picks
            goals_picks = self._generate_goals_picks(
                predicted_home_goals, predicted_away_goals, is_low_scoring
            )
            for pick in goals_picks:
                picks.add_pick(pick)
        
        # CRITICAL FIX: If we have odds-based picks, return them even if no stats!
        # The previous 'pass' block was doing nothing, but we want to ensure we don't return empty if we have *something*.
        if not picks.suggested_picks and home_win_prob > 0:
             # If we still have nothing but have probabilities, try harder to get a winner pick
             winner_pick = self._generate_winner_pick(
                match, home_win_prob, draw_prob, away_win_prob
            )
             if winner_pick:
                picks.add_pick(winner_pick)
            
        # Fallback: Si aún no hay picks pero tenemos estadísticas, intentamos mercados individuales
        # Esto asegura que si hay "data en la card" (stats), se genere al menos una sugerencia.
        if not picks.suggested_picks and has_home_stats and has_away_stats:
            fallback_picks = []
            
            # Intentar Córners Individuales
            p = self._generate_single_team_corners(home_stats, match, True)
            if p: fallback_picks.append(p)
            p = self._generate_single_team_corners(away_stats, match, False)
            if p: fallback_picks.append(p)
            
            # Intentar Tarjetas Individuales
            p = self._generate_single_team_cards(home_stats, match, True)
            if p: fallback_picks.append(p)
            p = self._generate_single_team_cards(away_stats, match, False)
            if p: fallback_picks.append(p)
            
            if fallback_picks:
                # Seleccionar el mejor pick individual disponible
                fallback_picks.sort(key=lambda x: x.probability, reverse=True)
                picks.add_pick(fallback_picks[0])

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
        
        # User Request: Return ONLY the pick with highest probability
        if picks:
            # Sort by probability descending
            picks.sort(key=lambda x: x.probability, reverse=True)
            return [picks[0]]
            
        return []
    
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
            
        potential_picks = []
        
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
                potential_picks.append(pick)
        
        # Select best overall card pick
        if potential_picks:
            potential_picks.sort(key=lambda x: x.probability, reverse=True)
            picks.append(potential_picks[0])
        
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
            total_expected = predicted_home + predicted_away
            probability = self._calculate_va_probability(goal_diff, handicap, total_expected)
            
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
                # Removed break to allow multiple handicap options
        
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
    
    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def _poisson_over_probability(expected: float, threshold: float) -> float:
        """Calculate probability of over threshold using Poisson distribution (Optimized)."""
        if expected <= 0:
            return 0.0
        
        # Optimization: Calculate Poisson iteratively to avoid expensive factorial/pow calls
        # P(k) = (lambda^k * e^-lambda) / k!
        # P(k) = P(k-1) * lambda / k
        p_k = math.exp(-expected)  # Probability for k=0
        under_prob = p_k
        
        for k in range(1, int(threshold) + 1):
            p_k *= expected / k
            under_prob += p_k
            
        return 1 - under_prob
    
    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def _calculate_va_probability(goal_diff: float, handicap: float, total_expected: float = 2.5) -> float:
        """
        Calculate probability of covering VA handicap.
        
        VA (+X) wins if: actual_diff + X > 0
        So we need actual_diff > -X
        """
        # Use Skellam approximation for goal difference variance
        # Variance of (Home - Away) = Var(Home) + Var(Away)
        # For Poisson, Var = Mean. So Var(Diff) = ExpHome + ExpAway = TotalExpected
        std_dev = math.sqrt(total_expected) if total_expected > 0 else 1.3
        
        # Need to beat -handicap threshold
        z_score = (goal_diff - (-handicap)) / std_dev
        
        # Approximate normal CDF
        return 0.5 * (1 + math.erf(z_score / math.sqrt(2)))
    
    @staticmethod
    def _calculate_risk_level(probability: float) -> int:
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
    
    def _generate_red_cards_pick(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
    ) -> Optional[SuggestedPick]:
        """Generate red cards pick based on historical data."""
        home_avg = home_stats.avg_red_cards_per_match
        away_avg = away_stats.avg_red_cards_per_match
        total_avg = home_avg + away_avg
        
        # Red cards are rare events, typically 0.1-0.3 per match
        probability = min(0.45, 0.12 + total_avg * 0.15)
        
        if probability > 0.10:
            confidence = SuggestedPick.get_confidence_level(probability)
            risk = self._calculate_risk_level(probability)
            
            return SuggestedPick(
                market_type=MarketType.RED_CARDS,
                market_label="Tarjeta Roja en el Partido",
                probability=round(probability, 3),
                confidence_level=confidence,
                reasoning=f"Promedio combinado: {total_avg:.2f} rojas/partido. "
                         f"Historial reciente indica {'tendencia a expulsiones' if total_avg > 0.2 else 'baja probabilidad'}.",
                risk_level=5,  # Red cards are always high risk
                is_recommended=False,  # Never recommend due to rarity
                priority_score=probability * 0.5,  # Low priority
            )
        return None
    
    def _generate_va_handicap_picks_v2(
        self,
        match: Match,
        predicted_home: float,
        predicted_away: float,
        home_win_prob: float,
        away_win_prob: float,
    ) -> list[SuggestedPick]:
        """Generate VA handicap picks based on win probabilities."""
        picks = []
        
        goal_diff = predicted_home - predicted_away
        
        # Determine dominant team and align goal_diff relative to that team
        if home_win_prob > away_win_prob + 0.10:
            team_name = match.home_team.name
            # Goal diff relative to Home is already set
        elif away_win_prob > home_win_prob + 0.10:
            team_name = match.away_team.name
            # Goal diff relative to Away
            goal_diff = -goal_diff
        else:
            # Balanced match - pick the one with positive diff, or Home if 0
            if goal_diff >= 0:
                team_name = match.home_team.name
            else:
                team_name = match.away_team.name
                goal_diff = -goal_diff
        
        total_expected = predicted_home + predicted_away
        
        # Iterate over all available handicaps instead of hardcoding 2.0
        for handicap in self.VA_HANDICAPS:
            # FIX: Use signed goal_diff, not abs(). 
            # If selected team is actually underdog (negative diff), we want that reflected.
            va_prob = self._calculate_va_probability(goal_diff, handicap, total_expected)
            
            # Use the calculated probability directly, but cap it slightly to account for uncertainty
            adjusted_prob = min(0.95, va_prob)
            adjusted_prob = max(0.55, adjusted_prob)
            
            if adjusted_prob > 0.60:
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.VA_HANDICAP,
                    market_label=f"Hándicap VA (+{handicap}) - {team_name.split()[0]}",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Ventaja para {team_name} con hándicap asiático. "
                              f"Diferencia de goles esperada: {abs(goal_diff):.1f}",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.65,
                    priority_score=adjusted_prob * self.MARKET_PRIORITY[MarketType.VA_HANDICAP],
                )
                picks.append(pick)
        
        return picks
    
    def _generate_winner_pick(
        self,
        match: Match,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
    ) -> Optional[SuggestedPick]:
        """Generate match winner pick."""
        max_prob = max(home_win_prob, draw_prob, away_win_prob)
        
        if home_win_prob == max_prob:
            label = f"Victoria {match.home_team.name} (1)"
            reasoning = "Análisis estadístico favorece al equipo local."
        elif away_win_prob == max_prob:
            label = f"Victoria {match.away_team.name} (2)"
            reasoning = "Análisis estadístico favorece al equipo visitante."
        else:
            label = "Empate (X)"
            reasoning = "Equipos equilibrados, el empate es el resultado más probable."
        
        confidence = SuggestedPick.get_confidence_level(max_prob)
        risk = self._calculate_risk_level(max_prob)
        
        return SuggestedPick(
            market_type=MarketType.WINNER,
            market_label=label,
            probability=round(max_prob, 3),
            confidence_level=confidence,
            reasoning=reasoning,
            risk_level=risk,
            is_recommended=max_prob > 0.50,
            priority_score=max_prob * self.MARKET_PRIORITY.get(MarketType.RESULT_1X2, 1.0),
        )

    # Fallback pick removed to strictly comply with 'no invented data' policy

    def _generate_single_team_corners(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool
    ) -> Optional[SuggestedPick]:
        """Generate corners pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_corners_per_match
        
        # Thresholds for single team
        thresholds = [3.5, 4.5, 5.5]
        
        for threshold in thresholds:
            prob = self._poisson_over_probability(avg, threshold)
            
            # Simple adjustment
            adjusted_prob = min(0.90, prob * 0.95)
            
            if adjusted_prob > 0.60:
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                return SuggestedPick(
                    market_type=MarketType.CORNERS_OVER,
                    market_label=f"{team_name} - Más de {threshold} córners",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Estadística individual: {team_name} promedia {avg:.1f} córners.",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.65,
                    priority_score=adjusted_prob * 1.1,
                )
        return None

    def _generate_single_team_cards(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool
    ) -> Optional[SuggestedPick]:
        """Generate cards pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_yellow_cards_per_match
        
        thresholds = [1.5, 2.5]
        
        for threshold in thresholds:
            prob = self._poisson_over_probability(avg, threshold)
            
            adjusted_prob = min(0.90, prob * 0.95)
            
            if adjusted_prob > 0.60:
                confidence = SuggestedPick.get_confidence_level(adjusted_prob)
                risk = self._calculate_risk_level(adjusted_prob)
                
                return SuggestedPick(
                    market_type=MarketType.CARDS_OVER,
                    market_label=f"{team_name} - Más de {threshold} tarjetas",
                    probability=round(adjusted_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Estadística individual: {team_name} promedia {avg:.1f} tarjetas.",
                    risk_level=risk,
                    is_recommended=adjusted_prob > 0.65,
                    priority_score=adjusted_prob * 1.1,
                )
        return None
