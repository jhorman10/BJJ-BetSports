from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta
import re
import logging

from src.api.dependencies import get_learning_service, get_football_data_uk, get_prediction_service, get_statistics_service, get_data_sources
from src.domain.services.learning_service import LearningService
from src.infrastructure.data_sources.football_data_uk import FootballDataUKSource
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.application.use_cases.suggested_picks_use_case import GetSuggestedPicksUseCase
from src.application.use_cases.use_cases import DataSources

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

@router.post("/train", response_model=TrainingStatus)
async def run_training_session(
    request: BacktestRequest,
    background_tasks: BackgroundTasks,
    learning_service: LearningService = Depends(get_learning_service),
    data_sources: DataSources = Depends(get_data_sources),
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
    match_history = []  # Track individual match predictions
    daily_stats = {}    # Track daily performance for ROI graph
    
    try:
        # 1. Determine leagues and fetch data
        # Default to major leagues if none specified
        leagues = request.league_ids if request.league_ids else ["E0", "SP1", "D1", "I1", "F1"]
        all_matches = []

        # Fetch historical data from multiple sources for robustness, like in prediction cards
        all_matches_map = {}
        
        # Define sources list explicitly
        sources_list = [
            data_sources.football_data_uk,
            data_sources.api_football,
            data_sources.football_data_org,
            data_sources.openfootball,
            data_sources.thesportsdb
        ]

        # Set primary data source for stats calculation (Football-Data.co.uk is best for this)
        data_source = data_sources.football_data_uk
        
        for source in sources_list:
            try:
                logger.info(f"Attempting to fetch historical data from {source.__class__.__name__}")
                for league_id in leagues:
                    matches = await source.get_historical_matches(league_id, seasons=["2223", "2324", "2425", "2526"])
                    for match in matches:
                        # Use a unique key to avoid duplicates, giving priority to earlier sources
                        match_key = (match.match_date.strftime('%Y-%m-%d'), match.home_team.name, match.away_team.name)
                        if match_key not in all_matches_map:
                            all_matches_map[match_key] = match
            except Exception as e:
                logger.warning(f"Could not fetch complete data from {source.__class__.__name__}: {e}")

        all_matches = list(all_matches_map.values())
        if not all_matches:
            raise HTTPException(status_code=404, detail="No historical match data could be fetched from any source.")
            
        # Sort by date to simulate timeline (Backtesting)
        all_matches.sort(key=lambda x: x.match_date)
        
        # Filter matches based on days_back requested
        if request.start_date:
            try:
                start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                start_date = datetime.now() - timedelta(days=request.days_back)
        else:
            start_date = datetime.now() - timedelta(days=request.days_back)
            
        completed_matches = [
            m for m in all_matches 
            if m.home_goals is not None 
            and m.away_goals is not None 
            and m.match_date >= start_date
        ]
        
        # Process all matches from the bot creation date (Dec 15, 2025) to now
        recent_matches = completed_matches
        
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
            
            # --- CALCULATE MULTIPLE PICKS FOR THIS MATCH ---
            picks_list = []
            
            # Pick 1: Resultado (1X2 - existing logic)
            suggested_pick = None
            pick_was_correct = None
            max_ev_value = None
            
            # --- 1. WINNER & DRAW (1X2) ---
            
            if match.home_odds and match.draw_odds and match.away_odds:
                # Calculate EV for 1X2 Market
                ev_home = (prediction.home_win_probability * match.home_odds) - 1
                ev_draw = (prediction.draw_probability * match.draw_odds) - 1
                ev_away = (prediction.away_win_probability * match.away_odds) - 1
                
                # Find best opportunity
                max_ev = max(ev_home, ev_draw, ev_away)
                
                # Only consider if EV is positive and significant
                if max_ev > 0.02:
                    total_bets += 1
                    stake = 1.0
                    total_staked += stake
                    
                    payout = 0.0
                    # Determine which pick was suggested
                    if ev_home == max_ev:
                        suggested_pick = f"1 ({match.home_team.name})"
                        pick_was_correct = (actual_winner == "home")
                        if actual_winner == "home":
                            payout = stake * match.home_odds
                        
                        # Add to picks list
                        picks_list.append(PickDetail(
                            market_type="winner",
                            market_label=suggested_pick,
                            was_correct=pick_was_correct,
                            probability=prediction.home_win_probability,
                            expected_value=round(max_ev * 100, 2),
                            confidence=round(prediction.home_win_probability, 3),
                            is_contrarian=(predicted_winner != "home")
                        ))
                    elif ev_away == max_ev:
                        suggested_pick = f"2 ({match.away_team.name})"
                        pick_was_correct = (actual_winner == "away")
                        if actual_winner == "away":
                            payout = stake * match.away_odds
                        
                        picks_list.append(PickDetail(
                            market_type="winner",
                            market_label=suggested_pick,
                            was_correct=pick_was_correct,
                            probability=prediction.away_win_probability,
                            expected_value=round(max_ev * 100, 2),
                            confidence=round(prediction.away_win_probability, 3),
                            is_contrarian=(predicted_winner != "away")
                        ))
                    elif ev_draw == max_ev:
                        suggested_pick = "X (Empate)"
                        pick_was_correct = (actual_winner == "draw")
                        if actual_winner == "draw":
                            payout = stake * match.draw_odds
                        
                        picks_list.append(PickDetail(
                            market_type="draw",
                            market_label=suggested_pick,
                            was_correct=pick_was_correct,
                            probability=prediction.draw_probability,
                            expected_value=round(max_ev * 100, 2),
                            confidence=round(prediction.draw_probability, 3),
                            is_contrarian=(predicted_winner != "draw")
                        ))
                    
                    max_ev_value = round(max_ev * 100, 2)
                    total_return += payout
            
                    # Track daily stats
                    date_str = match.match_date.strftime("%Y-%m-%d")
                    if date_str not in daily_stats:
                        daily_stats[date_str] = {'staked': 0.0, 'return': 0.0}
                    daily_stats[date_str]['staked'] += stake
                    daily_stats[date_str]['return'] += payout
            
            # --- 2. GOALS (Over/Under) ---
            # Calculate probability of total goals using Poisson distribution
            predicted_total = prediction.predicted_home_goals + prediction.predicted_away_goals
            actual_total = match.home_goals + match.away_goals
            
            # Simplified probabilities (using normal approximation)
            import math
            
            goal_thresholds = [0.5, 1.5, 2.5, 3.5]
            for threshold in goal_thresholds:
                # Probability of over
                prob_over = 1 / (1 + math.exp(-(predicted_total - threshold)))
                prob_under = 1 - prob_over
                
                # Assume typical over/under odds (simplified)
                # In real scenario, you'd fetch these from the data source
                over_implied_prob = 0.5  # 2.0 odds
                under_implied_prob = 0.5
                
                ev_over = prob_over - over_implied_prob
                ev_under = prob_under - under_implied_prob
                
                # Pick the better option
                if abs(ev_over) > 0.05:  # 5% edge threshold
                    is_over = ev_over > 0
                    pick_name = f"{'Over' if is_over else 'Under'} {threshold}"
                    was_correct = (actual_total > threshold) if is_over else (actual_total < threshold)
                    
                    picks_list.append(PickDetail(
                        market_type="goals_over" if is_over else "goals_under",
                        market_label=pick_name,
                        was_correct=was_correct,
                        probability=prob_over if is_over else prob_under,
                        expected_value=round(abs(max(ev_over, ev_under)) * 100, 2),
                        confidence=round(prob_over if is_over else prob_under, 3)
                    ))

            # --- 3. DOUBLE CHANCE ---
            # 1X: Home Win + Draw
            prob_1x = prediction.home_win_probability + prediction.draw_probability
            if prob_1x > 0.75:
                was_correct_1x = actual_winner in ["home", "draw"]
                picks_list.append(PickDetail(
                    market_type="double_chance",
                    market_label=f"1X ({match.home_team.name} o Empate)",
                    was_correct=was_correct_1x,
                    probability=prob_1x,
                    expected_value=0.0, # EV calculation omitted for simplicity
                    confidence=round(prob_1x, 3)
                ))

            # X2: Away Win + Draw
            prob_x2 = prediction.away_win_probability + prediction.draw_probability
            if prob_x2 > 0.75:
                was_correct_x2 = actual_winner in ["away", "draw"]
                picks_list.append(PickDetail(
                    market_type="double_chance",
                    market_label=f"X2 ({match.away_team.name} o Empate)",
                    was_correct=was_correct_x2,
                    probability=prob_x2,
                    expected_value=0.0,
                    confidence=round(prob_x2, 3)
                ))

            # --- 4. CORNERS (Over/Under) ---
            # Check if corner data is available (HC = Home Corners, AC = Away Corners)
            if hasattr(match, 'home_corners') and hasattr(match, 'away_corners') and \
               match.home_corners is not None and match.away_corners is not None:
                # Simple projection based on team averages if available, otherwise skip
                # Using stats from data_source calculation
                avg_home_corners = getattr(home_stats, 'avg_corners_per_match', 5.0)
                avg_away_corners = getattr(away_stats, 'avg_corners_per_match', 4.5)
                predicted_corners = avg_home_corners + avg_away_corners
                actual_corners = match.home_corners + match.away_corners
                
                # Line: 9.5
                if predicted_corners > 9.5:
                    picks_list.append(PickDetail(
                        market_type="corners_over",
                        market_label="Más de 9.5 Córners",
                        was_correct=actual_corners > 9.5,
                        probability=0.65, # Estimated
                        expected_value=0.0,
                        confidence=0.65
                    ))
                elif predicted_corners < 8.0:
                    picks_list.append(PickDetail(
                        market_type="corners_under",
                        market_label="Menos de 10.5 Córners",
                        was_correct=actual_corners < 10.5,
                        probability=0.60,
                        expected_value=0.0,
                        confidence=0.60
                    ))

            # --- 5. CARDS (Over/Under) ---
            if hasattr(match, 'home_yellow_cards') and match.home_yellow_cards is not None and \
               hasattr(match, 'away_yellow_cards') and match.away_yellow_cards is not None:
                avg_home_cards = getattr(home_stats, 'avg_yellow_cards_per_match', 2.0)
                avg_away_cards = getattr(away_stats, 'avg_yellow_cards_per_match', 2.0)
                predicted_cards = avg_home_cards + avg_away_cards
                
                home_red = match.home_red_cards if match.home_red_cards is not None else 0
                away_red = match.away_red_cards if match.away_red_cards is not None else 0
                actual_cards = match.home_yellow_cards + match.away_yellow_cards + home_red + away_red
                
                # Line: 4.5
                if predicted_cards > 4.0:
                    picks_list.append(PickDetail(
                        market_type="cards_over",
                        market_label="Más de 4.5 Tarjetas",
                        was_correct=actual_cards > 4.5,
                        probability=0.60,
                        expected_value=0.0,
                        confidence=0.60
                    ))

            # --- 6. RED CARDS ---
            if hasattr(match, 'home_red_cards') and match.home_red_cards is not None and \
               hasattr(match, 'away_red_cards') and match.away_red_cards is not None:
                # Only suggest "Red Card" if aggressive teams
                if getattr(home_stats, 'avg_red_cards_per_match', 0) > 0.2 or getattr(away_stats, 'avg_red_cards_per_match', 0) > 0.2:
                     has_red_card = (match.home_red_cards > 0 or match.away_red_cards > 0)
                     picks_list.append(PickDetail(
                        market_type="red_cards",
                        market_label="Tarjeta Roja en el partido",
                        was_correct=has_red_card,
                        probability=0.30,
                        expected_value=0.0,
                        confidence=0.30
                    ))
            
            # --- 8. BOTH TEAMS TO SCORE (BTTS / Ambos Marcan) ---
            # Calculate probability using Poisson: P(Goals > 0) = 1 - P(Goals = 0)
            prob_home_score = 1 - math.exp(-prediction.predicted_home_goals)
            prob_away_score = 1 - math.exp(-prediction.predicted_away_goals)
            prob_btts_yes = prob_home_score * prob_away_score
            prob_btts_no = 1 - prob_btts_yes
            
            actual_btts = (match.home_goals > 0 and match.away_goals > 0)
            
            if prob_btts_yes > 0.60:
                 picks_list.append(PickDetail(
                    market_type="btts_yes",
                    market_label="Ambos Marcan: Sí",
                    was_correct=actual_btts,
                    probability=prob_btts_yes,
                    expected_value=0.0,
                    confidence=round(prob_btts_yes, 2)
                ))
            elif prob_btts_no > 0.60:
                 picks_list.append(PickDetail(
                    market_type="btts_no",
                    market_label="Ambos Marcan: No",
                    was_correct=not actual_btts,
                    probability=prob_btts_no,
                    expected_value=0.0,
                    confidence=round(prob_btts_no, 2)
                ))

            # --- 9. TEAM CORNERS (Córners por Equipo) ---
            if hasattr(match, 'home_corners') and match.home_corners is not None:
                avg_home_corners = getattr(home_stats, 'avg_corners_per_match', 5.0)
                # Threshold: Home usually gets more corners, set line at 5.5
                if avg_home_corners > 6.0:
                    picks_list.append(PickDetail(
                        market_type="home_corners_over",
                        market_label=f"Córners {match.home_team.name}: +5.5",
                        was_correct=match.home_corners > 5.5,
                        probability=0.65,
                        expected_value=0.0,
                        confidence=0.65
                    ))
            
            if hasattr(match, 'away_corners') and match.away_corners is not None:
                avg_away_corners = getattr(away_stats, 'avg_corners_per_match', 4.0)
                if avg_away_corners > 4.5:
                    picks_list.append(PickDetail(
                        market_type="away_corners_over",
                        market_label=f"Córners {match.away_team.name}: +4.5",
                        was_correct=match.away_corners > 4.5,
                        probability=0.60,
                        expected_value=0.0,
                        confidence=0.60
                    ))

            # --- 10. TEAM YELLOW CARDS (Amarillas por Equipo) ---
            if hasattr(match, 'home_yellow_cards') and match.home_yellow_cards is not None:
                avg_home_yellows = getattr(home_stats, 'avg_yellow_cards_per_match', 2.0)
                if avg_home_yellows > 2.5:
                     picks_list.append(PickDetail(
                        market_type="home_cards_over",
                        market_label=f"Amarillas {match.home_team.name}: +2.5",
                        was_correct=match.home_yellow_cards > 2.5,
                        probability=0.60,
                        expected_value=0.0,
                        confidence=0.60
                    ))
            
            if hasattr(match, 'away_yellow_cards') and match.away_yellow_cards is not None:
                avg_away_yellows = getattr(away_stats, 'avg_yellow_cards_per_match', 2.0)
                if avg_away_yellows > 2.5:
                     picks_list.append(PickDetail(
                        market_type="away_cards_over",
                        market_label=f"Amarillas {match.away_team.name}: +2.5",
                        was_correct=match.away_yellow_cards > 2.5,
                        probability=0.60,
                        expected_value=0.0,
                        confidence=0.60
                    ))

            # --- 7. VA HANDICAP ---
            # Simple Asian Handicap approximation based on goal difference
            goal_diff = prediction.predicted_home_goals - prediction.predicted_away_goals
            if abs(goal_diff) > 1.5:
                is_home_fav = goal_diff > 0
                fav_team = match.home_team.name if is_home_fav else match.away_team.name
                pick_label = f"{fav_team} -1.5 (Handicap)"
                
                actual_diff = match.home_goals - match.away_goals
                was_correct_handicap = (actual_diff > 1.5) if is_home_fav else (actual_diff < -1.5)
                
                picks_list.append(PickDetail(
                    market_type="va_handicap",
                    market_label=pick_label,
                    was_correct=was_correct_handicap,
                    probability=0.55,
                    expected_value=0.0,
                    confidence=0.55
                ))
            
            # Logic to ensure suggested_pick is populated if we have picks but no 1X2 pick
            if suggested_pick is None and picks_list:
                # Find pick with highest EV
                best_pick = max(picks_list, key=lambda p: p.expected_value if p.expected_value is not None else 0)
                if best_pick.expected_value > 0:
                    suggested_pick = best_pick.market_label
                    pick_was_correct = best_pick.was_correct
                    max_ev_value = best_pick.expected_value

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
        # Log the full error for debugging
        import traceback
        print(f"Training error: {e}")
        traceback.print_exc()
        raise  # Re-raise to let FastAPI handle it
    
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
