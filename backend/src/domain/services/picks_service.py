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
        MarketType.TEAM_GOALS_OVER: 0.7,
        MarketType.TEAM_GOALS_UNDER: 0.85,
        MarketType.RESULT_1X2: 1.0,
        MarketType.BTTS_YES: 0.9,
        MarketType.BTTS_NO: 0.85,
    }
    
    
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
            # Generate handicap picks (needs win prob)
            handicap_picks = self._generate_handicap_picks(
                match, predicted_home_goals, predicted_away_goals, 
                home_win_prob, away_win_prob
            )
            for pick in handicap_picks:
                picks.add_pick(pick)
            
            # Generate winner pick
            winner_pick = self._generate_winner_pick(
                match, home_win_prob, draw_prob, away_win_prob
            )
            if winner_pick:
                picks.add_pick(winner_pick)
        
        # 5. Only generate goals picks if we actually have goal predictions
        if has_prediction_data:
            # Generate goals picks
            goals_picks = self._generate_goals_picks(
                predicted_home_goals, predicted_away_goals, is_low_scoring
            )
            for pick in goals_picks:
                picks.add_pick(pick)
                
            # Generate BTTS picks
            btts_pick = self._generate_btts_pick(
                predicted_home_goals, predicted_away_goals, is_low_scoring
            )
            if btts_pick:
                picks.add_pick(btts_pick)
                
            # Generate Team Goals picks
            home_goals_picks = self._generate_team_goals_picks(
                 predicted_home_goals, match.home_team.name, True, is_low_scoring
            )
            for pick in home_goals_picks:
                picks.add_pick(pick)
                
            away_goals_picks = self._generate_team_goals_picks(
                 predicted_away_goals, match.away_team.name, False, is_low_scoring
            )
            for pick in away_goals_picks:
                picks.add_pick(pick)
        
        # 6. Team Corners & Cards (Unconditional - User requested "all possible picks")
        if has_home_stats and has_away_stats:
             # Team Corners
            p_home_corners = self._generate_single_team_corners(home_stats, match, True)
            if p_home_corners: picks.add_pick(p_home_corners)
            
            p_away_corners = self._generate_single_team_corners(away_stats, match, False)
            if p_away_corners: picks.add_pick(p_away_corners)
            
            # Team Cards
            p_home_cards = self._generate_single_team_cards(home_stats, match, True)
            if p_home_cards: picks.add_pick(p_home_cards)
            
            p_away_cards = self._generate_single_team_cards(away_stats, match, False)
            if p_away_cards: picks.add_pick(p_away_cards)

        # CRITICAL FIX: If we have odds-based picks, return them even if no stats!
        if not picks.suggested_picks and home_win_prob > 0:
             winner_pick = self._generate_winner_pick(
                match, home_win_prob, draw_prob, away_win_prob
            )
             if winner_pick:
                picks.add_pick(winner_pick)
            
        # Finally, sort all generated picks by probability in descending order
        picks.suggested_picks.sort(key=lambda p: p.probability, reverse=True)

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
        """
        Generate DYNAMIC corner-based picks based on match data.
        """
        picks = []
        home_avg = home_stats.avg_corners_per_match
        away_avg = away_stats.avg_corners_per_match
        total_avg = home_avg + away_avg

        if total_avg <= 0:
            return picks

        # Generate a dynamic main line and an alternative
        main_line = math.floor(total_avg - 0.5) + 0.5
        alternative_line = main_line + 1.0

        lines_to_check = sorted(list(set([main_line, alternative_line])))

        for line in lines_to_check:
            if line <= 0: continue

            # --- OVER PICK ---
            over_prob = self._poisson_over_probability(total_avg, line)
            adj = self.learning_weights.get_market_adjustment(MarketType.CORNERS_OVER.value)
            adjusted_over_prob = min(1.0, over_prob * adj)

            if adjusted_over_prob > 0.53:
                adjusted_over_prob = self._boost_prob(adjusted_over_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_over_prob)
                risk = self._calculate_risk_level(adjusted_over_prob)
                pick = SuggestedPick(
                    market_type=MarketType.CORNERS_OVER,
                    market_label=f"Más de {line} córners",
                    probability=round(adjusted_over_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Promedio de córners: {total_avg:.2f}. "
                                f"Local promedia {home_avg:.2f}, Visitante {away_avg:.2f}.",
                    risk_level=risk,
                    is_recommended=adjusted_over_prob > 0.68,
                    priority_score=adjusted_over_prob * self.MARKET_PRIORITY[MarketType.CORNERS_OVER],
                    expected_value=0.0,
                )
                picks.append(pick)
            
            # --- UNDER PICK ---
            under_prob = 1 - over_prob
            adj_under = self.learning_weights.get_market_adjustment(MarketType.CORNERS_UNDER.value)
            adjusted_under_prob = min(1.0, under_prob * adj_under)

            if adjusted_under_prob > 0.53:
                adjusted_under_prob = self._boost_prob(adjusted_under_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_under_prob)
                risk = self._calculate_risk_level(adjusted_under_prob)
                pick = SuggestedPick(
                    market_type=MarketType.CORNERS_UNDER,
                    market_label=f"Menos de {line} córners",
                    probability=round(adjusted_under_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Línea de {line} córners es alta para el promedio de {total_avg:.2f} del partido.",
                    risk_level=risk,
                    is_recommended=adjusted_under_prob > 0.68,
                    priority_score=adjusted_under_prob * self.MARKET_PRIORITY[MarketType.CORNERS_UNDER],
                    expected_value=0.0,
                )
                picks.append(pick)
        
        return picks
    
    def _generate_cards_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
    ) -> list[SuggestedPick]:
        """
        Generate DYNAMIC card-based picks for a given match.
        """
        picks = []
        home_avg = home_stats.avg_yellow_cards_per_match
        away_avg = away_stats.avg_yellow_cards_per_match
        total_avg = home_avg + away_avg

        if total_avg <= 0:
            return picks

        # Dynamic main line for cards
        main_line = math.floor(total_avg - 0.5) + 0.5
        
        lines_to_check = [main_line]
        # Add a more aggressive line if the main one is not too high
        if main_line < 4.5:
            lines_to_check.append(main_line + 1.0)

        for line in sorted(list(set(lines_to_check))):
            if line <= 0: continue

            # --- OVER PICK ---
            over_prob = self._poisson_over_probability(total_avg, line)
            adj = self.learning_weights.get_market_adjustment(MarketType.CARDS_OVER.value)
            adjusted_over_prob = min(1.0, over_prob * adj)

            if adjusted_over_prob > 0.55:
                adjusted_over_prob = self._boost_prob(adjusted_over_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_over_prob)
                risk = self._calculate_risk_level(adjusted_over_prob)
                pick = SuggestedPick(
                    market_type=MarketType.CARDS_OVER,
                    market_label=f"Más de {line} tarjetas",
                    probability=round(adjusted_over_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Promedio de tarjetas: {total_avg:.2f}. "
                                f"Local: {home_avg:.2f}, Visitante: {away_avg:.2f}.",
                    risk_level=risk,
                    is_recommended=adjusted_over_prob > 0.68,
                    priority_score=adjusted_over_prob * self.MARKET_PRIORITY[MarketType.CARDS_OVER],
                    expected_value=0.0,
                )
                picks.append(pick)

            # --- UNDER PICK ---
            under_prob = 1 - over_prob
            adj_under = self.learning_weights.get_market_adjustment(MarketType.CARDS_UNDER.value)
            adjusted_under_prob = min(1.0, under_prob * adj_under)

            if adjusted_under_prob > 0.55:
                adjusted_under_prob = self._boost_prob(adjusted_under_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_under_prob)
                risk = self._calculate_risk_level(adjusted_under_prob)
                pick = SuggestedPick(
                    market_type=MarketType.CARDS_UNDER,
                    market_label=f"Menos de {line} tarjetas",
                    probability=round(adjusted_under_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Línea de {line} tarjetas es alta para el promedio de {total_avg:.2f} del partido.",
                    risk_level=risk,
                    is_recommended=adjusted_under_prob > 0.68,
                    priority_score=adjusted_under_prob * self.MARKET_PRIORITY[MarketType.CARDS_UNDER],
                    expected_value=0.0,
                )
                picks.append(pick)

        return picks
    
    def _generate_goals_picks(
        self,
        predicted_home: float,
        predicted_away: float,
        is_low_scoring: bool,
    ) -> list[SuggestedPick]:
        """
        Generate goals picks with DYNAMIC thresholds based on match data.
        This creates more specific, less repetitive picks.
        """
        picks = []
        total_expected = predicted_home + predicted_away

        if total_expected <= 0:
            return picks

        # Determine the main betting line (e.g., 2.8 total -> 2.5 line)
        main_line = math.floor(total_expected - 0.25) + 0.5

        # Also check an alternative, more aggressive line
        alternative_line = main_line + 1.0
        
        # Define lines to check: main line, and alternative if it's different
        lines_to_check = [main_line]
        if alternative_line != main_line:
            lines_to_check.append(alternative_line)

        for line in lines_to_check:
            # --- OVER PICK ---
            over_prob = self._poisson_over_probability(total_expected, line)
            
            # Apply learning adjustment
            adj_over = self.learning_weights.get_market_adjustment(MarketType.GOALS_OVER.value)
            adjusted_over_prob = over_prob * adj_over
            
            penalty_note = ""
            if is_low_scoring:
                adjusted_over_prob *= 0.8  # Stronger penalty for dynamic lines
                penalty_note = " ⚠️ Penalizado por contexto defensivo."

            adjusted_over_prob = min(1.0, adjusted_over_prob)
            
            # Only add if the probability is reasonable
            if adjusted_over_prob > 0.53:
                adjusted_over_prob = self._boost_prob(adjusted_over_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_over_prob)
                risk = self._calculate_risk_level(adjusted_over_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.GOALS_OVER,
                    market_label=f"Más de {line} goles",
                    probability=round(adjusted_over_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Goles esperados: {total_expected:.2f}. La línea de {line} se basa en esta predicción.{penalty_note}",
                    risk_level=risk,
                    is_recommended=adjusted_over_prob > 0.65 and not is_low_scoring,
                    priority_score=adjusted_over_prob * self.MARKET_PRIORITY[MarketType.GOALS_OVER],
                    expected_value=0.0,
                )
                picks.append(pick)

            # --- UNDER PICK ---
            under_prob = 1 - over_prob
            
            adj_under = self.learning_weights.get_market_adjustment(MarketType.GOALS_UNDER.value)
            adjusted_under_prob = under_prob * adj_under
            
            boost_note = ""
            if is_low_scoring:
                adjusted_under_prob *= 1.15  # Stronger boost for dynamic lines
                boost_note = " ✅ Favorecido por contexto defensivo."
            
            adjusted_under_prob = min(1.0, adjusted_under_prob)

            if adjusted_under_prob > 0.53:
                adjusted_under_prob = self._boost_prob(adjusted_under_prob)
                confidence = SuggestedPick.get_confidence_level(adjusted_under_prob)
                risk = self._calculate_risk_level(adjusted_under_prob)
                
                pick = SuggestedPick(
                    market_type=MarketType.GOALS_UNDER,
                    market_label=f"Menos de {line} goles",
                    probability=round(adjusted_under_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Goles esperados: {total_expected:.2f}. Contexto del partido apoya un resultado con pocos goles.{boost_note}",
                    risk_level=risk,
                    is_recommended=adjusted_under_prob > 0.65,
                    priority_score=adjusted_under_prob * self.MARKET_PRIORITY[MarketType.GOALS_UNDER],
                    expected_value=0.0,
                )
                picks.append(pick)
        
        
        return picks

    def _boost_prob(self, p: float) -> float:
        """Apply non-linear boost to separate strong picks from weak ones."""
        if p < 0.55: return p
        # Simple linear expansion: 0.55 stays same, 0.75 becomes 0.85
        # f(p) = p + (p - 0.55) * 0.6
        boosted = p + (p - 0.55) * 0.6
        return min(0.95, boosted)
    
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
    def _calculate_handicap_probability(goal_diff: float, handicap: float, total_expected: float = 2.5) -> float:
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
                expected_value=0.0,
            )
        return None
    
    def _generate_handicap_picks(
        self,
        match: Match,
        predicted_home: float,
        predicted_away: float,
        home_win_prob: float,
        away_win_prob: float,
    ) -> list[SuggestedPick]:
        """
        Generate DYNAMIC Asian Handicap picks (positive and negative) based on match data.
        """
        picks = []
        
        # Determine the favorite and the underdog
        if home_win_prob > away_win_prob + 0.1:
            favorite, underdog = match.home_team, match.away_team
            goal_diff = predicted_home - predicted_away # From favorite's perspective
        elif away_win_prob > home_win_prob + 0.1:
            favorite, underdog = match.away_team, match.home_team
            goal_diff = predicted_away - predicted_home # From favorite's perspective
        else: # Balanced match, no clear favorite
            # In this case, we can still offer +0.5 on either team
            for team, prob in [(match.home_team, home_win_prob), (match.away_team, away_win_prob)]:
                # Simplified goal_diff for balanced match
                bal_goal_diff = (predicted_home - predicted_away) if team == match.home_team else (predicted_away - predicted_home)
                
                # Test +0.5 for this team
                handicap = 0.5
                prob_cover = self._calculate_handicap_probability(bal_goal_diff, handicap, predicted_home + predicted_away)
                
                if prob_cover > 0.60:
                    picks.append(self._create_handicap_pick(
                        team_name=team.name,
                        handicap=handicap,
                        probability=prob_cover,
                        goal_diff=bal_goal_diff,
                    ))
            return picks

        # If there's a clear favorite, proceed here
        total_expected_goals = predicted_home + predicted_away

        # DYNAMIC HANDICAPS based on goal difference
        # Round goal_diff to nearest 0.25 to create realistic handicap lines
        base_handicap = round(goal_diff * 4) / 4

        handicaps_to_test = {
            # For Favorite (negative handicaps)
            "fav": [base_handicap - 0.25, base_handicap, base_handicap + 0.25],
            # For Underdog (positive handicaps)
            "und": [-base_handicap - 0.25, -base_handicap, -base_handicap + 0.25]
        }
        
        # Test handicaps for the FAVORITE (e.g., -0.5, -1.0)
        for handicap in sorted(list(set(h for h in handicaps_to_test["fav"] if h < 0))):
            prob_fav_covers = self._calculate_handicap_probability(goal_diff, handicap, total_expected_goals)
            
            if prob_fav_covers > 0.60:
                picks.append(self._create_handicap_pick(
                    team_name=favorite.name,
                    handicap=handicap,
                    probability=prob_fav_covers,
                    goal_diff=goal_diff,
                ))

        # Test handicaps for the UNDERDOG (e.g., +0.5, +1.0)
        for handicap in sorted(list(set(h for h in handicaps_to_test["und"] if h > 0))):
            # For underdog, the goal_diff perspective is negative
            prob_und_covers = self._calculate_handicap_probability(-goal_diff, handicap, total_expected_goals)
            
            if prob_und_covers > 0.60:
                 picks.append(self._create_handicap_pick(
                    team_name=underdog.name,
                    handicap=handicap,
                    probability=prob_und_covers,
                    goal_diff=-goal_diff,
                ))

        return picks
    
    def _create_handicap_pick(
        self, team_name: str, handicap: float, probability: float, goal_diff: float
    ) -> SuggestedPick:
        """Helper to create a SuggestedPick for handicaps."""
        
        # Format handicap sign and value
        handicap_str = f"+{handicap}" if handicap > 0 else str(handicap)
        
        # Adjust reasoning based on handicap type
        if handicap < 0:
            reason = f"{team_name} es favorito. Se espera que gane por un margen de ~{goal_diff:.2f} goles."
        else:
            reason = f"Margen de seguridad para {team_name}. Se espera que no pierda por más de {handicap-0.5} goles."

        adj_prob = min(0.95, probability) # Cap probability
        adj_prob = max(0.55, adj_prob)

        confidence = SuggestedPick.get_confidence_level(adj_prob)
        risk = self._calculate_risk_level(adj_prob)

        return SuggestedPick(
            market_type=MarketType.VA_HANDICAP,
            market_label=f"Hándicap Asiático {handicap_str} - {team_name.split()[0]}",
            probability=round(adj_prob, 3),
            confidence_level=confidence,
            reasoning=reason,
            risk_level=risk,
            is_recommended=adj_prob > 0.65,
            priority_score=adj_prob * self.MARKET_PRIORITY[MarketType.VA_HANDICAP],
            expected_value=0.0,
        )

    def _generate_winner_pick(
        self,
        match: Match,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
    ) -> Optional[SuggestedPick]:
        """Generate match winner pick."""
        max_prob = max(home_win_prob, draw_prob, away_win_prob)
        
        selected_odds = 0.0
        
        if home_win_prob == max_prob:
            label = f"Victoria {match.home_team.name} (1)"
            reasoning = "Análisis estadístico favorece al equipo local."
            selected_odds = match.home_odds if match.home_odds else 0.0
        elif away_win_prob == max_prob:
            label = f"Victoria {match.away_team.name} (2)"
            reasoning = "Análisis estadístico favorece al equipo visitante."
            selected_odds = match.away_odds if match.away_odds else 0.0
        else:
            label = "Empate (X)"
            reasoning = "Equipos equilibrados, el empate es el resultado más probable."
            selected_odds = match.draw_odds if match.draw_odds else 0.0
        
        # Profitability Check: Calculate Expected Value (EV)
        # EV = (Probability * Odds) - 1
        ev_note = ""
        is_value_bet = False
        kelly_stake = 0.0
        
        if selected_odds > 0:
            ev = (max_prob * selected_odds) - 1
            if ev > 0:
                # Kelly Criterion: f* = (bp - q) / b
                # b = odds - 1 (net odds)
                b = selected_odds - 1
                if b > 0:
                    q = 1 - max_prob
                    f = ((b * max_prob) - q) / b
                    # Use Quarter Kelly (1/4) for safety in sports betting
                    kelly_stake = max(0, (f * 0.25) * 100)
                
                ev_note = f" 💎 VALUE BET (EV +{ev:.1%}). Stake sugerido (Kelly 1/4): {kelly_stake:.1f}%."
                is_value_bet = True
            else:
                ev_note = f". ⚠️ Precaución: Cuota {selected_odds} sin valor matemático (EV {ev:.1%}). No apostar."

        confidence = SuggestedPick.get_confidence_level(max_prob)
        risk = self._calculate_risk_level(max_prob)
        
        # Boost priority significantly for Value Bets
        priority_mult = 2.0 if is_value_bet else 0.5
        
        # Recommendation Logic for Profitability:
        # 1. If Value Bet: Recommend if prob > 35% (allow underdogs if value exists)
        # 2. If No Odds: Recommend if prob > 60% (blind prediction)
        # 3. If Negative EV: Do NOT recommend (long term loss guaranteed)
        
        should_recommend = False
        if is_value_bet:
            # PROFITABILITY FIX: Allow lower probability for Value Bets if EV is positive.
            # E.g. Odds 4.0 (25%) with Model 30% is a massive value bet.
            should_recommend = max_prob > 0.30
        elif selected_odds == 0:
            # PROFITABILITY FIX: Without odds, we are betting blind. Require high certainty.
            should_recommend = max_prob > 0.70
        
        return SuggestedPick(
            market_type=MarketType.WINNER,
            market_label=label,
            probability=round(max_prob, 3),
            confidence_level=confidence,
            reasoning=reasoning + ev_note,
            risk_level=risk,
            is_recommended=should_recommend,
            # PROFITABILITY FIX: Use EV as priority score component if available
            priority_score=(ev if is_value_bet else max_prob) * self.MARKET_PRIORITY.get(MarketType.RESULT_1X2, 1.0) * priority_mult,
            expected_value=ev if is_value_bet else 0.0,
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
            
            if adjusted_prob > 0.55:
                adjusted_prob = self._boost_prob(adjusted_prob)
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
                    expected_value=0.0,
                )
        return None

    def _generate_btts_pick(
        self,
        predicted_home: float,
        predicted_away: float,
        is_low_scoring: bool
    ) -> Optional[SuggestedPick]:
        """Generate BTTS (Ambos Marcan) pick."""
        # P(Team Scored > 0) = 1 - P(0)
        # Using Poisson: P(0) = e^(-lambda)
        prob_home_score = 1.0 - math.exp(-predicted_home)
        prob_away_score = 1.0 - math.exp(-predicted_away)
        
        btts_yes_prob = prob_home_score * prob_away_score
        btts_no_prob = 1.0 - btts_yes_prob
        
        # Adjust based on logic
        if is_low_scoring:
            btts_yes_prob *= 0.9
            btts_no_prob = min(0.95, btts_no_prob * 1.05)
            
        btts_yes_prob = min(0.95, btts_yes_prob)
        btts_no_prob = min(0.95, btts_no_prob)
        
        # Decide which (if any) to recommend
        if btts_yes_prob > 0.55:
             btts_yes_prob = self._boost_prob(btts_yes_prob)
             confidence = SuggestedPick.get_confidence_level(btts_yes_prob)
             risk = self._calculate_risk_level(btts_yes_prob)
             return SuggestedPick(
                market_type=MarketType.BTTS_YES,
                market_label="Ambos Equipos Marcan: SÍ",
                probability=round(btts_yes_prob, 3),
                confidence_level=confidence,
                reasoning=f"Altas probabilidades de gol para ambos (Local: {prob_home_score:.0%}, Visitante: {prob_away_score:.0%}).",
                risk_level=risk,
                is_recommended=btts_yes_prob > 0.65,
                priority_score=btts_yes_prob * self.MARKET_PRIORITY.get(MarketType.BTTS_YES, 0.9),
                expected_value=0.0
             )
        elif btts_no_prob > 0.55:
             btts_no_prob = self._boost_prob(btts_no_prob)
             confidence = SuggestedPick.get_confidence_level(btts_no_prob)
             risk = self._calculate_risk_level(btts_no_prob)
             return SuggestedPick(
                market_type=MarketType.BTTS_NO,
                market_label="Ambos Equipos Marcan: NO",
                probability=round(btts_no_prob, 3),
                confidence_level=confidence,
                reasoning=f"Probabilidad de que al menos un equipo no marque es alta.",
                risk_level=risk,
                is_recommended=btts_no_prob > 0.65,
                priority_score=btts_no_prob * self.MARKET_PRIORITY.get(MarketType.BTTS_NO, 0.85),
                expected_value=0.0
             )
        return None

    def _generate_team_goals_picks(
        self,
        predicted_goals: float,
        team_name: str,
        is_home: bool,
        is_low_scoring: bool
    ) -> list[SuggestedPick]:
        """Generate goals picks for a specific team."""
        picks = []
        if predicted_goals <= 0: return picks
        
        thresholds = [0.5, 1.5, 2.5]
        
        for threshold in thresholds:
            # Over
            prob = self._poisson_over_probability(predicted_goals, threshold)
            
            # Context adjustment
            if is_low_scoring: prob *= 0.9
            prob = min(0.95, prob)
            
            if prob > 0.55:
                 prob = self._boost_prob(prob)
                 confidence = SuggestedPick.get_confidence_level(prob)
                 risk = self._calculate_risk_level(prob)
                 pick = SuggestedPick(
                    market_type=MarketType.TEAM_GOALS_OVER,
                    market_label=f"{team_name} - Más de {threshold} goles",
                    probability=round(prob, 3),
                    confidence_level=confidence,
                    reasoning=f"{team_name} esperamos {predicted_goals:.2f} goles.",
                    risk_level=risk,
                    is_recommended=prob > 0.65,
                    priority_score=prob * self.MARKET_PRIORITY.get(MarketType.TEAM_GOALS_OVER, 0.7),
                    expected_value=0.0
                 )
                 picks.append(pick)
                 
        return picks

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
                    expected_value=0.0,
                )
        return None
