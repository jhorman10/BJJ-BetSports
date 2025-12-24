from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import math
import re
import logging

from src.api.dependencies import get_learning_service, get_football_data_uk, get_prediction_service, get_statistics_service, get_data_sources
from src.domain.services.learning_service import LearningService
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.picks_service import PicksService
from src.domain.entities.suggested_pick import SuggestedPick
from src.domain.entities.entities import Match
from src.application.use_cases.use_cases import DataSources
from src.domain.entities.entities import TeamStatistics

logger = logging.getLogger(__name__)

router = APIRouter()

class BacktestRequest(BaseModel):
    league_ids: Optional[List[str]] = None
    days_back: int = 365
    start_date: Optional[str] = None
    reset_weights: bool = False

class PickDetail(BaseModel):
    """Individual pick/event prediction within a match."""
    market_type: str  # "winner", "corners_over", "goals_over", etc.
    market_label: str  # "Real Madrid gana", "Over 9.5 Corners", etc.
    was_correct: bool
    probability: float  # 0-1
    expected_value: float
    confidence: float
    is_contrarian: bool = False  # True if pick differs from main prediction (Value Bet)

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

def _verify_pick(pick: SuggestedPick, match: Match) -> PickDetail:
    """Compare a suggested pick against the actual match result."""
    actual_val = 0.0
    threshold = 0.0
    was_correct = False
    
    # Extract threshold from label logic (simplified for backtesting)
    try:
        if "Más de" in pick.market_label or "Menos de" in pick.market_label:
            threshold = float(re.findall(r"[-+]?\d*\.\d+|\d+", pick.market_label)[0])
    except:
        pass

    if pick.market_type == "winner" or pick.market_type == "draw":
         # Winner validation
        actual_winner = "draw"
        if match.home_goals > match.away_goals: actual_winner = "1" # Home
        elif match.away_goals > match.home_goals: actual_winner = "2" # Away
        else: actual_winner = "X"
        
        # Parse pick label to get predicted outcome
        predicted = "X"
        if "(1)" in pick.market_label: predicted = "1"
        if "(2)" in pick.market_label: predicted = "2"
        
        was_correct = (actual_winner == predicted)

    elif pick.market_type == "corners_over":
        actual = (match.home_corners or 0) + (match.away_corners or 0)
        was_correct = actual > threshold
    elif pick.market_type == "corners_under":
        actual = (match.home_corners or 0) + (match.away_corners or 0)
        was_correct = actual < threshold
    elif pick.market_type == "cards_over":
        # Simplified card counting
        actual = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
        was_correct = actual > threshold
    elif pick.market_type == "cards_under":
        actual = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
        was_correct = actual < threshold
    elif pick.market_type == "goals_over":
        actual = (match.home_goals or 0) + (match.away_goals or 0)
        was_correct = actual > threshold
    elif pick.market_type == "goals_under":
        actual = (match.home_goals or 0) + (match.away_goals or 0)
        was_correct = actual < threshold
    elif pick.market_type == "btts_yes":
        was_correct = (match.home_goals > 0 and match.away_goals > 0)
    elif pick.market_type == "btts_no":
        was_correct = not (match.home_goals > 0 and match.away_goals > 0)
    elif pick.market_type == "va_handicap":
        # Simple handicap validation logic for backtest
        # Needs parsing specific handicap value
        was_correct = pick.probability > 0.5 # Placeholder for complex logic, assuming high prob means likely correct in backtest 'simulation' if we trust model?? 
        # Actually better to approximate:
        pass # Allow complex validation if needed, for now trust the 'was_correct' if we can determine it easily.
        # Check logic in generate: if it was generated based on stats, we check stats
        pass 
        
    # Generic fallback
    if pick.market_type not in ["winner", "draw"]:
         # Re-evaluate just in case? Or trust the generation context?
         # Since we don't have the 'actual' result embedded in the pick, we MUST evaluate it here.
         # But the specific evaluation logic is complex for all types.
         # For the purpose of DRY, we can accept that we might need a shared 'ValidatorService' later.
         pass

    return PickDetail(
        market_type=pick.market_type.value,
        market_label=pick.market_label,
        was_correct=was_correct, # Logic to be refined
        probability=pick.probability,
        expected_value=pick.expected_value,
        confidence=float(pick.probability), # Map properly
        is_contrarian=False
    )

def _determine_winner_code(match):
    if match.home_goals > match.away_goals: return "home"
    if match.away_goals > match.home_goals: return "away"
    return "draw"

def _get_or_create_team_stats(team_name: str, stats_cache: dict) -> dict:
    if team_name not in stats_cache:
        stats_cache[team_name] = {
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_scored": 0,
            "goals_conceded": 0,
            "corners_for": 0,
            "corners_against": 0,
            "yellow_cards": 0,
            "red_cards": 0,
            # Form tracking (last 5) could be added here with a deque
        }
    return stats_cache[team_name]

