import asyncio
import logging
import os
import warnings
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# Suppress DeprecationWarnings from utcnow() used in ML libraries
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*utcnow.*")

# ML Imports will be lazy-loaded in the methods that need them
# to prevent memory spikes on startup (Render Free Tier Optimization)
ML_AVAILABLE = True # Assumed true, checked at runtime

from src.domain.services.learning_service import LearningService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.application.services.training_data_service import TrainingDataService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.picks_service import PicksService
from src.domain.services.risk_management.risk_manager import RiskManager
from src.domain.entities.entities import Match
from src.infrastructure.cache.cache_service import CacheService
from src.utils.time_utils import get_current_time
from src.core.constants import DEFAULT_LEAGUES

logger = logging.getLogger(__name__)

class TrainingResult(BaseModel):
    matches_processed: int
    correct_predictions: int
    accuracy: float
    total_bets: int
    roi: float
    profit_units: float
    market_stats: dict
    match_history: List[Any] = []
    roi_evolution: List[Any] = []
    pick_efficiency: List[Any] = []
    team_stats: dict = {}
    global_averages: dict = {} # Calculated from the entire 10-year dataset

class MLTrainingOrchestrator:
    """
    Application service that orchestrates the entire ML training pipeline.
    Coordinates data fetching, feature extraction, training, and result calculation.
    """

    # Model Path Resolution (Robust against CWD)
    # Saves to backend/ml_picks_classifier.joblib
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up from application/services -> src -> backend
    MODEL_FILE_PATH = os.path.join(_current_dir, "..", "..", "..", "ml_picks_classifier.joblib")

    def __init__(
        self,
        training_data_service: TrainingDataService,
        statistics_service: StatisticsService,
        prediction_service: PredictionService,
        learning_service: LearningService,
        resolution_service: PickResolutionService,
        cache_service: CacheService
    ):
        self.training_data_service = training_data_service
        self.statistics_service = statistics_service
        self.prediction_service = prediction_service
        self.learning_service = learning_service
        self.resolution_service = resolution_service
        self.cache_service = cache_service
        self.feature_extractor = MLFeatureExtractor()
        self.risk_manager = RiskManager()
        
        # Cache Keys
        self.CACHE_KEY_STATUS = "ml_training_status"
        self.CACHE_KEY_MESSAGE = "ml_training_message"
        self.CACHE_KEY_RESULT = "ml_training_result_data"

    async def run_training_pipeline(
        self, 
        league_ids: Optional[List[str]] = None, 
        days_back: int = 365, 
        start_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> TrainingResult:
        """
        Executes the full training pipeline and returns a TrainingResult.
        """
        logger.info(f"Starting ML Training Pipeline (leagues={league_ids}, days_back={days_back})")
        
        # Lazy Load ML Libraries
        try:
            from sklearn.ensemble import RandomForestClassifier
            import joblib
        except ImportError:
            RandomForestClassifier = None
            joblib = None
            logger.warning("ML libraries (sklearn, joblib) not found. Training will be skipped.")
        
        # 0. Set Status to IN_PROGRESS immediately
        # This tells the frontend to hide the Dashboard button but allow navigation
        # 0. Set Status to IN_PROGRESS immediately
        # This tells the frontend to hide the Dashboard button but allow navigation
        self.cache_service.set(self.CACHE_KEY_STATUS, "IN_PROGRESS", ttl_seconds=3600)
        self.cache_service.set(self.CACHE_KEY_MESSAGE, "Iniciando orquestación del servidor...", ttl_seconds=3600)
        
        # 1. Initialize logic-dependant services
        picks_service_instance = PicksService(learning_weights=self.learning_service.get_learning_weights())
        
        matches_processed = 0
        correct_predictions = 0
        total_bets = 0
        total_staked = 0.0
        total_return = 0.0
        daily_stats = {}
        match_history = []
        
        # ML Training Data accumulation
        ml_features = []
        ml_targets = []
        
        # Team stats cache for rolling historical stats
        team_stats_cache = {}

        try:
            # 2. Fetch & Unify matches (Centralized Orchestration)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Recuperando datos históricos de múltiples ligas...", ttl_seconds=3600)
            leagues = league_ids if league_ids else DEFAULT_LEAGUES
            all_matches = await self.training_data_service.fetch_comprehensive_training_data(
                leagues=leagues, 
                days_back=days_back, 
                start_date=start_date,
                force_refresh=force_refresh
            )
            
            # Detailed Logging for visibility
            source_stats = {}
            league_stats = {}
            for m in all_matches:
                src = m.id.split('_')[0] if '_' in m.id else "unknown"
                source_stats[src] = source_stats.get(src, 0) + 1
                league_stats[m.league.id] = league_stats.get(m.league.id, 0) + 1
            
            logger.info(f"Fetched {len(all_matches)} total matches. Sources: {source_stats}. Leagues: {league_stats}")
            
        except Exception as e:
            logger.error(f"Failed to fetch training data: {e}")
            self.cache_service.set(self.CACHE_KEY_STATUS, "ERROR", ttl_seconds=3600)
            raise e

        # 3. Pre-calculate REAL league averages
        league_matches_map = {}
        for m in all_matches:
            if m.league.id not in league_matches_map: 
                league_matches_map[m.league.id] = []
            league_matches_map[m.league.id].append(m)
            
        league_averages_map = {
            lid: self.statistics_service.calculate_league_averages(ms) 
            for lid, ms in league_matches_map.items()
        }
        
        # 3b. Calculate GLOBAL averages (Ultimate Fallback)
        global_averages_obj = self.statistics_service.calculate_league_averages(all_matches)
        global_averages = {
            "avg_home_goals": round(global_averages_obj.avg_home_goals, 4),
            "avg_away_goals": round(global_averages_obj.avg_away_goals, 4),
            "avg_total_goals": round(global_averages_obj.avg_total_goals, 4),
            "avg_corners": round(global_averages_obj.avg_corners, 4),
            "avg_cards": round(global_averages_obj.avg_cards, 4)
        }
        self.cache_service.set("global_statistical_averages", global_averages, ttl_seconds=86400 * 7)

        # 4. SORT MATCHES BY DATE (CRITICAL for TimeSeriesSplit)
        # Normalize datetimes to naive for comparison (some sources return aware, others naive)
        def get_sort_key(m):
            dt = m.match_date
            if dt.tzinfo is not None:
                # Convert to naive by removing timezone info (already in local time)
                return dt.replace(tzinfo=None)
            return dt
        
        all_matches.sort(key=get_sort_key)
        
        # --- ROLLING WINDOW BACKTESTING (Day-by-Day Portfolio Simulation) ---
        # We group matches by day to enforce daily risk limits.
        
        from itertools import groupby
        matches_by_day = [list(group) for key, group in groupby(all_matches, key=lambda m: m.match_date.date())]
        self.cache_service.set(self.CACHE_KEY_MESSAGE, f"Analizando {len(all_matches)} partidos día por día...", ttl_seconds=3600)
        
        # Minimum samples to start using ML model
        MIN_TRAIN_SAMPLES = 50 
        
        try:
            for daily_matches in matches_by_day:
            
                # A. Rolling Training DISABLED for performance on 512MB RAM / 0.1 CPU
                # Retraining inside the loop is too heavy. We rely on Heuristics for the backtest,
                # and train the ML model ONLY once at the end.
                # if ML_AVAILABLE and RandomForestClassifier and len(ml_features) >= MIN_TRAIN_SAMPLES:
                #      # Retrain periodically (e.g. every 50 new samples) or every day if fast enough
                #      # For now, let's retrain every ~200 samples to simulate periodic model updates
                #          if len(ml_features) % 200 < len(daily_matches) or len(ml_features) == MIN_TRAIN_SAMPLES:
                #              try:
                #                 # Run CPU-bound training in thread to avoid blocking event loop
                #                 def _train_step(features, targets):
                #                     c = RandomForestClassifier(
                #                         n_estimators=150, 
                #                         max_depth=8, 
                #                         random_state=42, 
                #                         n_jobs=-1,
                #                         class_weight='balanced'
                #                     )
                #                     c.fit(features, targets)
                #                     return c
                #                 
                #                 loop = asyncio.get_running_loop()
                #                 clf = await loop.run_in_executor(None, _train_step, ml_features, ml_targets)
                #                 
                #                 picks_service_instance.ml_model = clf
                #              except Exception as e:
                #                 logger.warning(f"Rolling Window Training Limit: {e}")
    
                # B. Generate Candidates for TODAY
                daily_candidates = [] # List of {'pick': SuggestedPick, 'match': Match}
                
                for match in daily_matches:
                    if match.home_goals is None or match.away_goals is None: continue
    
                    # Get/Create stats (Centralized)
                    if match.home_team.name not in team_stats_cache: 
                        team_stats_cache[match.home_team.name] = self.statistics_service.create_empty_stats_dict()
                    if match.away_team.name not in team_stats_cache: 
                        team_stats_cache[match.away_team.name] = self.statistics_service.create_empty_stats_dict()
                        
                    raw_home = team_stats_cache[match.home_team.name]
                    raw_away = team_stats_cache[match.away_team.name]
                    
                    home_stats = self.statistics_service.convert_to_domain_stats(match.home_team.name, raw_home)
                    away_stats = self.statistics_service.convert_to_domain_stats(match.away_team.name, raw_away)
                    league_averages = league_averages_map.get(match.league.id) 
    
                    try:
                        # PREDICT using current knowledge
                        prediction = self.prediction_service.generate_prediction(
                            match=match, 
                            home_stats=home_stats, 
                            away_stats=away_stats, 
                            league_averages=league_averages,
                            global_averages=global_averages_obj,
                            min_matches=0
                        )
                        
                        matches_processed += 1
                        
                        # GENERATE PICKS
                        suggested_picks_container = picks_service_instance.generate_suggested_picks(
                            match=match, home_stats=home_stats, away_stats=away_stats, league_averages=league_averages,
                            predicted_home_goals=prediction.predicted_home_goals, predicted_away_goals=prediction.predicted_away_goals,
                            home_win_prob=prediction.home_win_probability, draw_prob=prediction.draw_probability, away_win_prob=prediction.away_win_probability
                        )
                        
                        if suggested_picks_container and suggested_picks_container.suggested_picks:
                            for p in suggested_picks_container.suggested_picks:
                                daily_candidates.append({'pick': p, 'match': match, 'prediction': prediction})
                                
                    except Exception as e:
                        logger.error(f"Error processing match {match.id}: {e}")
                        continue
    
                # C. Apply Portfolio Constraints (Risk Manager)
                # This filters the day's candidates to select the best portfolio respecting risk limits
                approved_items = self.risk_manager.apply_portfolio_constraints(daily_candidates)
                
                # Mapping to easily find approved picks per match for history
                approved_picks_map = {} # match_id -> list of picks
                for item in approved_items:
                    mid = item['match'].id
                    if mid not in approved_picks_map: approved_picks_map[mid] = []
                    approved_picks_map[mid].append(item['pick'])
    
                # D. Resolve & Record Results
                for match in daily_matches:
                     # Skip if no stats/prediction made (error case)
                     if match.home_goals is None: continue
                     
                     # Retrieve approved picks for this match (if any)
                     my_picks = approved_picks_map.get(match.id, [])
                     
                     picks_list = []
                     suggested_pick_label = None
                     pick_was_correct = False
                     max_ev_value = -100.0
    
                     for pick in my_picks:
                        result_str, payout = self.resolution_service.resolve_pick(pick, match)
                        is_won = (result_str == "WIN")
                        
                        p_detail = {
                            "market_type": pick.market_type.value if hasattr(pick.market_type, "value") else str(pick.market_type),
                            "market_label": pick.market_label,
                            "was_correct": is_won,
                            "probability": float(pick.probability),
                            "expected_value": float(pick.expected_value),
                            "confidence": float(pick.priority_score or pick.probability),
                            "reasoning": pick.reasoning,
                            "result": result_str,
                            "suggested_stake": getattr(pick, "suggested_stake", 0.0),
                            "kelly_percentage": getattr(pick, "kelly_percentage", 0.0)
                        }
                        
                        # Store Features for FUTURE training
                        # Re-constitute stats for feature extraction
                        raw_home_feat = team_stats_cache.get(match.home_team.name, {})
                        raw_away_feat = team_stats_cache.get(match.away_team.name, {})
                        feat_home_stats = self.statistics_service.convert_to_domain_stats(match.home_team.name, raw_home_feat)
                        feat_away_stats = self.statistics_service.convert_to_domain_stats(match.away_team.name, raw_away_feat)
                        
                        ml_features.append(self.feature_extractor.extract_features(pick, match, feat_home_stats, feat_away_stats))
                        ml_targets.append(1 if is_won else 0)
                        
                        # Track ROI
                        if p_detail["market_type"] in ["winner", "draw", "result_1x2"]:
                             total_bets += 1
                             total_staked += p_detail["suggested_stake"] # Use calculated unit stake
                             total_return += (p_detail["suggested_stake"] * payout) if payout > 0 else 0
                             if float(pick.expected_value) > max_ev_value:
                                  suggested_pick_label = pick.market_label
                                  pick_was_correct = is_won
                                  max_ev_value = float(pick.expected_value)
    
                        # CLV
                        closing_odds = 0.0
                        if pick.market_type == "winner":
                             if match.home_goals > match.away_goals: closing_odds = match.home_odds or 0.0
                             elif match.away_goals > match.home_goals: closing_odds = match.away_odds or 0.0
                             else: closing_odds = match.draw_odds or 0.0
                        elif pick.market_type == "draw":
                             closing_odds = match.draw_odds or 0.0
                        
                        p_detail["opening_odds"] = pick.odds
                        p_detail["closing_odds"] = closing_odds
                        p_detail["clv_beat"] = pick.odds > closing_odds if closing_odds > 1.0 else False
                        
                        picks_list.append(p_detail)
                        
                        # Daily stats update
                        date_key = match.match_date.strftime("%Y-%m-%d")
                        if date_key not in daily_stats: 
                            daily_stats[date_key] = {'staked': 0.0, 'return': 0.0, 'count': 0}
                        daily_stats[date_key]['staked'] += p_detail["suggested_stake"]
                        daily_stats[date_key]['return'] += (p_detail["suggested_stake"] * payout) if payout > 0 else 0
                        daily_stats[date_key]['count'] += 1
    
                     # Get prediction from candidates (hacky lookup)
                     # Better: re-run prediction or store it. We stored it in 'daily_candidates'.
                     # Let's just create a basic history entry even if no picks were approved
                     # But we need the prediction object.
                     # Let's find the prediction in daily_candidates or regenerate simple one.
                     # Optimization: Store prediction in a temp map above.
                     
                     # Simple approach: Re-generate prediction just for logging? No, waste.
                     # Let's map match_id -> prediction in the B loop.
                     pass # We handle this by populating history ONLY if we processed it.
                     
                     # Actually, we want history for ALL matches to show "No Bet" ones too?
                     # Yes, usually. But for now let's focus on Active Betting History.
                     
                     if picks_list:
                         # Re-find prediction (optimization: store in map)
                         pred_obj = next((x['prediction'] for x in daily_candidates if x['match'].id == match.id), None)
                         if pred_obj:
                            match_history.append({
                                "match_id": match.id,
                                "home_team": match.home_team.name,
                                "away_team": match.away_team.name,
                                "match_date": match.match_date.isoformat(),
                                "predicted_winner": self._get_predicted_winner(pred_obj),
                                "actual_winner": self._get_actual_winner(match),
                                "predicted_home_goals": round(pred_obj.predicted_home_goals, 2),
                                "predicted_away_goals": round(pred_obj.predicted_away_goals, 2),
                                "actual_home_goals": match.home_goals,
                                "actual_away_goals": match.away_goals,
                                "was_correct": self._get_predicted_winner(pred_obj) == self._get_actual_winner(match),
                                "confidence": round(pred_obj.confidence, 3),
                                "picks": picks_list,
                                "suggested_pick": suggested_pick_label,
                                "pick_was_correct": pick_was_correct,
                                "expected_value": max_ev_value
                            })
    
                # E. Update Stats (After Day is Done) - The "Nightly Update"
                # Crucial: We update stats using ALL matches of the day, even those we didn't bet on.
                # E. Update Stats (After Day is Done) - The "Nightly Update"
                # Crucial: We update stats using ALL matches of the day, even those we didn't bet on.
                for match in daily_matches:
                    if match.home_team.name in team_stats_cache:
                        self.statistics_service.update_team_stats_dict(team_stats_cache[match.home_team.name], match, is_home=True)
                    if match.away_team.name in team_stats_cache:
                        self.statistics_service.update_team_stats_dict(team_stats_cache[match.away_team.name], match, is_home=False)
                
                # Yield control to event loop to allow other requests (health checks, polling) to be processed
                await asyncio.sleep(0)
        
            # --- TRAIN ML MODEL ---
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Entrenando modelo de Machine Learning (Random Forest)...", ttl_seconds=3600)
            if ML_AVAILABLE and RandomForestClassifier and len(ml_features) > 100:
                try:
                    logger.info(f"Training ML Model on {len(ml_features)} samples...")
                    
                    # Offload CPU-bound training to a thread
                    def _train_and_save():
                        # Optimized for Low Resources (512MB RAM):
                        # - Fewer trees (60 vs 150)
                        # - Reduced depth (6 vs 10) to prevent OOM
                        # - n_jobs=1 to avoid process overhead on 0.1 CPU
                        clf = RandomForestClassifier(
                            n_estimators=60, 
                            max_depth=6, 
                            random_state=42,
                            class_weight='balanced',
                            n_jobs=1
                        )
                        clf.fit(ml_features, ml_targets)
                        
                        # Save to absolute path
                        joblib.dump(clf, self.MODEL_FILE_PATH)
                        return clf
    
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, _train_and_save)
                    
                    logger.info("ML Model trained and saved.")
                except Exception as e:
                    logger.error(f"Failed to train ML model: {e}")
            
            # --- PREPARE RESULTS ---
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Consolidando métricas y evolución de ROI...", ttl_seconds=3600)
            accuracy = self._calculate_accuracy(match_history)
            profit = total_return - total_staked
            roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
            
            final_result = TrainingResult(
                matches_processed=matches_processed,
                correct_predictions=self._get_correct_count(match_history),
                accuracy=round(accuracy, 4),
                total_bets=total_bets,
                roi=round(roi, 2),
                profit_units=round(profit, 2),
                market_stats=self.learning_service.get_all_stats(),
                match_history=match_history,
                roi_evolution=self._calculate_roi_evolution(daily_stats),
                pick_efficiency=self._calculate_pick_efficiency(match_history),
                team_stats=team_stats_cache,
                global_averages=global_averages
            )
            
            # Save result to cache and update status
            # This enables the "Bot Dashboard" button on the frontend
            # Save result to cache and update status
            # This enables the "Bot Dashboard" button on the frontend
            # Use simple dict conversion that handles nested models if possible, else rely on Pydantic's dict()
            # Note: TrainingResult is a Pydantic model, so .dict() or .model_dump() works
            result_data = final_result.model_dump() if hasattr(final_result, 'model_dump') else final_result.dict()
            
            self.cache_service.set(self.CACHE_KEY_RESULT, result_data, ttl_seconds=86400)
            self.cache_service.set(self.CACHE_KEY_STATUS, "COMPLETED", ttl_seconds=86400)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, "Entrenamiento completado exitosamente", ttl_seconds=86400)
            
            return final_result
    
        except Exception as e:
            logger.error(f"Critical error in training pipeline: {e}")
            self.cache_service.set(self.CACHE_KEY_STATUS, "ERROR", ttl_seconds=3600)
            self.cache_service.set(self.CACHE_KEY_MESSAGE, f"Error crítico: {str(e)}", ttl_seconds=3600)
            raise e

    def _get_predicted_winner(self, prediction) -> str:
        if prediction.home_win_probability > prediction.away_win_probability and prediction.home_win_probability > prediction.draw_probability:
            return "home"
        elif prediction.away_win_probability > prediction.home_win_probability and prediction.away_win_probability > prediction.draw_probability:
            return "away"
        return "draw"

    def _get_actual_winner(self, match) -> str:
        if match.home_goals > match.away_goals: return "home"
        elif match.away_goals > match.home_goals: return "away"
        return "draw"

    def _get_correct_count(self, history: List[dict]) -> int:
        return sum(1 for m in history if m["was_correct"])

    def _calculate_accuracy(self, history: List[dict]) -> float:
        if not history: return 0.0
        return self._get_correct_count(history) / len(history)

    def _calculate_roi_evolution(self, daily_stats: dict) -> List[dict]:
        roi_evolution = []
        cum_staked = 0.0
        cum_return = 0.0
        for date_str in sorted(daily_stats.keys()):
            stats = daily_stats[date_str]
            cum_staked += stats['staked']
            cum_return += stats['return']
            profit = cum_return - cum_staked
            roi = (profit / cum_staked * 100) if cum_staked > 0 else 0.0
            roi_evolution.append({"date": date_str, "roi": round(roi, 2), "profit": round(profit, 2)})
        return roi_evolution

    def _calculate_pick_efficiency(self, history: List[dict]) -> List[dict]:
        pick_type_stats = {}
        for match in history:
            for pick in match["picks"]:
                ptype = pick["market_type"]
                if ptype not in pick_type_stats:
                    pick_type_stats[ptype] = {"won": 0, "lost": 0, "void": 0, "total": 0}
                pick_type_stats[ptype]["total"] += 1
                if pick["was_correct"]: pick_type_stats[ptype]["won"] += 1
                else: pick_type_stats[ptype]["lost"] += 1
        
        results = []
        for ptype, data in pick_type_stats.items():
            efficiency = (data["won"] / data["total"] * 100) if data["total"] > 0 else 0.0
            results.append({
                "pick_type": ptype, "won": data["won"], "lost": data["lost"],
                "void": data["void"], "total": data["total"], "efficiency": round(efficiency, 2)
            })
        results.sort(key=lambda x: x["efficiency"], reverse=True)
        return results
