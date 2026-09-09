from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class BasketballGame:
    """Represents a basketball game for prediction purposes."""

    game_id: str
    home_team: str
    away_team: str
    game_date: date
    venue: Optional[str] = None
    season: str = "2025-26"
    game_type: str = "R"  # 'R' regular, 'P' postseason

    # Team Season Stats
    home_wins: Optional[int] = None
    home_losses: Optional[int] = None
    away_wins: Optional[int] = None
    away_losses: Optional[int] = None

    # Recent Form (last 10)
    home_pts_avg: Optional[float] = None
    home_pts_allowed_avg: Optional[float] = None
    away_pts_avg: Optional[float] = None
    away_pts_allowed_avg: Optional[float] = None

    # Efficiency
    home_off_rating: Optional[float] = None
    home_def_rating: Optional[float] = None
    away_off_rating: Optional[float] = None
    away_def_rating: Optional[float] = None
    home_pace: Optional[float] = None
    away_pace: Optional[float] = None

    # Shooting
    home_fg_pct: Optional[float] = None
    home_3pt_pct: Optional[float] = None
    away_fg_pct: Optional[float] = None
    away_3pt_pct: Optional[float] = None

    # Context
    home_rest_days: Optional[int] = None
    away_rest_days: Optional[int] = None
    is_back_to_back_home: bool = False
    is_back_to_back_away: bool = False

    # Betting Odds
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    spread: Optional[float] = None
    total: Optional[float] = None

    # Result (for training)
    home_score: Optional[int] = None
    away_score: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "game_id": self.game_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "game_date": self.game_date.isoformat(),
            "venue": self.venue,
            "season": self.season,
            "game_type": self.game_type,
            "home_wins": self.home_wins,
            "home_losses": self.home_losses,
            "away_wins": self.away_wins,
            "away_losses": self.away_losses,
            "home_pts_avg": self.home_pts_avg,
            "home_pts_allowed_avg": self.home_pts_allowed_avg,
            "away_pts_avg": self.away_pts_avg,
            "away_pts_allowed_avg": self.away_pts_allowed_avg,
            "home_off_rating": self.home_off_rating,
            "home_def_rating": self.home_def_rating,
            "away_off_rating": self.away_off_rating,
            "away_def_rating": self.away_def_rating,
            "home_pace": self.home_pace,
            "away_pace": self.away_pace,
            "home_fg_pct": self.home_fg_pct,
            "home_3pt_pct": self.home_3pt_pct,
            "away_fg_pct": self.away_fg_pct,
            "away_3pt_pct": self.away_3pt_pct,
            "home_rest_days": self.home_rest_days,
            "away_rest_days": self.away_rest_days,
            "is_back_to_back_home": self.is_back_to_back_home,
            "is_back_to_back_away": self.is_back_to_back_away,
            "home_odds": self.home_odds,
            "away_odds": self.away_odds,
            "spread": self.spread,
            "total": self.total,
            "home_score": self.home_score,
            "away_score": self.away_score,
        }
