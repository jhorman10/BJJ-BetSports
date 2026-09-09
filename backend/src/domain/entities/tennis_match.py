# mypy: ignore-errors
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class TennisMatch:
    """Represents a tennis match for prediction purposes."""

    match_id: str
    tournament_name: str
    surface: str  # 'Hard', 'Clay', 'Grass', 'Carpet'
    tourney_level: str  # 'G' (Grand Slam), 'A' (ATP), 'M' (Masters), etc.
    round_name: str
    match_date: date
    best_of: int  # 3 or 5 sets

    # Player 1 (Winner in historical data)
    p1_name: str
    p1_id: Optional[str] = None
    p1_rank: Optional[int] = None
    p1_rank_points: Optional[int] = None
    p1_age: Optional[float] = None
    p1_hand: Optional[str] = None  # 'R', 'L'
    p1_height: Optional[int] = None
    p1_seed: Optional[int] = None
    p1_entry: Optional[str] = None  # 'Q', 'WC', 'LL', 'SE'

    # Player 2 (Loser in historical data)
    p2_name: str = ""
    p2_id: Optional[str] = None
    p2_rank: Optional[int] = None
    p2_rank_points: Optional[int] = None
    p2_age: Optional[float] = None
    p2_hand: Optional[str] = None
    p2_height: Optional[int] = None
    p2_seed: Optional[int] = None
    p2_entry: Optional[str] = None

    # Betting Odds (optional)
    p1_odds: Optional[float] = None  # Decimal odds for P1 win
    p2_odds: Optional[float] = None  # Decimal odds for P2 win

    # Match Result
    score: str = ""
    winner_id: Optional[str] = None
    loser_id: Optional[str] = None

    # Statistics (from 1991+)
    w_ace: Optional[int] = None
    w_df: Optional[int] = None
    w_svpt: Optional[int] = None
    w_1stIn: Optional[int] = None
    w_1stWon: Optional[int] = None
    w_2ndWon: Optional[int] = None
    w_SvGms: Optional[int] = None
    w_bpSaved: Optional[int] = None
    w_bpFaced: Optional[int] = None

    l_ace: Optional[int] = None
    l_df: Optional[int] = None
    l_svpt: Optional[int] = None
    l_1stIn: Optional[int] = None
    l_1stWon: Optional[int] = None
    l_2ndWon: Optional[int] = None
    l_SvGms: Optional[int] = None
    l_bpSaved: Optional[int] = None
    l_bpFaced: Optional[int] = None
