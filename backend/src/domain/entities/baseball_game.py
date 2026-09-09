from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class BaseballGame:
    """Represents a baseball game for prediction purposes."""

    game_id: str
    date: date
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    venue: Optional[str] = None
    day_night: str = "day"  # 'day' or 'night'

    # Probable pitchers (optional)
    home_pitcher_id: Optional[str] = None
    home_pitcher_name: Optional[str] = None
    away_pitcher_id: Optional[str] = None
    away_pitcher_name: Optional[str] = None

    season: Optional[int] = None
    series_id: Optional[str] = None

    # Betting Odds (optional)
    home_odds: Optional[float] = None  # Decimal odds for home win
    away_odds: Optional[float] = None  # Decimal odds for away win

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "game_id": self.game_id,
            "date": self.date.isoformat(),
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "venue": self.venue,
            "day_night": self.day_night,
            "home_pitcher_id": self.home_pitcher_id,
            "home_pitcher_name": self.home_pitcher_name,
            "away_pitcher_id": self.away_pitcher_id,
            "away_pitcher_name": self.away_pitcher_name,
            "season": self.season,
            "series_id": self.series_id,
            "home_odds": self.home_odds,
            "away_odds": self.away_odds,
        }
