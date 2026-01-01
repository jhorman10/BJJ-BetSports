"""
AI Picks Service Module

Extends the standard PicksService to provide "Exclusive AI Picks" driven by:
1. Reinforcement Learning (LearningWeights) - Model-First approach
2. Deep Match Context (Defensive Struggle, One-Sided, etc.)
3. High Confidence "AI Locks"
4. Algorithmic Value Bets
"""

import logging
from typing import Optional, List
from src.domain.entities.entities import Match, TeamStatistics, TeamH2HStatistics
from src.domain.entities.suggested_pick import (
    SuggestedPick,
    MatchSuggestedPicks,
    MarketType,
    ConfidenceLevel
)
from src.domain.value_objects.value_objects import LeagueAverages
from src.domain.services.picks_service import PicksService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor

logger = logging.getLogger(__name__)

class AIPicksService(PicksService):
    """
    Advanced service that acts as an "AI Architect" for betting picks.
    It wraps the statistical logic with a layer of intelligent filtering,
    context-awareness, and value detection.
    """

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
        Orchestrates the generation of AI-exclusive picks.
        """
        # 1. Generate Base Candidate Picks using Statistical Models (Poisson/Dixon-Coles)
        # We reuse the verified mathematical core of the parent class.
        candidates_container = super().generate_suggested_picks(
            match, home_stats, away_stats, league_averages, h2h_stats,
            predicted_home_goals, predicted_away_goals,
            home_win_prob, draw_prob, away_win_prob, market_odds
        )
        
        # Extract the raw list for processing
        candidates = candidates_container.suggested_picks
        
        if not candidates:
            return candidates_container

        # 2. Analyze Context Semantics
        context_semantics = self._derive_context_semantics(
            match, home_stats, away_stats, predicted_home_goals, predicted_away_goals
        )
        
        # 3. Apply "Model-First" Filtering & Logic
        # This is where the AI takes over: Filtering, Boosting, Locking.
        ai_refined_picks = self._process_ai_logic(
            match, candidates, context_semantics
        )
        
        # 4. Update the container
        candidates_container.suggested_picks = ai_refined_picks
        candidates_container.sort_picks() # Ensure best picks are top
        
        return candidates_container

    def _derive_context_semantics(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        pred_home: float,
        pred_away: float
    ) -> dict[str, bool]:
        """
        Derives semantic labels for the match context to drive business rules.
        """
        semantics = {
            "defensive_struggle": False,
            "one_sided": False,
            "high_volatility": False
        }
        
        if not home_stats or not away_stats:
            return semantics

        # Use parent logic + stricter boundaries
        is_low_scoring = self._is_low_scoring_context(home_stats, away_stats, pred_home, pred_away)
        
        # Defensive Struggle: Low scoring AND low conversion rates or high defensive form
        if is_low_scoring and (pred_home + pred_away < 2.2):
             semantics["defensive_struggle"] = True

        # One-Sided: Large probability gap
        prob_gap = abs(match.home_win_prob - match.away_win_prob) if hasattr(match, 'home_win_prob') else 0.0
        # Or calculate from extracted features if available, or implied from stats
        # We start with stats gap
        if home_stats.matches_played > 0 and away_stats.matches_played > 0:
             points_gap = abs(home_stats.points_per_match - away_stats.points_per_match)
             if points_gap > 1.2: # Significant PPG difference
                 semantics["one_sided"] = True
        
        return semantics

    def _process_ai_logic(
        self,
        match: Match,
        picks: List[SuggestedPick],
        context: dict[str, bool]
    ) -> List[SuggestedPick]:
        """
        The core "AI Brain" pipeline.
        Filters -> Context Boosts -> Locks -> Value Detection.
        """
        refined_picks = []
        
        for pick in picks:
            market_type = pick.market_type
            
            # PHASE A: Model-First Filtering (LearningWeights)
            # Automatically discard markets performing poorly historically
            weight = self.learning_weights.get_market_adjustment(market_type)
            
            # RELAXED: weight < 0.1 -> Discard (from 0.5) to allow almost everything
            if weight < 0.1:
                logger.debug(f"AI Discarded {pick.market_label} (Weight {weight:.2f} < 0.1)")
                continue

            # --- PHASE B: Integration of Context ---
            # Rule: Defensive Struggle -> Force UNDER / NO BTTS
            if context["defensive_struggle"]:
                if "UNDER" in market_type or "BTTS_NO" in market_type:
                    pick.priority_score *= 1.25
                    pick.reasoning += " 🛡️ Contexto Defensivo."
                    pick.confidence_level = ConfidenceLevel.HIGH # Boost confidence directly
                elif "OVER" in market_type or "BTTS_YES" in market_type:
                    # Penalize contradictory picks in this context
                     pick.priority_score *= 0.7
            
            # Rule: One-Sided -> Prioritize HANDICAP / TEAM GOALS
            if context["one_sided"]:
                if "HANDICAP" in market_type or "TEAM_GOALS" in market_type:
                     pick.priority_score *= 1.2
                     pick.reasoning += " ⚔️ Desigualdad detectada."

            # --- PHASE C: ML Confirmation (Predict Proba) ---
            ml_confidence = 0.0
            if self.ml_model:
                try:
                    features = [MLFeatureExtractor.extract_features(pick)]
                    ml_confidence = self.ml_model.predict_proba(features)[0][1]
                except Exception:
                    pass

            # --- PHASE D: AI Locks Generation ---
            # Criteria: Prob > 65%, Weight > 1.0, ML > 75%
            is_ai_lock = (
                pick.probability > 0.65 and
                weight >= 1.0 and
                ml_confidence > 0.75
            )
            
            if is_ai_lock:
                pick.priority_score *= 1.5 # Massive boost
                pick.reasoning = f"🤖 IA CONFIRMED: {pick.reasoning}"
                pick.is_recommended = True
                pick.is_ml_confirmed = True
                
            # --- PHASE E: Anomaly/Value Detection ---
            # Check implied odds vs internal probability
            if pick.odds > 1.0:
                implied_prob = 1.0 / pick.odds
                # If our model is > 15% more confident than the market
                discrepancy = pick.probability - implied_prob
                
                if discrepancy > 0.15:
                    # Validate with context to ensure it's not a "trap"
                    # Simple heuristic: if context agrees with pick direction
                    context_supports = True
                    if "OVER" in market_type and context["defensive_struggle"]:
                        context_supports = False
                    
                    if context_supports:
                        pick.priority_score *= 1.3
                        pick.reasoning += f" 💎 VALOR ALGORÍTMICO (Disc: {discrepancy*100:.1f}%)."
                        pick.expected_value = (pick.probability * pick.odds) - 1
                        pick.is_recommended = True

            refined_picks.append(pick)
            
        return refined_picks
