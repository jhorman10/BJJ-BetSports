import sys
import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from datetime import datetime

# Add the backend root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.data_sources.tennis_data_source import TennisDataSource
from src.domain.services.tennis_feature_extractor import TennisFeatureExtractor
from src.domain.entities.tennis_match import TennisMatch

OLD_ACCURACY = 0.855  # Reference only — actual baseline computed during training

def prepare_training_data(df: pd.DataFrame):
    """
    Convert raw DataFrame into a format suitable for feature extraction.
    We create TennisMatch objects for each row.
    """
    matches = []
    for _, row in df.iterrows():
        try:
            # Determine winner and loser info
            # The CSV format has 'winner_name', 'loser_name', etc.
            # We want to randomly flip players so the model doesn't learn that P1 always wins
            # But for simplicity in this script, we'll keep P1 as winner (target=1)
            # and later create a flipped version (target=0) for balance.

            # Extract odds if available
            p1_odds = None
            p2_odds = None
            if 'winner_odds' in df.columns and pd.notna(row.get('winner_odds')):
                try:
                    p1_odds = float(row['winner_odds'])
                except (ValueError, TypeError):
                    pass
            if 'loser_odds' in df.columns and pd.notna(row.get('loser_odds')):
                try:
                    p2_odds = float(row['loser_odds'])
                except (ValueError, TypeError):
                    pass

            def safe_int(val, default=0):
                """Convert CSV value to int, handling float strings like '2.0'."""
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

            match = TennisMatch(
                match_id=str(row.get('match_num', '')),
                tournament_name=row.get('tourney_name', ''),
                surface=row.get('surface', 'Hard'),
                tourney_level=row.get('tourney_level', 'A'),
                round_name=row.get('round', ''),
                match_date=pd.to_datetime(row.get('tourney_date', datetime.now().date())).date(),
                best_of=safe_int(row.get('best_of', 3), 3),

                p1_name=row.get('winner_name', ''),
                p1_id=str(row.get('winner_id', '')),
                p1_rank=safe_int(row.get('winner_rank'), 100),
                p1_rank_points=safe_int(row.get('winner_rank_points'), 0),
                p1_age=safe_float(row.get('winner_age'), 25.0),
                p1_hand=row.get('winner_hand', 'R'),
                p1_height=safe_int(row.get('winner_ht'), 180),
                p1_seed=safe_int(row.get('winner_seed'), 0),
                p1_entry=row.get('winner_entry', ''),

                p2_name=row.get('loser_name', ''),
                p2_id=str(row.get('loser_id', '')),
                p2_rank=safe_int(row.get('loser_rank'), 100),
                p2_rank_points=safe_int(row.get('loser_rank_points'), 0),
                p2_age=safe_float(row.get('loser_age'), 25.0),
                p2_hand=row.get('loser_hand', 'R'),
                p2_height=safe_int(row.get('loser_ht'), 180),
                p2_seed=safe_int(row.get('loser_seed'), 0),
                p2_entry=row.get('loser_entry', ''),

                score=row.get('score', ''),
                winner_id=str(row.get('winner_id', '')),
                loser_id=str(row.get('loser_id', '')),

                p1_odds=p1_odds,
                p2_odds=p2_odds,
            )
            matches.append(match)
        except Exception as e:
            print(f"Error processing row: {e}")
            continue

    return matches

