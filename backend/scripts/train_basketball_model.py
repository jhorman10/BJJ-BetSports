#!/usr/bin/env python3
"""
Basketball ML Model Training Script

Trains calibrated XGBoost/LightGBM models for basketball game outcomes.
Uses BasketballFeatureExtractor (40 features, 7 groups) and NBADataSource.

Targets:
  - home_win (binary classification)
  - total_points (regression for over/under)
  - home_spread (regression for point spread)

Models:
  - Classification: XGBoost/LightGBM with CalibratedClassifierCV(method='isotonic', cv=3)
  - Regression: XGBoost/LightGBM regressors

Save to: models/basketball_classifier.pkl (classification)
         models/basketball_regressor.pkl (regression for total_points and spread)
"""

import sys
import os
import logging
import warnings
from datetime import date
from typing import Optional, List, Dict, Any, Tuple

import numpy as np
import pandas as pd
import joblib

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.getcwd())

from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score, log_loss, brier_score_loss, roc_auc_score,
    classification_report, mean_squared_error, mean_absolute_error, r2_score
)
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor

# Try to import XGBoost and LightGBM
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

from src.infrastructure.data_sources.nba_data_source import NBADataSource
from src.domain.services.basketball_feature_extractor import BasketballFeatureExtractor
from src.domain.entities.basketball_game import BasketballGame

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def prepare_basketball_games(df: pd.DataFrame) -> List[BasketballGame]:
    """
    Convert raw NBA DataFrame into BasketballGame objects.
    Filters for valid games with scores.
    """
    games = []
    
    def safe_int(val, default=0):
        try:
            if pd.isna(val):
                return default
            return int(float(val))
        except (ValueError, TypeError):
            return default
    
    def safe_float(val, default=0.0):
        try:
            if pd.isna(val):
                return default
            return float(val)
        except (ValueError, TypeError):
            return default
    
    # Expected columns from NBA data sources
    # Adjust based on actual data format
    for _, row in df.iterrows():
        try:
            # Get scores - skip if missing
            home_score = safe_int(row.get("home_score") or row.get("HomeScore") or row.get("PTS_home"))
            away_score = safe_int(row.get("away_score") or row.get("VisitorScore") or row.get("PTS_away"))
            
            if home_score == 0 and away_score == 0:
                continue
            
            home_team = str(row.get("home_team") or row.get("HomeTeam") or row.get("TEAM_ABBREVIATION_home", "")).upper()
            away_team = str(row.get("away_team") or row.get("VisitorTeam") or row.get("TEAM_ABBREVIATION_away", "")).upper()
            
            if not home_team or not away_team:
                continue
            
            # Parse date
            try:
                game_date = pd.to_datetime(row.get("date") or row.get("Date") or row.get("GAME_DATE")).date()
            except Exception:
                continue
            
            # Season
            season = str(row.get("season") or row.get("Season") or f"{game_date.year}-{str(game_date.year+1)[2:]}")
            
            # Team stats if available
            home_wins = safe_int(row.get("home_wins"))
            home_losses = safe_int(row.get("home_losses"))
            away_wins = safe_int(row.get("away_wins"))
            away_losses = safe_int(row.get("away_losses"))
            
            game = BasketballGame(
                game_id=str(row.get("game_id") or row.get("GameID") or f"{away_team}@{home_team}_{game_date}"),
                home_team=home_team,
                away_team=away_team,
                game_date=game_date,
                venue=str(row.get("venue") or row.get("Arena") or ""),
                season=season,
                home_wins=home_wins if home_wins > 0 else None,
                home_losses=home_losses if home_losses > 0 else None,
                away_wins=away_wins if away_wins > 0 else None,
                away_losses=away_losses if away_losses > 0 else None,
                home_score=home_score,
                away_score=away_score,
                home_pts_avg=safe_float(row.get("home_pts_avg")) if pd.notna(row.get("home_pts_avg")) else None,
                away_pts_avg=safe_float(row.get("away_pts_avg")) if pd.notna(row.get("away_pts_avg")) else None,
                home_pts_allowed_avg=safe_float(row.get("home_pts_allowed_avg")) if pd.notna(row.get("home_pts_allowed_avg")) else None,
                away_pts_allowed_avg=safe_float(row.get("away_pts_allowed_avg")) if pd.notna(row.get("away_pts_allowed_avg")) else None,
                home_off_rating=safe_float(row.get("home_off_rating")) if pd.notna(row.get("home_off_rating")) else None,
                home_def_rating=safe_float(row.get("home_def_rating")) if pd.notna(row.get("home_def_rating")) else None,
                away_off_rating=safe_float(row.get("away_off_rating")) if pd.notna(row.get("away_off_rating")) else None,
                away_def_rating=safe_float(row.get("away_def_rating")) if pd.notna(row.get("away_def_rating")) else None,
                home_pace=safe_float(row.get("home_pace")) if pd.notna(row.get("home_pace")) else None,
                away_pace=safe_float(row.get("away_pace")) if pd.notna(row.get("away_pace")) else None,
                home_fg_pct=safe_float(row.get("home_fg_pct")) if pd.notna(row.get("home_fg_pct")) else None,
                home_3pt_pct=safe_float(row.get("home_3pt_pct")) if pd.notna(row.get("home_3pt_pct")) else None,
                away_fg_pct=safe_float(row.get("away_fg_pct")) if pd.notna(row.get("away_fg_pct")) else None,
                away_3pt_pct=safe_float(row.get("away_3pt_pct")) if pd.notna(row.get("away_3pt_pct")) else None,
            )
            games.append(game)
            
        except Exception as e:
            logger.debug(f"Error processing row: {e}")
            continue
    
    return games


