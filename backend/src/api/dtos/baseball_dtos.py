from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class BaseballPredictRequest(BaseModel):
    """Request model for baseball game prediction."""

    date: date
    home_team: str
    away_team: str
    venue: Optional[str] = None
    day_night: str = "day"
    home_pitcher_name: Optional[str] = None
    away_pitcher_name: Optional[str] = None
    season: Optional[int] = None
    series_id: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None


class BaseballGameResponse(BaseModel):
    """Response model for a single baseball game."""

    game_id: str
    date: str
    home_team: str
    away_team: str
    venue: Optional[str] = None
    day_night: str
    home_pitcher_name: Optional[str] = None
    away_pitcher_name: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None


class BaseballMarketResponse(BaseModel):
    """Response model for a baseball betting market."""

    market_type: str
    market_label: str
    probability: float
    confidence_level: str
    reasoning: str
    risk_level: float
    is_recommended: bool
    priority_score: float
    pick_code: str


class BaseballPredictionDetail(BaseModel):
    """Full prediction detail for a game."""

    home_win_prob: float
    away_win_prob: float
    predicted_winner: str
    confidence: float
    key_factors: List[str]
    markets: List[BaseballMarketResponse]


class BaseballPredictResponse(BaseModel):
    """Response model for baseball game prediction."""

    game_id: str
    home_team: str
    away_team: str
    home_win_prob: float
    away_win_prob: float
    predicted_winner: str
    confidence: float


class BaseballGamesResponse(BaseModel):
    """Response model for upcoming baseball games."""

    games: List[BaseballGameResponse]
    generated_at: str


class BaseballSeriesGame(BaseModel):
    """A single game within a series."""

    game_id: str
    date: str
    home_team: str
    away_team: str
    venue: Optional[str] = None
    day_night: str
    home_pitcher_name: Optional[str] = None
    away_pitcher_name: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    prediction: Optional[BaseballPredictionDetail] = None


class BaseballSeriesResponse(BaseModel):
    """Response model for baseball series."""

    series: List[List[BaseballSeriesGame]]
    generated_at: str
    is_demo: bool = False
