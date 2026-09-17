from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class BasketballPredictRequest(BaseModel):
    """Request model for basketball game prediction."""

    date: date
    home_team: str = Field(min_length=1, max_length=10)  # NBA codes: LAL, BOS, etc.
    away_team: str = Field(min_length=1, max_length=10)
    venue: Optional[str] = Field(None, max_length=100)
    season: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}$")  # e.g. "2025-26"
    game_type: Optional[Literal["R", "P"]] = None  # Regular / Playoffs
    home_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)
    away_odds: Optional[float] = Field(None, gt=1.0, le=1000.0)
    spread: Optional[float] = Field(None, ge=-50.0, le=50.0)
    total: Optional[float] = Field(None, ge=100.0, le=350.0)


class BasketballGameResponse(BaseModel):
    """Response model for a single basketball game."""

    game_id: str
    date: str
    home_team: str
    away_team: str
    venue: Optional[str] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None


class BasketballMarketResponse(BaseModel):
    """Response model for a basketball betting market."""

    market_type: str
    market_label: str
    probability: float
    confidence_level: str
    reasoning: str
    risk_level: float
    is_recommended: bool
    priority_score: float
    pick_code: str


class BasketballPredictionDetail(BaseModel):
    """Full prediction detail for a game."""

    home_win_prob: float
    away_win_prob: float
    predicted_winner: str
    confidence: float
    key_factors: List[str]
    markets: List[BasketballMarketResponse]


class BasketballPredictResponse(BaseModel):
    """Response model for basketball game prediction."""

    game_id: str
    home_team: str
    away_team: str
    home_win_prob: float
    away_win_prob: float
    predicted_winner: str
    confidence: float


class BasketballGamesResponse(BaseModel):
    """Response model for upcoming basketball games."""

    games: List[BasketballGameResponse]
    generated_at: str


class BasketballGameWithPrediction(BaseModel):
    """A single game with its prediction."""

    game_id: str
    date: str
    home_team: str
    away_team: str
    venue: Optional[str] = None
    home_team_name: Optional[str] = None
    away_team_name: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    prediction: Optional[BasketballPredictionDetail] = None


class BasketballConferenceResponse(BaseModel):
    """Response model for conferences."""

    conferences: List[dict]
    generated_at: str


class BasketballConferenceGamesResponse(BaseModel):
    """Response model for games grouped by conference."""

    conference_id: str
    conference_name: str
    games: List[BasketballGameWithPrediction]
    generated_at: str
