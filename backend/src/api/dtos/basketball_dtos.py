from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class BasketballPredictRequest(BaseModel):
    """Request model for basketball game prediction."""
    date: date
    home_team: str
    away_team: str
    venue: Optional[str] = None
    season: Optional[str] = None
    game_type: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
    spread: Optional[float] = None
    total: Optional[float] = None


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
