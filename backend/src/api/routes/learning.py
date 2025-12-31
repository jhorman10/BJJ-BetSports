from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import re
import logging
import os
import zlib
import gc

# ML Imports
try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
except ImportError:
    RandomForestClassifier = None

from src.api.dependencies import (
    get_learning_service, get_football_data_uk, get_prediction_service, 
    get_statistics_service, get_data_sources, get_cache_service,
    get_match_enrichment_service, get_pick_resolution_service, get_training_data_service,
    get_ml_training_orchestrator
)
from src.application.services.ml_training_orchestrator import MLTrainingOrchestrator, TrainingResult
from src.domain.services.learning_service import LearningService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.application.services.training_data_service import TrainingDataService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.picks_service import PicksService
from src.domain.services.match_enrichment_service import MatchEnrichmentService
from src.domain.entities.suggested_pick import SuggestedPick
from src.domain.entities.entities import Match
from src.application.use_cases.use_cases import DataSources
from src.domain.entities.entities import TeamStatistics
from src.utils.time_utils import get_current_time
from src.infrastructure.cache.cache_service import CacheService
from src.core.constants import DEFAULT_LEAGUES

logger = logging.getLogger(__name__)

router = APIRouter()

class BacktestRequest(BaseModel):
    league_ids: Optional[List[str]] = None
    days_back: int = 365
    start_date: Optional[str] = None
    reset_weights: bool = False
    force_refresh: bool = False

class PickDetail(BaseModel):
    """Individual pick/event prediction within a match."""
    market_type: str  # "winner", "corners_over", "goals_over", etc.
    market_label: str  # "Real Madrid gana", "Over 9.5 Corners", etc.
    was_correct: bool
    probability: float  # 0-1
    expected_value: float
    confidence: float
    is_contrarian: bool = False  # True if pick differs from main prediction (Value Bet)
    reasoning: Optional[str] = None
    result: Optional[str] = None

class MatchPredictionHistory(BaseModel):
    """Individual match prediction result for verification."""
    match_id: str
    home_team: str
    away_team: str
    match_date: str
    predicted_winner: str  # "home", "away", "draw"
    actual_winner: str
    predicted_home_goals: float
    predicted_away_goals: float
    actual_home_goals: int
    actual_away_goals: int
    was_correct: bool
    confidence: float
    # Probabilities for UI Charts
    home_win_probability: float = 0.0
    draw_probability: float = 0.0
    away_win_probability: float = 0.0
    # Multiple picks for different events
    picks: List[PickDetail] = []
    # Legacy single pick support (deprecated)
    suggested_pick: Optional[str] = None
    pick_was_correct: Optional[bool] = None
    expected_value: Optional[float] = None

class RoiEvolutionPoint(BaseModel):
    date: str
    roi: float
    profit: float

class TrainingStatus(BaseModel):
    matches_processed: int
    correct_predictions: int
    accuracy: float
    total_bets: int
    roi: float
    profit_units: float
    market_stats: dict
    match_history: List[MatchPredictionHistory] = []
    roi_evolution: List[RoiEvolutionPoint] = []
    pick_efficiency: List[dict] = [] # Granular stats per pick type
    team_stats: dict = {} # Consolidated team stats after training, for live predictions use
    global_averages: dict = {} # Ultimate baseline from 10-year history

class TrainingProgressStatus(BaseModel):
    """Status of the ongoing or completed training process."""
    status: str  # "IN_PROGRESS", "COMPLETED", "ERROR", "IDLE"
    message: str = ""
    last_update: Optional[str] = None
    has_result: bool = False
    result: Optional[TrainingStatus] = None


