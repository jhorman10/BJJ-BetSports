"""
Unified Pick Entity Module

A sport-agnostic pick representation used by the best-combination optimizer.
Every pick emitted by the four sport services is normalized into a
``UnifiedPick`` so the aggregator can consume candidates from soccer, tennis,
baseball, and basketball with a single shape.

Picks lacking ``sport`` or ``match_id`` are not valid combination candidates
and MUST be excluded by the aggregator (see combination_optimizer).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedPick:
    """Immutable normalized pick for cross-sport combination building.

    Attributes:
        sport: Sport identifier ("soccer", "tennis", "baseball", "basketball").
        match_id: Back-reference to the source match/game.
        match_label: Human-readable label for the match (e.g. team names).
        pick_label: Human-readable label for the pick/market.
        probability: Model probability for the pick (0.0 - 1.0).
        odds: Bookmaker decimal odds; 0.0 means missing (fair-odds fallback).
        confidence_level: "high", "medium", or "low".
        is_recommended: Whether the source service recommends the pick.
        priority_score: Source priority score (higher = better).
        is_ml_confirmed: ML validation flag (soccer quality gate).
        is_ia_confirmed: IA/best-pick flag (soccer quality gate).
        league: Optional league/tournament identifier (exclude_leagues filter).
    """

    sport: str
    match_id: str
    match_label: str
    pick_label: str
    probability: float
    confidence_level: str
    odds: float = 0.0
    is_recommended: bool = False
    priority_score: float = 0.0
    is_ml_confirmed: bool = False
    is_ia_confirmed: bool = False
    league: str | None = None
