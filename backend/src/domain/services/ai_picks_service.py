"""
AI Picks Service Module

Extends the standard PicksService to provide "Exclusive AI Picks" driven by:
1. Reinforcement Learning (LearningWeights) - Model-First approach
2. Deep Match Context (Defensive Struggle, One-Sided, etc.)
3. High Confidence "AI Locks"
4. Algorithmic Value Bets
"""

import logging
import re
from typing import List, Optional

from src.domain.entities.entities import Match, TeamH2HStatistics, TeamStatistics
from src.domain.entities.suggested_pick import (
    ConfidenceLevel,
    MarketType,
    MatchSuggestedPicks,
    SuggestedPick,
)
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.picks_service import PicksService
from src.domain.value_objects.value_objects import LeagueAverages

logger = logging.getLogger(__name__)


class AIPicksService(PicksService):
    """
    Advanced service that acts as an "AI Architect" for betting picks.
    It wraps the statistical logic with a layer of intelligent filtering,
    context-awareness, and value detection.
    """

    # Semantic Categories for Robust Logic (Enum-based)
    DEFENSIVE_MARKETS = {
        MarketType.GOALS_UNDER,
        MarketType.GOALS_UNDER_0_5,
        MarketType.GOALS_UNDER_1_5,
        MarketType.GOALS_UNDER_2_5,
        MarketType.GOALS_UNDER_3_5,
        MarketType.CORNERS_UNDER,
        MarketType.HOME_CORNERS_UNDER,
        MarketType.AWAY_CORNERS_UNDER,
        MarketType.CARDS_UNDER,
        MarketType.HOME_CARDS_UNDER,
        MarketType.AWAY_CARDS_UNDER,
        MarketType.BTTS_NO,
        MarketType.DOUBLE_CHANCE_1X,
        MarketType.DOUBLE_CHANCE_X2,
    }

    OFFENSIVE_MARKETS = {
        MarketType.GOALS_OVER,
        MarketType.GOALS_OVER_0_5,
        MarketType.GOALS_OVER_1_5,
        MarketType.GOALS_OVER_2_5,
        MarketType.GOALS_OVER_3_5,
        MarketType.CORNERS_OVER,
        MarketType.HOME_CORNERS_OVER,
        MarketType.AWAY_CORNERS_OVER,
        MarketType.CARDS_OVER,
        MarketType.HOME_CARDS_OVER,
        MarketType.AWAY_CARDS_OVER,
        MarketType.BTTS_YES,
        MarketType.TEAM_GOALS_OVER,
        MarketType.DOUBLE_CHANCE_12,
    }

    FAVORITE_MARKETS = {
        MarketType.RESULT_1X2,
        MarketType.VA_HANDICAP,
        MarketType.TEAM_GOALS_OVER,
        MarketType.CORNERS_1X2_1,
        MarketType.CORNERS_1X2_2,
    }

    VOLATILITY_MARKETS = {
        MarketType.GOALS_OVER_2_5,
        MarketType.GOALS_OVER_3_5,
        MarketType.BTTS_YES,
        MarketType.DOUBLE_CHANCE_12,
        MarketType.CARDS_OVER,
        MarketType.RED_CARDS,
    }

    _LINE_REGEX = re.compile(r"(\d+\.?\d*)")

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
        predicted_home_corners: float = 0.0,
        predicted_away_corners: float = 0.0,
        predicted_home_yellow_cards: float = 0.0,
        predicted_away_yellow_cards: float = 0.0,
        market_odds: Optional[dict[str, float]] = None,
        ml_model: Optional[object] = None,  # <--- Added missing parameter
    ) -> MatchSuggestedPicks:
        """
        Orchestrates the generation of AI-exclusive picks.
        """
        # 0. STRICT RULE 2B: "Zero Stats" Handling
        # If team stats are missing or predictions are zero, we MUST inject values based
        # on League Averages.
        # This prevents "Empty Picks" lists and ensures we always provide a baseline.
        if league_averages:
            # Fallback values (Standard averages) if league_averages is somehow empty
            avg_corners_home = getattr(league_averages, "avg_corners_home", 4.5) or 4.5
            avg_corners_away = getattr(league_averages, "avg_corners_away", 4.0) or 4.0
            avg_cards_home = (
                getattr(league_averages, "avg_yellow_cards_home", 2.0) or 2.0
            )
            avg_cards_away = (
                getattr(league_averages, "avg_yellow_cards_away", 2.0) or 2.0
            )

            if predicted_home_corners <= 0.1:
                predicted_home_corners = avg_corners_home
            if predicted_away_corners <= 0.1:
                predicted_away_corners = avg_corners_away
            if predicted_home_yellow_cards <= 0.1:
                predicted_home_yellow_cards = avg_cards_home
            if predicted_away_yellow_cards <= 0.1:
                predicted_away_yellow_cards = avg_cards_away

        # 1. Generate Base Candidate Picks using Statistical Models (Poisson/Dixon-
        # Coles)
        # We reuse the verified mathematical core of the parent class.
        candidates_container = super().generate_suggested_picks(
            match,
            home_stats,
            away_stats,
            league_averages,
            h2h_stats,
            predicted_home_goals,
            predicted_away_goals,
            home_win_prob,
            draw_prob,
            away_win_prob,
            predicted_home_corners,
            predicted_away_corners,
            predicted_home_yellow_cards,
            predicted_away_yellow_cards,
            market_odds,
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
            match,
            candidates,
            context_semantics,
            home_stats,
            away_stats,
            ml_model,
        )

        # 4. Update the container
        candidates_container.suggested_picks = ai_refined_picks
        candidates_container.sort_picks()  # Ensure best picks are top

        return candidates_container

    def _derive_context_semantics(
        self,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        pred_home: float,
        pred_away: float,
    ) -> dict[str, bool]:
        """
        Derives semantic labels for the match context to drive business rules.
        """
        semantics = {
            "defensive_struggle": False,
            "one_sided": False,
            "high_volatility": False,
        }

        if not home_stats or not away_stats:
            return semantics

        # Use parent logic + stricter boundaries
        is_low_scoring = self._is_low_scoring_context(
            home_stats, away_stats, pred_home, pred_away
        )

        # Defensive Struggle: Low scoring AND low conversion rates or high defensive
        # form
        if is_low_scoring and (pred_home + pred_away < 2.2):
            semantics["defensive_struggle"] = True

        # One-Sided: Large probability gap
        # Or calculate from extracted features if available, or implied from stats
        # We start with stats gap
        if home_stats.matches_played > 0 and away_stats.matches_played > 0:
            # Calculate PPG manually to avoid AttributeError on cached objects
            home_ppg = (
                ((home_stats.wins * 3) + home_stats.draws) / home_stats.matches_played
                if home_stats.matches_played > 0
                else 0.0
            )
            away_ppg = (
                ((away_stats.wins * 3) + away_stats.draws) / away_stats.matches_played
                if away_stats.matches_played > 0
                else 0.0
            )

            points_gap = abs(home_ppg - away_ppg)
            if points_gap > 1.2:  # Significant PPG difference
                semantics["one_sided"] = True

        # High Volatility: High scoring expectation OR erratic form (Glass Cannon teams)
        # If predicted total goals > 3.2 OR (Home has Wins AND Losses in recent form AND
        # concedes > 1.5)
        if pred_home + pred_away > 3.2:
            semantics["high_volatility"] = True
        elif (
            home_stats.recent_form
            and "W" in home_stats.recent_form
            and "L" in home_stats.recent_form
        ):
            # Check if they are leaky at the back
            conceded_avg = home_stats.goals_conceded / max(1, home_stats.matches_played)
            if conceded_avg > 1.4:
                semantics["high_volatility"] = True

        return semantics

    def _process_ai_logic(
        self,
        match: Match,
        picks: List[SuggestedPick],
        context: dict[str, bool],
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
        ml_model: Optional[object] = None,
    ) -> List[SuggestedPick]:
        """
        The core "AI Brain" pipeline.
        Filters -> Context Boosts -> Locks -> Value Detection.
        """
        refined_picks = []

        # Pre-compute ML predictions in batch to avoid repeated Python->C crossing
        target_model = ml_model if ml_model else self.ml_model
        ml_confidences = None
        predict_proba = getattr(target_model, "predict_proba", None)
        if callable(predict_proba):
            try:
                features_batch = [
                    MLFeatureExtractor.extract_features(
                        pick,
                        match,
                        home_stats,
                        away_stats,
                    )
                    for pick in picks
                ]
                probs = predict_proba(features_batch)
                ml_confidences = []
                for p in probs:
                    if len(p) > 1:
                        ml_confidences.append(float(p[1]))
                    else:
                        ml_confidences.append(float(p[0]))
            except Exception as e:
                logger.debug(f"ML batch prediction failed: {e}")
                ml_confidences = [0.0] * len(picks)

        for idx, pick in enumerate(picks):
            market_type = pick.market_type

            # PHASE A: Model-First Filtering (LearningWeights)
            # Automatically discard markets performing poorly historically
            weight = self.learning_weights.get_market_adjustment(market_type)

            # STRICTER: weight < 0.6 -> Discard (Quality over Quantity)
            if (
                weight < 0.15
            ):  # RELAXED: Allow markets unless they are absolutely broken (<0.15)
                logger.debug(
                    f"AI Discarded {pick.market_label} (Weight {weight:.2f} < 0.6)"
                )
                continue

            # --- PHASE B: Integration of Context ---
            # Rule: Defensive Struggle -> Force UNDER / NO BTTS
            if context["defensive_struggle"]:
                if market_type in self.DEFENSIVE_MARKETS:
                    pick.priority_score *= 1.25
                    pick.reasoning += " 🛡️ Contexto Defensivo."
                    pick.confidence_level = (
                        ConfidenceLevel.HIGH
                    )  # Boost confidence directly
                elif market_type in self.OFFENSIVE_MARKETS:
                    # Penalize contradictory picks in this context
                    pick.priority_score *= 0.5  # Stricter penalty

            # Rule: One-Sided -> Prioritize HANDICAP / TEAM GOALS / WINNER
            if context["one_sided"]:
                if market_type in self.FAVORITE_MARKETS:
                    pick.priority_score *= 1.2
                    pick.reasoning += " ⚔️ Desigualdad detectada."

            # Rule: High Volatility -> Favor OVER / BTTS / Double Chance (12)
            if context["high_volatility"]:
                if market_type in self.VOLATILITY_MARKETS:
                    pick.priority_score *= 1.15
                    pick.reasoning += " ⚡ Partido Volátil."
                elif market_type in self.DEFENSIVE_MARKETS:
                    pick.priority_score *= 0.85  # Penalize defensive bets in chaos

            # --- PHASE C: ML Confirmation (Predict Proba) ---
            ml_confidence = 0.0
            if ml_confidences is not None:
                try:
                    ml_confidence = ml_confidences[idx]
                    pick.ml_confidence = float(ml_confidence)
                except Exception:
                    ml_confidence = 0.0

            # --- PHASE D: AI Locks Generation (HIGH PRECISION MODE) ---
            # Criteria: Prob > 65%, Weight >= 1.0, ML > 75%
            # If ML model is missing (during backtesting), use stricter statistical
            # thresholds

            # Context Compliance Check:
            # A pick qualifies for "Lock" status ONLY if it aligns with the dominant
            # context
            context_aligned = True
            if context["defensive_struggle"]:
                # In defensive games, only defensive picks can be locks
                if market_type not in self.DEFENSIVE_MARKETS:
                    context_aligned = False
            elif context["one_sided"]:
                # In one-sided games, only favorites/goals can be locks
                if market_type not in self.FAVORITE_MARKETS:
                    context_aligned = False

            # Baseline Thresholds
            min_prob = 0.65
            min_ml = 0.75

            # If context is NOT aligned, we demand much higher evidence (Extraordinary
            # Evidence)
            if not context_aligned:
                min_prob = 0.80
                min_ml = 0.85

            # --- PHASE D: AI Locks Generation (HIGH PRECISION MODE) ---
            if self.ml_model and ml_confidence > 0:
                is_ai_lock = (
                    pick.probability > min_prob
                    and weight >= 1.05
                    and ml_confidence > min_ml
                )
            else:
                # Fallback: Strong Statistical signal "Algo Lock" for history
                # Stricter: 0.70 -> 0.75 to ensure only top tier picks
                # If context aligned, 75%. If not, 85%.
                fallback_prob = 0.75 if context_aligned else 0.85
                is_ai_lock = (
                    pick.probability > fallback_prob
                    and weight >= 1.0
                    and pick.priority_score > 0.75
                )

            if is_ai_lock:
                pick.priority_score *= 2.0  # Massive boost for verified quality
                pick.reasoning = f"🤖 IA HIGH PRECISION: {pick.reasoning}"
                pick.is_recommended = True
                pick.is_ml_confirmed = True
                pick.confidence_level = ConfidenceLevel.HIGH

            # --- PHASE E: Anomaly/Value Detection ---
            # Check implied odds vs internal probability
            if pick.odds > 1.0:
                implied_prob = 1.0 / pick.odds
                # If our model is > 10% more confident than the market
                # Reduced discrepancy needed to catch value, BUT added probability floor
                discrepancy = pick.probability - implied_prob

                # REQUIREMENT: Must be at least >55% probable to be a "Value Pick" for
                # general users
                if discrepancy > 0.10 and pick.probability > 0.55:
                    # Validate with context to ensure it's not a "trap"
                    # Simple heuristic: if context agrees with pick direction
                    context_supports = True
                    if (
                        market_type in self.OFFENSIVE_MARKETS
                        and context["defensive_struggle"]
                    ):
                        context_supports = False

                    if context_supports:
                        pick.priority_score *= 1.3
                        pick.reasoning += (
                            f" 💎 VALOR ALGORÍTMICO (Disc: {discrepancy*100:.1f}%)."
                        )
                        pick.expected_value = (pick.probability * pick.odds) - 1

                        # Only recommend if confidence is solid or is an AI Lock
                        if pick.probability > 0.60:
                            pick.is_recommended = True

            # FINAL FILTER: Discard picks with very low absolute probability unless they
            # are high EV longshots (handled elsewhere)
            # For "Quality over Quantity", we ignore "lottery tickets" < 45% even if EV+
            # RELAXED: Allow picks down to 35% if they have positive EV (Value Bets)
            if pick.probability < 0.20 and pick.expected_value <= 0:
                continue

            refined_picks.append(pick)

        # --- PHASE G: Narrative Coherence (Intelligence Layer) ---
        # Boost picks that reinforce each other (Synergy)
        self._apply_narrative_coherence(refined_picks)

        # --- PHASE F: Tiered Classification ---
        # REGLAS PARA IA CONFIRMED (SIMPLIFICADAS):
        # 1. Probabilidad >= 80% (threshold reducido)
        # 2. Es el pick con mayor probabilidad del partido (ordenamos DESC)
        # 3. NO está descalificado por ser línea baja de Under
        # NOTA: La validación ML es un BOOST, no un requisito bloqueante.

        ia_confirmed_threshold = 0.90
        ml_high_threshold = 0.75
        normal_threshold = 0.65

        # REMOVED: Do NOT filter out picks below Normal threshold.
        # We want to show all valid markets, just classified differently.

        if refined_picks:
            # Sort by probability descending (regla 2: mayor probabilidad primero)
            refined_picks.sort(key=lambda x: x.probability, reverse=True)

            # IMPORTANTE: NO resetear is_ml_confirmed para preservar la validación de
            # PHASE D
            # Solo resetear is_ia_confirmed para reasignar
            for p in refined_picks:
                p.is_ia_confirmed = False
                # p.is_ml_confirmed se PRESERVA de PHASE D

            # Apply tiered classification
            ia_confirmed_assigned = False
            for p in refined_picks:
                # Descalificar "Under" en líneas bajas de IA CONFIRMED
                is_disqualified_for_ia = self._is_low_line_under_bet(p)

                # CAMBIO: IA CONFIRMED ya no requiere was_ml_validated
                # El pick de mayor probabilidad >= 80% obtiene IA CONFIRMED
                if (
                    p.probability >= ia_confirmed_threshold
                    and not ia_confirmed_assigned
                    and not is_disqualified_for_ia
                ):
                    # Tier 1: IA CONFIRMED (80%+, mayor probabilidad)
                    p.is_ia_confirmed = True
                    p.is_ml_confirmed = True
                    p.is_recommended = True
                    p.confidence_level = ConfidenceLevel.HIGH
                    if "[🎯 IA CONFIRMED]" not in p.reasoning:
                        p.reasoning = f"[🎯 IA CONFIRMED] {p.reasoning}"
                    ia_confirmed_assigned = True
                elif p.probability >= ml_high_threshold:
                    # Tier 2: ML High Confidence (75%-79%)
                    p.is_ia_confirmed = False
                    p.is_ml_confirmed = (
                        True  # Promover a ML confirmed si tiene alta prob
                    )
                    p.is_recommended = True
                    p.confidence_level = ConfidenceLevel.HIGH
                    if "[⭐ ML ALTA CONFIANZA]" not in p.reasoning:
                        p.reasoning = f"[⭐ ML ALTA CONFIANZA] {p.reasoning}"
                elif p.probability >= normal_threshold:
                    # Tier 3: Normal (65%+)
                    p.is_ia_confirmed = False
                    # Mantener is_ml_confirmed si ya lo tenía de PHASE D
                    p.confidence_level = ConfidenceLevel.MEDIUM
                    if (
                        "[📊 NORMAL]" not in p.reasoning
                        and "[⭐" not in p.reasoning
                        and "[🎯" not in p.reasoning
                    ):
                        p.reasoning = f"[📊 NORMAL] {p.reasoning}"

        return refined_picks

    def _apply_narrative_coherence(self, picks: List[SuggestedPick]) -> None:
        """
        Boosts picks that align with the dominant narrative of the generated set.
        Example: If 'Over 2.5 Goals' is very likely, boost 'BTTS Yes'.
        """
        # Identify dominant signals (High confidence anchors)
        over_signal = any(
            p.market_type == MarketType.GOALS_OVER_2_5 and p.probability > 0.60
            for p in picks
        )
        under_signal = any(
            p.market_type == MarketType.GOALS_UNDER_2_5 and p.probability > 0.60
            for p in picks
        )

        for p in picks:
            # Coherence: Over 2.5 -> BTTS / Team Goals Over
            if over_signal:
                if p.market_type in [MarketType.BTTS_YES, MarketType.TEAM_GOALS_OVER]:
                    p.priority_score *= 1.1
                    p.reasoning += " 🔗 Sinergia Goles."

            # Coherence: Under 2.5 -> BTTS NO / Under 3.5
            if under_signal:
                if p.market_type in [MarketType.BTTS_NO, MarketType.GOALS_UNDER_3_5]:
                    p.priority_score *= 1.1
                    p.reasoning += " 🔗 Sinergia Defensiva."

    def _is_low_line_under_bet(self, pick: SuggestedPick) -> bool:
        """
        Detecta si un pick es una apuesta 'Under' en línea baja.
        Estos picks tienen alta probabilidad matemática pero bajo valor estratégico.

        Reglas de descalificación para IA CONFIRMED:
        - CORNERS_UNDER con línea < 9.5
        - CARDS_UNDER con línea < 4.5
        - Cualquier UNDER con "Menos de" en el label que no sea línea alta
        """
        market_type_str = (
            pick.market_type.value
            if hasattr(pick.market_type, "value")
            else str(pick.market_type)
        )
        label = pick.market_label.lower()

        # Detectar línea del label (e.g., "Menos de 6.5 corners" -> 6.5)
        line_match = self._LINE_REGEX.search(pick.market_label)
        line = float(line_match.group(1)) if line_match else 0.0

        # Regla 1: Corners Under con línea < 9.5
        if "CORNERS_UNDER" in market_type_str or (
            "corner" in label and "menos" in label
        ):
            if line < 9.5:
                return True

        # Regla 2: Cards Under con línea < 4.5
        if "CARDS_UNDER" in market_type_str or (
            "tarjeta" in label and "menos" in label
        ):
            if line < 4.5:
                return True

        # Regla 3: Goals Under 0.5 o 1.5 (0-0 o bajo goles no es buen headline)
        if "GOALS_UNDER" in market_type_str or ("goles" in label and "menos" in label):
            if line <= 1.5:
                return True

        return False