def fetch_historical_nba_data(start_year: int = 2010, end_year: int = 2023) -> pd.DataFrame:
    """
    Fetch historical NBA data. Since NBADataSource is primarily for current standings,
    we generate realistic synthetic data for training.
    In production, this would connect to a proper NBA historical database.
    """
    logger.info(f"Fetching NBA historical data from {start_year} to {end_year}...")
    
    source = NBADataSource()
    
    # Try to get current standings for team stats
    try:
        standings = source.fetch_standings()
        if standings:
            logger.info(f"Loaded current standings for {len(standings)} teams")
    except Exception as e:
        logger.warning(f"Could not fetch standings: {e}")
        standings = {}
    
    # Generate synthetic historical data with realistic stats
    df = generate_synthetic_nba_data(start_year, end_year, standings)
    
    logger.info(f"Generated {len(df)} NBA games")
    return df


def generate_synthetic_nba_data(start_year: int, end_year: int, standings: Dict) -> pd.DataFrame:
    """
    Generate realistic synthetic NBA training data with proper statistical distributions.
    """
    np.random.seed(42)
    
    teams = [
        "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN",
        "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA",
        "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX",
        "POR", "SAC", "SAS", "TOR", "UTA", "WAS"
    ]
    
    venues = [
        "State Farm Arena", "TD Garden", "Barclays Center", "Spectrum Center",
        "United Center", "Rocket Mortgage FieldHouse", "American Airlines Center",
        "Ball Arena", "Little Caesars Arena", "Chase Center",
        "Toyota Center", "Gainbridge Fieldhouse", "Crypto.com Arena",
        "Crypto.com Arena", "FedExForum", "Kaseya Center",
        "Fiserv Forum", "Target Center", "Smoothie King Center",
        "Madison Square Garden", "Paycom Center", "Amway Center",
        "Wells Fargo Center", "Footprint Center", "Moda Center",
        "Golden 1 Center", "Frost Bank Center", "Scotiabank Arena",
        "Delta Center", "Capital One Arena"
    ]
    
    # Team strength parameters (based on recent performance)
    team_strength = {
        "BOS": 0.65, "DEN": 0.62, "MIL": 0.60, "GSW": 0.58, "PHI": 0.57,
        "PHX": 0.56, "MIA": 0.55, "LAC": 0.54, "DAL": 0.53, "CLE": 0.52,
        "NYK": 0.51, "MEM": 0.50, "MIN": 0.50, "LAL": 0.49, "ATL": 0.48,
        "IND": 0.47, "OKC": 0.46, "SAC": 0.45, "NOP": 0.44, "TOR": 0.43,
        "ORL": 0.42, "CHI": 0.41, "BKN": 0.40, "UTA": 0.39, "POR": 0.38,
        "HOU": 0.37, "WAS": 0.36, "DET": 0.35, "CHA": 0.34, "SAS": 0.33,
    }
    
    all_games = []
    game_id = 0
    
    for year in range(start_year, end_year + 1):
        # 1230 games per season (30 teams * 82 / 2)
        n_games = 1230
        
        for _ in range(n_games):
            home_team = np.random.choice(teams)
            away_team = np.random.choice([t for t in teams if t != home_team])
            
            # Home court advantage ~60% in NBA
            home_strength = team_strength.get(home_team, 0.5)
            away_strength = team_strength.get(away_team, 0.5)
            
            # Home win probability with home court advantage
            strength_diff = home_strength - away_strength
            home_win_prob = 0.60 + strength_diff * 0.3  # Base 60% + strength factor
            home_win_prob = np.clip(home_win_prob, 0.35, 0.85)
            
            home_win = np.random.random() < home_win_prob
            
            # Generate realistic scores (NBA avg ~112 pts per team)
            base_score = 112
            pace_factor = np.random.normal(1.0, 0.05)  # Pace variation
            
            if home_win:
                home_score = int(np.random.normal(base_score + 5, 10) * pace_factor)
                away_score = int(np.random.normal(base_score - 3, 10) * pace_factor)
            else:
                home_score = int(np.random.normal(base_score - 3, 10) * pace_factor)
                away_score = int(np.random.normal(base_score + 5, 10) * pace_factor)
            
            # Ensure reasonable scores
            home_score = np.clip(home_score, 80, 150)
            away_score = np.clip(away_score, 80, 150)
            
            # No ties in NBA
            if home_score == away_score:
                if home_win:
                    home_score += 1
                else:
                    away_score += 1
            
            # Generate season date (Oct-Apr)
            month = np.random.choice([10, 11, 12, 1, 2, 3, 4], p=[0.1, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15])
            if month >= 10:
                game_year = year
            else:
                game_year = year + 1
            game_date = date(game_year, month, np.random.randint(1, 28))
            
            # Team stats
            home_wr = team_strength.get(home_team, 0.5)
            away_wr = team_strength.get(away_team, 0.5)
            home_wins = int(home_wr * 82)
            home_losses = 82 - home_wins
            away_wins = int(away_wr * 82)
            away_losses = 82 - away_wins
            
            # Efficiency ratings
            home_off = 112 + (home_wr - 0.5) * 15
            home_def = 112 - (home_wr - 0.5) * 15
            away_off = 112 + (away_wr - 0.5) * 15
            away_def = 112 - (away_wr - 0.5) * 15
            
            all_games.append({
                "game_id": f"syn_{game_id}",
                "date": game_date.isoformat(),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": int(home_score),
                "away_score": int(away_score),
                "venue": venues[teams.index(home_team)] if home_team in teams else "Arena",
                "season": f"{year}-{str(year+1)[2:]}",
                "home_wins": home_wins,
                "home_losses": home_losses,
                "away_wins": away_wins,
                "away_losses": away_losses,
                "home_pts_avg": round(home_off, 1),
                "away_pts_avg": round(away_off, 1),
                "home_pts_allowed_avg": round(home_def, 1),
                "away_pts_allowed_avg": round(away_def, 1),
                "home_off_rating": round(home_off, 1),
                "home_def_rating": round(home_def, 1),
                "away_off_rating": round(away_off, 1),
                "away_def_rating": round(away_def, 1),
                "home_pace": round(np.random.normal(100, 3), 1),
                "away_pace": round(np.random.normal(100, 3), 1),
                "home_fg_pct": round(np.random.normal(0.465, 0.02), 3),
                "home_3pt_pct": round(np.random.normal(0.365, 0.02), 3),
                "away_fg_pct": round(np.random.normal(0.465, 0.02), 3),
                "away_3pt_pct": round(np.random.normal(0.365, 0.02), 3),
            })
            game_id += 1
    
    df = pd.DataFrame(all_games)
    logger.info(f"Generated {len(df)} synthetic NBA games")
    return df


