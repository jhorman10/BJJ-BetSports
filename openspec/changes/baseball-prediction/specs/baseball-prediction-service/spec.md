# Spec: baseball-prediction-service

## Purpose

Orchestrates the full prediction pipeline: loads the trained RandomForest model, extracts features, generates predictions for 6 markets, detects value bets, and extracts key contributing factors. Mirrors `TennisPredictionService` pattern.

## Requirements

### Requirement: Model loading and lifecycle

`BaseballPredictionService` MUST load the trained model (joblib file) on first use and cache it in memory. The service MUST detect model file changes and reload automatically. Model path MUST be configurable via environment variable or settings.

#### Scenario: Model loaded on first prediction

- GIVEN a `BaseballPredictionService` instance with no model loaded
- WHEN `predict(game)` is called
- THEN the model file is loaded from disk
- AND subsequent predictions reuse the cached model

#### Scenario: Model file missing

- GIVEN the model file does not exist at configured path
- WHEN `predict(game)` is called
- THEN a `ModelNotFoundError` is raised with descriptive message

### Requirement: Prediction flow

The prediction flow MUST execute in this order:
1. Validate input game data
2. Fetch historical data for both teams
3. Extract 46 features via `BaseballFeatureExtractor`
4. Run model inference
5. Generate market predictions from model output
6. Detect value bets if odds provided
7. Extract key factors
8. Return structured prediction response

#### Scenario: Full prediction flow

- GIVEN a valid `BaseballGame` with both teams having historical data
- WHEN `predict(game)` is called
- THEN all 8 steps execute in order
- AND the response contains all 6 market predictions
- AND key factors are populated

#### Scenario: Prediction with unconfirmed starter

- GIVEN a `BaseballGame` with `home_pitcher_id=None`
- WHEN `predict(game)` is called
- THEN pitcher-dependent markets (First 5 Innings, Moneyline) use team-level pitching averages
- AND the response includes `"unconfirmed_starter": true` flag

### Requirement: Market generation — 6 markets

The service MUST generate predictions for these 6 markets:

| Market | Type | Output |
|--------|------|--------|
| Moneyline | Binary | Home win probability (0-1) |
| Run Line (-1.5) | Binary | Home covers -1.5 probability |
| Total Runs O/U | Threshold | Over/under probability at 7.5, 8.5, 9.5 |
| First 5 Innings | Binary | Home lead after 5 innings probability |
| Team Total Runs | Threshold | Home team O/U at 3.5, 4.5, 5.5 |
| Both Teams Score | Binary | Both score >= 1 probability |

#### Scenario: Moneyline probabilities sum to 1

- GIVEN a prediction response
- WHEN Moneyline market is inspected
- THEN `home_prob + away_prob ≈ 1.0` (within 0.01 tolerance)

#### Scenario: Total Runs thresholds

- GIVEN a prediction response
- WHEN Total Runs market is inspected
- THEN it contains probabilities for 7.5, 8.5, and 9.5 thresholds
- AND probabilities decrease as threshold increases

### Requirement: Value bet detection

When betting odds are provided, the service MUST compare implied probabilities against model probabilities. A value bet exists when `model_prob > implied_prob + margin`. The margin threshold MUST be configurable (default 2%).

#### Scenario: Value bet detected

- GIVEN a game where model gives home team 60% win probability
- AND betting odds imply 50% home probability
- WHEN value bets are computed
- THEN the home moneyline is flagged as a value bet
- AND the edge is reported as `60% - 50% = 10%`

#### Scenario: No value bets

- GIVEN a game where model probabilities closely match implied probabilities
- WHEN value bets are computed
- THEN no markets are flagged as value bets

### Requirement: Key factors extraction

For each prediction, the service MUST identify the top 3-5 features that most influenced the outcome. This SHOULD use feature importance from the RandomForest or SHAP values.

#### Scenario: Key factors returned

- GIVEN a prediction for a specific game
- WHEN key factors are extracted
- THEN 3-5 factors are returned with feature name and contribution direction
- AND factors are ranked by absolute impact

### Requirement: Prediction response structure

The prediction response MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `game_id` | `str` | Input game identifier |
| `markets` | `dict` | 6 market predictions |
| `value_bets` | `list` | Detected value opportunities |
| `key_factors` | `list` | Top influencing features |
| `confidence` | `float` | Overall model confidence (0-1) |
| `unconfirmed_starter` | `bool` | Whether pitcher was unconfirmed |
| `model_version` | `str` | Model file version/timestamp |

#### Scenario: Response serialization

- GIVEN a completed prediction
- WHEN the response is serialized to JSON
- THEN all fields are JSON-compatible
- AND probabilities are between 0 and 1

## Acceptance Criteria

- [ ] Model loads on first call and caches in memory
- [ ] 6 markets generated with correct probability ranges
- [ ] Value bets detected when odds provided and margin exceeded
- [ ] 3-5 key factors extracted per prediction
- [ ] Unconfirmed starter flag propagated through response
- [ ] Full flow completes in < 500ms for cached model
