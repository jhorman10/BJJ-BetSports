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
from src.utils.time_utils import get_current_time

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
    
    # Get the string value from Enum
    market_type_str = pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type)

    if market_type_str == "winner" or market_type_str == "draw":
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

    elif market_type_str == "corners_over":
        actual = (match.home_corners or 0) + (match.away_corners or 0)
        was_correct = actual > threshold
    elif market_type_str == "corners_under":
        actual = (match.home_corners or 0) + (match.away_corners or 0)
        was_correct = actual < threshold
    elif market_type_str == "cards_over":
        # Simplified card counting
        actual = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
        was_correct = actual > threshold
    elif market_type_str == "cards_under":
        actual = (match.home_yellow_cards or 0) + (match.away_yellow_cards or 0)
        was_correct = actual < threshold
    elif market_type_str == "goals_over" or "goals_over" in market_type_str:
        actual = (match.home_goals or 0) + (match.away_goals or 0)
        was_correct = actual > threshold
    elif market_type_str == "goals_under" or "goals_under" in market_type_str:
        actual = (match.home_goals or 0) + (match.away_goals or 0)
        was_correct = actual < threshold
    elif market_type_str == "btts_yes":
        was_correct = (match.home_goals > 0 and match.away_goals > 0)
    elif market_type_str == "btts_no":
        was_correct = not (match.home_goals > 0 and match.away_goals > 0)
    elif market_type_str == "va_handicap":
        # Simple handicap validation logic for backtest
        # Needs parsing specific handicap value
        was_correct = pick.probability > 0.5 # Placeholder for complex logic, assuming high prob means likely correct in backtest 'simulation' if we trust model?? 
        # Actually better to approximate:
        pass # Allow complex validation if needed, for now trust the 'was_correct' if we can determine it easily.
        # Check logic in generate: if it was generated based on stats, we check stats
        pass 
        
    # Generic fallback
    if market_type_str not in ["winner", "draw"]:
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
    
    market_type_val = pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type)
    
    # 1. 1X2 Market
    if market_type_val in ["winner", "draw", "result_1x2"]:
        # Show all result picks in history (removed EV filter)
        is_won = False
        # Determine predicted side
        if "wins" in pick.market_label.lower() or "Victoria" in pick.market_label or "(1)" in pick.market_label or "(2)" in pick.market_label:
            predicted_side = "home" if match.home_team.name in pick.market_label or "(1)" in pick.market_label else "away"
            is_won = (actual_winner == predicted_side)
            if is_won:
                odds = match.home_odds if predicted_side == "home" else match.away_odds
                payout = odds if odds else 0.0
        elif "Empate" in pick.market_label or "(X)" in pick.market_label:
            is_won = (actual_winner == "draw")
            if is_won:
                payout = match.draw_odds if match.draw_odds else 0.0
        
        return PickDetail(
            market_type="winner",
            market_label=pick.market_label,
            was_correct=is_won,
            probability=pick.probability,
            expected_value=pick.expected_value * 100,
            confidence=float(pick.probability),
            is_contrarian=is_value_bet
        ), payout

    # 2. Double Chance
    if market_type_val.startswith("double_chance"):
        is_won = False
        if market_type_val == "double_chance_1x":
            is_won = actual_winner in ["home", "draw"]
        elif market_type_val == "double_chance_x2":
            is_won = actual_winner in ["away", "draw"]
        elif market_type_val == "double_chance_12":
            is_won = actual_winner in ["home", "away"]
            
        return PickDetail(
            market_type=market_type_val,
            market_label=pick.market_label,
            was_correct=is_won,
            probability=pick.probability,
            expected_value=pick.expected_value * 100,
            confidence=float(pick.probability),
            is_contrarian=is_value_bet
        ), 0.0

    # 3. Props Markets (Corners/Cards/Goals)
    is_won = False
    threshold = 0.0
    
    # Extract threshold
    # Also handle labels like "+2.5 goles" or "Over 2.5"
    threshold_match = re.search(r"((?:\+|-)?\d+\.?\d*)", pick.market_label)
    if threshold_match:
        threshold = float(threshold_match.group(1).replace("+", ""))
    else:
        # Special case for BTTS or Red Cards which don't have numeric thresholds in label
        pass

    # Goals (Unified handling)
    if market_type_val.startswith("goals_over") or market_type_val == "goals_over":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals + match.away_goals) > threshold
    elif market_type_val.startswith("goals_under") or market_type_val == "goals_under":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals + match.away_goals) < threshold
        
    # Corners (Unified handling)
    elif market_type_val == "corners_over":
        if match.home_corners is None or match.away_corners is None: return None, 0.0
        is_won = (match.home_corners + match.away_corners) > threshold
    elif market_type_val == "corners_under":
        if match.home_corners is None or match.away_corners is None: return None, 0.0
        is_won = (match.home_corners + match.away_corners) < threshold
        
    # Cards (Unified handling)
    elif market_type_val == "cards_over":
        if match.home_yellow_cards is None or match.away_yellow_cards is None: return None, 0.0
        total_cards = (match.home_yellow_cards + match.away_yellow_cards + 
                      (match.home_red_cards or 0) + (match.away_red_cards or 0))
        is_won = total_cards > threshold
    elif market_type_val == "cards_under":
        if match.home_yellow_cards is None or match.away_yellow_cards is None: return None, 0.0
        total_cards = (match.home_yellow_cards + match.away_yellow_cards + 
                      (match.home_red_cards or 0) + (match.away_red_cards or 0))
        is_won = total_cards < threshold
        
    # BTTS
    elif market_type_val == "btts_yes":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = (match.home_goals > 0 and match.away_goals > 0)
    elif market_type_val == "btts_no":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        is_won = not (match.home_goals > 0 and match.away_goals > 0)
        
    # Team Goals
    elif market_type_val == "team_goals_over":
        # Determine team from label
        is_home = match.home_team.name.split()[0].lower() in pick.market_label.lower()
        actual = match.home_goals if is_home else match.away_goals
        if actual is None: return None, 0.0
        is_won = actual > threshold
    elif market_type_val == "team_goals_under":
        is_home = match.home_team.name.split()[0].lower() in pick.market_label.lower()
        actual = match.home_goals if is_home else match.away_goals
        if actual is None: return None, 0.0
        is_won = actual < threshold

    # Team Corners
    elif market_type_val == "home_corners_over":
        if match.home_corners is None: return None, 0.0
        is_won = match.home_corners > threshold
    elif market_type_val == "away_corners_over":
        if match.away_corners is None: return None, 0.0
        is_won = match.away_corners > threshold
        
    # Team Cards
    elif market_type_val == "home_cards_over":
        if match.home_yellow_cards is None: return None, 0.0
        is_won = match.home_yellow_cards > threshold
    elif market_type_val == "away_cards_over":
        if match.away_yellow_cards is None: return None, 0.0
        is_won = match.away_yellow_cards > threshold

    # Red Cards
    elif market_type_val == "red_cards":
        if match.home_red_cards is None or match.away_red_cards is None: return None, 0.0
        is_won = (match.home_red_cards > 0 or match.away_red_cards > 0)

    # VA Handicap
    elif market_type_val == "va_handicap":
        if match.home_goals is None or match.away_goals is None: return None, 0.0
        try:
            # Better regex for handicap: find + or - followed by number
            h_match = re.search(r"([+-]\d+\.?\d*)", pick.market_label)
            if not h_match: return None, 0.0
            handicap_val = float(h_match.group(1))
            
            # Determine team
            is_home_handicap = match.home_team.name.split()[0].lower() in pick.market_label.lower()
            
            score_diff = match.home_goals - match.away_goals if is_home_handicap else match.away_goals - match.home_goals
            is_won = (score_diff + handicap_val) > 0
        except:
            return None, 0.0

    else:
        # Unknown market type
        return None, 0.0

    return PickDetail(
        market_type=market_type_val,
        market_label=pick.market_label,
        was_correct=is_won,
        probability=pick.probability,
        expected_value=pick.expected_value * 100,
        confidence=float(pick.probability),
        is_contrarian=is_value_bet
    ), 0.0

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
    
    # Helper to create dedup key
    def match_key(m):
        return (m.home_team.name.lower(), m.away_team.name.lower(), m.match_date.strftime("%Y-%m-%d"))
    
    # 1. Fetch from CSV source (football-data.co.uk) - historical data with corners/cards
    for league_id in leagues:
        # Fetch last 2 seasons from CSV files
        matches = await data_sources.football_data_uk.get_historical_matches(league_id, seasons=["2324", "2425"])
        all_matches.extend(matches)
    
    logger.info(f"Fetched {len(all_matches)} matches from football-data.co.uk CSV")
    if all_matches:
        first_m = all_matches[0]
        last_m = all_matches[-1]
        logger.info(f"  Date range: {first_m.match_date} to {last_m.match_date}")
    existing_keys = {match_key(m) for m in all_matches}
    
    # Track statistics for logging
    source_stats = {"CSV": len(all_matches)}
    
    # 2. Fetch from API-Football for recent matches WITH STATS (corners, cards)
    # Priority: API-Football has better stats than football-data.org
    try:
        from src.infrastructure.data_sources.api_football import APIFootballSource
        api_fb = APIFootballSource()
        
        if api_fb.is_configured:
            today = get_current_time()
            # Fetch recent matches (limited by rate limit - 100 req/day)
            # Only fetch last 14 days to conserve API calls
            date_from = (today - timedelta(days=14)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            
            api_fb_matches = await api_fb.get_finished_matches(date_from, date_to, leagues)
            
            added_count = 0
            for api_match in api_fb_matches:
                key = match_key(api_match)
                if key not in existing_keys:
                    all_matches.append(api_match)
                    existing_keys.add(key)
                    added_count += 1
                    
            if added_count > 0:
                logger.info(f"Added {added_count} unique matches from API-Football (with corners/cards stats)")
                source_stats["API-Football"] = added_count
    except Exception as e:
        logger.warning(f"Could not fetch from API-Football (skipping): {e}")
    
    # 3. Fetch from football-data.org API for recent matches (fallback, no corners/cards but more coverage)
    try:
        from src.infrastructure.data_sources.football_data_org import FootballDataOrgSource
        fd_org = FootballDataOrgSource()
        
        if fd_org.is_configured:
            # Get matches from last 60 days via API (covers current season gaps)
            today = get_current_time()
            date_from = (today - timedelta(days=60)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            
            api_matches = await fd_org.get_finished_matches(date_from, date_to, leagues)
            
            added_count = 0
            for api_match in api_matches:
                key = match_key(api_match)
                if key not in existing_keys:
                    all_matches.append(api_match)
                    existing_keys.add(key)
                    added_count += 1
                    
            logger.info(f"Added {added_count} unique matches from football-data.org API")
    except Exception as e:
        logger.warning(f"Could not fetch from football-data.org API: {e}")
    
    # 4. Fetch from TheSportsDB for additional recent matches
    try:
        from src.infrastructure.data_sources.thesportsdb import TheSportsDBClient
        tsdb = TheSportsDBClient()
        
        added_count = 0
        for league_id in leagues:
            tsdb_matches = await tsdb.get_past_events(league_id, max_events=30)
            for tsdb_match in tsdb_matches:
                key = match_key(tsdb_match)
                if key not in existing_keys:
                    all_matches.append(tsdb_match)
                    existing_keys.add(key)
                    added_count += 1
                    
        if added_count > 0:
            logger.info(f"Added {added_count} unique matches from TheSportsDB")
    except Exception as e:
        logger.warning(f"Could not fetch from TheSportsDB: {e}")
    
    # 5. Fetch from FootyStats for detailed stats (corners, cards)
    # Note: Free tier only supports Premier League
    try:
        from src.infrastructure.data_sources.footystats import FootyStatsSource
        footystats = FootyStatsSource()
        
        if footystats.is_configured:
            added_count = 0
            # Free tier: Premier League only
            fs_matches = await footystats.get_finished_matches(["E0"])
            for fs_match in fs_matches:
                key = match_key(fs_match)
                if key not in existing_keys:
                    all_matches.append(fs_match)
                    existing_keys.add(key)
                    added_count += 1
                    
            if added_count > 0:
                logger.info(f"Added {added_count} unique matches from FootyStats (with corners/cards)")
    except Exception as e:
        logger.warning(f"Could not fetch from FootyStats: {e}")
    
    # 6. Fetch from BDFutbol for Spanish football historical data
    try:
        from src.infrastructure.data_sources.bdfutbol import BDFutbolSource
        bdfutbol = BDFutbolSource()
        
        if bdfutbol.is_configured:
            added_count = 0
            bd_matches = await bdfutbol.get_finished_matches()
            for bd_match in bd_matches:
                key = match_key(bd_match)
                if key not in existing_keys:
                    all_matches.append(bd_match)
                    existing_keys.add(key)
                    added_count += 1
                    
            if added_count > 0:
                logger.info(f"Added {added_count} unique matches from BDFutbol (Spanish football)")
    except Exception as e:
        logger.warning(f"Could not fetch from BDFutbol: {e}")
    
    # 7. Fetch from Football Prediction API (RapidAPI) for past results
    try:
        from src.infrastructure.data_sources.football_prediction_api import FootballPredictionAPISource
        fp_api = FootballPredictionAPISource()
        
        if fp_api.is_configured:
            added_count = 0
            fp_matches = await fp_api.get_finished_matches(days_back=7)
            for fp_match in fp_matches:
                key = match_key(fp_match)
                if key not in existing_keys:
                    all_matches.append(fp_match)
                    existing_keys.add(key)
                    added_count += 1
                    
            if added_count > 0:
                logger.info(f"Added {added_count} unique matches from Football Prediction API")
    except Exception as e:
        logger.warning(f"Could not fetch from Football Prediction API: {e}")
        
    # 8. Fetch from Local GitHub Dataset (Massive historical data 2000-2025)
    try:
        from src.infrastructure.data_sources.github_dataset import LocalGithubDataSource
        gh_data = LocalGithubDataSource()
        
        # Determine start date for GitHub data
        gh_start_date = None
        if request.days_back:
            gh_start_date = get_current_time() - timedelta(days=request.days_back)
        elif request.start_date:
            try:
                gh_start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                pass
                
        added_count = 0
        gh_matches = await gh_data.get_finished_matches(league_codes=leagues, date_from=gh_start_date)
        for gh_match in gh_matches:
            key = match_key(gh_match)
            if key not in existing_keys:
                all_matches.append(gh_match)
                existing_keys.add(key)
                added_count += 1
                
        if added_count > 0:
            logger.info(f"Added {added_count} unique matches from GitHub Dataset (2000-2025)")
    except Exception as e:
        logger.warning(f"Could not fetch from GitHub Dataset: {e}")

    # 9. Fetch from ESPN (Recent ~30 days with detailed stats)
    try:
        from src.infrastructure.data_sources.espn import ESPNSource
        espn = ESPNSource()
        
        # Determine days_back strict for ESPN (max 30 to be polite)
        espn_days = 14 # Default 2 weeks to stay fast
        if request.days_back and request.days_back < 60:
             espn_days = request.days_back
             
        added_count = 0
        espn_matches = await espn.get_finished_matches(league_codes=leagues, days_back=espn_days)
        for e_match in espn_matches:
            key = match_key(e_match)
            if key not in existing_keys:
                all_matches.append(e_match)
                existing_keys.add(key)
                added_count += 1
                
        if added_count > 0:
            logger.info(f"Added {added_count} unique matches from ESPN API")
    except Exception as e:
        logger.warning(f"Could not fetch from ESPN: {e}")
            
    # Sort by date (normalize to timezone-aware to avoid comparison errors)
    from src.utils.time_utils import COLOMBIA_TZ
    def get_sortable_date(match):
        dt = match.match_date
        if dt.tzinfo is None:
            # Localize naive datetime to Colombia timezone
            return COLOMBIA_TZ.localize(dt)
        return dt
    
    all_matches.sort(key=lambda x: get_sortable_date(x))
    
    # Log match counts per league for debugging
    league_match_counts = {}
    for m in all_matches:
        lid = m.league.id
        league_match_counts[lid] = league_match_counts.get(lid, 0) + 1
    
    logger.info(f"Match distribution by league (total {len(all_matches)} matches):")
    for lid in sorted(league_match_counts.keys()):
        logger.info(f"  - {lid}: {league_match_counts[lid]} matches")
    
    # Flag problematic leagues
    problematic_leagues = ["B1", "I1", "G1", "SC0", "T1", "I2", "SC1", "T2", "G2"]
    for target in problematic_leagues:
        if target not in league_match_counts or league_match_counts[target] == 0:
            logger.warning(f"⚠️ No matches found for league: {target}")
    
    # Filter by start date if provided
    if request.start_date:
        # Handle simple date string YYYY-MM-DD
        try:
            from src.utils.time_utils import COLOMBIA_TZ
            start_dt_naive = datetime.strptime(request.start_date, "%Y-%m-%d")
            start_dt = COLOMBIA_TZ.localize(start_dt_naive)
            all_matches = [m for m in all_matches if get_sortable_date(m) >= start_dt]
        except ValueError:
            pass
    elif request.days_back:
        start_dt = get_current_time().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=request.days_back)
        logger.info(f"Filtering matches from {start_dt} (days_back={request.days_back})")
        before_filter = len(all_matches)
        all_matches = [m for m in all_matches if get_sortable_date(m) >= start_dt]
        logger.info(f"Filter: {before_filter} -> {len(all_matches)} matches")

    # Process matches
    # We need to maintain a history of processed matches to calculate stats "as of that date"
    # OPTIMIZATION: Use incremental stats cache instead of reprocessing history list
    team_stats_cache = {}

    # Pre-calculate REAL league averages from the dataset (Backtest optimization)
    # This avoids hardcoded defaults (1.5/1.2) and respects league characteristics
    league_matches_map = {}
    for m in all_matches:
        if m.league.id not in league_matches_map:
            league_matches_map[m.league.id] = []
        league_matches_map[m.league.id].append(m)
        
    league_averages_map = {}
    for lid, matches in league_matches_map.items():
        if matches:
            league_averages_map[lid] = statistics_service.calculate_league_averages(matches)

    for match in all_matches:
        if match.home_goals is None or match.away_goals is None:
            continue

        # 1. Get current stats from cache (O(1))
        raw_home_stats = _get_or_create_team_stats(match.home_team.name, team_stats_cache)
        raw_away_stats = _get_or_create_team_stats(match.away_team.name, team_stats_cache)
        
        # Convert to domain entities for the service
        home_stats = _convert_to_domain_stats(match.home_team.name, raw_home_stats)
        away_stats = _convert_to_domain_stats(match.away_team.name, raw_away_stats)
        
        # League averages (Calculated from real data)
        league_averages = league_averages_map.get(match.league.id) 

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
            
            # Yield to event loop to prevent blocking (important for CORS/Preflights)
            if matches_processed % 100 == 0:
                import asyncio
                await asyncio.sleep(0)
            
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
                        
                    # Update daily stats for ROI evolution (outside market-specific if)
                    date_key = match.match_date.strftime("%Y-%m-%d")
                    if date_key not in daily_stats:
                        daily_stats[date_key] = {'staked': 0.0, 'return': 0.0, 'count': 0}
                    
                    # Use simple unit system: 1 unit stake, return 2 if win, 0 if loss
                    # This gives: Win = +1 unit profit, Loss = -1 unit profit
                    daily_stats[date_key]['staked'] += 1.0
                    daily_stats[date_key]['return'] += 2.0 if pick_detail.was_correct else 0.0
                    daily_stats[date_key]['count'] += 1

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
                # Probabilities
                home_win_probability=round(prediction.home_win_probability, 4),
                draw_probability=round(prediction.draw_probability, 4),
                away_win_probability=round(prediction.away_win_probability, 4),
                
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
    
    # Calculate pick efficiency
    # Collect all picks from all matches
    all_picks_flat = []
    for match in match_history:
        for pick in match.picks:
            # AnalyticsService expects objects with .status and .pick_type
            # We can create a simple container or just calculate it here directly for speed
            all_picks_flat.append(pick)
            
    # Calculate efficiency using internal helper
    pick_type_stats = {}
    for pick in all_picks_flat:
        ptype = pick.market_type
        if ptype not in pick_type_stats:
            pick_type_stats[ptype] = {"won": 0, "lost": 0, "void": 0, "total": 0}
        
        pick_type_stats[ptype]["total"] += 1
        if pick.was_correct:
            pick_type_stats[ptype]["won"] += 1
        else:
            pick_type_stats[ptype]["lost"] += 1
            
    pick_efficiency_list = []
    for ptype, data in pick_type_stats.items():
        efficiency = (data["won"] / (data["won"] + data["lost"]) * 100) if (data["won"] + data["lost"]) > 0 else 0.0
        pick_efficiency_list.append({
            "pick_type": ptype,
            "won": data["won"],
            "lost": data["lost"],
            "void": data["void"],
            "total": data["total"],
            "efficiency": round(efficiency, 2)
        })
    
    # Sort by efficiency descending
    pick_efficiency_list.sort(key=lambda x: x["efficiency"], reverse=True)

    # Limit match history in the response to prevent massive JSON payloads
    # Keep the most recent 500 matches for the UI
    logger.info(f"Total historical matches processed: {len(match_history)}")
    response_history = match_history[-500:] if len(match_history) > 500 else match_history
    if len(match_history) > 500:
        logger.info(f"Payload optimization: Truncated match_history from {len(match_history)} to 500 records")

    result = TrainingStatus(
        matches_processed=matches_processed,
        correct_predictions=correct_predictions,
        accuracy=round(accuracy, 4),
        total_bets=total_bets,
        roi=round(roi, 2),
        profit_units=round(profit, 2),
        market_stats=learning_service.get_all_stats(),
        match_history=response_history,
        roi_evolution=roi_evolution,
        pick_efficiency=pick_efficiency_list,
        team_stats=team_stats_cache
    )
    
    # Cache the result
    from src.infrastructure.cache import get_training_cache
    cache = get_training_cache()
    cache.set_training_results(result.model_dump())
    
    return result


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
            message="Cached training data retrieved successfully"
        )
    else:
        return CachedTrainingResponse(
            cached=False,
            last_update=None,
            data=None,
            message="No cached data available. Training runs daily at 7:00 AM COT or call POST /train to generate."
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
        "message": "Training started in background. Results will be cached when complete."
    }
