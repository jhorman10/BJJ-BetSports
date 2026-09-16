from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BaseballPredictRequest(BaseModel):
    """Request model for baseball game prediction."""

    date: date
    home_team: str = Field(min_length=1, max_length=10)  # MLB codes: NYY, LAD, etc.
    away_team: str = Field(min_length=1, max_length=10)
    venue: Optional[str] = Field(None, max_length=100)
    day_night: Literal["day", "night"] = "day"
    home_pitcher_name: Optional[str] = Field(None, max_length=100)
    away_pitcher_name: Optional[str] = Field(None, max_length=100)
    season: Optional[int] = Field(None, ge=1900, le=2100)
    series_id: Optional[str] = Field(None, max_length=50)
    home_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)
    away_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)


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
