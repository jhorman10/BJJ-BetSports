from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from src.api.dependencies import get_learning_service, get_football_data_uk, get_prediction_service
from src.domain.services.learning_service import LearningService
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.domain.services.prediction_service import PredictionService

router = APIRouter()

class BacktestRequest(BaseModel):
    league_ids: Optional[List[str]] = None
    days_back: int = 365
    reset_weights: bool = False

class TrainingStatus(BaseModel):
    matches_processed: int
    correct_predictions: int
    accuracy: float
    total_bets: int
    roi: float
    profit_units: float
    market_stats: dict

@router.post("/train", response_model=TrainingStatus)
async def run_training_session(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    learning_service: LearningService = Depends(get_learning_service),
    data_source: FootballDataUKSource = Depends(get_football_data_uk),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    """
    Trigger a backtesting session to train the model on historical data.
    """
    if request.reset_weights:
        learning_service.reset_weights()
    
    # PROFITABILITY FIX: Real implementation of backtesting loop
    # This iterates through historical data to calibrate the model
    
    matches_processed = 0
    correct_predictions = 0
    total_bets = 0
    total_staked = 0.0
    total_return = 0.0
    
    try:
        # 1. Determine leagues and fetch data
        # Default to major leagues if none specified
        leagues = request.league_ids if request.league_ids else ["E0", "SP1", "D1", "I1", "F1"]
        all_matches = []
        
        # Fetch last 2 seasons to ensure we have enough history for stats
        for league_id in leagues:
            matches = await data_source.get_historical_matches(league_id, seasons=["2324", "2425"])
            all_matches.extend(matches)
            
        # Sort by date to simulate timeline (Backtesting)
        all_matches.sort(key=lambda x: x.match_date)
        
        # Process only completed matches (with results)
        completed_matches = [m for m in all_matches if m.home_goals is not None and m.away_goals is not None]
        
        # Limit processing based on days_back (but process recent matches first)
        # Take the LAST N matches based on days_back approximation
        max_matches_to_process = min(len(completed_matches), request.days_back // 3)  # ~3 matches per day approx
        recent_matches = completed_matches[-max_matches_to_process:] if max_matches_to_process > 0 else completed_matches
        
        for i, match in enumerate(recent_matches):
            # 2. Calculate stats using ONLY past matches (to avoid look-ahead bias)
            # We slice the sorted list up to the current match
            past_matches = all_matches[:all_matches.index(match)]
            
            home_stats = data_source.calculate_team_statistics(match.home_team.name, past_matches)
            away_stats = data_source.calculate_team_statistics(match.away_team.name, past_matches)
            
            # Skip if insufficient history for these teams
            if home_stats.matches_played < 5 or away_stats.matches_played < 5:
                continue
                
            # 3. Calculate League Averages from past matches in the same league
            league_past = [m for m in past_matches if m.league.id == match.league.id]
            if len(league_past) < 10:
                continue
                
            avg_home = sum(m.home_goals for m in league_past if m.home_goals is not None) / len(league_past)
            avg_away = sum(m.away_goals for m in league_past if m.away_goals is not None) / len(league_past)
            
            from src.domain.value_objects.value_objects import LeagueAverages
            league_averages = LeagueAverages(
                avg_home_goals=avg_home,
                avg_away_goals=avg_away,
                avg_total_goals=avg_home + avg_away
            )
            
            # 4. Generate Prediction
            prediction = prediction_service.generate_prediction(
                match=match,
                home_stats=home_stats,
                away_stats=away_stats,
                league_averages=league_averages
            )
            
            # Learning service doesn't need updating during backtesting
            # (it learns from user feedback via register_feedback)
            matches_processed += 1
            
            # Track accuracy (Winner)
            actual_winner = "draw"
            if match.home_goals > match.away_goals:
                actual_winner = "home"
            elif match.away_goals > match.home_goals:
                actual_winner = "away"
                
            predicted_winner = "draw"
            if prediction.home_win_probability > prediction.away_win_probability and prediction.home_win_probability > prediction.draw_probability:
                predicted_winner = "home"
            elif prediction.away_win_probability > prediction.home_win_probability and prediction.away_win_probability > prediction.draw_probability:
                predicted_winner = "away"
                
            if actual_winner == predicted_winner:
                correct_predictions += 1
            
            # --- ROI CALCULATION (Real Viability Test) ---
            # Simulate betting 1 unit on Value Bets (EV > 2%)
            if match.home_odds and match.draw_odds and match.away_odds:
                # Calculate EV for 1X2 Market
                ev_home = (prediction.home_win_probability * match.home_odds) - 1
                ev_draw = (prediction.draw_probability * match.draw_odds) - 1
                ev_away = (prediction.away_win_probability * match.away_odds) - 1
                
                # Find best opportunity
                max_ev = max(ev_home, ev_draw, ev_away)
                
                # Only bet if EV is positive and significant
                if max_ev > 0.02:
                    total_bets += 1
                    stake = 1.0  # Flat betting simulation
                    total_staked += stake
                    
                    payout = 0.0
                    if ev_home == max_ev and actual_winner == "home":
                        payout = stake * match.home_odds
                    elif ev_away == max_ev and actual_winner == "away":
                        payout = stake * match.away_odds
                    elif ev_draw == max_ev and actual_winner == "draw":
                        payout = stake * match.draw_odds
                    
                    total_return += payout
            
    except Exception as e:
        # Log the full error for debugging
        import traceback
        print(f"Training error: {e}")
        traceback.print_exc()
        raise  # Re-raise to let FastAPI handle it
    
    accuracy = correct_predictions / matches_processed if matches_processed > 0 else 0.0
    profit = total_return - total_staked
    roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
    
    return TrainingStatus(
        matches_processed=matches_processed,
        correct_predictions=correct_predictions,
        accuracy=round(accuracy, 4),
        total_bets=total_bets,
        roi=round(roi, 2),
        profit_units=round(profit, 2),
        market_stats=learning_service.get_all_stats()
    )
