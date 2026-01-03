"""
Data Transfer Objects (DTOs) Module

DTOs are used to transfer data between layers and to/from the API.
They use Pydantic for validation and serialization.
"""

from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, model_validator


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
    logo_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class LeagueDTO(BaseModel):
    """League data transfer object."""
    id: str
    name: str
    country: str
    season: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class MatchDTO(BaseModel):
    """Match data transfer object."""
    id: str
    home_team: TeamDTO
    away_team: TeamDTO
    league: LeagueDTO
    match_date: datetime
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: str = "NS"
    home_corners: Optional[int] = None
    away_corners: Optional[int] = None
    home_yellow_cards: Optional[int] = None
    away_yellow_cards: Optional[int] = None
    home_red_cards: Optional[int] = None
    away_red_cards: Optional[int] = None
    away_odds: Optional[float] = None
    minute: Optional[str] = None
    # Extended Stats
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    home_total_shots: Optional[int] = None
    away_total_shots: Optional[int] = None
    home_possession: Optional[str] = None
    away_possession: Optional[str] = None
    home_fouls: Optional[int] = None
    away_fouls: Optional[int] = None
    home_offsides: Optional[int] = None
    away_offsides: Optional[int] = None
    home_spi: Optional[float] = None
    away_spi: Optional[float] = None
    events: list["MatchEventDTO"] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def validate_stats_consistency(self) -> 'MatchDTO':
        """Ensure shots on target are at least equal to goals."""
        if self.home_goals is not None and self.home_goals > 0:
            if self.home_shots_on_target is None or self.home_shots_on_target < self.home_goals:
                self.home_shots_on_target = self.home_goals
            if self.home_total_shots is None or (self.home_shots_on_target is not None and self.home_total_shots < self.home_shots_on_target):
                self.home_total_shots = self.home_shots_on_target

        if self.away_goals is not None and self.away_goals > 0:
            if self.away_shots_on_target is None or self.away_shots_on_target < self.away_goals:
                self.away_shots_on_target = self.away_goals
            if self.away_total_shots is None or (self.away_shots_on_target is not None and self.away_total_shots < self.away_shots_on_target):
                self.away_total_shots = self.away_shots_on_target
        return self


class MatchEventDTO(BaseModel):
    """Event in a match."""
    time: str
    team_id: str
    player_name: str
    type: str
    detail: str
    
    model_config = ConfigDict(from_attributes=True)


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
    
    predicted_home_corners: float = Field(default=0.0, ge=0)
    predicted_away_corners: float = Field(default=0.0, ge=0)
    predicted_home_yellow_cards: float = Field(default=0.0, ge=0)
    predicted_away_yellow_cards: float = Field(default=0.0, ge=0)
    predicted_home_red_cards: float = Field(default=0.0, ge=0)
    predicted_away_red_cards: float = Field(default=0.0, ge=0)
    
    confidence: float = Field(..., ge=0, le=1)
    data_sources: list[str] = Field(default_factory=list)
    recommended_bet: str
    over_under_recommendation: str
    suggested_picks: list["SuggestedPickDTO"] = Field(default_factory=list) # Full list of picks
    highlights_url: Optional[str] = None
    real_time_odds: Optional[dict[str, float]] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MatchPredictionDTO(BaseModel):
    """Combined match and prediction DTO."""
    match: MatchDTO
    prediction: PredictionDTO
    
    model_config = ConfigDict(from_attributes=True)


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


# ============================================================
# Suggested Picks DTOs
# ============================================================

class SuggestedPickDTO(BaseModel):
    """Suggested pick data transfer object."""
    market_type: str
    market_label: str
    probability: float = Field(..., ge=0, le=1)
    confidence_level: str  # "high", "medium", "low"
    reasoning: str
    risk_level: int = Field(..., ge=1, le=5)
    is_recommended: bool = True
    priority_score: float = 0.0
    is_ml_confirmed: bool = False
    ml_confidence: float = 0.0
    suggested_stake: float = 0.0
    kelly_percentage: float = 0.0
    clv_beat: bool = False
    expected_value: float = 0.0
    opening_odds: float = 0.0
    closing_odds: float = 0.0
    
    model_config = ConfigDict(from_attributes=True)


class MatchSuggestedPicksDTO(BaseModel):
    """Container for all suggested picks for a match."""
    match_id: str
    suggested_picks: list[SuggestedPickDTO] = Field(default_factory=list)
    combination_warning: Optional[str] = None
    highlights_url: Optional[str] = None
    real_time_odds: Optional[dict[str, float]] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Betting Feedback DTOs
# ============================================================

class BettingFeedbackRequestDTO(BaseModel):
    """Request for registering betting feedback."""
    match_id: str = Field(..., description="Match identifier")
    market_type: str = Field(..., description="Type of market (corners_over, cards_over, etc.)")
    prediction: str = Field(..., description="The prediction made")
    actual_outcome: str = Field(..., description="What actually happened")
    was_correct: bool = Field(..., description="Whether prediction was correct")
    odds: float = Field(..., ge=1.0, description="Betting odds")
    stake: Optional[float] = Field(None, ge=0, description="Amount staked")


class BettingFeedbackResponseDTO(BaseModel):
    """Response for betting feedback registration."""
    success: bool
    message: str
    market_type: str
    new_confidence_adjustment: float


class MarketPerformanceDTO(BaseModel):
    """Market performance statistics DTO."""
    market_type: str
    total_predictions: int
    correct_predictions: int
    success_rate: float
    avg_odds: float
    total_profit_loss: float
    confidence_adjustment: float
    last_updated: datetime
    
    model_config = ConfigDict(from_attributes=True)


class LearningStatsResponseDTO(BaseModel):
    """Response containing all learning statistics."""
    market_performances: list[MarketPerformanceDTO]
    total_feedback_count: int
    last_updated: datetime


class TopMLPicksDTO(BaseModel):
    """Container for the top aggregated ML picks across all leagues."""
    picks: list[SuggestedPickDTO] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
