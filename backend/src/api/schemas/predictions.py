from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from src.api.schemas.leagues import LeagueModel
from src.api.utils.serializers import _utc_now_iso


class TeamModel(BaseModel):
    id: str
    name: str
    short_name: str | None = None
    country: str | None = None
    logo_url: str | None = None


class MatchModel(BaseModel):
    id: str
    home_team: TeamModel
    away_team: TeamModel
    league: LeagueModel
    match_date: str
    status: str
    home_goals: int | None = None
    away_goals: int | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None
    home_spi: float | None = None
    away_spi: float | None = None


class PredictionModel(BaseModel):
    match_id: str
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0
    over_25_probability: float = 0.0
    under_25_probability: float = 0.0
    predicted_home_goals: float = 0.0
    predicted_away_goals: float = 0.0
    # Map Extended Predictions
    predicted_home_corners: float = 0.0
    predicted_away_corners: float = 0.0
    predicted_home_yellow_cards: float = 0.0
    predicted_away_yellow_cards: float = 0.0
    predicted_home_red_cards: float = 0.0
    predicted_away_red_cards: float = 0.0
    over_95_corners_probability: float = 0.0
    under_95_corners_probability: float = 0.0
    over_45_cards_probability: float = 0.0
    under_45_cards_probability: float = 0.0
    confidence: float = 0.0
    data_sources: list[str] = Field(default_factory=list)
    recommended_bet: str = ""
    over_under_recommendation: str = ""
    created_at: str = Field(default_factory=_utc_now_iso)
    data_updated_at: str | None = None
    highlights_url: str | None = None
    real_time_odds: dict[str, float] | None = None
    fundamental_analysis: dict[str, bool] | None = None
    suggested_picks: list[dict[str, Any]] = Field(default_factory=list)
    # Model traceability metadata
    model_metadata: dict[str, Any] | None = None
    score_probabilities: list[dict[str, Any]] | None = None
    score_confidence_tier: str | None = None
    score_matrix: list[list[dict[str, Any]]] | None = None
    score_accuracy_history: dict[str, Any] | None = None


class MatchPredictionModel(BaseModel):
    match: MatchModel
    prediction: PredictionModel
    top_ml_picks: list[dict[str, Any]] = Field(default_factory=list)


class PredictionsResponse(BaseModel):
    league: LeagueModel
    predictions: list[MatchPredictionModel]
    generated_at: str
