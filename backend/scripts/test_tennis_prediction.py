import sys
import os
from datetime import date

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.entities.tennis_match import TennisMatch
from src.domain.services.tennis_feature_extractor import TennisFeatureExtractor
from src.domain.services.tennis_prediction_service import TennisPredictionService

def test_prediction():
    print("=" * 60)
    print("  TENNIS PREDICTION TEST")
    print("=" * 60)

    # 1. Load historical data for feature extraction (H2H, rolling stats)
    from src.infrastructure.data_sources.tennis_data_source import TennisDataSource
    source = TennisDataSource(tour="atp")
    print("\nLoading historical data (2014-2023)...")

    # Load 10 years of data for rolling stats
    hist_df = source.fetch_matches_range(2014, 2023)
    print(f"  Loaded {len(hist_df)} historical matches")

    # 2. Initialize services
    extractor = TennisFeatureExtractor(historical_data=hist_df)
    predictor = TennisPredictionService(feature_extractor=extractor)

    # 3. Create a hypothetical match
    # Alcaraz vs Sinner with betting odds
    match = TennisMatch(
        match_id="test_001",
        tournament_name="Australian Open",
        surface="Hard",
        tourney_level="G",  # Grand Slam
        round_name="F",  # Final
        match_date=date(2024, 1, 28),
        best_of=5,

        p1_name="Carlos Alcaraz",
        p1_rank=2,
        p1_rank_points=8855,
        p1_age=20.0,
        p1_hand="R",
        p1_height=183,

        p2_name="Jannik Sinner",
        p2_rank=4,
        p2_rank_points=7020,
        p2_age=22.0,
        p2_hand="R",
        p2_height=188,

        p1_odds=1.8,  # Decimal odds — Alcaraz favored
        p2_odds=2.1,  # Decimal odds — Sinner underdog
    )

    # 4. Show features
    features = extractor.extract_features(match)
    feature_names = extractor.get_feature_names()
    print(f"\n  Features extracted: {len(feature_names)}")
    print(f"\n  Rolling Stats for {match.p1_name}:")
    print(f"    Win rate (last 10): {features['p1_win_rate_10']:.2%}")
    print(f"    Win rate (last 20): {features['p1_win_rate_20']:.2%}")
    print(f"    Ace rate (last 10): {features['p1_ace_rate_10']:.2f}")
    print(f"    Surface win rate:   {features['p1_surface_win_rate']:.2%}")
    print(f"    Implied prob (odds): {features['p1_implied_prob']:.2%}")
    print(f"\n  Rolling Stats for {match.p2_name}:")
    print(f"    Win rate (last 10): {features['p2_win_rate_10']:.2%}")
    print(f"    Win rate (last 20): {features['p2_win_rate_20']:.2%}")
    print(f"    Ace rate (last 10): {features['p2_ace_rate_10']:.2f}")
    print(f"    Surface win rate:   {features['p2_surface_win_rate']:.2%}")
    print(f"    Implied prob (odds): {features['p2_implied_prob']:.2%}")
    print(f"    Odds diff:          {features['odds_diff']:.4f}")

    # 5. Predict
    prediction = predictor.predict(match)

    if prediction:
        print(f"\n{'='*60}")
        print(f"  PREDICTION")
        print(f"{'='*60}")
        print(f"  Match: {match.p1_name} vs {match.p2_name}")
        print(f"  Surface: {match.surface}")
        print(f"  Odds: {match.p1_name} {match.p1_odds} | {match.p2_name} {match.p2_odds}")
        print(f"  Result:")
        print(f"    {match.p1_name} Win Probability: {prediction.p1_win_prob:.2%}")
        print(f"    {match.p2_name} Win Probability: {prediction.p2_win_prob:.2%}")
        print(f"    Predicted Winner: {prediction.predicted_winner}")
        print(f"    Confidence: {prediction.confidence:.2%}")
        print(f"{'='*60}")
    else:
        print("Prediction failed. Check model path.")

if __name__ == "__main__":
    test_prediction()