def _update_team_stats(team_name: str, stats_cache: dict, match: Match, is_home: bool):
    stats = _get_or_create_team_stats(team_name, stats_cache)
    
    goals_for = match.home_goals if is_home else match.away_goals
    goals_against = match.away_goals if is_home else match.home_goals
    
    stats["matches_played"] += 1
    stats["goals_scored"] += goals_for
    stats["goals_conceded"] += goals_against
    
    if goals_for > goals_against:
        stats["wins"] += 1
    elif goals_for == goals_against:
        stats["draws"] += 1
    else:
        stats["losses"] += 1
        
    # Update props if available
    if match.home_corners is not None and match.away_corners is not None:
        stats["corners_for"] += match.home_corners if is_home else match.away_corners
        stats["corners_against"] += match.away_corners if is_home else match.home_corners
        
    if match.home_yellow_cards is not None:
        stats["yellow_cards"] += match.home_yellow_cards if is_home else match.away_yellow_cards
        
    if match.home_red_cards is not None:
        stats["red_cards"] += match.home_red_cards if is_home else match.away_red_cards

def _convert_to_domain_stats(team_name: str, raw_stats: dict) -> TeamStatistics:
    """Convert raw dict stats to domain entity."""
    mp = raw_stats["matches_played"]
    if mp == 0:
        return TeamStatistics(
            team_id=team_name.lower().replace(" ", "_"),
            matches_played=0,
            wins=0,
            draws=0,
            losses=0,
            goals_scored=0,
            goals_conceded=0,
            home_wins=0,
            away_wins=0,
            total_corners=0,
            total_yellow_cards=0,
            total_red_cards=0,
            recent_form=""
        )
        
    return TeamStatistics(
        team_id=team_name.lower().replace(" ", "_"),
        matches_played=mp,
        wins=raw_stats.get("wins", 0),
        draws=raw_stats.get("draws", 0),
        losses=raw_stats.get("losses", 0),
        goals_scored=raw_stats["goals_scored"],
        goals_conceded=raw_stats["goals_conceded"],
        home_wins=raw_stats.get("home_wins", 0),
        away_wins=raw_stats.get("away_wins", 0),
        total_corners=raw_stats.get("corners_for", 0),
        total_yellow_cards=raw_stats.get("yellow_cards", 0),
        total_red_cards=raw_stats.get("red_cards", 0),
        recent_form=raw_stats.get("recent_form", "")
    )

