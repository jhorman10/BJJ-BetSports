from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TennisMatchRequest(BaseModel):
    """Request model for tennis match prediction.

    Strict bounds prevent oversized payloads from reaching downstream ML
    feature extraction and rule out absurd values (rank 0, odds < 1.0).
    """

    tournament_name: str = Field(min_length=1, max_length=200)
    surface: Literal["Hard", "Clay", "Grass", "Carpet"]
    tourney_level: str = Field(min_length=1, max_length=8)  # 'G', 'A', 'M', etc.
    round_name: str = Field(min_length=1, max_length=50)
    match_date: date
    best_of: Literal[3, 5]

    # Player 1
    p1_name: str = Field(min_length=1, max_length=100)
    p1_rank: Optional[int] = Field(None, ge=1, le=3000)
    p1_rank_points: Optional[int] = Field(None, ge=0, le=30_000)
    p1_age: Optional[float] = Field(None, ge=14.0, le=60.0)
    p1_hand: Optional[Literal["R", "L", "U"]] = None
    p1_height: Optional[int] = Field(None, ge=140, le=230)  # cm
    p1_seed: Optional[int] = Field(None, ge=1, le=128)
    p1_entry: Optional[str] = Field(None, max_length=20)
    p1_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)

    # Player 2
    p2_name: str = Field(min_length=1, max_length=100)
    p2_rank: Optional[int] = Field(None, ge=1, le=3000)
    p2_rank_points: Optional[int] = Field(None, ge=0, le=30_000)
    p2_age: Optional[float] = Field(None, ge=14.0, le=60.0)
    p2_hand: Optional[Literal["R", "L", "U"]] = None
    p2_height: Optional[int] = Field(None, ge=140, le=230)
    p2_seed: Optional[int] = Field(None, ge=1, le=128)
    p2_entry: Optional[str] = Field(None, max_length=20)
    p2_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)


class TennisPredictionResponse(BaseModel):
    """Response model for tennis match prediction."""

    match_id: str
    p1_name: str
    p2_name: str
    p1_win_prob: float
    p2_win_prob: float
    predicted_winner: str
    confidence: float
    surface: str
    tournament_name: str
