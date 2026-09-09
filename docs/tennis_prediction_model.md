# Tennis Match Prediction Model

This document outlines the architecture and implementation of the Tennis Match Prediction Model.

## 1. Objective

To predict the outcome of professional tennis matches (who will win) using historical match data, player statistics, and match characteristics.

## 2. Data Sources

The model utilizes the following data sources:

### 2.1. Historical Data (Training & Backtesting)
- **Kaggle / GitHub Datasets**:
    - **ATP Data (2000-2025)**: `https://github.com/jegqwll/tennis_atp_2000_2025`
    - **Format**: Yearly CSV files (e.g., `atp_matches_2023.csv`).
    - **Content**: Match results, player rankings, detailed match stats (aces, double faults, serve percentages, break points) from 1991 onwards.
- **Kaggle Datasets**:
    - `ATP matches` (by sijovm): Consolidated ATP match data.
    - `A large Tennis dataset for ATP and ITF betting` (by ehallmar): Includes betting odds and ITF data.

### 2.2. Live Data (Real-time Predictions)
- **Live Tennis API**: `https://livetennisapi.com`
    - **Free Tier**: Live scores, current players, fixtures (30 req/min, 100/day).
    - **Paid Tiers**: Historical results (Basic), Odds (Pro), Win Probability (Ultra).
- **SportScore API**: `https://sportscore.com`
    - **Python Client**: `pip install sportscore`
    - **Free Tier**: Live scores, match details, standings (requires attribution backlink).

## 3. Model Architecture

### 3.1. Type
- **Classification**: Binary (Player 1 Wins vs. Player 2 Wins).
- **Algorithm**: `RandomForestClassifier` (consistent with the Football prediction model).

### 3.2. Features
The model processes the following input features:

- **Player Rankings**: Current ATP/WTA ranking and ranking points.
- **Player Statistics**: Age, handedness, height.
- **Match Context**: Surface type (Hard, Clay, Grass), tournament level (Grand Slam, ATP, Masters), round.
- **Head-to-Head (H2H)**: Historical win rate between the two players.
- **Recent Form**: Win/loss ratio in the last N matches (e.g., last 10 matches).
- **Surface Preference**: Player's historical win rate on the specific surface.

### 3.3. Training
- **Target Variable**: Winner of the match (1 if Player 1 wins, 0 if Player 2 wins).
- **Dataset**: Historical match data from ATP/WTA tours (2010-2023 used for initial training).
- **Performance**: Initial training achieved ~85.5% accuracy on the holdout set.

## 4. Implementation Plan

1.  **Data Collection**: Implemented scraper to ingest historical data from GitHub.
2.  **Preprocessing**: Implemented data cleaning and normalization in `TennisFeatureExtractor`.
3.  **Feature Engineering**: Implemented rolling averages, H2H stats, and surface-specific metrics.
4.  **Training Pipeline**: Implemented `train_tennis_model.py` script.
5.  **Deployment**: Serve predictions via the FastAPI backend.

## 5. File Structure

- `backend/src/domain/entities/tennis_match.py`: Data model for tennis matches.
- `backend/src/domain/services/tennis_feature_extractor.py`: Feature engineering logic.
- `backend/src/domain/services/tennis_prediction_service.py`: Prediction logic.
- `backend/src/infrastructure/data_sources/tennis_data_source.py`: Data fetching (GitHub API).
- `backend/scripts/train_tennis_model.py`: Training script.
- `backend/models/tennis_classifier.pkl`: Saved trained model.
