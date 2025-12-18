"""
Data Transfer Objects (DTOs) Module

DTOs are used to transfer data between layers and to/from the API.
They use Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================

class SortBy(str, Enum):
    """Sorting options for predictions."""
    DATE = "date"
    CONFIDENCE = "confidence"
    HOME_PROBABILITY = "home_probability"
    AWAY_PROBABILITY = "away_probability"


# ============================================================
# Request DTOs
# ============================================================

class GetPredictionsRequest(BaseModel):
    """Request for getting predictions."""
    league_id: str = Field(..., description="League identifier")
    limit: int = Field(default=10, ge=1, le=50, description="Max matches to return")
    sort_by: SortBy = Field(default=SortBy.CONFIDENCE, description="Field to sort by")
    sort_desc: bool = Field(default=True, description="Sort in descending order")


class GetMatchPredictionRequest(BaseModel):
    """Request for getting a single match prediction."""
    match_id: str = Field(..., description="Match identifier")


# ============================================================
# Response DTOs
# ============================================================

class TeamDTO(BaseModel):
    """Team data transfer object."""
    id: str
    name: str
    short_name: Optional[str] = None
    country: Optional[str] = None
    
    class Config:
        from_attributes = True


class LeagueDTO(BaseModel):
    """League data transfer object."""
    id: str
    name: str
    country: str
    season: Optional[str] = None
    
    class Config:
        from_attributes = True


class MatchDTO(BaseModel):
    """Match data transfer object."""
    id: str
    home_team: TeamDTO
    away_team: TeamDTO
    league: LeagueDTO
    match_date: datetime
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    
    class Config:
        from_attributes = True


class PredictionDTO(BaseModel):
    """Prediction data transfer object."""
    match_id: str
    home_win_probability: float = Field(..., ge=0, le=1)
    draw_probability: float = Field(..., ge=0, le=1)
    away_win_probability: float = Field(..., ge=0, le=1)
    over_25_probability: float = Field(..., ge=0, le=1)
    under_25_probability: float = Field(..., ge=0, le=1)
    predicted_home_goals: float = Field(..., ge=0)
    predicted_away_goals: float = Field(..., ge=0)
    confidence: float = Field(..., ge=0, le=1)
    data_sources: list[str] = Field(default_factory=list)
    recommended_bet: str
    over_under_recommendation: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MatchPredictionDTO(BaseModel):
    """Combined match and prediction DTO."""
    match: MatchDTO
    prediction: PredictionDTO
    
    class Config:
        from_attributes = True


class CountryDTO(BaseModel):
    """Country with available leagues."""
    name: str
    code: str
    flag: Optional[str] = None
    leagues: list[LeagueDTO] = Field(default_factory=list)


class LeaguesResponseDTO(BaseModel):
    """Response containing all available leagues grouped by country."""
    countries: list[CountryDTO]
    total_leagues: int


class PredictionsResponseDTO(BaseModel):
    """Response containing match predictions."""
    league: LeagueDTO
    predictions: list[MatchPredictionDTO]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponseDTO(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponseDTO(BaseModel):
    """Error response."""
    error: str
    message: str
    details: Optional[dict] = None