def extract_features_and_targets(
    games: List[BasketballGame],
    historical_games: List[BasketballGame],
    feature_names: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract features and targets from games using temporal splits.
    Returns X, y_classification, y_total_points, y_spread, dates.
    """
    hist_df = pd.DataFrame([g.to_dict() for g in historical_games])
    
    extractor = BasketballFeatureExtractor(historical_data=hist_df)
    
    X = []
    y_win = []      # Classification target: 1 if home wins
    y_total = []    # Regression target: total points
    y_spread = []   # Regression target: home spread (home - away)
    dates = []
    
    for game in games:
        features = extractor.extract_features(game)
        X.append([features[f] for f in feature_names])
        
        # Classification target
        home_win = 1 if game.home_score > game.away_score else 0
        y_win.append(home_win)
        
        # Regression targets
        total_points = game.home_score + game.away_score
        y_total.append(total_points)
        
        spread = game.home_score - game.away_score
        y_spread.append(spread)
        
        dates.append(game.game_date)
    
    return (
        np.array(X),
        np.array(y_win),
        np.array(y_total),
        np.array(y_spread),
        np.array(dates),
    )


def train_classification_model(
    X: np.ndarray,
    y: np.ndarray,
    dates: np.ndarray,
    feature_names: List[str],
    use_calibration: bool = True,
    cv_folds: int = 3
) -> Tuple[Any, Dict[str, float]]:
    """Train calibrated classification model for home_win prediction."""
    logger.info(f"Training CLASSIFICATION model on {len(X)} samples")
    logger.info(f"Class distribution: Home wins={y.sum()} ({y.mean():.1%}), Away wins={len(y)-y.sum()} ({1-y.mean():.1%})")
    
    # Temporal split
    split_idx = int(len(X) * 0.8)
    sort_idx = np.argsort(dates)
    X_sorted = X[sort_idx]
    y_sorted = y[sort_idx]
    dates_sorted = dates[sort_idx]
    
    X_train, X_test = X_sorted[:split_idx], X_sorted[split_idx:]
    y_train, y_test = y_sorted[:split_idx], y_sorted[split_idx:]
    dates_train, dates_test = dates_sorted[:split_idx], dates_sorted[split_idx:]
    
    logger.info(f"Train: {len(X_train)} samples ({dates_train[0]} to {dates_train[-1]})")
    logger.info(f"Test:  {len(X_test)} samples ({dates_test[0]} to {dates_test[-1]})")
    
    # Choose base estimator
    if XGBOOST_AVAILABLE:
        logger.info("Using XGBoost as base estimator")
        base_model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            reg_alpha=0.1,
            reg_lambda=1.0,
            scale_pos_weight=(len(y_train) - y_train.sum()) / y_train.sum() if y_train.sum() > 0 else 1,
            random_state=42,
            n_jobs=-1,
            eval_metric='logloss',
            verbosity=0,
        )
    elif LIGHTGBM_AVAILABLE:
        logger.info("Using LightGBM as base estimator")
        base_model = lgb.LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_samples=20,
            reg_alpha=0.1,
            reg_lambda=1.0,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    else:
        logger.info("Using GradientBoostingClassifier as base estimator")
        base_model = GradientBoostingClassifier(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            min_samples_leaf=10,
            random_state=42,
        )
    
    # Apply calibration
    if use_calibration:
        logger.info(f"Applying CalibratedClassifierCV (isotonic, cv={cv_folds})")
        model = CalibratedClassifierCV(
            base_model,
            method='isotonic',
            cv=TimeSeriesSplit(n_splits=cv_folds),
            n_jobs=-1
        )
    else:
        model = base_model
    
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = model.predict(X_test)
    
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'log_loss': log_loss(y_test, y_pred_proba),
        'brier_score': brier_score_loss(y_test, y_pred_proba),
        'auc': roc_auc_score(y_test, y_pred_proba),
    }
    
    logger.info("=" * 50)
    logger.info("CLASSIFICATION EVALUATION METRICS")
    logger.info("=" * 50)
    for metric, value in metrics.items():
        logger.info(f"  {metric}: {value:.4f}")
    
    logger.info("\nClassification Report:")
    logger.info(f"\n{classification_report(y_test, y_pred, target_names=['Away Win', 'Home Win'])}")
    
    # Feature importance
    if hasattr(model, 'calibrated_classifiers_'):
        base_estimator = model.calibrated_classifiers_[0].estimator
    else:
        base_estimator = model
    
    if hasattr(base_estimator, 'feature_importances_'):
        importances = base_estimator.feature_importances_
        feature_importance = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        
        logger.info("\nTop 20 Feature Importances (Classification):")
        for name, imp in feature_importance[:20]:
            logger.info(f"  {name:30s} {imp:.4f}")
    
    return model, metrics


def train_regression_models(
    X: np.ndarray,
    y_total: np.ndarray,
    y_spread: np.ndarray,
    dates: np.ndarray,
    feature_names: List[str]
) -> Tuple[Any, Any, Dict[str, float], Dict[str, float]]:
    """Train regression models for total_points and home_spread."""
    logger.info(f"Training REGRESSION models on {len(X)} samples")
    
    # Temporal split
    split_idx = int(len(X) * 0.8)
    sort_idx = np.argsort(dates)
    X_sorted = X[sort_idx]
    y_total_sorted = y_total[sort_idx]
    y_spread_sorted = y_spread[sort_idx]
    dates_sorted = dates[sort_idx]
    
    X_train, X_test = X_sorted[:split_idx], X_sorted[split_idx:]
    y_total_train, y_total_test = y_total_sorted[:split_idx], y_total_sorted[split_idx:]
    y_spread_train, y_spread_test = y_spread_sorted[:split_idx], y_spread_sorted[split_idx:]
    dates_train, dates_test = dates_sorted[:split_idx], dates_sorted[split_idx:]
    
    logger.info(f"Train: {len(X_train)} samples, Test: {len(X_test)} samples")
    
    # Choose base estimator for regression
    if XGBOOST_AVAILABLE:
        logger.info("Using XGBoost Regressor")
        TotalModel = xgb.XGBRegressor
        SpreadModel = xgb.XGBRegressor
        total_params = {
            'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.05,
            'subsample': 0.8, 'colsample_bytree': 0.8, 'min_child_weight': 3,
            'reg_alpha': 0.1, 'reg_lambda': 1.0, 'random_state': 42,
            'n_jobs': -1, 'verbosity': 0,
        }
        spread_params = total_params.copy()
    elif LIGHTGBM_AVAILABLE:
        logger.info("Using LightGBM Regressor")
        TotalModel = lgb.LGBMRegressor
        SpreadModel = lgb.LGBMRegressor
        total_params = {
            'n_estimators': 300, 'max_depth': 6, 'learning_rate': 0.05,
            'num_leaves': 31, 'subsample': 0.8, 'colsample_bytree': 0.8,
            'min_child_samples': 20, 'reg_alpha': 0.1, 'reg_lambda': 1.0,
            'random_state': 42, 'n_jobs': -1, 'verbose': -1,
        }
        spread_params = total_params.copy()
    else:
        logger.info("Using GradientBoostingRegressor")
        TotalModel = GradientBoostingRegressor
        SpreadModel = GradientBoostingRegressor
        total_params = {
            'n_estimators': 300, 'max_depth': 5, 'learning_rate': 0.05,
            'subsample': 0.8, 'min_samples_leaf': 10, 'random_state': 42,
        }
        spread_params = total_params.copy()
    
    # Train total points model
    logger.info("Training Total Points Regressor...")
    total_model = TotalModel(**total_params)
    total_model.fit(X_train, y_total_train)
    
    total_pred = total_model.predict(X_test)
    total_metrics = {
        'mse': mean_squared_error(y_total_test, total_pred),
        'rmse': np.sqrt(mean_squared_error(y_total_test, total_pred)),
        'mae': mean_absolute_error(y_total_test, total_pred),
        'r2': r2_score(y_total_test, total_pred),
    }
    
    logger.info("Total Points Metrics:")
    for metric, value in total_metrics.items():
        logger.info(f"  {metric}: {value:.4f}")
    
    # Train spread model
    logger.info("Training Home Spread Regressor...")
    spread_model = SpreadModel(**spread_params)
    spread_model.fit(X_train, y_spread_train)
    
    spread_pred = spread_model.predict(X_test)
    spread_metrics = {
        'mse': mean_squared_error(y_spread_test, spread_pred),
        'rmse': np.sqrt(mean_squared_error(y_spread_test, spread_pred)),
        'mae': mean_absolute_error(y_spread_test, spread_pred),
        'r2': r2_score(y_spread_test, spread_pred),
    }
    
    logger.info("Home Spread Metrics:")
    for metric, value in spread_metrics.items():
        logger.info(f"  {metric}: {value:.4f}")
    
    # Feature importance for regression
    if hasattr(total_model, 'feature_importances_'):
        importances = total_model.feature_importances_
        feature_importance = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        
        logger.info("\nTop 15 Feature Importances (Total Points):")
        for name, imp in feature_importance[:15]:
            logger.info(f"  {name:30s} {imp:.4f}")
    
    return total_model, spread_model, total_metrics, spread_metrics


def save_models(
    clf_model: Any,
    total_model: Any,
    spread_model: Any,
    clf_path: str,
    reg_path: str,
    metadata: Dict[str, Any]
) -> None:
    """Save both classification and regression models."""
    os.makedirs(os.path.dirname(clf_path), exist_ok=True)
    os.makedirs(os.path.dirname(reg_path), exist_ok=True)
    
    # Save classification model directly for prediction service
    joblib.dump(clf_model, clf_path)
    logger.info(f"Classification model saved to {clf_path}")
    
    # Save regression models as a tuple/dict
    reg_obj = {
        'total_model': total_model,
        'spread_model': spread_model,
    }
    joblib.dump(reg_obj, reg_path)
    logger.info(f"Regression models saved to {reg_path}")
    
    # Save metadata separately
    meta_path = clf_path.replace('.pkl', '_meta.pkl')
    joblib.dump(metadata, meta_path)
    logger.info(f"Metadata saved to {meta_path}")


def verify_models(clf_path: str, reg_path: str) -> bool:
    """Verify both models can be loaded and used."""
    try:
        # Classification
        clf_model = joblib.load(clf_path)
        
        # Try to get feature names from metadata
        meta_path = clf_path.replace('.pkl', '_meta.pkl')
        feature_names = []
        if os.path.exists(meta_path):
            metadata = joblib.load(meta_path)
            feature_names = metadata.get('feature_names', [])
        
        dummy_X = np.zeros((1, len(feature_names) if feature_names else 40))
        _ = clf_model.predict_proba(dummy_X)
        logger.info("✓ Classification model verification passed")
        
        # Regression
        reg_saved = joblib.load(reg_path)
        total_model = reg_saved['total_model']
        spread_model = reg_saved['spread_model']
        
        _ = total_model.predict(dummy_X)
        _ = spread_model.predict(dummy_X)
        logger.info("✓ Regression models verification passed")
        
        return True
    except Exception as e:
        logger.error(f"✗ Model verification failed: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("  BASKETBALL PREDICTION MODELS — TRAINING")
    logger.info("=" * 60)
    
    # Configuration
    START_YEAR = 2010
    END_YEAR = 2023
    VALIDATION_YEAR = 2024
    CLF_MODEL_PATH = "models/basketball_classifier.pkl"
    REG_MODEL_PATH = "models/basketball_regressor.pkl"
    
    # 1. Fetch historical data
    logger.info("\n[1/7] Fetching historical NBA data...")
    df = fetch_historical_nba_data(START_YEAR, END_YEAR)
    
    if df.empty:
        logger.error("No data available for training")
        return 1
    
    # 2. Prepare BasketballGame objects
    logger.info("\n[2/7] Preparing training data...")
    all_games = prepare_basketball_games(df)
    logger.info(f"Created {len(all_games)} BasketballGame objects")
    
    if len(all_games) < 100:
        logger.error("Not enough games for training")
        return 1
    
    # Sort by date
    all_games.sort(key=lambda g: g.game_date)
    
    # 3. Feature extraction
    logger.info("\n[3/7] Extracting features...")
    extractor = BasketballFeatureExtractor()
    feature_names = extractor.get_feature_names()
    logger.info(f"Feature count: {len(feature_names)}")
    
    X, y_win, y_total, y_spread, dates = extract_features_and_targets(
        all_games, all_games, feature_names
    )
    logger.info(f"Extracted features: {X.shape}")
    logger.info(f"Targets - Win: {y_win.shape}, Total: {y_total.shape}, Spread: {y_spread.shape}")
    
    # 4. Train classification model
    logger.info("\n[4/7] Training classification model (home_win)...")
    clf_model, clf_metrics = train_classification_model(
        X, y_win, dates, feature_names
    )
    
    # 5. Train regression models
    logger.info("\n[5/7] Training regression models (total_points, home_spread)...")
    total_model, spread_model, total_metrics, spread_metrics = train_regression_models(
        X, y_total, y_spread, dates, feature_names
    )
    
    # 6. Save models
    logger.info("\n[6/7] Saving models...")
    metadata = {
        'model_type': 'CalibratedClassifierCV + XGBoost/LightGBM Regressors',
        'base_estimator': 'XGBoost' if XGBOOST_AVAILABLE else ('LightGBM' if LIGHTGBM_AVAILABLE else 'GradientBoosting'),
        'training_period': f"{START_YEAR}-{END_YEAR}",
        'validation_period': str(VALIDATION_YEAR),
        'feature_count': len(feature_names),
        'feature_names': feature_names,
        'classification_metrics': clf_metrics,
        'total_points_metrics': total_metrics,
        'home_spread_metrics': spread_metrics,
        'calibration_method': 'isotonic',
        'cv_folds': 3,
    }
    save_models(clf_model, total_model, spread_model, CLF_MODEL_PATH, REG_MODEL_PATH, metadata)
    
    # 7. Verify
    logger.info("\n[7/7] Verifying models...")
    verify_models(CLF_MODEL_PATH, REG_MODEL_PATH)
    
    logger.info("=" * 60)
    logger.info("  TRAINING COMPLETE")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())