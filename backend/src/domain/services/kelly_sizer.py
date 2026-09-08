"""
Kelly Criterion Position Sizing Module

Implements Kelly Criterion and fractional Kelly for optimal bet sizing:
- Full Kelly: f* = (bp - q) / b = (p * odds - 1) / (odds - 1)
- Fractional Kelly: f = fraction * f* (typically 0.25 for quarter Kelly)
- Handles multiple outcomes (home/draw/away for football)
- Confidence-adjusted Kelly with minimum edge requirements
- Bankroll management with max stake caps
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class KellyVariant(str, Enum):
    """Kelly criterion variants."""

    FULL = "full"
    HALF = "half"
    QUARTER = "quarter"
    CUSTOM = "custom"


@dataclass(frozen=True)
class KellyResult:
    """Result of Kelly calculation for a single outcome."""

    outcome: str
    kelly_fraction: float  # Optimal fraction of bankroll (0-1)
    fractional_kelly: float  # After applying fraction (e.g., 0.25)
    recommended_stake: float  # Absolute stake units
    expected_value: float  # EV of the bet
    edge: float  # Model probability - implied probability
    confidence_adjusted: float  # Kelly adjusted for confidence
    meets_min_edge: bool  # Whether edge exceeds minimum threshold


@dataclass(frozen=True)
class MultiOutcomeKellyResult:
    """Kelly results for multiple outcomes (e.g., 1X2)."""

    outcomes: dict[str, KellyResult]
    total_kelly: float  # Sum of all kelly fractions
    total_stake: float  # Total recommended stake
    bankroll_allocation: dict[str, float]  # Outcome -> stake
    max_single_stake_pct: float  # Maximum single bet as % of bankroll
    is_balanced: bool  # Whether stakes are balanced (no arbitrage)


@dataclass(frozen=True)
class StakeRecommendation:
    """Final stake recommendation with risk management."""

    outcome: str
    stake_units: float  # Absolute stake in units
    stake_pct_bankroll: float  # As percentage of bankroll
    kelly_fraction: float  # Raw Kelly fraction
    fractional_kelly: float  # Applied fractional Kelly
    confidence: float  # Model confidence (0-1)
    risk_level: int  # 1-5 risk rating
    reasoning: str


class KellySizer:
    """
    Kelly Criterion position sizing for sports betting.

    Features:
    - Full, Half, Quarter Kelly support
    - Custom fractional Kelly
    - Multi-outcome handling (1X2, Over/Under, etc.)
    - Confidence-adjusted sizing
    - Minimum edge requirements
    - Maximum stake caps
    - Bankroll-aware recommendations
    """

    DEFAULT_KELLY_FRACTION = 0.25  # Quarter Kelly (recommended)
    DEFAULT_MAX_STAKE_PCT = 0.05  # 5% max single bet
    DEFAULT_MIN_EDGE = 0.02  # 2% minimum edge

    def __init__(
        self,
        kelly_fraction: float = DEFAULT_KELLY_FRACTION,
        max_stake_pct: float = DEFAULT_MAX_STAKE_PCT,
        min_edge: float = DEFAULT_MIN_EDGE,
    ):
        """
        Initialize Kelly sizer.

        Args:
            kelly_fraction: Fraction of full Kelly to use (0.25 = quarter Kelly)
            max_stake_pct: Maximum single bet as fraction of bankroll
            min_edge: Minimum edge required to place bet
        """
        if not 0 < kelly_fraction <= 1:
            raise ValueError("kelly_fraction must be between 0 and 1")
        if not 0 < max_stake_pct <= 1:
            raise ValueError("max_stake_pct must be between 0 and 1")
        if not 0 <= min_edge < 1:
            raise ValueError("min_edge must be between 0 and 1")

        self.kelly_fraction = kelly_fraction
        self.max_stake_pct = max_stake_pct
        self.min_edge = min_edge

    def calculate_kelly_fraction(
        self,
        model_prob: float,
        odds: float,
        kelly_fraction: Optional[float] = None,
    ) -> float:
        """
        Calculate Kelly fraction for a single bet.

        Kelly formula: f* = (bp - q) / b
        where:
        - b = odds - 1 (net odds)
        - p = model probability of winning
        - q = 1 - p = probability of losing

        Simplified: f* = (p * odds - 1) / (odds - 1)

        Args:
            model_prob: Model's estimated win probability (0-1)
            odds: Decimal odds
            kelly_fraction: Override default fractional Kelly (e.g., 0.25)

        Returns:
            Optimal fraction of bankroll to bet (can be negative = no bet)
        """
        if odds <= 1.0:
            return 0.0
        if not 0 < model_prob < 1:
            return 0.0

        # Full Kelly
        edge = model_prob * odds - 1
        if edge <= 0:
            return 0.0  # No edge, no bet

        full_kelly = edge / (odds - 1)

        # Apply fractional Kelly
        fraction = kelly_fraction if kelly_fraction is not None else self.kelly_fraction
        fractional_kelly = full_kelly * fraction

        # Cap at reasonable maximum (safety)
        return max(0.0, min(fractional_kelly, 0.5))

    def calculate_optimal_stake(
        self,
        bankroll: float,
        model_prob: float,
        odds: float,
        max_stake_pct: Optional[float] = None,
    ) -> float:
        """
        Calculate optimal absolute stake in bankroll units.

        Args:
            bankroll: Total bankroll
            model_prob: Model win probability
            odds: Decimal odds
            max_stake_pct: Override max stake percentage

        Returns:
            Recommended stake in absolute units
        """
        kelly_frac = self.calculate_kelly_fraction(model_prob, odds)
        max_pct = max_stake_pct if max_stake_pct is not None else self.max_stake_pct

        # Cap at max stake percentage
        stake_frac = min(kelly_frac, max_pct)

        return bankroll * stake_frac

    def kelly_with_confidence(
        self,
        model_prob: float,
        odds: float,
        confidence: float,
        min_edge: Optional[float] = None,
        kelly_fraction: Optional[float] = None,
    ) -> KellyResult:
        """
        Calculate Kelly with confidence adjustment.

        Confidence reduces the effective edge:
        - High confidence (0.9): minimal reduction
        - Low confidence (0.5): significant reduction

        Args:
            model_prob: Model probability
            odds: Decimal odds
            confidence: Model confidence (0-1)
            min_edge: Minimum edge threshold
            kelly_fraction: Fractional Kelly override

        Returns:
            KellyResult with all details
        """
        min_e = min_edge if min_edge is not None else self.min_edge
        fraction = kelly_fraction if kelly_fraction is not None else self.kelly_fraction

        # Calculate implied probability
        implied_prob = 1 / odds
        edge = model_prob - implied_prob

        # Check minimum edge
        meets_min_edge = edge >= min_e

        if not meets_min_edge or edge <= 0:
            return KellyResult(
                outcome="",
                kelly_fraction=0.0,
                fractional_kelly=0.0,
                recommended_stake=0.0,
                expected_value=edge,
                edge=edge,
                confidence_adjusted=0.0,
                meets_min_edge=False,
            )

        # Confidence adjustment: reduce effective probability
        # High confidence -> model_prob closer to true
        # Low confidence -> shrink toward implied probability
        adjusted_prob = implied_prob + (model_prob - implied_prob) * confidence
        adjusted_edge = adjusted_prob * odds - 1

        if adjusted_edge <= 0:
            return KellyResult(
                outcome="",
                kelly_fraction=0.0,
                fractional_kelly=0.0,
                recommended_stake=0.0,
                expected_value=edge,
                edge=edge,
                confidence_adjusted=0.0,
                meets_min_edge=False,
            )

        # Calculate Kelly with adjusted probability
        full_kelly = adjusted_edge / (odds - 1)
        fractional_kelly = full_kelly * fraction

        return KellyResult(
            outcome="",
            kelly_fraction=full_kelly,
            fractional_kelly=max(0.0, min(fractional_kelly, 0.5)),
            recommended_stake=0.0,  # Set by caller with bankroll
            expected_value=edge,
            edge=edge,
            confidence_adjusted=fractional_kelly,
            meets_min_edge=True,
        )

    def calculate_multi_outcome_kelly(
        self,
        model_probs: dict[str, float],
        odds: dict[str, float],
        bankroll: float,
        kelly_fraction: Optional[float] = None,
        max_stake_pct: Optional[float] = None,
        min_edge: Optional[float] = None,
    ) -> MultiOutcomeKellyResult:
        """
        Calculate Kelly for multiple mutually exclusive outcomes.

        For markets like 1X2 (home/draw/away) where only one wins.
        Kelly for simultaneous mutually exclusive bets requires
        solving a system - we use the simplified independent approximation
        with a correlation adjustment.

        Args:
            model_probs: Dict of outcome -> model probability
            odds: Dict of outcome -> decimal odds
            bankroll: Total bankroll
            kelly_fraction: Fractional Kelly override
            max_stake_pct: Max stake per bet override
            min_edge: Minimum edge override

        Returns:
            MultiOutcomeKellyResult with all outcomes
        """
        fraction = kelly_fraction if kelly_fraction is not None else self.kelly_fraction
        max_pct = max_stake_pct if max_stake_pct is not None else self.max_stake_pct
        min_e = min_edge if min_edge is not None else self.min_edge

        outcomes = {}
        total_kelly = 0.0
        total_stake = 0.0
        allocation = {}

        for outcome, prob in model_probs.items():
            outcome_odds = odds.get(outcome, 0)
            if outcome_odds <= 1.0:
                continue

            implied = 1 / outcome_odds
            edge = prob - implied

            if edge < min_e:
                outcomes[outcome] = KellyResult(
                    outcome=outcome,
                    kelly_fraction=0.0,
                    fractional_kelly=0.0,
                    recommended_stake=0.0,
                    expected_value=edge,
                    edge=edge,
                    confidence_adjusted=0.0,
                    meets_min_edge=False,
                )
                continue

            # Full Kelly for this outcome
            full_kelly = edge / (outcome_odds - 1)
            frac_kelly = max(0.0, min(full_kelly * fraction, max_pct))

            stake = bankroll * frac_kelly

            outcomes[outcome] = KellyResult(
                outcome=outcome,
                kelly_fraction=full_kelly,
                fractional_kelly=frac_kelly,
                recommended_stake=stake,
                expected_value=edge,
                edge=edge,
                confidence_adjusted=frac_kelly,
                meets_min_edge=True,
            )

            total_kelly += full_kelly
            total_stake += stake
            allocation[outcome] = stake

        # Check if total allocation exceeds max daily exposure
        max_daily = 0.10  # 10% max daily (configurable)
        if total_stake > bankroll * max_daily:
            # Scale down proportionally
            scale = (bankroll * max_daily) / total_stake
            for outcome in outcomes:
                if outcomes[outcome].meets_min_edge:
                    new_stake = outcomes[outcome].recommended_stake * scale
                    new_frac = outcomes[outcome].fractional_kelly * scale
                    outcomes[outcome] = KellyResult(
                        outcome=outcome,
                        kelly_fraction=outcomes[outcome].kelly_fraction,
                        fractional_kelly=new_frac,
                        recommended_stake=new_stake,
                        expected_value=outcomes[outcome].expected_value,
                        edge=outcomes[outcome].edge,
                        confidence_adjusted=new_frac,
                        meets_min_edge=True,
                    )
            total_stake = bankroll * max_daily
            allocation = {
                k: v.recommended_stake
                for k, v in outcomes.items()
                if v.meets_min_edge
            }

        return MultiOutcomeKellyResult(
            outcomes=outcomes,
            total_kelly=total_kelly,
            total_stake=total_stake,
            bankroll_allocation=allocation,
            max_single_stake_pct=max_pct,
            is_balanced=len([o for o in outcomes.values() if o.meets_min_edge]) > 1,
        )

    def calculate_football_1x2_kelly(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        bankroll: float,
        confidence: float = 1.0,
    ) -> MultiOutcomeKellyResult:
        """
        Convenience method for football 1X2 market.

        Args:
            home_prob, draw_prob, away_prob: Model probabilities
            home_odds, draw_odds, away_odds: Decimal odds
            bankroll: Total bankroll
            confidence: Model confidence (applied to all outcomes)

        Returns:
            MultiOutcomeKellyResult for 1X2 market
        """
        model_probs = {
            "home": home_prob,
            "draw": draw_prob,
            "away": away_prob,
        }
        odds_dict = {
            "home": home_odds,
            "draw": draw_odds,
            "away": away_odds,
        }

        # Adjust probabilities by confidence
        adjusted_probs = {}
        for outcome, prob in model_probs.items():
            implied = 1 / odds_dict[outcome]
            adjusted_probs[outcome] = implied + (prob - implied) * confidence

        # Renormalize
        total = sum(adjusted_probs.values())
        if total > 0:
            adjusted_probs = {k: v / total for k, v in adjusted_probs.items()}

        return self.calculate_multi_outcome_kelly(
            model_probs=adjusted_probs,
            odds=odds_dict,
            bankroll=bankroll,
        )

    def calculate_tennis_kelly(
        self,
        p1_prob: float,
        p2_prob: float,
        p1_odds: float,
        p2_odds: float,
        bankroll: float,
        confidence: float = 1.0,
    ) -> MultiOutcomeKellyResult:
        """Kelly for tennis match winner (2 outcomes)."""
        model_probs = {"player1": p1_prob, "player2": p2_prob}
        odds_dict = {"player1": p1_odds, "player2": p2_odds}

        adjusted_probs = {}
        for outcome, prob in model_probs.items():
            implied = 1 / odds_dict[outcome]
            adjusted_probs[outcome] = implied + (prob - implied) * confidence

        total = sum(adjusted_probs.values())
        if total > 0:
            adjusted_probs = {k: v / total for k, v in adjusted_probs.items()}

        return self.calculate_multi_outcome_kelly(
            model_probs=adjusted_probs,
            odds=odds_dict,
            bankroll=bankroll,
        )

    def calculate_baseball_kelly(
        self,
        home_prob: float,
        away_prob: float,
        home_odds: float,
        away_odds: float,
        bankroll: float,
        confidence: float = 1.0,
    ) -> MultiOutcomeKellyResult:
        """Kelly for baseball moneyline (2 outcomes)."""
        return self.calculate_tennis_kelly(
            home_prob, away_prob, home_odds, away_odds, bankroll, confidence
        )

    def calculate_basketball_kelly(
        self,
        home_prob: float,
        away_prob: float,
        home_odds: float,
        away_odds: float,
        bankroll: float,
        confidence: float = 1.0,
    ) -> MultiOutcomeKellyResult:
        """Kelly for basketball moneyline (2 outcomes)."""
        return self.calculate_tennis_kelly(
            home_prob, away_prob, home_odds, away_odds, bankroll, confidence
        )

    def generate_stake_recommendations(
        self,
        multi_result: MultiOutcomeKellyResult,
        bankroll: float,
        confidence: float = 1.0,
    ) -> list[StakeRecommendation]:
        """
        Generate final stake recommendations with risk ratings.

        Args:
            multi_result: Multi-outcome Kelly result
            bankroll: Total bankroll
            confidence: Overall model confidence

        Returns:
            List of StakeRecommendation sorted by stake size
        """
        recommendations = []

        for outcome, result in multi_result.outcomes.items():
            if not result.meets_min_edge:
                continue

            stake_pct = result.recommended_stake / bankroll if bankroll > 0 else 0

            # Risk level based on Kelly fraction and odds
            kelly_pct = result.fractional_kelly
            if kelly_pct > 0.03:
                risk_level = 4
            elif kelly_pct > 0.015:
                risk_level = 3
            elif kelly_pct > 0.005:
                risk_level = 2
            else:
                risk_level = 1

            # Reasoning
            edge_pct = result.edge * 100
            kelly_pct_display = result.fractional_kelly * 100
            reasoning = (
                f"Edge: {edge_pct:.1f}%, Kelly: {kelly_pct_display:.2f}%, "
                f"Confidence: {confidence:.0%}"
            )

            recommendations.append(
                StakeRecommendation(
                    outcome=outcome,
                    stake_units=result.recommended_stake,
                    stake_pct_bankroll=stake_pct,
                    kelly_fraction=result.kelly_fraction,
                    fractional_kelly=result.fractional_kelly,
                    confidence=confidence,
                    risk_level=risk_level,
                    reasoning=reasoning,
                )
            )

        # Sort by stake size (largest first)
        recommendations.sort(key=lambda r: r.stake_units, reverse=True)

        return recommendations

    @staticmethod
    def calculate_expected_growth(
        bankroll: float,
        kelly_fraction: float,
        win_prob: float,
        odds: float,
        num_bets: int = 1,
    ) -> float:
        """
        Calculate expected bankroll growth after N bets.

        E[log(bankroll)] = N * (p * log(1 + f*(b-1)) + q * log(1 - f))
        """
        if num_bets <= 0 or kelly_fraction <= 0:
            return bankroll

        b = odds - 1
        p = win_prob
        q = 1 - p
        f = kelly_fraction

        if f >= 1:
            return 0.0  # Ruin

        growth_per_bet = p * math.log(1 + f * b) + q * math.log(1 - f)
        total_growth = math.exp(num_bets * growth_per_bet)

        return bankroll * total_growth

    @staticmethod
    def probability_of_ruin(
        bankroll: float,
        kelly_fraction: float,
        win_prob: float,
        odds: float,
        target_bankroll: float,
    ) -> float:
        """
        Calculate probability of ruin before reaching target.

        Using gambler's ruin formula for Kelly betting.
        """
        if bankroll <= 0 or target_bankroll <= bankroll:
            return 1.0

        b = odds - 1
        p = win_prob
        q = 1 - p
        f = kelly_fraction

        if f <= 0:
            return 1.0

        # Simplified: probability of hitting 0 before target
        # Using diffusion approximation
        drift = p * f * b - q * f
        variance = p * q * (f * b) ** 2

        if drift <= 0:
            return 1.0

        # Probability of ruin ≈ exp(-2 * drift * log(target/bankroll) / variance)
        log_ratio = math.log(target_bankroll / bankroll)
        ruin_prob = math.exp(-2 * drift * log_ratio / variance) if variance > 0 else 0.0

        return min(max(ruin_prob, 0.0), 1.0)


def create_kelly_sizer_from_config(config: dict[str, Any]) -> KellySizer:
    """Create KellySizer from configuration dictionary."""
    return KellySizer(
        kelly_fraction=config.get("kelly_fraction", KellySizer.DEFAULT_KELLY_FRACTION),
        max_stake_pct=config.get("max_stake_pct", KellySizer.DEFAULT_MAX_STAKE_PCT),
        min_edge=config.get("min_edge", KellySizer.DEFAULT_MIN_EDGE),
    )