def _validate_pick(pick: SuggestedPick, match: Match, actual_winner: str) -> tuple[Optional[PickDetail], float]:
    """
    Validate a pick against match results and return details + payout.
    Returns (PickDetail, payout). Payout is 0.0 if lost or not a betting market.
    """
    payout = 0.0
    
    # Determine if it was a value bet based on expected value
    is_value_bet = pick.expected_value > 0.0
    
    # 1. 1X2 Market
    if pick.market_type.value in ["winner", "draw"]:
        if pick.expected_value <= 0.02:
            return None, 0.0
            
        is_won = False
        # Determine predicted side
        if "wins" in pick.market_label.lower() or "Victoria" in pick.market_label or "(1)" in pick.market_label or "(2)" in pick.market_label:
            predicted_side = "home" if match.home_team.name in pick.market_label or "(1)" in pick.market_label else "away"
            is_won = (actual_winner == predicted_side)
            if is_won:
                odds = match.home_odds if predicted_side == "home" else match.away_odds
                payout = odds if odds else 0.0
        elif "Empate" in pick.market_label:
            is_won = (actual_winner == "draw")
            if is_won:
                payout = match.draw_odds if match.draw_odds else 0.0
        
        return PickDetail(
            market_type="winner", # Unifying 1x2 as 'winner' for history table
            market_label=pick.market_label,
            was_correct=is_won,
            probability=pick.probability,
            expected_value=pick.expected_value * 100,
            confidence=float(0.8 if pick.confidence_level.value == "high" else 0.6),
            is_contrarian=is_value_bet
        ), payout

    # 2. Props Markets (Corners/Cards/Goals)
    is_won = False
    threshold = 0.0
    
    # Extract threshold
    threshold_match = re.search(r"(?:Más|Menos) de (\d+\.?\d*)", pick.market_label)
    if threshold_match:
        threshold = float(threshold_match.group(1))
    else:
        # Fallback or skip if no threshold found for these markets
        return None, 0.0

    if pick.market_type.value == "corners_over":
        if match.home_corners is None or match.away_corners is None: return None, 0.0
        is_won = (match.home_corners + match.away_corners) > threshold
        
    elif pick.market_type.value == "corners_under":
        if match.home_corners is None or match.away_corners is None: return None, 0.0
        is_won = (match.home_corners + match.away_corners) < threshold
        
    elif pick.market_type.value == "cards_over":
        if match.home_yellow_cards is None or match.away_yellow_cards is None: return None, 0.0
        total_cards = (match.home_yellow_cards + match.away_yellow_cards + 
                      (match.home_red_cards or 0) + (match.away_red_cards or 0))
        is_won = total_cards > threshold
        
    elif pick.market_type.value == "cards_under":
        if match.home_yellow_cards is None or match.away_yellow_cards is None: return None, 0.0
        total_cards = (match.home_yellow_cards + match.away_yellow_cards + 
                      (match.home_red_cards or 0) + (match.away_red_cards or 0))
        is_won = total_cards < threshold
        
    elif pick.market_type.value == "goals_over":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals + match.away_goals) > threshold

    elif pick.market_type.value == "goals_under":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals + match.away_goals) < threshold

    elif pick.market_type.value == "btts_yes":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals > 0 and match.away_goals > 0)

    elif pick.market_type.value == "btts_no":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = not (match.home_goals > 0 and match.away_goals > 0)

    elif pick.market_type.value == "red_cards":
        if match.home_red_cards is None or match.away_red_cards is None: return None, 0.0
        is_won = (match.home_red_cards > 0 or match.away_red_cards > 0)

    elif pick.market_type.value == "home_corners_over":
        if match.home_corners is None: return None, 0.0
        is_won = match.home_corners > threshold

    elif pick.market_type.value == "away_corners_over":
        if match.away_corners is None: return None, 0.0
        is_won = match.away_corners > threshold

    elif pick.market_type.value == "home_cards_over":
        if match.home_yellow_cards is None: return None, 0.0
        # Assuming threshold is for yellow cards primarily based on picks_service logic
        is_won = match.home_yellow_cards > threshold

    elif pick.market_type.value == "away_cards_over":
        if match.away_yellow_cards is None: return None, 0.0
        is_won = match.away_yellow_cards > threshold

    elif pick.market_type.value == "va_handicap":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        # Extract handicap value and team from label
        # Format: "Hándicap Asiático +0.5 - TeamName" or "-1.5"
        try:
            handicap_val = float(re.findall(r"[-+]?\d*\.\d+|\d+", pick.market_label)[0])
            # Determine if handicap is for home or away based on label text matching team name
            is_home_handicap = match.home_team.name.split()[0] in pick.market_label
            
            score_diff = match.home_goals - match.away_goals if is_home_handicap else match.away_goals - match.home_goals
            is_won = (score_diff + handicap_val) > 0
        except:
            return None, 0.0

    else:
        return None, 0.0

    return PickDetail(
        market_type=pick.market_type.value,
        market_label=pick.market_label,
        was_correct=is_won,
        probability=pick.probability,
        expected_value=pick.expected_value * 100,
        confidence=float(0.8 if pick.confidence_level.value == "high" else 0.6),
        is_contrarian=is_value_bet
    ), 0.0

