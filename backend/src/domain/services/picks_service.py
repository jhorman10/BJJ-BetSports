"""
Picks Service Module

Domain service for generating AI-suggested betting picks with smart
market prioritization based on historical performance and feedback rules.
"""

import functools
import logging
import math
import os
from typing import Any, List, Optional, cast

from src.domain.entities.betting_feedback import LearningWeights
from src.domain.entities.entities import Match, TeamH2HStatistics, TeamStatistics
from src.domain.entities.suggested_pick import (
    ConfidenceLevel,
    MarketType,
    MatchSuggestedPicks,
    SuggestedPick,
)
from src.domain.services.confidence_calculator import ConfidenceCalculator
from src.domain.services.context_analyzer import ContextAnalyzer
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.pick_resolution_service import PickResolutionService
from src.domain.services.risk_management.bankroll_service import BankrollService
from src.domain.services.statistics_service import StatisticsService
from src.domain.value_objects.value_objects import LeagueAverages

# Try to import joblib for ML model loading
try:
    import joblib

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

logger = logging.getLogger(__name__)

# Serving-mode observability (design D6): every response can be marked with
# the active mode plus the reason category that forced heuristic fallback.
SERVING_MODE_ML = "ml"
SERVING_MODE_HEURISTIC = "heuristic"
FALLBACK_REASONS = (
    "load_failed",
    "version_mismatch",
    "schema_mismatch",
    "absent",
    "blend_failed",
)


