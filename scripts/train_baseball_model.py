#!/usr/bin/env python3
"""
Training script for baseball prediction model.
Loads Retrosheet data, extracts 46 features, trains RandomForestClassifier,
and saves the model + scaler to disk.

Usage:
    python scripts/train_baseball_model.py
"""

import os
import sys
import logging
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.data_sources.retrosheet_data_source import RetrosheetDataSource
from src.domain.services.baseball_feature_extractor import BaseballFeatureExtractor
from src.domain.entities.baseball_game import BaseballGame

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "baseball_classifier.pkl")
SCALER_PATH = os.path.join(MODEL_DIR, "baseball_scaler.pkl")


def prepare_training_data(df: pd.DataFrame, feature_extractor: BaseballFeatureExtractor):
    """Convert raw data into feature matrix X and label vector y."""
    X_rows = []
    y_labels = []

    for _, row in df.iterrows():
        try:
            home_score = int(float(row.get("home_score", 0)))
            away_score = int(float(row.get("away_score", 0)))
        except (ValueError, TypeError):
            continue

        game_date_str = row.get("date")
        try:
            game_date = pd.to_datetime(game_date_str).date()
        except Exception:
            continue

        game = BaseballGame(
            game_id=str(row.get("game_id", "")),
            date=game_date,
            home_team=row.get("home_team", ""),
            away_team=row.get("away_team", ""),
            home_score=home_score,
            away_score=away_score,
            venue=row.get("venue", ""),
        )

        features = feature_extractor.extract_features(game)
        feature_names = feature_extractor.get_feature_names()
        X_rows.append([features[f] for f in feature_names])
        y_labels.append(1 if home_score > away_score else 0)

    return np.array(X_rows), np.array(y_labels)


def main():
    logger.info("Starting baseball model training...")

    # 1. Fetch historical data
    data_source = RetrosheetDataSource()
    logger.info("Fetching Retrosheet data (2015-2024)...")
    df = data_source.fetch_range(2015, 2024)
    if df.empty:
        logger.error("No data fetched. Exiting.")
        return
    logger.info(f"Fetched {len(df)} games.")

    # 2. Initialize feature extractor
    feature_extractor = BaseballFeatureExtractor()

    # 3. Prepare training data
    logger.info("Extracting features...")
    X, y = prepare_training_data(df, feature_extractor)
    logger.info(f"Feature matrix shape: {X.shape}, Labels: {len(y)}")

    if len(X) == 0:
        logger.error("No training samples generated. Exiting.")
        return

    # 4. Temporal split (80/20 — no shuffle for time series)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # 5. Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 6. Train model
    logger.info("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_scaled, y_train)

    # 7. Evaluate
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Test accuracy: {accuracy:.4f}")
    logger.info(f"\n{classification_report(y_test, y_pred, target_names=['Away Win', 'Home Win'])}")

    # 8. Save model and scaler
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")
    logger.info(f"Scaler saved to {SCALER_PATH}")

    # 9. Feature importance
    feature_names = feature_extractor.get_feature_names()
    importances = model.feature_importances_
    top_indices = np.argsort(importances)[::-1][:10]
    logger.info("\nTop 10 features:")
    for i in top_indices:
        logger.info(f"  {feature_names[i]}: {importances[i]:.4f}")


if __name__ == "__main__":
    main()
