"""
Best-Combination Optimizer Module

Assembles a single 4-leg cross-sport combination (one pick per sport) from
the candidate pools produced by the soccer, tennis, baseball, and basketball
prediction services.

Pipeline:
    1. ``aggregate_pools`` — normalize every per-sport pick into a
       ``UnifiedPick``, dropping candidates that lack ``sport``/``match_id``
       (design 2.2).
    2. ``build_combination`` — coverage checks, per-sport quality filtering
       with best-available fallback, leg selection, odds resolution, totals,
       and EV guard (design 2.3/2.4/2.5).
    3. ``size_stake`` — fractional Kelly capped by the portfolio RiskManager
       (design 2.6).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, Optional

from src.domain.entities.unified_pick import UnifiedPick
from src.domain.services.kelly_sizer import KellySizer
from src.domain.services.risk_management.risk_manager import RiskManager

SPORTS: tuple[str, ...] = ("soccer", "tennis", "baseball", "basketball")

#: How a leg's odds were obtained.
OddsSource = Literal["market", "fair"]

INDEPENDENCE_DISCLAIMER = (
    "Combinada armada sobre eventos independientes de cuatro deportes distintos; "
    "el resultado de una pierna no afecta la probabilidad de las demás."
)


class CombinationError(Exception):
    """Domain error raised while assembling the combination.

    Attributes:
        code: Stable machine-readable error code ("insufficient_pool",
            "no_picks_available", "no_positive_ev").
        detail: Human-readable explanation (Spanish, user-facing).
        missing_sports: Sports with no eligible picks (coverage errors only).
    """

    def __init__(
        self,
        code: str,
        detail: str,
        missing_sports: Optional[list[str]] = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.missing_sports = missing_sports


@dataclass(frozen=True)
class CombinationLeg:
    """A selected leg with resolved odds metadata."""

    sport: str
    match_id: str
    match_label: str
    pick_label: str
    league: Optional[str]
    probability: float
    odds: float
    odds_source: OddsSource  # "market" | "fair"
    confidence_level: str
    is_recommended: bool
    priority_score: float
    confidence_warning: bool
    odds_warning: bool


@dataclass(frozen=True)
class CombinationTotals:
    """Aggregated metrics for the whole combination."""

    total_probability: float
    total_odds: float
    expected_value: float
    mixed_odds: bool


@dataclass(frozen=True)
class StakeSuggestion:
    """Stake sizing recommendation for the combination."""

    suggested_stake_pct: float
    risk_level: int
    kelly_fraction: float


@dataclass(frozen=True)
class CombinationResult:
    """Fully assembled combination."""

    legs: tuple[CombinationLeg, ...]
    totals: CombinationTotals
    stake: StakeSuggestion
    independence_disclaimer: str
    warnings: tuple[str, ...]


class CombinationOptimizer:
    """Pure assembler for the cross-sport best combination."""

    #: Only these sports produce combination legs.
    SPORTS: tuple[str, ...] = SPORTS

    @staticmethod
    def to_unified(raw: dict[str, Any], sport: str) -> Optional[UnifiedPick]:
        """Normalize a raw service pick dict into a UnifiedPick.

        Candidates without a ``match_id`` or a pick label are not valid
        combination inputs and are dropped. ``market_label`` is accepted as an
        alias of ``pick_label`` (tennis/baseball/basketball market dicts emit
        ``market_label``).
        """
        match_id = raw.get("match_id")
        pick_label = raw.get("pick_label") or raw.get("market_label")
        probability = raw.get("probability")
        if not match_id or not pick_label:
            return None
        if not isinstance(probability, (int, float)) or not 0 < probability <= 1:
            return None

        odds = raw.get("odds") or 0.0
        try:
            odds = float(odds) if odds else 0.0
            probability = float(probability)
            priority_score = float(raw.get("priority_score") or 0.0)
        except (TypeError, ValueError):
            return None

        try:
            return UnifiedPick(
                sport=sport,
                match_id=str(match_id),
                match_label=str(raw.get("match_label") or ""),
                pick_label=str(pick_label),
                probability=probability,
                confidence_level=str(raw.get("confidence_level") or "medium").lower(),
                odds=round(odds, 2),
                is_recommended=bool(raw.get("is_recommended", False)),
                priority_score=round(priority_score, 2),
                is_ml_confirmed=bool(raw.get("is_ml_confirmed", False)),
                is_ia_confirmed=bool(raw.get("is_ia_confirmed", False)),
                league=str(raw["league"]) if raw.get("league") else None,
            )
        except (TypeError, ValueError):
            return None

    def aggregate_pools(
        self, per_sport_picks: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[UnifiedPick]]:
        """Normalize every per-sport pick list, dropping invalid candidates."""
        pools: dict[str, list[UnifiedPick]] = {}
        for sport in self.SPORTS:
            raw_list = per_sport_picks.get(sport) or []
            pools[sport] = [
                pick
                for raw in raw_list
                if (pick := self.to_unified(raw, sport)) is not None
            ]
        return pools

    @staticmethod
    def _passes_quality(pick: UnifiedPick) -> bool:
        """Quality gate per sport (spec: quality filter)."""
        if pick.sport == "soccer":
            return pick.is_ml_confirmed or pick.is_ia_confirmed
        return pick.confidence_level == "high" and pick.is_recommended

    @staticmethod
    def _best(pool: list[UnifiedPick]) -> UnifiedPick:
        """Best candidate: highest priority score, ties broken by probability."""
        return max(pool, key=lambda p: (p.priority_score, p.probability))

    def _select_sport_leg(
        self,
        sport: str,
        pool: list[UnifiedPick],
        threshold: float,
        excluded: set[str],
    ) -> Optional[tuple[UnifiedPick, bool]]:
        """Pick the best candidate for one sport.

        Returns ``(pick, confidence_warning)`` or ``None`` when the sport has
        no eligible candidates (coverage error).
        """
        if not pool:
            return None
        quality = [
            p
            for p in pool
            if p.probability >= threshold
            and (p.league is None or p.league not in excluded)
            and self._passes_quality(p)
        ]
        # Fallback pool relaxes the quality gate but never the user's
        # exclude_leagues hard constraint (design: best-available fallback).
        fallback = [p for p in pool if p.league is None or p.league not in excluded]
        if not fallback:
            return None
        if quality:
            return self._best(quality), False
        return self._best(fallback), True

    def build_combination(
        self,
        pools: dict[str, list[UnifiedPick]],
        min_probability: Optional[float] = None,
        exclude_leagues: Optional[list[str]] = None,
    ) -> CombinationResult:
        """Assemble the best 4-leg combination from normalized pools.

        Raises:
            CombinationError: with code "no_picks_available" when no sport has
                picks, "insufficient_pool" when fewer than four sports have
                eligible picks, or "no_positive_ev" when the assembled
                combination has zero/negative expected value.
        """
        excluded = set(exclude_leagues or [])
        threshold = min_probability or 0.0

        missing: list[str] = []
        selected: list[tuple[UnifiedPick, bool]] = []
        warnings: list[str] = []

        for sport in self.SPORTS:
            selection = self._select_sport_leg(
                sport, pools.get(sport) or [], threshold, excluded
            )
            if selection is None:
                missing.append(sport)
                continue
            selected.append(selection)

        if not missing and not selected:
            missing = list(self.SPORTS)

        if len(missing) == len(self.SPORTS):
            raise CombinationError(
                "no_picks_available",
                "No hay predicciones disponibles para ningún deporte.",
                missing,
            )
        if missing:
            raise CombinationError(
                "insufficient_pool",
                "No hay suficientes picks para armar una combinada de cuatro piernas.",
                missing,
            )

        legs: list[CombinationLeg] = []
        market_odds: list[float] = []
        all_market = True
        for pick, confidence_warning in selected:
            odds, odds_source, odds_warning = self._leg_odds(pick)
            all_market = all_market and odds_source == "market"
            market_odds.append(odds)
            legs.append(
                self._build_leg(
                    pick, confidence_warning, odds, odds_source, odds_warning
                )
            )
            self._append_leg_warnings(warnings, pick, confidence_warning, odds_warning)

        total_probability, total_odds, mixed_odds, warnings = self._compute_totals(
            legs, market_odds, all_market, warnings
        )

        expected_value = round(total_probability * total_odds - 1.0, 4)
        if expected_value <= 0:
            raise CombinationError(
                "no_positive_ev",
                "La combinada no tiene valor esperado positivo "
                f"(EV {expected_value * 100:.2f}%).",
            )

        stake = self.size_stake(total_probability, total_odds)

        return CombinationResult(
            legs=tuple(legs),
            totals=CombinationTotals(
                total_probability=total_probability,
                total_odds=total_odds,
                expected_value=expected_value,
                mixed_odds=mixed_odds,
            ),
            stake=stake,
            independence_disclaimer=INDEPENDENCE_DISCLAIMER,
            warnings=tuple(warnings),
        )

    @staticmethod
    def _build_leg(
        pick: UnifiedPick,
        confidence_warning: bool,
        odds: float,
        odds_source: OddsSource,
        odds_warning: bool,
    ) -> CombinationLeg:
        """Map a candidate pick into an assembled leg."""
        return CombinationLeg(
            sport=pick.sport,
            match_id=pick.match_id,
            match_label=pick.match_label,
            pick_label=pick.pick_label,
            league=pick.league,
            probability=round(pick.probability, 4),
            odds=odds,
            odds_source=odds_source,
            confidence_level=pick.confidence_level,
            is_recommended=pick.is_recommended,
            priority_score=pick.priority_score,
            confidence_warning=confidence_warning,
            odds_warning=odds_warning,
        )

    @staticmethod
    def _append_leg_warnings(
        warnings: list[str],
        pick: UnifiedPick,
        confidence_warning: bool,
        odds_warning: bool,
    ) -> None:
        """Collect per-leg human-readable warnings."""
        if confidence_warning:
            warnings.append(
                f"{pick.sport}: sin picks de alta confianza, se usó la mejor "
                "opción disponible."
            )
        if odds_warning:
            warnings.append(
                f"{pick.sport}: sin cuota de mercado, se usó cuota justa "
                "(1/probabilidad)."
            )

    @staticmethod
    def _compute_totals(
        legs: list[CombinationLeg],
        market_odds: list[float],
        all_market: bool,
        warnings: list[str],
    ) -> tuple[float, float, bool, list[str]]:
        """Aggregate probabilities and odds across the four legs."""
        total_probability = round(math.prod(leg.probability for leg in legs), 4)
        if all_market:
            total_odds = round(math.prod(market_odds), 2)
            mixed_odds = False
        else:
            # Mixed/missing odds: price the combination at fair odds so the EV
            # calculation never assumes a bookmaker edge that does not exist.
            total_odds = (
                round(1.0 / total_probability, 2) if total_probability > 0 else 1.0
            )
            mixed_odds = True
            warnings.append(
                "No todas las piernas tienen cuota de mercado; el total se "
                "calculó con cuota justa (1/probabilidad)."
            )
        return total_probability, total_odds, mixed_odds, warnings

    @staticmethod
    def _leg_odds(pick: UnifiedPick) -> tuple[float, OddsSource, bool]:
        """Resolve leg odds: market when available, fair 1/p otherwise."""
        if pick.odds and pick.odds > 1.0:
            return round(pick.odds, 2), "market", False
        fair = round(1.0 / pick.probability, 2) if pick.probability > 0 else 1.0
        return fair, "fair", True

    def size_stake(
        self,
        total_probability: float,
        total_odds: float,
        kelly_sizer: Optional[KellySizer] = None,
        risk_manager: Optional[RiskManager] = None,
    ) -> StakeSuggestion:
        """Size the combination stake: fractional Kelly capped by RiskManager."""
        kelly_sizer = kelly_sizer or KellySizer()
        risk_manager = risk_manager or RiskManager()
        kelly_fraction = kelly_sizer.calculate_kelly_fraction(
            total_probability, total_odds
        )
        stake_pct = min(
            kelly_fraction,
            risk_manager.MAX_SINGLE_STAKE,
            risk_manager.MAX_DAILY_EXPOSURE,
        )
        return StakeSuggestion(
            suggested_stake_pct=round(stake_pct, 4),
            risk_level=self._risk_level_for_stake(stake_pct),
            kelly_fraction=round(kelly_fraction, 4),
        )

    @staticmethod
    def _risk_level_for_stake(stake_pct: float) -> int:
        """Map stake magnitude to 1-5 risk (mirrors KellySizer buckets)."""
        if stake_pct > 0.03:
            return 4
        if stake_pct > 0.015:
            return 3
        if stake_pct > 0.005:
            return 2
        return 1
