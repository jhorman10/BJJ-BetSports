import asyncio
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

# ML Imports
try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    ML_AVAILABLE = True
except ImportError:
    RandomForestClassifier = None
    ML_AVAILABLE = False

from src.domain.services.learning_service import LearningService
from src.domain.services.prediction_service import PredictionService
from src.domain.services.statistics_service import StatisticsService
from src.domain.services.pick_resolution_service import PickResolutionService
from src.application.services.training_data_service import TrainingDataService
from src.domain.services.ml_feature_extractor import MLFeatureExtractor
from src.domain.services.picks_service import PicksService
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

class MLTrainingOrchestrator:
    """
    Application service that orchestrates the entire ML training pipeline.
    Coordinates data fetching, feature extraction, training, and result calculation.
    """

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

        # 2. Fetch & Unify matches (Centralized Orchestration)
        leagues = league_ids if league_ids else DEFAULT_LEAGUES
        all_matches = await self.training_data_service.fetch_comprehensive_training_data(
            leagues=leagues, 
            days_back=days_back, 
            start_date=start_date,
            force_refresh=force_refresh
        )

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

        # 4. SORT MATCHES BY DATE (CRITICAL for TimeSeriesSplit)
        all_matches.sort(key=lambda m: m.match_date)
        
        # --- ROLLING WINDOW BACKTESTING (Walk-Forward Validation) ---
        # 1. Initial Training Window (e.g. first 100 matches)
        # 2. Predict Next Batch (e.g. next 7 days or next 50 matches)
        # 3. Retrain Model including new batch
        # 4. Repeat
        
        current_train_set = []
        validation_queue = all_matches[:] 
        
        # Minimum samples to start using ML model
        MIN_TRAIN_SAMPLES = 50 
        BATCH_SIZE = 50
        
        while validation_queue:
            # 1. Take next batch (matches to PREDICT)
            current_batch = validation_queue[:BATCH_SIZE]
            validation_queue = validation_queue[BATCH_SIZE:]
            
            if not current_batch: break
            
            # 2. Train Model on Current Train Set (if enough data)
            if ML_AVAILABLE and RandomForestClassifier and len(ml_features) >= MIN_TRAIN_SAMPLES:
                 try:
                    # Train strict model only on PAST knowledge
                    # ml_features contains features from *current_train_set* processed so far
                    # Wait, we need to extract features from current_train_set first?
                    # Ah, we process matches sequentially. 
                    # We can use the accumulating ml_features list which grows as we process.
                    
                    # Optimization: Don't retrain EVERY batch if very large. 
                    # Maybe every 2-3 batches or simple incremental.
                    # For sk-learn RF, we must refit.
                    
                    clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42, n_jobs=-1)
                    clf.fit(ml_features, ml_targets)
                    self.cache_service.set("temp_ml_model", clf) # Fake in-memory persistence using service? No, just assign to instance or joblib.
                    
                    # Update the service instance with the NEW model for this batch
                    # This ensures picks_service uses the time-travelling correct model
                    picks_service_instance.ml_model = clf
                 except Exception as e:
                    logger.warning(f"Rolling Window Training Limit: {e}")

            # 3. Reference to newly processed matches to add to history later
            batch_features = []
            batch_targets = []
            
            for match in current_batch:
                if match.home_goals is None or match.away_goals is None:
                    continue

                # Get/Create stats (Centralized in StatisticsService)
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
                    # PREDICT (Using model trained only on data BEFORE this batch)
                    prediction = self.prediction_service.generate_prediction(
                        match=match, home_stats=home_stats, away_stats=away_stats, league_averages=league_averages,
                        min_matches=0
                    )
                    
                    matches_processed += 1
                    
                    # --- EVALUATE PICKS ---
                    # (Here we use picks_service_instance, which has the updated model!)
                    suggested_picks_container = picks_service_instance.generate_suggested_picks(
                        match=match, home_stats=home_stats, away_stats=away_stats, league_averages=league_averages,
                        predicted_home_goals=prediction.predicted_home_goals, predicted_away_goals=prediction.predicted_away_goals,
                        home_win_prob=prediction.home_win_probability, draw_prob=prediction.draw_probability, away_win_prob=prediction.away_win_probability
                    )
                    
                    # Resolve picks
                    picks_list = []
                    suggested_pick_label = None
                    pick_was_correct = False
                    max_ev_value = -100.0
                    
                    picks_to_process = suggested_picks_container.suggested_picks if suggested_picks_container else []
                    
                    for pick in picks_to_process:
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
                        
                        # Store Features for FUTURE training (Data Leakage Prevention: We store now, train later)
                        batch_features.append(self.feature_extractor.extract_features(pick))
                        batch_targets.append(1 if is_won else 0)
                        
                        # Track ROI
                        if p_detail["market_type"] in ["winner", "draw", "result_1x2"]:
                            total_bets += 1
                            total_staked += 1.0
                            total_return += payout
                            if float(pick.expected_value) > max_ev_value:
                                 suggested_pick_label = pick.market_label
                                 pick_was_correct = is_won
                                 max_ev_value = float(pick.expected_value)

                        # --- CLV CALCULATION ---
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

                    # Daily stats
                    date_key = match.match_date.strftime("%Y-%m-%d")
                    if date_key not in daily_stats: 
                        daily_stats[date_key] = {'staked': 0.0, 'return': 0.0, 'count': 0}
                    daily_stats[date_key]['staked'] += 1.0
                    daily_stats[date_key]['return'] += 2.0 if pick_was_correct else 0.0
                    daily_stats[date_key]['count'] += 1

                    match_history.append({
                        "match_id": match.id,
                        "home_team": match.home_team.name,
                        "away_team": match.away_team.name,
                        "match_date": match.match_date.isoformat(),
                        "predicted_winner": self._get_predicted_winner(prediction),
                        "actual_winner": self._get_actual_winner(match),
                        "predicted_home_goals": round(prediction.predicted_home_goals, 2),
                        "predicted_away_goals": round(prediction.predicted_away_goals, 2),
                        "actual_home_goals": match.home_goals,
                        "actual_away_goals": match.away_goals,
                        "was_correct": self._get_predicted_winner(prediction) == self._get_actual_winner(match),
                        "confidence": round(prediction.confidence, 3),
                        "home_win_probability": round(prediction.home_win_probability, 4),
                        "draw_probability": round(prediction.draw_probability, 4),
                        "away_win_probability": round(prediction.away_win_probability, 4),
                        "picks": picks_list,
                        "suggested_pick": suggested_pick_label,
                        "pick_was_correct": pick_was_correct,
                        "expected_value": max_ev_value
                    })
                    
                    if matches_processed % 100 == 0: await asyncio.sleep(0)

                except Exception as e:
                    logger.error(f"Error processing match {match.id}: {e}")
                    continue

                # 5. Update stats incrementally (AFTER prediction)
                # This ensures we predict utilizing knowledge up to THIS match, then update knowledge for NEXT
                self.statistics_service.update_team_stats_dict(raw_home, match, is_home=True)
                self.statistics_service.update_team_stats_dict(raw_away, match, is_home=False)
            
            # 6. ADD BATCH TO HISTORY FOR NEXT TRAINING LOOP
            # This is the "Walk Forward" step
            ml_features.extend(batch_features)
            ml_targets.extend(batch_targets)
            current_train_set.extend(current_batch)
        
        # --- TRAIN ML MODEL ---
        if ML_AVAILABLE and RandomForestClassifier and len(ml_features) > 100:
            try:
                logger.info(f"Training ML Model on {len(ml_features)} samples...")
                
                # Offload CPU-bound training to a thread
                def _train_and_save():
                    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
                    clf.fit(ml_features, ml_targets)
                    joblib.dump(clf, "ml_picks_classifier.joblib")
                    return clf

                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, _train_and_save)
                
                logger.info("ML Model trained and saved.")
            except Exception as e:
                logger.error(f"Failed to train ML model: {e}")
        
        # --- PREPARE RESULTS ---
        accuracy = self._calculate_accuracy(match_history)
        profit = total_return - total_staked
        roi = (profit / total_staked * 100) if total_staked > 0 else 0.0
        
        return TrainingResult(
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
            team_stats=team_stats_cache
        )

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
