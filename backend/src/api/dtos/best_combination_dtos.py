"""
Best Combination API DTOs.

Request/response models for ``POST /api/v1/best-combination`` — the single
4-leg cross-sport combination (one pick per sport) endpoint.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class BestCombinationRequest(BaseModel):
    """Request body for the best-combination endpoint."""

    min_probability: Optional[float] = Field(
        default=None,
        gt=0.0,
        lt=1.0,
        description="Discard candidate legs below this probability (0 < p < 1).",
    )
    exclude_leagues: Optional[list[str]] = Field(
        default=None,
        description="League/tournament identifiers to exclude from the combination.",
    )


class BestCombinationLeg(BaseModel):
    """One selected leg of the combination."""

    sport: str
    match_id: str
    match_label: str
    pick_label: str
    league: Optional[str] = None
    probability: float
    odds: float
    odds_source: Literal["market", "fair"]
    confidence_level: str
    is_recommended: bool = False
    priority_score: float = 0.0
    confidence_warning: bool = False
    odds_warning: bool = False


class BestCombinationAggregate(BaseModel):
    """Aggregated combination metrics."""

    total_probability: float
    total_odds: float
    expected_value: float
    mixed_odds: bool = False


class BestCombinationStake(BaseModel):
    """Stake sizing suggestion for the whole combination."""

    suggested_stake_pct: float
    risk_level: int = Field(ge=1, le=5)
    kelly_fraction: float


class BestCombinationResponse(BaseModel):
    """Successful best-combination payload."""

    legs: list[BestCombinationLeg]
    aggregate: BestCombinationAggregate
    stake: BestCombinationStake
    generated_at: str
    independence_disclaimer: str
    warnings: list[str] = Field(default_factory=list)