def train_model(start_year=2000, end_year=2023):
    print(f"{'='*60}")
    print(f"  TENNIS PREDICTION MODEL — TRAINING")
    print(f"{'='*60}")

    # 1. Fetch Data — try combined first, fallback to range
    source = TennisDataSource(tour="atp")
    print("\n[1/6] Fetching data...")
    df = source.fetch_combined_data()

    if df.empty:
        print("  Combined CSV not available, fetching year-by-year...")
        df = source.fetch_matches_range(start_year, end_year)

    if df.empty:
        print("No data fetched.")
        return

    print(f"  Total matches loaded: {len(df)}")

    # 2. Prepare Data
    print("\n[2/6] Preparing training data...")
    matches = prepare_training_data(df)
    print(f"  Created {len(matches)} TennisMatch objects")

    # 3. Feature Extraction
    print("\n[3/6] Extracting features...")
    # Initialize extractor with the full dataset to compute rolling stats + H2H correctly
    extractor = TennisFeatureExtractor(historical_data=df)

    X = []
    y = []
    all_features = []  # Store feature dicts for baseline comparison

    feature_names = extractor.get_feature_names()
    print(f"  Feature count: {len(feature_names)}")

    for match in matches:
        # Positive sample (Winner as P1)
        features = extractor.extract_features(match)
        X.append([features[f] for f in feature_names])
        all_features.append(features)
        y.append(1)

        # Negative sample (Flip players)
        # We create a synthetic match where the loser is P1 and winner is P2
        # This doubles the dataset and balances the classes
        flipped_match = TennisMatch(
            match_id=match.match_id + "_flip",
            tournament_name=match.tournament_name,
            surface=match.surface,
            tourney_level=match.tourney_level,
            round_name=match.round_name,
            match_date=match.match_date,
            best_of=match.best_of,

            p1_name=match.p2_name,
            p1_id=match.p2_id,
            p1_rank=match.p2_rank,
            p1_rank_points=match.p2_rank_points,
            p1_age=match.p2_age,
            p1_hand=match.p2_hand,
            p1_height=match.p2_height,
            p1_seed=match.p2_seed,
            p1_entry=match.p2_entry,

            p2_name=match.p1_name,
            p2_id=match.p1_id,
            p2_rank=match.p1_rank,
            p2_rank_points=match.p1_rank_points,
            p2_age=match.p1_age,
            p2_hand=match.p1_hand,
            p2_height=match.p1_height,
            p2_seed=match.p1_seed,
            p2_entry=match.p1_entry,

            score=match.score,
            winner_id=match.winner_id,
            loser_id=match.loser_id,

            p1_odds=match.p2_odds,
            p2_odds=match.p1_odds,
        )

        features_flipped = extractor.extract_features(flipped_match)
        X.append([features_flipped[f] for f in feature_names])
        all_features.append(features_flipped)
        y.append(0)  # P1 (original loser) loses

    print(f"  Training samples: {len(X)}")

    # 4. Train Model
    print("\n[4/6] Training RandomForestClassifier...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    clf.fit(X, y)

    # 5. Evaluate (Simple Split)
    print("\n[5/6] Evaluating...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    clf_eval = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    clf_eval.fit(X_train, y_train)
    y_pred = clf_eval.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    print(classification_report(y_test, y_pred))

    # Feature importance
    importances = clf_eval.feature_importances_
    feature_importance = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    print("\n  Top 15 Feature Importances:")
    for name, imp in feature_importance[:15]:
        print(f"    {name:30s} {imp:.4f}")

    print(f"{'='*60}")
    print(f"  ACCURACY COMPARISON")
    print(f"{'='*60}")

    # Train baseline model (old features only) for fair comparison
    print("\n  Training baseline model (old features only)...")
    old_feature_names = [
        'rank_diff', 'rank_points_diff', 'age_diff', 'height_diff',
        'p1_is_lefty', 'p2_is_lefty', 'best_of',
        'h2h_total', 'h2h_p1_win_rate', 'h2h_p2_win_rate',
        'p1_seed', 'p2_seed', 'p1_is_qualifier', 'p2_is_qualifier'
    ]
    surface_features_old = [f'surface_{s}' for s in TennisFeatureExtractor.SURFACES]
    level_features_old = [f'level_{l}' for l in TennisFeatureExtractor.LEVELS]
    old_feature_names += surface_features_old + level_features_old

    X_old = [[features[f] for f in old_feature_names] for features in all_features]
    X_old_train, X_old_test, y_old_train, y_old_test = train_test_split(X_old, y, test_size=0.2, random_state=42)
    clf_old = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    clf_old.fit(X_old_train, y_old_train)
    y_old_pred = clf_old.predict(X_old_test)
    old_accuracy = accuracy_score(y_old_test, y_old_pred)

    print(f"  Old features (14 base + surface + level):  {old_accuracy:.2%}")
    print(f"  New features (rolling stats + odds):       {accuracy:.2%}")
    improvement = accuracy - old_accuracy
    if improvement > 0:
        print(f"  Improvement: +{improvement:.2%}")
    elif improvement < 0:
        print(f"  Change: {improvement:.2%}")
    else:
        print(f"  No change")
    print(f"{'='*60}")

    # 6. Save Model
    print(f"\n[6/6] Saving model...")
    model_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "tennis_classifier.pkl")
    joblib.dump(clf, model_path)
    print(f"  Model saved to {model_path}")

if __name__ == "__main__":
    train_model(start_year=2010, end_year=2023)
