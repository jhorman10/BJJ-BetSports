from datetime import date
from typing import Optional

from pydantic import BaseModel


class TennisMatchRequest(BaseModel):
    """Request model for tennis match prediction."""

    tournament_name: str
    surface: str  # 'Hard', 'Clay', 'Grass', 'Carpet'
    tourney_level: str  # 'G' (Grand Slam), 'A' (ATP), 'M' (Masters), etc.
    round_name: str
    match_date: date
    best_of: int  # 3 or 5 sets

    # Player 1
    p1_name: str
    p1_rank: Optional[int] = None
    p1_rank_points: Optional[int] = None
    p1_age: Optional[float] = None
    p1_hand: Optional[str] = None
    p1_height: Optional[int] = None
    p1_seed: Optional[int] = None
    p1_entry: Optional[str] = None
    p1_odds: Optional[float] = None

    # Player 2
    p2_name: str
    p2_rank: Optional[int] = None
    p2_rank_points: Optional[int] = None
    p2_age: Optional[float] = None
    p2_hand: Optional[str] = None
    p2_height: Optional[int] = None
    p2_seed: Optional[int] = None
    p2_entry: Optional[str] = None
    p2_odds: Optional[float] = None


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