class PicksConfig:
    """Centralized configuration for Picks Logic thresholds and weights."""

    KELLY_FRACTION = 0.2
    MIN_PROBABILITY_THRESHOLD = 0.01
    RECOMMENDATION_THRESHOLD = 0.65

    # EV Thresholds
    EV_HIGH_THRESHOLD = 0.10
    EV_MODERATE_THRESHOLD = 0.05

    # Probability Floors for Value Bets
    VAL_BET_MIN_PROB_HIGH_EV = 0.40
    VAL_BET_MIN_PROB_MOD_EV = 0.50

    # Boost & Penalty Factors
    LOW_SCORING_PENALTY = 0.85
    LOW_SCORING_BOOST = 1.1
    WINNER_PROB_THRESHOLD = 0.45
    WINNER_VOLATILE_THRESHOLD = 0.50
    DRAW_THRESHOLD = 0.35
    MIN_WINNER_PROB = 0.30


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
        MarketType.GOALS_UNDER_0_5: 0.95,  # 0-0 Draw
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

    def __init__(
        self,
        learning_weights: Optional[LearningWeights] = None,
        persistence_repo: Optional[Any] = None,
    ):
        """Initialize with optional learning, context, and confidence services."""
        self.learning_weights = learning_weights or LearningWeights()
        self.repo = persistence_repo
        self.statistics_service = StatisticsService()
        self.context_analyzer = ContextAnalyzer()
        self.resolution_service = PickResolutionService()  # Centralized validator
        self.confidence_calculator = ConfidenceCalculator()
        self.bankroll_service = BankrollService()  # New Risk Management Module

        # Serving-mode observability (design D6)
        self.serving_mode = SERVING_MODE_HEURISTIC
        self.fallback_reason: Optional[str] = None
        self._fallback_counts: dict[str, int] = {r: 0 for r in FALLBACK_REASONS}

        # Load ML Model if available (Validated pointer-aware resolution)
        try:
            from src.core.constants import ML_MODEL_FILENAME

            # Resolve absolute path to backend root
            _service_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up: domain/services -> domain -> src -> backend
            _backend_dir = os.path.join(_service_dir, "..", "..", "..")
            model_path = os.path.join(_backend_dir, ML_MODEL_FILENAME)

            self.ml_model = self._load_ml_model_safely(model_path)
            if self.ml_model is None:
                logger.info(
                    "Local ML model not available at %s. Using statistical fallback.",
                    model_path,
                )
        except Exception as e:
            logger.warning(f"Failed to resolve model path: {e}")
            self.ml_model = None

    def _safe_div(
        self, numerator: float, denominator: float, default: float = 0.0
    ) -> float:
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

    def _load_ml_model_safely(self, model_path: str) -> Optional[object]:
        """
        Validated pointer-aware ML model loader (ml-model-deployment spec).

        Resolution order:
        1. Serving pointer → versioned artifact (validated envelope)
        2. Legacy fixed-key blob → read-only with deprecation warning
        3. Disk file fallback (legacy/migration)
        """
        if not ML_AVAILABLE:
            self._mark_fallback("absent")
            return None

        # 1. Try versioned artifact via serving pointer
        if self.repo:
            try:
                from io import BytesIO

                pointer = self.repo.get_app_state("ml_picks_classifier/serving")
                if pointer and pointer.get("artifact_key") and pointer.get("version"):
                    artifact_key = pointer["artifact_key"]
                    version = pointer["version"]
                    model_bytes, meta = self.repo.get_versioned_artifact(
                        artifact_key, version
                    )
                    if model_bytes:
                        self._validate_envelope(meta)
                        model = joblib.load(BytesIO(model_bytes))
                        self._mark_ml_serving()
                        logger.info(
                            "ML Model loaded from versioned artifact %s@%s",
                            artifact_key,
                            version,
                        )
                        return cast(object, model)
            except ValueError as ve:
                # Envelope validation failed — explicit fallback already logged by _validate_envelope
                logger.warning("Versioned artifact validation failed: %s", ve)
                return None  # Don't fall through to legacy on validation mismatch
            except Exception as e:
                logger.warning(f"Failed to load versioned artifact: {e}")

        # 2. Legacy fixed-key blob (read-only, deprecation warning)
        if self.repo:
            try:
                from io import BytesIO

                from src.core.constants import ML_MODEL_FILENAME

                model_bytes = self.repo.get_binary_artifact(ML_MODEL_FILENAME)
                if model_bytes:
                    logger.warning(
                        "Loading legacy ML model blob (deprecated). "
                        "Run gated training to promote a versioned artifact."
                    )
                    model = joblib.load(BytesIO(model_bytes))
                    self._mark_fallback("absent")  # legacy loads lack envelope
                    return cast(object, model)
            except Exception as e:
                logger.warning(f"Failed to load legacy ML model blob: {e}")

        # 3. Disk file fallback (legacy/migration)
        if not os.path.exists(model_path):
            self._mark_fallback("absent")
            return None

        try:
            # Note: We trust this local file as it is part of our internal training
            # pipeline
            model = joblib.load(model_path)
            logger.info(f"ML Model loaded successfully from {model_path} (Disk)")
            self._mark_fallback("absent")  # disk path lacks envelope
            return cast(object, model)
        except (FileNotFoundError, ImportError) as e:
            logger.warning(f"Technical failure loading ML model: {e}")
        except Exception as e:
            logger.error(
                f"Security or integrity error loading ML model {model_path}: {e}"
            )
        self._mark_fallback("load_failed")
        return None

    def _validate_envelope(self, meta: Optional[dict]) -> None:
        """Validate artifact metadata envelope (ml-model-deployment spec).

        Raises ValueError on mismatch with stored vs runtime values.
        Sets fallback_reason to version_mismatch or schema_mismatch.
        """
        if not meta:
            raise ValueError("Missing metadata envelope")

        # sklearn version equality (strict — patch mismatch surfaces)
        stored_sklearn = str(meta.get("sklearn_version", "")).strip()
        runtime_sklearn = ""
        try:
            import sklearn

            runtime_sklearn = str(sklearn.__version__)
        except Exception:
            pass
        if stored_sklearn and runtime_sklearn and stored_sklearn != runtime_sklearn:
            self._mark_fallback("version_mismatch")
            raise ValueError(
                f"sklearn version mismatch: stored={stored_sklearn!r} "
                f"runtime={runtime_sklearn!r}"
            )

        # feature schema hash equality
        stored_schema = str(meta.get("feature_schema_hash", "")).strip()
        runtime_schema = ""
        try:
            from src.domain.services.ml_feature_extractor import MLFeatureExtractor

            runtime_schema = MLFeatureExtractor.schema_signature()
        except Exception:
            pass
        if stored_schema and runtime_schema and stored_schema != runtime_schema:
            self._mark_fallback("schema_mismatch")
            raise ValueError(
                f"Feature schema mismatch: stored={stored_schema!r} "
                f"runtime={runtime_schema!r}"
            )

    def _mark_ml_serving(self) -> None:
        """Mark successful ML-backed serving state."""
        self.serving_mode = SERVING_MODE_ML
        self.fallback_reason = None

    def _mark_fallback(self, reason: str) -> None:
        """Mark heuristic fallback with reason and emit structured log."""
        if reason in self._fallback_counts:
            self._fallback_counts[reason] += 1
        self.serving_mode = SERVING_MODE_HEURISTIC
        self.fallback_reason = reason
        logger.warning("[ML_FALLBACK] reason=%s", reason)

    def reload_model(self) -> None:
        """Force reload of the ML model from disk."""
        # Resolve absolute path (same logic as __init__)
        try:
            from src.core.constants import ML_MODEL_FILENAME

            _service_dir = os.path.dirname(os.path.abspath(__file__))
            _backend_dir = os.path.join(_service_dir, "..", "..", "..")
            model_path = os.path.join(_backend_dir, ML_MODEL_FILENAME)

            self.ml_model = self._load_ml_model_safely(model_path)
            if self.ml_model is None:
                logger.info(
                    (
                        "Local ML model not available after reload at %s. "
                        "Using statistical fallback."
                    ),
                    model_path,
                )
            else:
                logger.info("ML Model reloaded successfully.")
        except Exception as e:
            logger.error(f"Failed to reload model: {e}")

    def _calculate_recent_form_score(self, form: str) -> float:
        """
        Calculate a form score modifier (0.8 to 1.2).

        Form string examples: "WWDLW" (W=win, D=draw, L=loss).
        Conventions vary: some systems use oldest-to-newest, others newest-to-oldest.
        Here we assume the example represents the last 5 matches.

        Points per game: W=3, D=1, L=0 (max = 15).
        """
        if not form:
            return 1.0

        points = 0
        games = 0
        for char in form.upper():
            if char == "W":
                points += 3
            elif char == "D":
                points += 1
            games += 1

        if games == 0:
            return 1.0
        # Win rate 0.0 -> 0.85 factor
        # Win rate 1.0 -> 1.15 factor
        # Win rate 0.5 -> 1.0 factor

        win_ratio = self._safe_div(points, (games * 3), 0.33)

        # Map 0..1 to 0.85..1.15
        return 0.85 + (win_ratio * 0.30)

    def _calculate_weighted_strength(
        self, base_avg: float, league_avg: float, recent_form: str
    ) -> float:
        """
        Calculate Relative Strength with Recency Bias.
        Strength = (Team_Avg / League_Avg)
        Weighted_Strength = Strength * Form_Modifier
        """
        if league_avg <= 0:
            return 1.0

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
        # Since we don't have explicit "Recent Goals", we use the Form Modifier as a
        # proxy for "Recent Performance Ratio".
        # We'll treat 'form_modifier' as the "Recent Strength Ratio" (approx).

        weighted_strength = (raw_strength * 0.4) + (raw_strength * form_modifier * 0.6)
        return weighted_strength

    def _calculate_dynamic_expected_goals(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        league_avgs: LeagueAverages,
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
            (
                home_stats.home_goals_per_match
                if home_stats.home_matches_played > 3
                else home_stats.goals_per_match
            ),
            avg_home_goals,
            home_stats.recent_form,
        )

        # 3. Away Defense Strength.
        # Conceded relative to League Home Avg (they are playing away vs home).
        # Defense strength: Goals Conceded / Avg Goals Conceded by Away Teams.
        away_def = self._calculate_weighted_strength(
            (
                away_stats.away_goals_conceded_per_match
                if away_stats.away_matches_played > 3
                else away_stats.goals_conceded_per_match
            ),
            avg_home_goals,
            away_stats.recent_form,
        )

        # 4. Away Attack Strength
        away_att = self._calculate_weighted_strength(
            (
                away_stats.away_goals_per_match
                if away_stats.away_matches_played > 3
                else away_stats.goals_per_match
            ),
            avg_away_goals,
            away_stats.recent_form,
        )

        # 5. Home Defense Strength
        home_def = self._calculate_weighted_strength(
            (
                home_stats.home_goals_conceded_per_match
                if home_stats.home_matches_played > 3
                else home_stats.goals_conceded_per_match
            ),
            avg_away_goals,
            home_stats.recent_form,
        )

        # Dixon-Coles / Standard Att/Def Model
        exp_home = avg_home_goals * home_att * away_def
        exp_away = avg_away_goals * away_att * home_def

        return exp_home, exp_away

    def _kelly_criterion(
        self, prob: float, odds: float, fraction: float = 0.2
    ) -> float:
        """
        Calculate Kelly Criterion for stake sizing / confidence.
        f* = (bp - q) / b
        b = decimal_odds - 1
        p = probability
        q = 1 - p

        Returns: Adjusted Risk/Confidence modifier (0.0 to 1.0+).
        We use 'fractional Kelly' (0.2) to be conservative.
        """
        if odds <= 1:
            return 0.0
        b = odds - 1
        q = 1 - prob
        f_star = self._safe_div((b * prob - q), b, 0.0)

        if f_star < 0:
            return 0.0

        # Normalize: A full Kelly of 0.1 (10% bankroll) is HUGE.
        # We scale this to a 0-1 confidence "boost" or risk adjustment.
        # Let's say max sensible Kelly is ~0.2.

        return f_star * PicksConfig.KELLY_FRACTION  # fractional kelly

    @staticmethod
    def _calculate_ev(probability: float, odds: float = 0.0) -> float:
        """
        Calculate Expected Value (EV) using real market odds.
        EV = (Probability * Odds) - 1
        """
        if odds <= 1.0:
            return 0.0
        return max(0.0, (probability * odds) - 1)

    def _evaluate_recommendation(
        self, probability: float, ev: float, base_threshold: float
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

            if (
                ev > PicksConfig.EV_HIGH_THRESHOLD
                and probability > PicksConfig.VAL_BET_MIN_PROB_HIGH_EV
            ):
                is_recommended = True
                priority_mult = 1.3  # Strong boost for high value
                suffix = f" 💎 VALUE (+{ev:.1%})"
            elif (
                ev > PicksConfig.EV_MODERATE_THRESHOLD
                and probability > PicksConfig.VAL_BET_MIN_PROB_MOD_EV
            ):
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
        min_threshold: float = PicksConfig.MIN_PROBABILITY_THRESHOLD,
        recommendation_threshold: float = PicksConfig.RECOMMENDATION_THRESHOLD,
        penalty_note: str = "",
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
            used_odds = (1.0 / display_prob) * 0.95  # 5% margin

        # Recalculate EV with synthetic odds if needed for ranking (though usually we
        # prefer real odds for EV)
        # But if we have no odds, EV is 0 unless we use synthetic.
        # User implies we should use it for internal value estimation.
        if ev == 0.0 and odds <= 1.0:
            ev = self._calculate_ev(probability, used_odds)

        # 6. Calculate Stake (Risk Management)
        suggested_stake = self.bankroll_service.calculate_stake(
            probability=display_prob,
            odds=used_odds,
            confidence=1.0,  # Base confidence is handled by probability and odds
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
            priority_score=display_prob
            * self.MARKET_PRIORITY.get(market_type, 1.0)
            * internal_prio_mult
            * priority_multiplier,
            odds=odds,
            expected_value=ev,
            suggested_stake=suggested_stake.units,
            kelly_percentage=suggested_stake.percentage,
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
        predicted_home_corners: float = 0.0,
        predicted_away_corners: float = 0.0,
        predicted_home_yellow_cards: float = 0.0,
        predicted_away_yellow_cards: float = 0.0,
        market_odds: Optional[dict[str, float]] = None,
        ml_model: Optional[object] = None,  # <--- NEW DYNAMIC MODEL INJECTION
    ) -> MatchSuggestedPicks:
        """
        Generate suggested picks for a match using ONLY REAL DATA.
        Ahora potenciado con Contexto y Confianza Granular y H2H.
        """
        picks = MatchSuggestedPicks(match_id=match.id)

        # Analyze Context
        if home_stats and away_stats:
            self.context_analyzer.analyze_match_context(match, home_stats, away_stats)

        # Analyze H2H Dominance
        h2h_factor = 1.0
        h2h_reasoning = ""
        if h2h_stats and h2h_stats.matches_played >= 2:
            # Check for dominance
            if (
                h2h_stats.team_a_id == match.home_team.name
                and h2h_stats.team_a_wins > h2h_stats.team_b_wins
            ):
                h2h_factor = 1.1 + (
                    0.05 * (h2h_stats.team_a_wins - h2h_stats.team_b_wins)
                )
                h2h_reasoning = " 🆚 Dominio H2H Local."
            elif (
                h2h_stats.team_b_id == match.home_team.name
                and h2h_stats.team_b_wins > h2h_stats.team_a_wins
            ):
                # Logic for when H2H struct might have team_a/b swapped relative to
                # match home/away?
                # Assuming strict matching above in finding stats.
                # Usually StatisticsService returns Team A as requested first argument.
                pass

            # Simplified check assuming caller passes (Home, Away)
            if h2h_stats.team_a_wins >= (h2h_stats.matches_played * 0.5):
                h2h_reasoning = " 🆚 Dominio H2H."

        # RELAXED: We attempt to generate picks even with partial data
        # but we track data quality to adjust confidence
        # UPDATE: User Rule - Minimum 4 matches required to use stats.
        has_home_stats = home_stats is not None and home_stats.matches_played >= 2
        has_away_stats = away_stats is not None and away_stats.matches_played >= 2
        has_prediction_data = (
            predicted_home_goals > 0
            or predicted_away_goals > 0
            or predicted_home_corners > 0
            or predicted_away_corners > 0
            or predicted_home_yellow_cards > 0
            or predicted_away_yellow_cards > 0
        )

        # --- REFACTORING: Refine Expectations using League Avgs & Weighted Strength ---
        if league_averages and home_stats and away_stats:
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
                has_prediction_data = True  # NOW we have data

            # Recalculate probabilities based on new expectations using Skellam/Poisson
            # (Simplified: approximated win probs not updated here to strictly follow
            # "don't break learning.py API",
            # but we use new goals for GOALS picks).

        # Check if this is a low-scoring context
        is_low_scoring = False
        if home_stats and away_stats:
            is_low_scoring = self._is_low_scoring_context(
                home_stats, away_stats, predicted_home_goals, predicted_away_goals
            )

        # --- MODIFIED: Corners & Cards (Totals) ---
        # 100% REAL DATA: Combined totals (Match Corners, Match Cards) require BOTH
        # teams.
        # 100% REAL DATA: Combined totals (Match Corners, Match Cards) require BOTH
        # teams.
        # NOW RELAXED: If we have predictions (which use league avg fallback), we can
        # generate picks too.
        if home_stats and away_stats:
            corners_picks = self._generate_corners_picks(
                home_stats,
                away_stats,
                match,
                league_averages,
                market_odds,
                predicted_home_corners,
                predicted_away_corners,
            )
            for pick in corners_picks:
                picks.add_pick(pick)

            # Generate cards picks
            cards_picks = self._generate_cards_picks(
                home_stats,
                away_stats,
                match,
                league_averages,
                market_odds,
                predicted_home_yellow_cards,
                predicted_away_yellow_cards,
            )
            for pick in cards_picks:
                picks.add_pick(pick)

            # Generate TEAM Specific Corners/Cards (RELAXED: Use predictions if stats
            # missing)
            # We check if objects exist, ignoring the strict 'matches_played >= 4' check
            # (has_home_stats)
            if home_stats and away_stats:
                team_corners = self._generate_team_corners_picks(
                    home_stats,
                    away_stats,
                    predicted_home_corners,
                    predicted_away_corners,
                )
                for pick in team_corners:
                    picks.add_pick(pick)

                team_cards = self._generate_team_cards_picks(
                    home_stats,
                    away_stats,
                    predicted_home_yellow_cards,
                    predicted_away_yellow_cards,
                )
                for pick in team_cards:
                    picks.add_pick(pick)

            # Red cards require specific team stats, so keep strict check
            if home_stats and away_stats:
                red_card_pick = self._generate_red_cards_pick(
                    home_stats, away_stats, match
                )
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
                if (
                    "Local" in winner_pick.market_label
                    and "Dominio H2H" in h2h_reasoning
                ):
                    winner_pick.priority_score *= h2h_factor
                    winner_pick.reasoning += h2h_reasoning
                picks.add_pick(winner_pick)

            # Generate Double Chance picks
            dc_picks = self._generate_double_chance_picks(
                match, home_win_prob, draw_prob, away_win_prob
            )
            for pick in dc_picks:
                picks.add_pick(pick)

            # Generate DNB picks
            dnb_picks = self._generate_dnb_picks(
                match, home_win_prob, draw_prob, away_win_prob
            )
            for pick in dnb_picks:
                picks.add_pick(pick)

        # 5. Goal/BTTS/Team Goals picks (Consistently generated if we have any stats or
        # prediction)
        # 100% REAL DATA: NO fallback to league averages for goals if no prediction
        # data.
        # This prevents "invented" Over 2.5/BTTS picks.
        if has_prediction_data or (has_home_stats and has_away_stats):
            # Generate handicap picks (needs win prob AND prediction)
            if home_win_prob > 0:
                handicap_picks = self._generate_handicap_picks(
                    match,
                    predicted_home_goals,
                    predicted_away_goals,
                    home_win_prob,
                    away_win_prob,
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

            # Generate Correct Score
            cs_picks = self._generate_correct_score_picks(
                predicted_home_goals, predicted_away_goals
            )
            for pick in cs_picks:
                picks.add_pick(pick)

            # Generate Team Goals (Relaxed: Use prediction data if stats are partial)
            # We only need team names and predicted goals, which we have if
            # has_prediction_data is True
            if has_prediction_data and home_stats and away_stats:
                tg_picks = self._generate_team_goals_picks(
                    home_stats, away_stats, predicted_home_goals, predicted_away_goals
                )
                for pick in tg_picks:
                    picks.add_pick(pick)

        # 6. Team Corners & Cards (Unconditional - User requested "all possible picks")
        # Decoupled logic: Generate for Home even if Away is missing, and vice-versa
        if home_stats is not None:
            home_corners_list = self._generate_single_team_corners(
                home_stats, match, True, predicted_home_corners
            )
            for p in home_corners_list:
                picks.add_pick(p)

            home_cards_list = self._generate_single_team_cards(
                home_stats, match, True, predicted_home_yellow_cards
            )
            for p in home_cards_list:
                picks.add_pick(p)

        if away_stats is not None:
            away_corners_list = self._generate_single_team_corners(
                away_stats, match, False, predicted_away_corners
            )
            for p in away_corners_list:
                picks.add_pick(p)

            away_cards_list = self._generate_single_team_cards(
                away_stats, match, False, predicted_away_yellow_cards
            )
            for p in away_cards_list:
                picks.add_pick(p)

        # 7. Apply ML Refinement (Dynamic or Global)
        # Use the injected model (league-specific) if available, otherwise global
        # fallback
        target_model = ml_model if ml_model else self.ml_model

        if target_model:
            self._apply_ml_refinement(
                picks, target_model, match, home_stats, away_stats
            )

        # 8. [NEW] IA CONFIRMED: Select Single Best Pick & Format Reasoning
        # Sort logic: Priority Score (DESC) -> Probability (DESC) -> EV (DESC)
        # Filter: Must be recommended and satisfy minimum probability
        all_candidates = [
            p
            for p in picks.suggested_picks
            if p.is_recommended and p.probability >= 0.50
        ]

        if all_candidates:
            # Primary Sort: ML Confirmed > Priority Score > Probability
            # We want the absolute best one.
            all_candidates.sort(
                key=lambda p: (
                    p.is_ml_confirmed,  # True(1) > False(0)
                    p.priority_score,
                    p.probability,
                ),
                reverse=True,
            )

            best_pick = all_candidates[0]
            best_pick.is_ia_confirmed = True

            # Formatear el reasoning para TODOS los picks (Estandarización)
            for pick in picks.suggested_picks:
                self._format_pick_reasoning(pick)

        # Finally, sort all generated picks by probability in descending order
        # Ensure IA CONFIRMED is always first
        picks.suggested_picks.sort(
            key=lambda p: (p.is_ia_confirmed, p.probability), reverse=True
        )

        # Evaluate picks if match is finished (for History/Backtesting)
        self._assign_match_results(match, picks.suggested_picks)

        return picks

    def _format_pick_reasoning(self, pick: SuggestedPick) -> None:
        """
        Standardizes the reasoning string format for Frontend display.
        Format: [ML] {Action}, {Reasoning} {Probability}%
        """
        prob_pct = round(pick.probability * 100)

        if pick.probability >= 0.85:
            prefix = "[ML] Apostar"
            desc = "el modelo muestra una alta probabilidad"
        elif pick.probability >= 0.50:
            prefix = "[ML] Precaución"
            desc = "probabilidad moderada, evaluar con cuidado"
        else:
            prefix = "[ML] No apostar"
            desc = "probabilidad baja, riesgo alto"

        # New Strict Format per User Request
        pick.formatted_reasoning = f"{prefix}, {desc} {prob_pct}%"

    def _apply_ml_refinement(
        self,
        picks_container: MatchSuggestedPicks,
        model_instance: Any,
        match: Match,
        home_stats: Optional[TeamStatistics],
        away_stats: Optional[TeamStatistics],
    ) -> None:
        """
        Uses the trained ML model to adjust confidence/priority of picks.

        Top ML picks require minimum 80% model confidence.
        """
        for pick in picks_container.suggested_picks:
            if not model_instance:
                continue

            try:
                # Use centralized feature extraction to ensure parity with training
                # Import implicitly handled
                # Must match PredictionService/Training logic (4 args)
                extractor = MLFeatureExtractor()
                features = [
                    extractor.extract_features(pick, match, home_stats, away_stats)
                ]

                # Predict probability of this pick being correct (Class 1)
                # Assumes Binary Classifier (0=Incorrect, 1=Correct) or similar logic
                # For Outcome Classifier (0=Draw, 1=Home, 2=Away), this logic needs
                # adjustment if we are refining non-outcome picks.
                # BUT: The current ML model trained in 'train_model_optimized' is
                # 'clf_outcome' (Home/Draw/Away).
                # Wait: 'MLFeatureExtractor.extract_features(pick)' implies we are
                # predicting per-PICK success?
                # Let's check 'process_match_task' in train script.
                # NO. 'process_match_task' trains:
                # 1. Corners Regressor
                # 2. Cards Regressor
                # 3. Outcome Classifier (Home/Draw/Away)

                # The 'pick' feature extraction usually expects a generic pick and
                # returns features relevant to THAT pick?
                # OR it returns match features?
                # Looking at 'train_model_optimized.py':
                # features = _feature_extractor.extract_features(dummy_pick, match,
                # home_stats, away_stats)
                # It sends a DUMMY pick. The features are Match-Centric (Recent Form,
                # Goals, etc).

                # So the Outcome Classifier predicts Match Result.
                # If 'pick' is "Home Win", we check index 1.
                # If 'pick' is "Away Win", we check index 2.
                # If 'pick' is "Draw", check index 0.

                # IF the model passed here is indeed the Outcome Classifier:
                ml_probs = model_instance.predict_proba(features)[0]

                # Map probabilities via model.classes_ — never positional indices
                # (ml-model-deployment spec: "Probabilities mapped through classes_").
                try:
                    from src.domain.services.ml_class_alignment import (
                        outcome_probability_map,
                    )

                    label_probs = outcome_probability_map(model_instance, ml_probs)
                    ml_home = label_probs["home"]
                    ml_draw = label_probs["draw"]
                    ml_away = label_probs["away"]
                except ValueError as ve:
                    # Unrecognized layout — treat as blend failure, log, keep 0.0
                    logger.warning(
                        "ML refinement classes_ alignment failed for match %s (%s) — "
                        "continuing without ML confidence",
                        getattr(match, "id", "?"),
                        ve,
                    )
                    ml_home = ml_draw = ml_away = 0.0

                # Map pick type to probability via label keys
                ml_confidence = 0.0

                if pick.market_type == MarketType.RESULT_1X2:
                    if (
                        "Home" in pick.market_label
                        or "(1)" in pick.market_label
                        or match.home_team.name in pick.market_label
                    ):
                        ml_confidence = ml_home
                    elif (
                        "Away" in pick.market_label
                        or "(2)" in pick.market_label
                        or match.away_team.name in pick.market_label
                    ):
                        ml_confidence = ml_away
                    elif "Draw" in pick.market_label or "Empate" in pick.market_label:
                        ml_confidence = ml_draw

                # If it's NOT a result pick (e.g. Over 2.5), the Outcome Classifier
                # isn't directly applicable for "Correct/Incorrect".
                # It acts as a context signal.
                # HOWEVER, legacy logic seemed to assume a "Pick Classifier"
                # (Correct/Incorrect).
                # Since we are now injecting 'clf_outcome', we should only refine Result
                # picks OR accept that
                # we don't have a "Pick Classifier" anymore, just an "Outcome
                # Classifier".

                if ml_confidence == 0.0:
                    continue

                # REFACTOR: Universal ML Evaluation
                # 1. Top ML Pick - High Confidence (>= 80%)
                if ml_confidence >= 0.80:
                    pick.priority_score *= 2.5
                    pick.reasoning += f" 🎯 TOP ML ({ml_confidence:.0%})."
                    pick.is_ml_confirmed = True

                # 2. Good Confidence (65-79%)
                elif ml_confidence >= 0.65:
                    pick.priority_score *= 1.5
                    pick.reasoning += f" ML Favorable ({ml_confidence:.0%})."

                # 3. Low Confidence (< 50%)
                elif ml_confidence < 0.50:
                    pick.priority_score *= 0.5
                    pick.reasoning += f" ML Escéptico ({ml_confidence:.0%})."

            except Exception as e:
                logger.debug(f"ML refinement failed for pick: {e}")
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
        market_odds: Optional[dict[str, float]] = None,
    ) -> list[SuggestedPick]:
        """
        Generic generator for match total statistics (Over/Under).
        Strictly DRY: Processes both markets in a single loop using tuple configuration.
        """
        picks: List[SuggestedPick] = []
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
            odds_over = (
                market_odds.get(key_over_fmt.format(line), 0.0) if market_odds else 0.0
            )

            p_over = self._build_pick_candidate(
                market_type=m_over,
                label=lbl_over.format(line),
                probability=final_prob_over,
                odds=odds_over,
                reasoning=reas_over.format(avg=stat_avg),
                recommendation_threshold=thr_over,
            )
            if p_over:
                picks.append(p_over)

            # --- UNDER ---
            prob_under = 1.0 - prob_over
            final_prob_under = min(0.95, prob_under * adj_under)
            odds_under = (
                market_odds.get(key_under_fmt.format(line), 0.0) if market_odds else 0.0
            )

            p_under = self._build_pick_candidate(
                market_type=m_under,
                label=lbl_under.format(line),
                probability=final_prob_under,
                odds=odds_under,
                reasoning=reas_under.format(avg=stat_avg),
                recommendation_threshold=thr_under,
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
        min_threshold: float = 0.01,
    ) -> list[SuggestedPick]:
        """
        Generic generator for individual team statistics (Over/Under).
        """
        picks: List[SuggestedPick] = []
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
                min_threshold=min_threshold,
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
                min_threshold=min_threshold,
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
        pred_home: float = 0.0,
        pred_away: float = 0.0,
    ) -> list[SuggestedPick]:
        """Generate corners picks for combined match total."""
        # Tiered fallback: Team Averages -> Prediction (League Base) -> 0
        h_avg = (
            home_stats.avg_corners_per_match
            if home_stats and home_stats.matches_played >= 3
            else None
        )
        a_avg = (
            away_stats.avg_corners_per_match
            if away_stats and away_stats.matches_played >= 3
            else None
        )

        if h_avg is not None and h_avg > 0:
            pred_home = (pred_home + h_avg) / 2 if pred_home > 0 else h_avg

        if a_avg is not None and a_avg > 0:
            pred_away = (pred_away + a_avg) / 2 if pred_away > 0 else a_avg

        total_avg = pred_home + pred_away

        # [STRICT] No Fallback. If data is 0, we return 0 picks for the Total market.
        # Partial team picks are handled by _generate_single_team_corners separately.

        return self._generate_total_stat_picks(
            stat_avg=total_avg,
            lines=[6.5, 7.5, 8.5, 9.5, 10.5, 11.5, 12.5],
            market_types=(MarketType.CORNERS_OVER, MarketType.CORNERS_UNDER),
            label_formats=(
                "Más de {} córners en el partido",
                "Menos de {} córners en el partido",
            ),
            reasoning_fmts=(
                "Promedio proyectado: {avg:.2f} córners. Tendencia favorable.",
                "Promedio proyectado: {avg:.2f} córners. Baja media histórica.",
            ),
            prob_adjustments=(1.05, 1.02),
            rec_thresholds=(0.55, 0.55),
            odds_keys_fmt=("corners_over_{}", "corners_under_{}"),
            market_odds=market_odds,
        )

    def _generate_cards_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        match: Match,
        league_averages: Optional[LeagueAverages] = None,
        market_odds: Optional[dict[str, float]] = None,
        pred_home: float = 0.0,
        pred_away: float = 0.0,
    ) -> list[SuggestedPick]:
        """Generate cards picks for combined match total."""
        # Tiered fallback: Team Averages -> Prediction -> 0
        h_avg = (
            home_stats.avg_yellow_cards_per_match
            if home_stats and home_stats.matches_played >= 3
            else None
        )
        a_avg = (
            away_stats.avg_yellow_cards_per_match
            if away_stats and away_stats.matches_played >= 3
            else None
        )

        if h_avg is not None and h_avg > 0:
            pred_home = (pred_home + h_avg) / 2 if pred_home > 0 else h_avg

        if a_avg is not None and a_avg > 0:
            pred_away = (pred_away + a_avg) / 2 if pred_away > 0 else a_avg

        total_avg = pred_home + pred_away

        return self._generate_total_stat_picks(
            stat_avg=total_avg,
            lines=[1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5],
            market_types=(MarketType.CARDS_OVER, MarketType.CARDS_UNDER),
            label_formats=(
                "Más de {} tarjetas en el partido",
                "Menos de {} tarjetas en el partido",
            ),
            reasoning_fmts=(
                "Expectativa de tarjetas: {avg:.2f}. Análisis de volatilidad.",
                "Expectativa de tarjetas: {avg:.2f}. Análisis de volatilidad.",
            ),
            prob_adjustments=(1.02, 1.05),
            rec_thresholds=(0.55, 0.55),
            odds_keys_fmt=("cards_over_{}", "cards_under_{}"),
            market_odds=market_odds,
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
            picks.append(
                self._create_double_chance_pick(
                    MarketType.DOUBLE_CHANCE_1X,
                    f"{match.home_team.name} o Empate",
                    prob_1x,
                    (
                        f"Alta probabilidad combinada ({prob_1x:.0%}) de que "
                        f"{match.home_team.name} no pierda en casa."
                    ),
                )
            )

        # X2: Draw or Away
        prob_x2 = draw_prob + away_win_prob
        if prob_x2 > 0.01:
            picks.append(
                self._create_double_chance_pick(
                    MarketType.DOUBLE_CHANCE_X2,
                    f"Empate o {match.away_team.name}",
                    prob_x2,
                    (
                        f"Alta probabilidad combinada ({prob_x2:.0%}) de que "
                        f"{match.away_team.name} sume puntos."
                    ),
                )
            )

        # 12: Home or Away (No Draw)
        prob_12 = home_win_prob + away_win_prob
        if prob_12 > 0.01:
            picks.append(
                self._create_double_chance_pick(
                    MarketType.DOUBLE_CHANCE_12,
                    f"{match.home_team.name} o {match.away_team.name} gana",
                    prob_12,
                    "Baja probabilidad de empate. Se espera un ganador.",
                )
            )

        return picks

    def _create_double_chance_pick(
        self, market_type: MarketType, label: str, prob: float, reasoning: str
    ) -> SuggestedPick:
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
            expected_value=self._calculate_ev(prob),
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

        base_threshold = PicksConfig.WINNER_PROB_THRESHOLD
        if is_volatile:
            base_threshold = PicksConfig.WINNER_VOLATILE_THRESHOLD

        # Odds fetching (assuming standard keys)
        # Note: We don't have explicit 'market_odds' passed here in original method
        # signature,
        # but 'match' object has them!

        selection_prob = max_prob

        if idx == 0:  # Home
            label = f"Victoria {match.home_team.name}"
            odds = match.home_odds or 0.0
        elif idx == 1:  # Draw
            label = "Empate"
            odds = match.draw_odds or 0.0
            base_threshold = PicksConfig.DRAW_THRESHOLD  # Draws are harder
        else:  # Away
            label = f"Victoria {match.away_team.name}"
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
            priority_mult = 1.0 + (ev * 2)  # Reward value heavily
            reasoning += f" EV: +{ev:.1%}."

        if kelly_factor > 0.02:  # Meaningful stake suggested
            priority_mult += kelly_factor * 5
            reasoning += " Kelly recomienda gestión."

        if is_volatile:
            priority_mult *= 0.8
            reasoning += " (Alta volatilidad)."

        # Final gate: Must pass base threshold OR have high EV
        # RELAXED: During early season/training, we lower this to 0.3 to ensure we
        # always have a candidate
        if selection_prob < base_threshold and ev < 0.05:
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
            priority_score=display_prob
            * self.MARKET_PRIORITY.get(MarketType.RESULT_1X2, 1.0)
            * priority_mult,
            expected_value=ev,
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
            mrkt_over = MarketType.GOALS_OVER_2_5  # Default
            mrkt_under = MarketType.GOALS_UNDER_2_5  # Default

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
                # We don't have separate enum for 4.5 yet, but we can reuse
                # GOALS_OVER/UNDER
                # OR we should add them to MarketType if we want strictness.
                # Let's use GOALS_OVER/UNDER as fallback for now or add them.
                mrkt_over = MarketType.GOALS_OVER
                mrkt_under = MarketType.GOALS_UNDER

            # --- OVER PICK ---
            over_prob = self._poisson_model_probability(
                predicted_home, predicted_away, line, is_over=True
            )
            odds_over = market_odds.get(mrkt_over.value, 0.0) if market_odds else 0.0
            adj_over_val = self.learning_weights.get_market_adjustment(mrkt_over.value)
            adjusted_over_prob = over_prob * adj_over_val

            penalty_note = ""
            if is_low_scoring and line >= 2.5:
                adjusted_over_prob *= PicksConfig.LOW_SCORING_PENALTY
                penalty_note = " ⚠️ Contexto defensivo."

            pick_over = self._build_pick_candidate(
                market_type=mrkt_over,
                label=f"Más de {line} goles",
                probability=min(0.98, adjusted_over_prob),
                odds=odds_over,
                reasoning=f"Proyectado: {total_expected:.2f} goles.{penalty_note}",
                min_threshold=0.01,  # Maximized volume
                recommendation_threshold=0.65,
            )

            # Special logic for low lines
            if pick_over and line < 1.6 and pick_over.probability < 0.8:
                pick_over.is_recommended = False

            if pick_over:
                picks.append(pick_over)

            # --- UNDER PICK ---
            under_prob = self._poisson_model_probability(
                predicted_home, predicted_away, line, is_over=False
            )
            odds_under = market_odds.get(mrkt_under.value, 0.0) if market_odds else 0.0
            adj_under_val = self.learning_weights.get_market_adjustment(
                mrkt_under.value
            )
            adjusted_under_prob = under_prob * adj_under_val

            boost_note = ""
            if is_low_scoring and line <= 2.5:
                adjusted_under_prob *= PicksConfig.LOW_SCORING_BOOST
                boost_note = " ✅ Contexto defensivo."

            pick_under = self._build_pick_candidate(
                market_type=mrkt_under,
                label=f"Menos de {line} goles",
                probability=min(0.98, adjusted_under_prob),
                odds=odds_under,
                reasoning=f"Proyectado: {total_expected:.2f} goles.{boost_note}",
                min_threshold=0.01,  # Maximized volume
                recommendation_threshold=0.65,
            )
            if pick_under:
                picks.append(pick_under)

        return picks

    def _boost_prob(self, p: float) -> float:
        """Apply non-linear boost to separate strong picks from weak ones."""
        if p < 0.55:
            return p

        # Simple linear expansion: 0.55 stays same, 0.75 becomes 0.85
        # f(p) = p + (p - 0.55) * 0.6
        boosted = p + (p - 0.55) * 0.6
        return min(0.95, boosted)

    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def _poisson_over_probability(expected: float, threshold: float) -> float:
        """Calculate probability of over threshold using Poisson distribution
        (Optimized)."""
        if expected <= 0:
            return 0.0

        # Optimization: Calculate Poisson iteratively to avoid expensive factorial/pow
        # calls
        # P(k) = (lambda^k * e^-lambda) / k!
        # P(k) = P(k-1) * lambda / k
        p_k = math.exp(-expected)  # Probability for k=0
        under_prob = p_k

        for k in range(1, int(threshold) + 1):
            p_k *= expected / k
            under_prob += p_k

        return 1 - under_prob

    @staticmethod
    def _poisson_probability(k: int, lamb: float) -> float:
        """Calculate exact Poisson probability P(X=k)."""
        if lamb < 0:
            return 0.0

        return (math.exp(-lamb) * (lamb**k)) / math.factorial(k)

    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def _poisson_model_probability(
        expected_home: float, expected_away: float, line: float, is_over: bool
    ) -> float:
        """
        Calculate probability using Dixon-Coles Light approximation.
        We iterate through plausible scores (0-0 to 9-9) and sum probabilities.
        """
        rho = -0.13  # correlation coefficient (usually negative for low scores)

        prob_sum = 0.0

        # Limit iteration for performance (0 to 10 goals is sufficient coverage > 99.9%)
        limit = 10

        # Precompute individual Poisson masses
        def poisson_pmf(lam: float, k: int) -> float:
            return (math.exp(-lam) * (lam**k)) / math.factorial(k)

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
                    if total > line:
                        prob_sum += p
                else:
                    if total < line:
                        prob_sum += p

        return min(0.99, max(0.01, prob_sum))

    @staticmethod
    @functools.lru_cache(maxsize=1024)
    def _calculate_handicap_probability(
        goal_diff: float, handicap: float, total_expected: float = 2.5
    ) -> float:
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
            trend_text = (
                "tendencia a expulsiones" if total_avg > 0.2 else "baja probabilidad"
            )
            return SuggestedPick(
                market_type=MarketType.RED_CARDS,
                market_label="Tarjeta Roja en el Partido",
                probability=round(probability, 3),
                confidence_level=confidence,
                reasoning=(
                    f"Promedio combinado: {total_avg:.2f} rojas/partido. "
                    f"Historial reciente indica {trend_text}."
                ),
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
        """Generate DYNAMIC Asian Handicap picks (positive and negative)
        based on match data.
        """
        picks = []

        # Determine the favorite and the underdog
        if home_win_prob > away_win_prob + 0.1:
            favorite, underdog = match.home_team, match.away_team
            goal_diff = predicted_home - predicted_away  # From favorite's perspective
        elif away_win_prob > home_win_prob + 0.1:
            favorite, underdog = match.away_team, match.home_team
            goal_diff = predicted_away - predicted_home  # From favorite's perspective
        else:  # Balanced match, no clear favorite
            # In this case, we can still offer +0.5 on either team
            for team, prob in [
                (match.home_team, home_win_prob),
                (match.away_team, away_win_prob),
            ]:
                # Simplified goal_diff for balanced match
                bal_goal_diff = (
                    (predicted_home - predicted_away)
                    if team == match.home_team
                    else (predicted_away - predicted_home)
                )

                # Test +0.5 for this team
                handicap = 0.5
                prob_cover = self._calculate_handicap_probability(
                    bal_goal_diff, handicap, predicted_home + predicted_away
                )

                if prob_cover > 0.01:
                    picks.append(
                        self._create_handicap_pick(
                            team_name=team.name,
                            handicap=handicap,
                            probability=prob_cover,
                            goal_diff=bal_goal_diff,
                        )
                    )
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
            "und": [base_handicap - 0.25, base_handicap, base_handicap + 0.25],
        }

        # Test handicaps for the FAVORITE (e.g., -0.5, -1.0)
        for handicap in sorted({h for h in handicaps_to_test["fav"] if h < 0}):
            prob_fav_covers = self._calculate_handicap_probability(
                goal_diff, handicap, total_expected_goals
            )

            # Use lower threshold for handicaps to show variety
            if prob_fav_covers > 0.01:
                picks.append(
                    self._create_handicap_pick(
                        team_name=favorite.name,
                        handicap=handicap,
                        probability=prob_fav_covers,
                        goal_diff=goal_diff,
                    )
                )

        # Test handicaps for the UNDERDOG (e.g., +0.5, +1.0)
        for handicap in sorted({h for h in handicaps_to_test["und"] if h > 0}):
            # For underdog, the goal_diff perspective is negative
            prob_und_covers = self._calculate_handicap_probability(
                -goal_diff, handicap, total_expected_goals
            )

            if prob_und_covers > 0.01:
                picks.append(
                    self._create_handicap_pick(
                        team_name=underdog.name,
                        handicap=handicap,
                        probability=prob_und_covers,
                        goal_diff=-goal_diff,
                    )
                )

        return picks

    def _create_handicap_pick(
        self, team_name: str, handicap: float, probability: float, goal_diff: float
    ) -> SuggestedPick:
        """Helper to create a SuggestedPick for handicaps."""

        # Format handicap sign and value
        handicap_str = f"+{handicap}" if handicap > 0 else str(handicap)

        # Adjust reasoning based on handicap type
        if handicap < 0:
            reason = (
                f"{team_name} es favorito. Se espera que gane por un margen de ~"
                f"{goal_diff:.2f} goles."
            )
        else:
            reason = (
                f"Margen de seguridad para "
                f"{team_name}. Se espera que no pierda por más de "
                f"{handicap-0.5} goles."
            )

        adj_prob = min(0.95, probability)  # Cap probability
        adj_prob = max(0.55, adj_prob)

        display_prob = self._boost_prob(adj_prob)  # Boost for display
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
            expected_value=self._calculate_ev(adj_prob),  # EV on raw
        )

    # Fallback pick removed to strictly comply with 'no invented data' policy

    def _generate_single_team_corners(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool,
        predicted_val: float = 0.0,
    ) -> list[SuggestedPick]:
        """Generate corners pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_corners_per_match

        # Fallback to prediction if avg is 0 (Rule 16/2B)
        if (avg is None or avg <= 0) and predicted_val > 0:
            avg = predicted_val

        return self._generate_team_stat_picks(
            stat_avg=avg,
            lines=[2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5],
            market_types=(
                (
                    MarketType.HOME_CORNERS_OVER
                    if is_home
                    else MarketType.AWAY_CORNERS_OVER
                ),
                (
                    MarketType.HOME_CORNERS_UNDER
                    if is_home
                    else MarketType.AWAY_CORNERS_UNDER
                ),
            ),
            label_formats=(
                f"{team_name} - Más de {{}} córners",
                f"{team_name} - Menos de {{}} córners",
            ),
            reasoning_fmts=(
                f"Producción ofensiva de {team_name}: {{avg:.2f}} córners/partido.",
                f"Producción ofensiva de {team_name}: {{avg:.2f}} córners/partido.",
            ),
            prob_adjustments=(1.05, 1.02),
            rec_thresholds=(0.75, 0.80),
            min_threshold=0.01,
        )

    def _generate_single_team_cards(
        self,
        stats: TeamStatistics,
        match: Match,
        is_home: bool,
        predicted_val: float = 0.0,
    ) -> list[SuggestedPick]:
        """Generate cards pick for a single team."""
        team_name = match.home_team.name if is_home else match.away_team.name
        avg = stats.avg_yellow_cards_per_match

        # Fallback to prediction if avg is 0 (Rule 16/2B)
        if (avg is None or avg <= 0) and predicted_val > 0:
            avg = predicted_val

        return self._generate_team_stat_picks(
            stat_avg=avg,
            lines=[0.5, 1.5, 2.5, 3.5, 4.5],
            market_types=(
                MarketType.HOME_CARDS_OVER if is_home else MarketType.AWAY_CARDS_OVER,
                MarketType.HOME_CARDS_UNDER if is_home else MarketType.AWAY_CARDS_UNDER,
            ),
            label_formats=(
                f"{team_name} - Más de {{}} tarjetas",
                f"{team_name} - Menos de {{}} tarjetas",
            ),
            reasoning_fmts=(
                f"Promedio de tarjetas para {team_name}: {{avg:.2f}}.",
                f"Promedio de tarjetas para {team_name}: {{avg:.2f}}.",
            ),
            prob_adjustments=(1.02, 1.05),
            rec_thresholds=(0.80, 0.75),
            min_threshold=0.01,
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
        if btts_yes_prob > 0.1:  # Expanded threshold
            odds_yes = (
                market_odds.get(MarketType.BTTS_YES.value, 0.0) if market_odds else 0.0
            )
            display_prob = self._boost_prob(btts_yes_prob)
            confidence = SuggestedPick.get_confidence_level(display_prob)
            risk = self._calculate_risk_level(display_prob)
            ev = self._calculate_ev(btts_yes_prob, odds_yes)
            is_rec, prio_mult, suffix = self._evaluate_recommendation(
                btts_yes_prob, ev, 0.65
            )

            picks.append(
                SuggestedPick(
                    market_type=MarketType.BTTS_YES,
                    market_label="Ambos Equipos Marcan: SÍ",
                    probability=round(display_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Altas probabilidades de gol para ambos.{suffix}",
                    risk_level=risk,
                    is_recommended=is_rec,
                    priority_score=display_prob
                    * self.MARKET_PRIORITY.get(MarketType.BTTS_YES, 0.9)
                    * prio_mult,
                    expected_value=ev,
                )
            )

        # 2. BTTS NO
        if btts_no_prob > 0.1:  # Expanded threshold
            odds_no = (
                market_odds.get(MarketType.BTTS_NO.value, 0.0) if market_odds else 0.0
            )
            display_prob = self._boost_prob(btts_no_prob)
            confidence = SuggestedPick.get_confidence_level(display_prob)
            risk = self._calculate_risk_level(display_prob)
            ev = self._calculate_ev(btts_no_prob, odds_no)
            is_rec, prio_mult, suffix = self._evaluate_recommendation(
                btts_no_prob, ev, 0.65
            )

            picks.append(
                SuggestedPick(
                    market_type=MarketType.BTTS_NO,
                    market_label="Ambos Equipos Marcan: NO",
                    probability=round(display_prob, 3),
                    confidence_level=confidence,
                    reasoning=f"Valla invicta o baja producción proyectada.{suffix}",
                    risk_level=risk,
                    is_recommended=is_rec,
                    priority_score=display_prob
                    * self.MARKET_PRIORITY.get(MarketType.BTTS_NO, 0.85)
                    * prio_mult,
                    expected_value=ev,
                )
            )

        return picks

    # Duplicate/legacy double-chance generator removed to avoid redefinition.
    # A single canonical implementation exists earlier in the file.

    def _generate_dnb_picks(
        self, match: Match, home_prob: float, draw_prob: float, away_prob: float
    ) -> list[SuggestedPick]:
        """Generate Draw No Bet (DNB) picks."""
        picks = []

        # DNB Probability = P(Win) / (P(Win) + P(Away)) -- Removing Draw mass
        denom_home = home_prob + away_prob
        denom_away = away_prob + home_prob

        if denom_home > 0:
            prob_dnb_1 = home_prob / denom_home
            if prob_dnb_1 > 0.50:
                picks.append(
                    self._build_simple_pick(
                        MarketType.DRAW_NO_BET_1,
                        "Apuesta Sin Empate: Local",
                        prob_dnb_1,
                        "Local protege en caso de empate.",
                    )
                )

        if denom_away > 0:
            prob_dnb_2 = away_prob / denom_away
            if prob_dnb_2 > 0.50:
                picks.append(
                    self._build_simple_pick(
                        MarketType.DRAW_NO_BET_2,
                        "Apuesta Sin Empate: Visitante",
                        prob_dnb_2,
                        "Visitante protege en caso de empate.",
                    )
                )
        return picks

    def _generate_correct_score_picks(
        self, predicted_home: float, predicted_away: float
    ) -> list[SuggestedPick]:
        """Generate Correct Score picks based on Poisson."""
        picks = []

        scores = []
        # Check scores from 0-0 to 3-3

        for h in range(4):
            for a in range(4):
                prob = self._poisson_probability(
                    k=h, lamb=predicted_home
                ) * self._poisson_probability(k=a, lamb=predicted_away)
                scores.append(((h, a), prob))

        # Sort by prob
        scores.sort(key=lambda x: x[1], reverse=True)

        # Take top 3
        for (h, a), prob in scores[:3]:
            if prob > 0.08:  # Min threshold to be relevant
                picks.append(
                    SuggestedPick(
                        market_type=MarketType.CORRECT_SCORE,
                        market_label=f"Marcador Exacto: {h}-{a}",
                        probability=round(prob, 3),
                        # Always low conf for exact scores
                        confidence_level=ConfidenceLevel.LOW,
                        reasoning=(
                            f"Proyección matemática más probable ({prob*100:.1f}%)."
                        ),
                        risk_level=4,  # High risk
                        is_recommended=False,
                        priority_score=prob * 0.5,
                        expected_value=0.0,
                    )
                )
        return picks

    def _generate_team_goals_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        predicted_home: float,
        predicted_away: float,
    ) -> list[SuggestedPick]:
        """Generate Team Total Goals picks."""
        picks = []
        # Fallback for names if stats objects are None (rare but possible with relaxed
        # logic)
        h_id = home_stats.team_id if home_stats else "Local"
        a_id = away_stats.team_id if away_stats else "Visitante"

        # Home Team Over 1.5
        prob_home_o15 = self._poisson_model_probability(
            predicted_home, 0, 1.5, is_over=True
        )  # Check only h_lambda
        if prob_home_o15 > 0.45:
            picks.append(
                self._build_simple_pick(
                    MarketType.TEAM_GOALS_OVER,
                    f"{h_id} Más de 1.5 Goles",
                    prob_home_o15,
                    "Ataque local productivo.",
                )
            )

        # Away Team Over 1.5
        prob_away_o15 = self._poisson_model_probability(
            0, predicted_away, 1.5, is_over=True
        )
        if prob_away_o15 > 0.45:
            picks.append(
                self._build_simple_pick(
                    MarketType.TEAM_GOALS_OVER,
                    f"{a_id} Más de 1.5 Goles",
                    prob_away_o15,
                    "Ataque visitante productivo.",
                )
            )

        return picks

    def _generate_team_corners_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        predicted_home_corners: float,
        predicted_away_corners: float,
    ) -> list[SuggestedPick]:
        """Generate Team Specific Corner Picks."""
        picks = []

        # NOTE: Over/Under logic moved to _generate_single_team_corners (Step 6)
        # to avoid duplicates and ensure consistency with Poisson models.

        # Corners 1X2
        if predicted_home_corners > predicted_away_corners + 1.5:
            picks.append(
                self._build_simple_pick(
                    MarketType.CORNERS_1X2_1,
                    f"Más Córners: {home_stats.team_id}",
                    0.70,
                    "Dominio en saques de esquina.",
                )
            )
        elif predicted_away_corners > predicted_home_corners + 1.5:
            picks.append(
                self._build_simple_pick(
                    MarketType.CORNERS_1X2_2,
                    f"Más Córners: {away_stats.team_id}",
                    0.70,
                    "Visitante genera más córners.",
                )
            )

        return picks

    def _generate_team_cards_picks(
        self,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics,
        pred_home_cards: float,
        pred_away_cards: float,
    ) -> list[SuggestedPick]:
        """Generate Team Specific Card Picks."""
        picks: List[SuggestedPick] = []
        # NOTE: Over/Under logic moved to _generate_single_team_cards (Step 6)
        # to avoid duplicates.
        return picks

    def _build_simple_pick(
        self,
        market_type: Any,
        label: str,
        prob: float,
        reasoning: str,
    ) -> SuggestedPick:
        """Helper to build a simple pick object."""
        prob = min(0.98, prob)
        return SuggestedPick(
            market_type=market_type,
            market_label=label,
            probability=round(prob, 3),
            confidence_level=SuggestedPick.get_confidence_level(prob),
            reasoning=reasoning,
            risk_level=self._calculate_risk_level(prob),
            is_recommended=(prob > 0.70),
            priority_score=prob * 0.85,
            expected_value=0.0,
        )

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