@router.post("/train", response_model=TrainingStatus)
async def run_training_session(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    learning_service: LearningService = Depends(get_learning_service),
    orchestrator: MLTrainingOrchestrator = Depends(get_ml_training_orchestrator)
):
    """
    Executes a full backtest/training session.
    """
    if request.reset_weights:
        learning_service.reset_weights()

    # Run the full training pipeline via centralized orchestrator
    leagues = request.league_ids if request.league_ids else DEFAULT_LEAGUES
    
    result: TrainingResult = await orchestrator.run_training_pipeline(
        league_ids=leagues,
        days_back=request.days_back,
        start_date=request.start_date,
        force_refresh=request.force_refresh
    )
    
    # Force garbage collection to free up memory after training
    gc.collect()

    # Convert Result to Response DTO (Payload optimization)
    # The UI only needs the most recent match history to avoid 50MB responses
    history_limit = 500
    display_history = result.match_history[-history_limit:] if len(result.match_history) > history_limit else result.match_history
    
    response = TrainingStatus(
        matches_processed=result.matches_processed,
        correct_predictions=result.correct_predictions,
        accuracy=result.accuracy,
        total_bets=result.total_bets,
        roi=result.roi,
        profit_units=result.profit_units,
        market_stats=result.market_stats,
        match_history=display_history,
        roi_evolution=result.roi_evolution,
        pick_efficiency=result.pick_efficiency,
        team_stats=result.team_stats,
        global_averages=result.global_averages
    )
    
    # Cache the result for the dashboard
    from src.infrastructure.cache import get_training_cache
    cache = get_training_cache()
    cache.set_training_results(response.model_dump())
    
    return response


class CachedTrainingResponse(BaseModel):
    """Response for cached training data."""
    cached: bool
    last_update: Optional[str] = None
    data: Optional[TrainingStatus] = None
    message: str = ""


@router.get("/train/cached", response_model=CachedTrainingResponse)
async def get_cached_training_data():
    """
    Get cached training data without recomputation.
    
    Returns cached results from the last scheduled training run.
    If no cache exists, returns a message indicating training needs to run.
    
    This endpoint is fast and doesn't trigger any computation.
    """
    from src.infrastructure.cache import get_training_cache
    
    cache = get_training_cache()
    
    if cache.is_valid():
        results = cache.get_training_results()
        last_update = cache.get_last_update()
        
        return CachedTrainingResponse(
            cached=True,
            last_update=last_update.isoformat() if last_update else None,
            data=TrainingStatus(**results),
            message="Datos de entrenamiento recuperados exitosamente"
        )
    else:
        return CachedTrainingResponse(
            cached=False,
            last_update=None,
            data=None,
            message="No hay datos en caché disponibles. El entrenamiento se ejecuta diariamente a las 7:00 AM COT o use POST /train para generar."
        )


@router.post("/train/run-now")
async def trigger_training_now(
    background_tasks: BackgroundTasks,
):
    """
    Trigger training immediately and cache results.
    
    This is useful for manual refresh outside the daily schedule.
    Training runs in background but caches results when complete.
    """
    from src.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    
    # Run training in background
    background_tasks.add_task(scheduler.run_daily_orchestrated_job)
    
    return {
        "status": "started",
        "message": "Entrenamiento iniciado en segundo plano. Los resultados se guardarán al completar."
    }


@router.get("/train/status", response_model=TrainingProgressStatus)
async def get_training_status(
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Get the current status of the ML training process.
    Returns: IN_PROGRESS, COMPLETED, ERROR, or IDLE.
    If COMPLETED, includes the training result.
    """
    # Keys used in MLTrainingOrchestrator
    CACHE_KEY_STATUS = "ml_training_status"
    CACHE_KEY_MESSAGE = "ml_training_message"
    CACHE_KEY_RESULT = "ml_training_result_data"
    
    status = cache_service.get(CACHE_KEY_STATUS) or "IDLE"
    message = cache_service.get(CACHE_KEY_MESSAGE)
    result_data = None
    
    if not message:
        if status == "IDLE": message = "El bot está listo"
        elif status == "IN_PROGRESS": message = "Entrenamiento en curso"
        elif status == "COMPLETED": message = "Entrenamiento completado"
        elif status == "ERROR": message = "Error en el entrenamiento"
        else: message = f"Estado: {status}"

    if status == "COMPLETED":
        result_data = cache_service.get(CACHE_KEY_RESULT)

    return TrainingProgressStatus(
        status=status,
        message=message, 
        has_result=(result_data is not None),
        result=result_data if result_data else None
    )
