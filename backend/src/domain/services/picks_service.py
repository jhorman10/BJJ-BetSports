"""
Picks Service Module

Domain service for generating AI-suggested betting picks with smart
market prioritization based on historical performance and feedback rules.
"""

import math
import functools
import os
import zlib
import logging
from typing import Optional
from src.domain.entities.entities import Match, TeamStatistics, TeamH2HStatistics
from src.domain.entities.suggested_pick import (
    SuggestedPick,
    MatchSuggestedPicks,
    MarketType,
    ConfidenceLevel,
)
from src.domain.entities.betting_feedback import LearningWeights
from src.domain.value_objects.value_objects import LeagueAverages
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.context_analyzer import ContextAnalyzer
from src.domain.services.confidence_calculator import ConfidenceCalculator
from src.domain.services.pick_resolution_service import PickResolutionService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.risk_management.bankroll_service import BankrollService

# Try to import joblib for ML model loading
try:
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

class PicksService:
    """
    Domain service for generating suggested picks.
    
    Implements the betting feedback rules:
    1. Prioritize statistical markets (corners, cards) over goals
    2. Penalize over goals when teams average < 1.5 goals/match
    3. Favor VA handicaps (+1.5/+2) for dominant teams
    4. Avoid duplicating similar markets
    5. Reduce weight for long combinations (>3 picks)
    
    STRICT POLICY:
    - NO MOCK DATA ALLOWED.
    - All predictions and picks must be derived from REAL historical data.
    - DO NOT use random number generators y or zero results instead of fake values.
    - CONSISTENCY & CACHING: Picks generated during training are cached and treated as 
      immutable history. This cache is the SINGLE SOURCE OF TRUTH for the application.
      Live predictions must use the exact same logic versions to ensure uniformity.
    
    CORE LOGIC PROTECTION RULE:
    - The mathematical models (Poisson, Skellam/Normal approximations) and data-driven 
      decision logic in this file are verified for production.
    - MODIFICATION OF CORE ALGORITHMS IS FORBIDDEN to preserve statistical integrity.
    - New features must be implemented by EXTENDING this class or adding new methods, 
      never by altering the existing probability calculation formulas.
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
        
        # New Markets
        MarketType.DOUBLE_CHANCE_1X: 1.1,
        MarketType.DOUBLE_CHANCE_X2: 1.1,
        MarketType.DOUBLE_CHANCE_12: 1.05,
        
        MarketType.GOALS_OVER_1_5: 0.9,
        MarketType.GOALS_OVER_2_5: 0.85,
        MarketType.GOALS_OVER_3_5: 0.8,
        
        MarketType.GOALS_UNDER_1_5: 0.8,
        MarketType.GOALS_UNDER_2_5: 0.85,
        MarketType.GOALS_UNDER_3_5: 0.9,
        
        MarketType.GOALS_OVER_0_5: 0.95, 
        MarketType.GOALS_UNDER_0_5: 0.95, # 0-0 Draw
        
        # Team Props Priority
        MarketType.HOME_CORNERS_OVER: 1.15,
        MarketType.HOME_CORNERS_UNDER: 1.1,
        MarketType.AWAY_CORNERS_OVER: 1.15,
        MarketType.AWAY_CORNERS_UNDER: 1.1,
        
        MarketType.HOME_CARDS_OVER: 1.15,
        MarketType.HOME_CARDS_UNDER: 1.1,
        MarketType.AWAY_CARDS_OVER: 1.15,
        MarketType.AWAY_CARDS_UNDER: 1.1,
    }
    
    
    def __init__(self, learning_weights: Optional[LearningWeights] = None):
        """Initialize with optional learning, context, and confidence services."""
        self.learning_weights = learning_weights or LearningWeights()
        self.statistics_service = StatisticsService()
        self.context_analyzer = ContextAnalyzer()
        self.resolution_service = PickResolutionService() # Centralized validator
        self.confidence_calculator = ConfidenceCalculator()
        self.bankroll_service = BankrollService() # New Risk Management Module
        
        # Load ML Model if available (Robust Path Resolution)
        try:
             # Resolve absolute path to backend root
            _service_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up: domain/services -> domain -> src -> backend
            _backend_dir = os.path.join(_service_dir, "..", "..", "..")
            model_path = os.path.join(_backend_dir, "ml_picks_classifier.joblib")
            
            self.ml_model = self._load_ml_model_safely(model_path)
        except Exception as e:
            logger.warning(f"Failed to resolve model path: {e}")
            self.ml_model = None

    def _safe_div(self, numerator: float, denominator: float, default: float = 0.0) -> float:
        """Safe division to avoid ZeroDivisionError and NaN/Inf results."""
        try:
            # Check for zero or non-finite denominator
            if not denominator or math.isnan(denominator) or math.isinf(denominator):
                return default
            res = numerator / denominator
            # Check for non-finite result
            if math.isnan(res) or math.isinf(res):
                return default
            return res
        except (ZeroDivisionError, ValueError, TypeError):
            return default

    def _load_ml_model_safely(self, model_path: str):
        """
        Securely load the ML model with proper error handling and logging.
        """
        if not ML_AVAILABLE:
            return None
            
        if not os.path.exists(model_path):
            return None
            
        try:
            # Note: We trust this local file as it is part of our internal training pipeline
            model = joblib.load(model_path)
            logger.info(f"ML Model loaded successfully from {model_path}")
            return model
        except (FileNotFoundError, ImportError) as e:
            logger.warning(f"Technical failure loading ML model: {e}")
        except Exception as e:
            logger.error(f"Security or integrity error loading ML model {model_path}: {e}")
        return None

    def _calculate_recent_form_score(self, form: str) -> float:
        """
        Calculate a form score modifier (0.8 to 1.2) based on recent results.
        Form string format: "WWDLW" (Left is most recent usually, or right? 
        Standard convention vary, but usually read left-to-right as oldest-to-newest 
        OR newest-to-oldest. Let's assume standard 'WWDLW' means last 5 games.
        We'll treat them equally for now or give slight weight to absolute recency if known.
        
        Using simple points per game relative to max.
        W=3, D=1, L=0. Max = 15.
        """
        if not form:
            return 1.0
            
        points = 0
        games = 0
        for char in form.upper():
            if char == 'W': points += 3
            elif char == 'D': points += 1
            games += 1
            
        if games == 0: return 1.0
        
        # Win rate 0.0 -> 0.85 factor
        # Win rate 1.0 -> 1.15 factor
        # Win rate 0.5 -> 1.0 factor
        
        win_ratio = self._safe_div(points, (games * 3), 0.33)
        
        # Map 0..1 to 0.85..1.15
        return 0.85 + (win_ratio * 0.30)

    def _calculate_weighted_strength(
        self, 
        base_avg: float, 
        league_avg: float, 
        recent_form: str
    ) -> float:
        """
        Calculate Relative Strength with Recency Bias.
        Strength = (Team_Avg / League_Avg)
        Weighted_Strength = Strength * Form_Modifier
        """
        if league_avg <= 0: return 1.0
        
        raw_strength = self._safe_div(base_avg, league_avg, 1.0)
        form_modifier = self._calculate_recent_form_score(recent_form)
        
        # Weighted Composition: 40% Historical Strength, 60% Form
        # Note: raw_strength includes the WHOLE season, so it IS historical.
        # We assume 'raw_strength' is the baseline capability.
        # We blend it with the form modifier.
        
        # Actually, standard "Relative Strength" models usually just multiply:
        # Strength * Form_Factor.
        # If we want 60/40 blend of "Performance":
        # Form_Strength = raw_strength * form_modifier
        # Blended = (raw_strength * 0.4) + (Form_Strength * 0.6)
        # Simplified: Strength * (0.4 + 0.6 * Form_Mod)
        
        # Let's go with the prompt's request: 
        # "tengan un peso del 60% sobre el promedio histórico (40%)"
        # Since we don't have explicit "Recent Goals", we use the Form Modifier as a proxy for "Recent Performance Ratio".
        # We'll treat 'form_modifier' as the "Recent Strength Ratio" (approx).
        
        weighted_strength = (raw_strength * 0.4) + (raw_strength * form_modifier * 0.6)
        return weighted_strength

    def _calculate_dynamic_expected_goals(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        league_avgs: LeagueAverages
    ) -> tuple[float, float]:
        """
        Calculate refined expected goals using Attack/Defense strength + Recency.
        
        Home_Exp = League_Home_Avg * Home_Att * Away_Def
        Away_Exp = League_Away_Avg * Away_Att * Home_Def
        """
        # 1. League Baselines
        avg_home_goals = league_avgs.avg_home_goals
        avg_away_goals = league_avgs.avg_away_goals
        
        # 2. Home Attack Strength
        home_att = self._calculate_weighted_strength(
            home_stats.home_goals_per_match if home_stats.home_matches_played > 3 else home_stats.goals_per_match,
            avg_home_goals,
            home_stats.recent_form
        )
        
        # 3. Away Defense Strength (Conceded relative to League Home Avg - because they are playing Away vs Home)
        # Wait, Defense strength is: (Goals Conceded / Average Goals Conceded by Away Teams)
        # Avg Goals Conceded by Away Teams = Avg Home Goals Scored (?) -> Yes.
        away_def = self._calculate_weighted_strength(
            away_stats.away_goals_conceded_per_match if away_stats.away_matches_played > 3 else away_stats.goals_conceded_per_match,
            avg_home_goals, # Away def compares to how many goals home teams usually score
            away_stats.recent_form # Use defense form? Or general form. Using general.
        )
        
        # 4. Away Attack Strength
        away_att = self._calculate_weighted_strength(
            away_stats.away_goals_per_match if away_stats.away_matches_played > 3 else away_stats.goals_per_match,
            avg_away_goals,
            away_stats.recent_form
        )
        
        # 5. Home Defense Strength
        home_def = self._calculate_weighted_strength(
            home_stats.home_goals_conceded_per_match if home_stats.home_matches_played > 3 else home_stats.goals_conceded_per_match,
            avg_away_goals,
            home_stats.recent_form
        )
        
        # Dixon-Coles / Standard Att/Def Model
        exp_home = avg_home_goals * home_att * away_def
        exp_away = avg_away_goals * away_att * home_def
        
        return exp_home, exp_away

    def _kelly_criterion(self, prob: float, odds: float, fraction: float = 0.2) -> float:
        """
        Calculate Kelly Criterion for stake sizing / confidence.
        f* = (bp - q) / b
        b = decimal_odds - 1
        p = probability
        q = 1 - p
        
        Returns: Adjusted Risk/Confidence modifier (0.0 to 1.0+).
        We use 'fractional Kelly' (0.2) to be conservative.
        """
        if odds <= 1: return 0.0
        b = odds - 1
        q = 1 - prob
        f_star = self._safe_div((b * prob - q), b, 0.0)
        
        if f_star < 0: return 0.0
        
        # Normalize: A full Kelly of 0.1 (10% bankroll) is HUGE.
        # We scale this to a 0-1 confidence "boost" or risk adjustment.
        # Let's say max sensible Kelly is ~0.2.
        
        return f_star * fraction # fractional kelly

    
    @staticmethod
    def _calculate_ev(probability: float, odds: float = 0.0) -> float:
        """
        Calculate Expected Value (EV) using real market odds.
        EV = (Probability * Odds) - 1
        """
        if odds <= 1.0: return 0.0
        return max(0.0, (probability * odds) - 1)
    
    def _evaluate_recommendation(
        self, 
        probability: float, 
        ev: float, 
        base_threshold: float
    ) -> tuple[bool, float, str]:
        """
        Determine if a pick should be recommended based on Probability and EV.
        
        Logic:
        - High EV (>10%) allows lower probability (down to 40%).
        - Moderate EV (>5%) allows probability down to 50%.
        - Otherwise uses base_threshold.
        
        Returns:
            (is_recommended, priority_multiplier, reasoning_suffix)
        """
        is_recommended = probability > base_threshold
        priority_mult = 1.0
        suffix = ""
        
        if ev > 0:
            # Boost priority based on EV
            priority_mult = 1.0 + ev  # e.g. EV 0.20 -> 1.2x multiplier
            
            if ev > 0.10 and probability > 0.40:
                is_recommended = True
                priority_mult = 1.3 # Strong boost for high value
                suffix = f" 💎 VALUE (+{ev:.1%})"
            elif ev > 0.05 and probability > 0.50:
                is_recommended = True
                priority_mult = 1.15
                suffix = f" (EV +{ev:.1%})"
            elif probability > (base_threshold - 0.05):
                is_recommended = True
                priority_mult = 1.05
                suffix = f" (EV +{ev:.1%})"
                
        return is_recommended, priority_mult, suffix

    def _build_pick_candidate(
        self,
        market_type: MarketType,
        label: str,
        probability: float,
        odds: float,
        reasoning: str,
        priority_multiplier: float = 1.0,
        min_threshold: float = 0.01,
        recommendation_threshold: float = 0.65,
        penalty_note: str = ""
    ) -> Optional[SuggestedPick]:
        """
        DRY helper to evaluate and build a SuggestedPick candidate.
        Encapsulates boost, confidence, risk, EV, and recommendation logic.
        """
        # 1. Verification against minimum threshold
        if probability < min_threshold:
            return None

        # 2. Probability processing
        display_prob = self._boost_prob(probability)
        
        # 3. Metrics calculation
        confidence = SuggestedPick.get_confidence_level(display_prob)
        risk = self._calculate_risk_level(display_prob)
        ev = self._calculate_ev(probability, odds)
        
        # 4. Recommendation evaluation
        is_rec, internal_prio_mult, suffix = self._evaluate_recommendation(
            probability, ev, recommendation_threshold
        )
        
        # 5. Build Final Reasoning
        final_reasoning = f"{reasoning}{penalty_note}{suffix}"

        # Synthetic Odds Logic if real odds invalid
        used_odds = odds
        if used_odds <= 1.0:
             used_odds = (1.0 / display_prob) * 0.95 # 5% margin
             
        # Recalculate EV with synthetic odds if needed for ranking (though usually we prefer real odds for EV)
        # But if we have no odds, EV is 0 unless we use synthetic.
        # User implies we should use it for internal value estimation.
        if ev == 0.0 and odds <= 1.0:
             ev = self._calculate_ev(probability, used_odds)

        # 6. Calculate Stake (Risk Management)
        suggested_stake = self.bankroll_service.calculate_stake(
            probability=display_prob,
            odds=used_odds, 
            confidence=1.0 # Base confidence is handled by probability and odds
        )
        
        # 7. Instantiate Pick
        return SuggestedPick(
            market_type=market_type,
            market_label=label,
            probability=round(display_prob, 3),
            confidence_level=confidence,
            reasoning=final_reasoning,
            risk_level=risk,
            is_recommended=is_rec,
            priority_score=display_prob * self.MARKET_PRIORITY.get(market_type, 1.0) * internal_prio_mult * priority_multiplier,
            odds=odds,
            expected_value=ev,
            suggested_stake=suggested_stake.units,
            kelly_percentage=suggested_stake.percentage
        )

    def generate_suggested_picks(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        league_averages: Optional[LeagueAverages] = None,
        h2h_stats: Optional[TeamH2HStatistics] = None,
        predicted_home_goals: float = 0.0,
        predicted_away_goals: float = 0.0,
        home_win_prob: float = 0.0,
        draw_prob: float = 0.0,
        away_win_prob: float = 0.0,
        market_odds: Optional[dict[str, float]] = None,
    ) -> MatchSuggestedPicks:
        """
        Generate suggested picks for a match using ONLY REAL DATA.
        Ahora potenciado con Contexto y Confianza Granular y H2H.
        """
        picks = MatchSuggestedPicks(match_id=match.id)
        
        # Analyze Context
        context = self.context_analyzer.analyze_match_context(match, home_stats, away_stats)
        
        # Analyze H2H Dominance
        h2h_factor = 1.0
        h2h_reasoning = ""
        if h2h_stats and h2h_stats.matches_played >= 2:
            # Check for dominance
            if h2h_stats.team_a_id == match.home_team.name and h2h_stats.team_a_wins > h2h_stats.team_b_wins:
                 h2h_factor = 1.1 + (0.05 * (h2h_stats.team_a_wins - h2h_stats.team_b_wins))
                 h2h_reasoning = " 🆚 Dominio H2H Local."
            elif h2h_stats.team_b_id == match.home_team.name and h2h_stats.team_b_wins > h2h_stats.team_a_wins:
                 # Logic for when H2H struct might have team_a/b swapped relative to match home/away?
                 # Assuming strict matching above in finding stats. 
                 # Usually StatisticsService returns Team A as requested first argument.
                 pass
            
            # Simplified check assuming caller passes (Home, Away)
            if h2h_stats.team_a_wins >= (h2h_stats.matches_played * 0.5):
                h2h_reasoning = " 🆚 Dominio H2H."
        
        # RELAXED: We attempt to generate picks even with partial data
        # but we track data quality to adjust confidence
        has_home_stats = home_stats is not None and home_stats.matches_played > 0
        has_away_stats = away_stats is not None and away_stats.matches_played > 0
        has_prediction_data = predicted_home_goals > 0 or predicted_away_goals > 0
        
        # --- REFACTORING: Refine Expectations using League Avgs & Weighted Strength ---
        if league_averages and has_home_stats and has_away_stats:
            # Calculate refined expected goals
            ref_home, ref_away = self._calculate_dynamic_expected_goals(
                home_stats, away_stats, league_averages
            )
            # Blend with incoming prediction if it exists (50/50 blend for robustness)
            if has_prediction_data:
                predicted_home_goals = (predicted_home_goals * 0.5) + (ref_home * 0.5)
                predicted_away_goals = (predicted_away_goals * 0.5) + (ref_away * 0.5)
            else:
                predicted_home_goals = ref_home
                predicted_away_goals = ref_away
                has_prediction_data = True # NOW we have data
                
            # Recalculate probabilities based on new expectations using Skellam/Poisson
            # (Simplified: approximated win probs not updated here to strictly follow "don't break learning.py API",
            # but we use new goals for GOALS picks).
        
        # Check if this is a low-scoring context
        is_low_scoring = False
        if has_home_stats and has_away_stats:
            is_low_scoring = self._is_low_scoring_context(
                home_stats, away_stats, predicted_home_goals, predicted_away_goals
            )
        
        # --- MODIFIED: Corners & Cards (Totals) ---
        # 100% REAL DATA: Combined totals (Match Corners, Match Cards) require BOTH teams.
        if (home_stats is not None and home_stats.matches_played > 0) and (away_stats is not None and away_stats.matches_played > 0):
            corners_picks = self._generate_corners_picks(home_stats, away_stats, match, league_averages, market_odds)
            for pick in corners_picks:
                picks.add_pick(pick)
        
            # Generate cards picks
            cards_picks = self._generate_cards_picks(home_stats, away_stats, match, league_averages, market_odds)
            for pick in cards_picks:
                picks.add_pick(pick)
            
            # Red cards require specific team stats, so keep strict check
            red_card_pick = self._generate_red_cards_pick(home_stats, away_stats, match)
            if red_card_pick:
                picks.add_pick(red_card_pick)
        
        # 4. Prediction-based picks (Winner/Goals)
        # We can generate winner picks if we have probability (even from odds), 
        # but Goals picks require goal stats.
        if home_win_prob > 0:
            # Generate winner pick
            winner_pick = self._generate_winner_pick(
                match, home_win_prob, draw_prob, away_win_prob
            )
            if winner_pick:
                # Apply H2H boost to Winner Pick if directions match
                if "Local" in winner_pick.market_label and "Dominio H2H" in h2h_reasoning:
                    winner_pick.priority_score *= h2h_factor
                    winner_pick.reasoning += h2h_reasoning
                picks.add_pick(winner_pick)
            
            # Generate Double Chance picks
            dc_picks = self._generate_double_chance_picks(
                match, home_win_prob, draw_prob, away_win_prob
            )
            for pick in dc_picks:
                picks.add_pick(pick)
        
        # 5. Goal/BTTS/Team Goals picks (Consistently generated if we have any stats or prediction)
        # 100% REAL DATA: NO fallback to league averages for goals if no prediction data.
        # This prevents "invented" Over 2.5/BTTS picks.
        if has_prediction_data or (has_home_stats and has_away_stats):
            # Generate handicap picks (needs win prob AND prediction)
            if home_win_prob > 0:
                handicap_picks = self._generate_handicap_picks(
                    match, predicted_home_goals, predicted_away_goals, 
                    home_win_prob, away_win_prob
                )
                for pick in handicap_picks:
                    picks.add_pick(pick)

            # Generate goals picks (Fixed lines 0.5, 1.5, 2.5, 3.5)
            goals_picks = self._generate_goals_picks(
                predicted_home_goals, predicted_away_goals, is_low_scoring, market_odds
            )
            for pick in goals_picks:
                picks.add_pick(pick)
                
            # Generate BTTS picks (returns list)
            btts_picks = self._generate_btts_pick(
                predicted_home_goals, predicted_away_goals, is_low_scoring, market_odds
            )
            for pick in btts_picks:
                picks.add_pick(pick)
                
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
        # Decoupled logic: Generate for Home even if Away is missing, and vice-versa
        if home_stats is not None:
            home_corners_list = self._generate_single_team_corners(home_stats, match, True)
            for p in home_corners_list: picks.add_pick(p)
            home_cards_list = self._generate_single_team_cards(home_stats, match, True)
            for p in home_cards_list: picks.add_pick(p)

        if away_stats is not None:
            away_corners_list = self._generate_single_team_corners(away_stats, match, False)
            for p in away_corners_list: picks.add_pick(p)
            away_cards_list = self._generate_single_team_cards(away_stats, match, False)
            for p in away_cards_list: picks.add_pick(p)

        # 7. Apply ML Refinement (if model exists)
        if self.ml_model:
            self._apply_ml_refinement(picks)

        # Finally, sort all generated picks by probability in descending order
        picks.suggested_picks.sort(key=lambda p: p.probability, reverse=True)

        # Evaluate picks if match is finished (for History/Backtesting)
        self._assign_match_results(match, picks.suggested_picks)

        return picks
    
    def _apply_ml_refinement(self, picks_container: MatchSuggestedPicks):
        """
        Uses the trained ML model to adjust confidence/priority of picks.
        """
        for pick in picks_container.suggested_picks:
            if not self.ml_model:
                continue
                
            try:
                # Use centralized feature extraction to ensure parity with training
                features = [MLFeatureExtractor.extract_features(pick)]
                
                # Predict probability of this pick being correct (Class 1)
                ml_confidence = self.ml_model.predict_proba(features)[0][1]
                
                # REFACTOR: Universal ML Evaluation
                # 1. High Confidence (> 65%)
                if ml_confidence > 0.65:
                    pick.priority_score *= 2.0
                    pick.reasoning += f" ML Confianza Alta ({ml_confidence:.0%})."
                    # We don't force is_recommended=True here, we let the score speak, 
                    # but the label "ML Confianza Alta" causes Frontend to show it in Top ML.
                    
                # 2. Low Confidence (< 40%)
                elif ml_confidence < 0.40:
                    pick.priority_score *= 0.5
                    pick.reasoning += f" ML Escéptico ({ml_confidence:.0%})."
                    
            except Exception:
                continue
    
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

    def _generate_total_stat_picks(
        self,
        stat_avg: float,
        lines: list[float],
        market_types: tuple[MarketType, MarketType],
        label_formats: tuple[str, str],
        reasoning_fmts: tuple[str, str],
        prob_adjustments: tuple[float, float],
        rec_thresholds: tuple[float, float],
        odds_keys_fmt: tuple[str, str],
        market_odds: Optional[dict[str, float]] = None
    ) -> list[SuggestedPick]:
        """
        Generic generator for match total statistics (Over/Under).
        Strictly DRY: Processes both markets in a single loop using tuple configuration.
        """
        picks = []
        if stat_avg <= 0:
            return picks

        m_over, m_under = market_types
        lbl_over, lbl_under = label_formats
        reas_over, reas_under = reasoning_fmts
        adj_over, adj_under = prob_adjustments
        thr_over, thr_under = rec_thresholds
        key_over_fmt, key_under_fmt = odds_keys_fmt

        for line in lines:
            # --- OVER ---
            prob_over = self._poisson_over_probability(stat_avg, line)
            final_prob_over = min(0.95, prob_over * adj_over)
            odds_over = market_odds.get(key_over_fmt.format(line), 0.0) if market_odds else 0.0
            
            p_over = self._build_pick_candidate(
                market_type=m_over,
                label=lbl_over.format(line),
                probability=final_prob_over,
                odds=odds_over,
                reasoning=reas_over.format(avg=stat_avg),
                recommendation_threshold=thr_over
            )
            if p_over:
                picks.append(p_over)

            # --- UNDER ---
            prob_under = 1.0 - prob_over
            final_prob_under = min(0.95, prob_under * adj_under)
            odds_under = market_odds.get(key_under_fmt.format(line), 0.0) if market_odds else 0.0
            
            p_under = self._build_pick_candidate(
                market_type=m_under,
                label=lbl_under.format(line),
                probability=final_prob_under,
                odds=odds_under,
                reasoning=reas_under.format(avg=stat_avg),
                recommendation_threshold=thr_under
            )
            if p_under:
                picks.append(p_under)

        return picks

    def _generate_team_stat_picks(
        self,
        stat_avg: float,
        lines: list[float],
        market_types: tuple[MarketType, MarketType],
        label_formats: tuple[str, str],
        reasoning_fmts: tuple[str, str],
        prob_adjustments: tuple[float, float],
        rec_thresholds: tuple[float, float],
        min_threshold: float = 0.01
    ) -> list[SuggestedPick]:
        """
        Generic generator for individual team statistics (Over/Under).
        """
        picks = []
        if stat_avg <= 0:
            return picks

        m_over, m_under = market_types
        lbl_over, lbl_under = label_formats
        reas_over, reas_under = reasoning_fmts
        adj_over, adj_under = prob_adjustments
        thr_over, thr_under = rec_thresholds

        for line in lines:
            # --- OVER ---
            prob_over = self._poisson_over_probability(stat_avg, line)
            final_prob_over = min(0.95, prob_over * adj_over)
            
            p_over = self._build_pick_candidate(
                market_type=m_over,
                label=lbl_over.format(line),
                probability=final_prob_over,
                odds=0.0,
                reasoning=reas_over.format(avg=stat_avg),
                recommendation_threshold=thr_over,
                min_threshold=min_threshold
            )
            if p_over:
                picks.append(p_over)

            # --- UNDER ---
            prob_under = 1.0 - prob_over
            final_prob_under = min(0.95, prob_under * adj_under)
            
            p_under = self._build_pick_candidate(
                market_type=m_under,
                label=lbl_under.format(line),
                probability=final_prob_under,
                odds=0.0,
                reasoning=reas_under.format(avg=stat_avg),
                recommendation_threshold=thr_under,
                min_threshold=min_threshold
            )
            if p_under:
                picks.append(p_under)

        return picks

    def _generate_corners_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
        league_averages: Optional[LeagueAverages] = None,
        market_odds: Optional[dict[str, float]] = None,
    ) -> list[SuggestedPick]:
        """Generate corners picks for combined match total."""
        # Tiered fallback: Team Averages -> League Averages
        h_avg = home_stats.avg_corners_per_match if home_stats and home_stats.matches_played >= 3 else None
        a_avg = away_stats.avg_corners_per_match if away_stats and away_stats.matches_played >= 3 else None
        
        if h_avg is not None and a_avg is not None:
            total_avg = h_avg + a_avg
        else:
            # 100% REAL DATA: No fallback to league averages for combined markets
            total_avg = 0.0
            
        return self._generate_total_stat_picks(
            stat_avg=total_avg,
            lines=[6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
            market_types=(MarketType.CORNERS_OVER, MarketType.CORNERS_UNDER),
            label_formats=("Más de {} córners en el partido", "Menos de {} córners en el partido"),
            reasoning_fmts=("Promedio de córners: {avg:.2f}. Tendencia favorable.", "Promedio de córners: {avg:.2f}. Baja producción."),
            prob_adjustments=(1.05, 1.02),
            rec_thresholds=(0.55, 0.55),
            odds_keys_fmt=("corners_over_{}", "corners_under_{}"),
            market_odds=market_odds
        )

    def _generate_cards_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
        league_averages: Optional[LeagueAverages] = None,
        market_odds: Optional[dict[str, float]] = None,
    ) -> list[SuggestedPick]:
        """Generate cards picks for combined match total."""
        # Tiered fallback: Team Averages -> League Averages
        h_avg = home_stats.avg_yellow_cards_per_match if home_stats and home_stats.matches_played >= 3 else None
        a_avg = away_stats.avg_yellow_cards_per_match if away_stats and away_stats.matches_played >= 3 else None
        
        if h_avg is not None and a_avg is not None:
            total_avg = h_avg + a_avg
        else:
            # 100% REAL DATA: No fallback to league averages for combined markets
            total_avg = 0.0
            
        return self._generate_total_stat_picks(
            stat_avg=total_avg,
            lines=[1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
            market_types=(MarketType.CARDS_OVER, MarketType.CARDS_UNDER),
            label_formats=("Más de {} tarjetas en el partido", "Menos de {} tarjetas en el partido"),
            reasoning_fmts=("Expectativa de tarjetas: {avg:.2f}. Análisis de volatilidad.", "Expectativa de tarjetas: {avg:.2f}. Análisis de volatilidad."),
            prob_adjustments=(1.02, 1.05),
            rec_thresholds=(0.55, 0.55),
            odds_keys_fmt=("cards_over_{}", "cards_under_{}"),
            market_odds=market_odds
        )


    def _generate_double_chance_picks(
        self,
        match: Match,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
    ) -> list[SuggestedPick]:
        """Generate Double Chance picks."""
        picks = []
        
        # 1X: Home or Draw
        prob_1x = home_win_prob + draw_prob
        # Only suggest if it's reasonably likely
        if prob_1x > 0.01:
             picks.append(self._create_double_chance_pick(
                MarketType.DOUBLE_CHANCE_1X,
                f"1X - {match.home_team.name} o Empate",
                prob_1x,
                f"Alta probabilidad combinada ({prob_1x:.0%}) de que {match.home_team.name} no pierda en casa."
            ))
            
        # X2: Draw or Away
        prob_x2 = draw_prob + away_win_prob
        if prob_x2 > 0.01:
             picks.append(self._create_double_chance_pick(
                MarketType.DOUBLE_CHANCE_X2,
                f"X2 - Empate o {match.away_team.name}",
                prob_x2,
                f"Alta probabilidad combinada ({prob_x2:.0%}) de que {match.away_team.name} sume puntos."
            ))
            
        # 12: Home or Away (No Draw)
        prob_12 = home_win_prob + away_win_prob
        if prob_12 > 0.01:
             picks.append(self._create_double_chance_pick(
                MarketType.DOUBLE_CHANCE_12,
                f"12 - {match.home_team.name} o {match.away_team.name}",
                prob_12,
                f"Baja probabilidad de empate. Se espera un ganador."
            ))
            
        return picks

    def _create_double_chance_pick(self, market_type: MarketType, label: str, prob: float, reasoning: str) -> SuggestedPick:
        """Helper for Double Chance picks."""
        # Cap double chance as it's a safe bet usually
        prob = min(0.92, prob)
        display_prob = self._boost_prob(prob)
        
        confidence = SuggestedPick.get_confidence_level(display_prob)
        risk = self._calculate_risk_level(display_prob)
        
        return SuggestedPick(
            market_type=market_type,
            market_label=label,
            probability=round(display_prob, 3),
            confidence_level=confidence,
            reasoning=reasoning,
            risk_level=risk,
            is_recommended=display_prob > 0.75,
            priority_score=display_prob * self.MARKET_PRIORITY.get(market_type, 1.05),
            expected_value=self._calculate_ev(prob)
        )
    
    def _generate_winner_pick(
        self,
        match: Match,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
    ) -> Optional[SuggestedPick]:
        """Generate winner pick based on probabilities and Kelly Criterion."""
        
        # Determine favorite and associated probability
        # 0 = Home, 1 = Draw, 2 = Away
        probs = [home_win_prob, draw_prob, away_win_prob]
        max_prob = max(probs)
        idx = probs.index(max_prob)
        
        # Volatility check: High draw probability reduces confidence in any winner
        is_volatile = draw_prob > 0.28
        
        base_threshold = 0.45
        if is_volatile: base_threshold = 0.50

        # Odds fetching (assuming standard keys)
        # Note: We don't have explicit 'market_odds' passed here in original method signature, 
        # but 'match' object has them!
        
        selection_prob = max_prob
        
        if idx == 0: # Home
            label = f"Victoria {match.home_team.name} (1)"
            odds = match.home_odds or 0.0
        elif idx == 1: # Draw
             label = "Empate (X)"
             odds = match.draw_odds or 0.0
             base_threshold = 0.35 # Draws are harder
        else: # Away
            label = f"Victoria {match.away_team.name} (2)"
            odds = match.away_odds or 0.0
            
        # Refined EV Calculation
        ev = self._calculate_ev(selection_prob, odds)
        
        # Kelly Criterion for Confidence Boost
        kelly_factor = self._kelly_criterion(selection_prob, odds)
        
        # Decision Logic
        is_recommended = False
        priority_mult = 1.0
        reasoning = f"Probabilidad: {selection_prob:.1%}."
        
        if ev > 0:
            is_recommended = True
            priority_mult = 1.0 + (ev * 2) # Reward value heavily
            reasoning += f" EV: +{ev:.1%}."
            
        if kelly_factor > 0.02: # Meaningful stake suggested
            priority_mult += kelly_factor * 5
            reasoning += f" Kelly recomienda gestión."
            
        if is_volatile:
            priority_mult *= 0.8
            reasoning += " (Alta volatilidad)."
            
        # Final gate: Must pass base threshold OR have high EV
        # RELAXED: During early season/training, we lower this to 0.3 to ensure we always have a candidate
        if selection_prob < 0.3 and ev < 0.05:
            return None
        # Construct Pick
        # Boost probability for confidence display only if valid bet
        display_prob = self._boost_prob(selection_prob)
        
        return SuggestedPick(
            market_type=MarketType.RESULT_1X2,
            market_label=label,
            probability=round(display_prob, 3),
            confidence_level=SuggestedPick.get_confidence_level(display_prob),
            reasoning=reasoning,
            risk_level=self._calculate_risk_level(display_prob),
            is_recommended=is_recommended,
            priority_score=display_prob * self.MARKET_PRIORITY.get(MarketType.RESULT_1X2, 1.0) * priority_mult,
            expected_value=ev
        )
    
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
    
    
    def _generate_goals_picks(
        self,
        predicted_home: float,
        predicted_away: float,
        is_low_scoring: bool,
        market_odds: Optional[dict[str, float]] = None,
    ) -> list[SuggestedPick]:
        """
        Generate goals picks for multiple lines (1.5, 2.5, 3.5).
        """
        picks = []
        total_expected = predicted_home + predicted_away
        # RELAXED: 0.0 is a valid expected value (e.g. 0-0 prediction)
        # We should still generate Under picks in this case.

        # Define lines to check: 0.5, 1.5, 2.5, 3.5, 4.5
        lines_to_check = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]

        for line in lines_to_check:
            # Map float line to Enum MarketType (Over)
            mrkt_over = MarketType.GOALS_OVER_2_5 # Default
            mrkt_under = MarketType.GOALS_UNDER_2_5 # Default
            
            if line == 0.5:
                mrkt_over = MarketType.GOALS_OVER_0_5
                mrkt_under = MarketType.GOALS_UNDER_0_5
            elif line == 1.5:
                mrkt_over = MarketType.GOALS_OVER_1_5
                mrkt_under = MarketType.GOALS_UNDER_1_5
            elif line == 2.5:
                mrkt_over = MarketType.GOALS_OVER_2_5
                mrkt_under = MarketType.GOALS_UNDER_2_5
            elif line == 3.5:
                 mrkt_over = MarketType.GOALS_OVER_3_5
                 mrkt_under = MarketType.GOALS_UNDER_3_5
            elif line == 4.5:
                 # We don't have separate enum for 4.5 yet, but we can reuse GOALS_OVER/UNDER
                 # OR we should add them to MarketType if we want strictness.
                 # Let's use GOALS_OVER/UNDER as fallback for now or add them.
                 mrkt_over = MarketType.GOALS_OVER
                 mrkt_under = MarketType.GOALS_UNDER
            
            # --- OVER PICK ---
            over_prob = self._poisson_model_probability(predicted_home, predicted_away, line, is_over=True)
            odds_over = market_odds.get(mrkt_over.value, 0.0) if market_odds else 0.0
            adj_over_val = self.learning_weights.get_market_adjustment(mrkt_over.value)
            adjusted_over_prob = over_prob * adj_over_val
            
            penalty_note = ""
            if is_low_scoring and line >= 2.5:
                adjusted_over_prob *= 0.85 
                penalty_note = " ⚠️ Contexto defensivo."

            pick_over = self._build_pick_candidate(
                market_type=mrkt_over,
                label=f"Más de {line} goles",
                probability=min(0.98, adjusted_over_prob),
                odds=odds_over,
                reasoning=f"Proyectado: {total_expected:.2f} goles.{penalty_note}",
                min_threshold=0.01, # Maximized volume
                recommendation_threshold=0.65,
            )
            
            # Special logic for low lines
            if pick_over and line < 1.6 and pick_over.probability < 0.8:
                pick_over.is_recommended = False
                
            if pick_over:
                picks.append(pick_over)
                
            # --- UNDER PICK ---
            under_prob = self._poisson_model_probability(predicted_home, predicted_away, line, is_over=False)
            odds_under = market_odds.get(mrkt_under.value, 0.0) if market_odds else 0.0
            adj_under_val = self.learning_weights.get_market_adjustment(mrkt_under.value)
            adjusted_under_prob = under_prob * adj_under_val
            
            boost_note = ""
            if is_low_scoring and line <= 2.5:
                adjusted_under_prob *= 1.1
                boost_note = " ✅ Contexto defensivo."

            pick_under = self._build_pick_candidate(
                market_type=mrkt_under,
                label=f"Menos de {line} goles",
                probability=min(0.98, adjusted_under_prob),
                odds=odds_under,
                reasoning=f"Proyectado: {total_expected:.2f} goles.{boost_note}",
                min_threshold=0.01, # Maximized volume
                recommendation_threshold=0.65
            )
            if pick_under:
                picks.append(pick_under)
        
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
    def _poisson_model_probability(expected_home: float, expected_away: float, line: float, is_over: bool) -> float:
        """
        Calculate probability using Dixon-Coles Light approximation.
        We iterate through plausible scores (0-0 to 9-9) and sum probabilities.
        """
        rho = -0.13 # correlation coefficient (usually negative for low scores)
        
        prob_sum = 0.0
        
        # Limit iteration for performance (0 to 10 goals is sufficient coverage > 99.9%)
        limit = 10
        
        # Precompute individual Poisson masses
        def poisson_pmf(lam, k):
            return (math.exp(-lam) * (lam ** k)) / math.factorial(k)
            
        home_probs = [poisson_pmf(expected_home, i) for i in range(limit)]
        away_probs = [poisson_pmf(expected_away, i) for i in range(limit)]
        
        for h in range(limit):
            for a in range(limit):
                # Base independence probability
                p = home_probs[h] * away_probs[a]
                
                # Dixon-Coles Adjustment for low scores
                # Adjustment factor tau(h,a)
                # 0,0: 1 - (lambda*mu*rho)  <-- Simplified heuristic
                # But standard DC adjustment is:
                # if h=0, a=0: 1 - (lambda*mu*rho) -- wait, rho is small parameter.
                # Let's use the explicit correction:
                correction = 1.0
                if h == 0 and a == 0:
                    correction = 1.0 - (expected_home * expected_away * rho)
                elif h == 0 and a == 1:
                    correction = 1.0 + (expected_home * rho)
                elif h == 1 and a == 0:
                    correction = 1.0 + (expected_away * rho)
                elif h == 1 and a == 1:
                    correction = 1.0 - rho
                
                p *= correction
                
                total = h + a
                if is_over:
                    if total > line: prob_sum += p
                else:
                    if total < line: prob_sum += p
                    
        return min(0.99, max(0.01, prob_sum))
    
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
        
        if probability > 0.01:
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
                expected_value=self._calculate_ev(probability),
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
                
                if prob_cover > 0.01:
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
            "fav": [-base_handicap - 0.25, -base_handicap, -base_handicap + 0.25],
            # For Underdog (positive handicaps)
            "und": [base_handicap - 0.25, base_handicap, base_handicap + 0.25]
        }
        
        # Test handicaps for the FAVORITE (e.g., -0.5, -1.0)
        for handicap in sorted(list(set(h for h in handicaps_to_test["fav"] if h < 0))):
            prob_fav_covers = self._calculate_handicap_probability(goal_diff, handicap, total_expected_goals)
            
            # Use lower threshold for handicaps to show variety
            if prob_fav_covers > 0.01:
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
            
            if prob_und_covers > 0.01:
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

        display_prob = self._boost_prob(adj_prob) # Boost for display
        confidence = SuggestedPick.get_confidence_level(display_prob)
        risk = self._calculate_risk_level(display_prob)

        return SuggestedPick(
            market_type=MarketType.VA_HANDICAP,
            market_label=f"Hándicap Asiático {handicap_str} - {team_name}",
            probability=round(display_prob, 3),
            confidence_level=confidence,
            reasoning=reason,
            risk_level=risk,
            is_recommended=display_prob > 0.65,
            priority_score=display_prob * self.MARKET_PRIORITY[MarketType.VA_HANDICAP],
            expected_value=self._calculate_ev(adj_prob), # EV on raw
        )


    # Fallback pick removed to strictly comply with 'no invented data' policy

    def _generate_single_team_corners(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool
    ) -> list[SuggestedPick]:
        """Generate corners pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_corners_per_match
        
        return self._generate_team_stat_picks(
            stat_avg=avg,
            lines=[2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5],
            market_types=(
                MarketType.HOME_CORNERS_OVER if is_home else MarketType.AWAY_CORNERS_OVER,
                MarketType.HOME_CORNERS_UNDER if is_home else MarketType.AWAY_CORNERS_UNDER
            ),
            label_formats=(f"{team_name} - Más de {{}} córners", f"{team_name} - Menos de {{}} córners"),
            reasoning_fmts=(f"Producción ofensiva de {team_name}: {{avg:.2f}} córners/partido.", f"Producción ofensiva de {team_name}: {{avg:.2f}} córners/partido."),
            prob_adjustments=(1.05, 1.02),
            rec_thresholds=(0.75, 0.80),
            min_threshold=0.01
        )

    def _generate_single_team_cards(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool
    ) -> list[SuggestedPick]:
        """Generate cards pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_yellow_cards_per_match
        
        return self._generate_team_stat_picks(
            stat_avg=avg,
            lines=[0.5, 1.5, 2.5, 3.5, 4.5],
            market_types=(
                MarketType.HOME_CARDS_OVER if is_home else MarketType.AWAY_CARDS_OVER,
                MarketType.HOME_CARDS_UNDER if is_home else MarketType.AWAY_CARDS_UNDER
            ),
            label_formats=(f"{team_name} - Más de {{}} tarjetas", f"{team_name} - Menos de {{}} tarjetas"),
            reasoning_fmts=(f"Promedio de tarjetas para {team_name}: {{avg:.2f}}.", f"Promedio de tarjetas para {team_name}: {{avg:.2f}}."),
            prob_adjustments=(1.02, 1.05),
            rec_thresholds=(0.80, 0.75),
            min_threshold=0.01
        )

    def _generate_btts_pick(
        self,
        predicted_home: float,
        predicted_away: float,
        is_low_scoring: bool,
        market_odds: Optional[dict[str, float]] = None,
    ) -> list[SuggestedPick]:
        """Generate BTTS (Ambos Marcan) picks for both outcomes."""
        picks = []
        # P(Team Scored > 0) = 1 - P(0)
        # Using Poisson: P(0) = e^(-lambda)
        prob_home_score = 1.0 - math.exp(-predicted_home)
        prob_away_score = 1.0 - math.exp(-predicted_away)
        
        btts_yes_prob = prob_home_score * prob_away_score
        btts_no_prob = 1.0 - btts_yes_prob
        
        # Adjust based on logic
        if is_low_scoring:
            btts_yes_prob *= 0.9
            # Recalculate NO to keep sum=1
            btts_no_prob = 1.0 - btts_yes_prob
            
        btts_yes_prob = min(0.98, btts_yes_prob)
        btts_no_prob = min(0.98, btts_no_prob)
        
        # 1. BTTS YES
        if btts_yes_prob > 0.1: # Expanded threshold
             odds_yes = market_odds.get(MarketType.BTTS_YES.value, 0.0) if market_odds else 0.0
             display_prob = self._boost_prob(btts_yes_prob)
             confidence = SuggestedPick.get_confidence_level(display_prob)
             risk = self._calculate_risk_level(display_prob)
             ev = self._calculate_ev(btts_yes_prob, odds_yes)
             is_rec, prio_mult, suffix = self._evaluate_recommendation(btts_yes_prob, ev, 0.65)
             
             picks.append(SuggestedPick(
                market_type=MarketType.BTTS_YES,
                market_label="Ambos Equipos Marcan: SÍ",
                probability=round(display_prob, 3),
                confidence_level=confidence,
                reasoning=f"Altas probabilidades de gol para ambos.{suffix}",
                risk_level=risk,
                is_recommended=is_rec,
                priority_score=display_prob * self.MARKET_PRIORITY.get(MarketType.BTTS_YES, 0.9) * prio_mult,
                expected_value=ev
             ))

        # 2. BTTS NO
        if btts_no_prob > 0.1: # Expanded threshold
             odds_no = market_odds.get(MarketType.BTTS_NO.value, 0.0) if market_odds else 0.0
             display_prob = self._boost_prob(btts_no_prob)
             confidence = SuggestedPick.get_confidence_level(display_prob)
             risk = self._calculate_risk_level(display_prob)
             ev = self._calculate_ev(btts_no_prob, odds_no)
             is_rec, prio_mult, suffix = self._evaluate_recommendation(btts_no_prob, ev, 0.65)
             
             picks.append(SuggestedPick(
                market_type=MarketType.BTTS_NO,
                market_label="Ambos Equipos Marcan: NO",
                probability=round(display_prob, 3),
                confidence_level=confidence,
                reasoning=f"Valla invicta o baja producción proyectada.{suffix}",
                risk_level=risk,
                is_recommended=is_rec,
                priority_score=display_prob * self.MARKET_PRIORITY.get(MarketType.BTTS_NO, 0.85) * prio_mult,
                expected_value=ev
             ))
             
        return picks

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
        
        thresholds = [0.5, 1.5, 2.5, 3.5]
        
        for threshold in thresholds:
            # Over
            prob = self._poisson_over_probability(predicted_goals, threshold)
            
            # Context adjustment
            if is_low_scoring: prob *= 0.9
            prob = min(0.95, prob)
            
            if prob > 0.01:
                 display_prob = self._boost_prob(prob)
                 confidence = SuggestedPick.get_confidence_level(display_prob)
                 risk = self._calculate_risk_level(display_prob)
                 pick = SuggestedPick(
                    market_type=MarketType.TEAM_GOALS_OVER,
                    market_label=f"{team_name} - Más de {threshold} goles",
                    probability=round(display_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"{team_name} esperamos {predicted_goals:.2f} goles.",
                    risk_level=risk,
                    is_recommended=display_prob > 0.65,
                    priority_score=display_prob * self.MARKET_PRIORITY.get(MarketType.TEAM_GOALS_OVER, 0.7),
                    expected_value=self._calculate_ev(prob)
                 )
                 picks.append(pick)
                 
        return picks

    def _assign_match_results(self, match: Match, picks: list[SuggestedPick]) -> None:
        """
        Assign results (WIN/LOSS) to picks based on match outcome.
        Delegates to PickResolutionService for centralized logic.
        """
        if match.home_goals is None or match.away_goals is None:
            return

        for pick in picks:
            result, _ = self.resolution_service.resolve_pick(pick, match)
            pick.result = result