@router.post("/train", response_model=TrainingStatus)
async def run_training_session(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    learning_service: LearningService = Depends(get_learning_service),
    data_sources: DataSources = Depends(get_data_sources),
    prediction_service: PredictionService = Depends(get_prediction_service),
    statistics_service: StatisticsService = Depends(get_statistics_service)
):
    """
    Trigger a backtesting session to train the model on historical data.
    """
    if request.reset_weights:
        learning_service.reset_weights()

    # Initialize PicksService
    picks_service_instance = PicksService(learning_weights=learning_service.get_learning_weights())
    
    matches_processed = 0
    correct_predictions = 0
    total_bets = 0
    total_staked = 0.0
    total_return = 0.0
    daily_stats = {}
    match_history = []

    # Fetch matches
    leagues = request.league_ids if request.league_ids else ["E0", "SP1", "D1", "I1", "F1"]
    all_matches = []
    
    for league_id in leagues:
        # Fetch last 2 seasons
        matches = await data_sources.football_data_uk.get_historical_matches(league_id, seasons=["2324", "2425"])
        all_matches.extend(matches)
            
    # Sort by date
    all_matches.sort(key=lambda x: x.match_date)
    
    # Filter by start date if provided
    if request.start_date:
        # Handle simple date string YYYY-MM-DD
        try:
            start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
            all_matches = [m for m in all_matches if m.match_date >= start_dt]
        except ValueError:
            pass
    elif request.days_back:
        start_dt = datetime.utcnow() - timedelta(days=request.days_back)
        all_matches = [m for m in all_matches if m.match_date >= start_dt]

    # Process matches
    # We need to maintain a history of processed matches to calculate stats "as of that date"
    # OPTIMIZATION: Use incremental stats cache instead of reprocessing history list
    team_stats_cache = {}

    for match in all_matches:
        if match.home_goals is None or match.away_goals is None:
            continue

        # 1. Get current stats from cache (O(1))
        raw_home_stats = _get_or_create_team_stats(match.home_team.name, team_stats_cache)
        raw_away_stats = _get_or_create_team_stats(match.away_team.name, team_stats_cache)
        
        # Convert to domain entities for the service
        home_stats = _convert_to_domain_stats(match.home_team.name, raw_home_stats)
        away_stats = _convert_to_domain_stats(match.away_team.name, raw_away_stats)
        
        # League averages (simplified for backtest)
        league_averages = None 

        # 4. Generate Prediction
        try:
            prediction = prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages
            )
            
            # Learning service doesn't need updating during backtesting
            # (it learns from user feedback via register_feedback)
            matches_processed += 1
            
            # Determine actual/predicted winner
            actual_winner = _determine_winner_code(match)
            predicted_winner = "draw"
            if prediction.home_win_probability > prediction.away_win_probability and prediction.home_win_probability > prediction.draw_probability:
                predicted_winner = "home"
            elif prediction.away_win_probability > prediction.home_win_probability and prediction.away_win_probability > prediction.draw_probability:
                predicted_winner = "away"
                
            if actual_winner == predicted_winner:
                correct_predictions += 1
            
            # --- GENERATE PICKS USING DOMAIN SERVICE ---
            # Use the single source of truth for picks logic
            suggested_picks_container = picks_service_instance.generate_suggested_picks(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages,
                predicted_home_goals=prediction.predicted_home_goals,
                predicted_away_goals=prediction.predicted_away_goals,
                home_win_prob=prediction.home_win_probability,
                draw_prob=prediction.draw_probability,
                away_win_prob=prediction.away_win_probability
            )

            # Convert to local backtest structure and verify result
            picks_list = []
            suggested_pick = None
            pick_was_correct = None
            max_ev_value = None
            
            for pick in suggested_picks_container.suggested_picks:
                pick_detail, payout = _validate_pick(pick, match, actual_winner)
                
                if pick_detail:
                    picks_list.append(pick_detail)
                    
                    # Track 1X2 bets for ROI
                    if pick_detail.market_type == "winner":
                        total_bets += 1
                        total_staked += 1.0
                        total_return += payout
                        
                        if pick.expected_value > (max_ev_value or -1):
                             suggested_pick = pick.market_label
                             pick_was_correct = pick_detail.was_correct
                             max_ev_value = pick.expected_value

            # Store match prediction with picks
            match_history.append(MatchPredictionHistory(
                match_id=match.id,
                home_team=match.home_team.name,
                away_team=match.away_team.name,
                match_date=match.match_date.isoformat(),
                predicted_winner=predicted_winner,
                actual_winner=actual_winner,
                predicted_home_goals=round(prediction.predicted_home_goals, 2),
                predicted_away_goals=round(prediction.predicted_away_goals, 2),
                actual_home_goals=match.home_goals,
                actual_away_goals=match.away_goals,
                was_correct=(actual_winner == predicted_winner),
                confidence=round(prediction.confidence, 3),
                picks=picks_list,  # New: multiple picks
                suggested_pick=suggested_pick,  # Legacy support
                pick_was_correct=pick_was_correct,
                expected_value=max_ev_value
            ))
            
        except Exception as e:
            logger.error(f"Error processing match {match.id}: {e}")
            continue

        # 5. Update stats incrementally for next iteration (O(1))
        _update_team_stats(match.home_team.name, team_stats_cache, match, is_home=True)
        _update_team_stats(match.away_team.name, team_stats_cache, match, is_home=False)
    
    accuracy = correct_predictions / matches_processed if matches_processed > 0 else 0.0
    profit = total_return - total_staked
    roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
    
    # Calculate ROI evolution
    roi_evolution = []
    cum_staked = 0.0
    cum_return = 0.0
    
    for date_str in sorted(daily_stats.keys()):
        stats = daily_stats[date_str]
        cum_staked += stats['staked']
        cum_return += stats['return']
        
        current_profit = cum_return - cum_staked
        current_roi = (current_profit / cum_staked * 100) if cum_staked > 0 else 0.0
        
        roi_evolution.append(RoiEvolutionPoint(
            date=date_str,
            roi=round(current_roi, 2),
            profit=round(current_profit, 2)
        ))
    
    # Reverse history to show newest matches first
    match_history.reverse()
    
    return TrainingStatus(
        matches_processed=matches_processed,
        correct_predictions=correct_predictions,
        accuracy=round(accuracy, 4),
        total_bets=total_bets,
        roi=round(roi, 2),
        profit_units=round(profit, 2),
        market_stats=learning_service.get_all_stats(),
        match_history=match_history,
        roi_evolution=roi_evolution
    )
