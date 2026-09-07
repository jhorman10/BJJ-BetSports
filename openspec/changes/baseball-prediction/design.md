# Design: Baseball Prediction Module

## Technical Approach

Mirror the existing tennis prediction architecture — same layered structure (entity → data source → feature extractor → prediction service → API → frontend) with baseball-specific domain logic. Use RandomForestClassifier for consistency with the tennis module. Data sourced from Retrosheet CSVs (historical) and MLB Stats API (fixtures/live).

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|----------|--------|----------|--------|
| ML Algorithm | RandomForest vs XGBoost vs Logistic | RF matches tennis pattern; XGBoost slightly better but adds dependency | **RandomForestClassifier** |
| Data Source | Retrosheet CSV vs web scrape | Retrosheet is free, structured, reliable; scrape is fragile | **Retrosheet CSV** |
| Feature Count | 46 (spec) vs fewer | 46 covers all categories; feature selection is post-training concern | **46 features** |
| Frontend Path | `client/` (spec) vs `frontend/` (actual) | Spec says `client/` but repo uses `frontend/` | **`frontend/`** — follow repo convention |
| Model Storage | File-based joblib (tennis pattern) vs DB | File matches existing pattern; DB adds infra complexity | **joblib file** |
| Fixture API | MLB Stats API (free) vs paid | Free, no auth, sufficient for upcoming games | **MLB Stats API** |

## Data Flow

```
Retrosheet CSV ──→ RetrosheetDataSource ──→ Historical Data (DataFrame)
                                                    │
MLB Stats API ──→ MLBFixtureDataSource ──→ Upcoming Games ──→ BaseballGame entity
                                                    │
                                                    ▼
                                        BaseballFeatureExtractor
                                         (46 features, rolling stats)
                                                    │
                                                    ▼
                                        BaseballPredictionService
                                         (model inference, market gen)
                                                    │
                                        ┌───────────┴───────────┐
                                        ▼                       ▼
                                   API Response          Value Bets + Key Factors
                                        │
                                        ▼
                                   Frontend Components
```

## Data Model

### BaseballGame

```python
@dataclass
class BaseballGame:
    # Required
    game_id: str
    date: str           # ISO 8601
    home_team: str      # 3-letter abbreviation
    away_team: str
    home_score: int
    away_score: int
    venue: str
    day_night: str      # "day" | "night"

    # Optional — pitchers
    home_pitcher_id: Optional[str] = None
    away_pitcher_id: Optional[str] = None
    home_pitcher_name: Optional[str] = None
    away_pitcher_name: Optional[str] = None

    # Optional — context
    season: Optional[int] = None       # derived from date
    series_id: Optional[str] = None
    home_odds: Optional[float] = None
    away_odds: Optional[float] = None
```

### Feature Vector (46 features, 7 groups)

| Group | # | Features | Default |
|-------|---|----------|---------|
| Pitcher Matchup | 8 | home/away ERA, WHIP, K/9, FIP proxy | Team avg |
| Team Batting | 10 | OPS, wOBA proxy, R/G, HR/G, BABIP | League avg |
| Bullpen/Pitching | 8 | Bullpen ERA, WHIP, saves, team ERA | League avg |
| Recent Form | 6 | Last-10 W%, run diff avg, streak | 0.5 / 0.0 |
| Head-to-Head | 3 | Season H2H, overall, home/away | 0.5 |
| Context | 8 | Home flag, day/night, month, division, park factor, travel, rest days | Computed |
| Betting Odds | 3 | Implied probs, odds diff | 0.0 |

### Model Input/Output

```python
# Input: 46-element float vector
X = [[f1, f2, ..., f46]]

# Output: 2-class probability
proba = model.predict_proba(X)  # [home_loss_prob, home_win_prob]
```

## Feature Engineering

### Pitcher Matchup (8 features)

| Feature | Formula |
|---------|---------|
| `home_era` | Season ERA for home starter |
| `away_era` | Season ERA for away starter |
| `home_whip` | Season WHIP for home starter |
| `away_whip` | Season WHIP for away starter |
| `home_k_per_9` | `K * 9 / IP` |
| `away_k_per_9` | Same for away |
| `home_fip_proxy` | `3 + (13*HR + 3*(BB+HBP) - 2*K) / IP` |
| `away_fip_proxy` | Same for away |

### Team Batting (10 features)

| Feature | Formula |
|---------|---------|
| `home_ops` | `OBP + SLG` |
| `away_ops` | Same |
| `home_woba_proxy` | `(0.69*BB + 0.72*H + 0.89*2B + 1.27*3B + 1.62*HR) / (AB+BB+SF+HBP)` |
| `away_woba_proxy` | Same |
| `home_r_per_game` | `RS / games_played` |
| `away_r_per_game` | Same |
| `home_hr_per_game` | `HR / games_played` |
| `away_hr_per_game` | Same |
| `home_babip` | `(H - HR) / (AB - K - HR + SF)` |
| `away_babip` | Same |

### Rolling Aggregation

- **Last 10 games**: Win%, run differential avg, streak (for form features)
- **Season-to-date**: All cumulative stats (ERA, OPS, WHIP, etc.)
- **H2H**: Filter by team pair, compute win% season and all-time

### Missing Data Handling

| Source | Fallback |
|--------|----------|
| Pitcher not confirmed | Team-level pitching averages |
| Missing batting stats | League average |
| No H2H history | 0.5 (neutral) |
| No odds | 0.0 + flag |

### Normalization

Z-score normalization using pre-fitted scaler from training. Scaler saved alongside model in joblib file.

## Model Architecture

| Property | Value |
|----------|-------|
| Algorithm | `RandomForestClassifier` |
| Training range | 2015–2024 seasons |
| Train/test split | 80/20, temporal (no shuffle) |
| Features | 46 |
| `n_estimators` | 200 |
| `max_depth` | 12 |
| `min_samples_split` | 10 |
| `min_samples_leaf` | 5 |
| `random_state` | 42 |
| Expected accuracy | ~58–62% (baseball is high-variance) |

Model saved to `models/baseball_classifier.pkl` with scaler in same joblib bundle.

## Market Generation Logic

### 1. Moneyline
- Direct from model: `home_prob = model.predict_proba(X)[0][1]`
- `away_prob = 1 - home_prob`

### 2. Run Line (-1.5)
- Estimate: `P(home covers -1.5) ≈ home_prob * 0.42` (calibrated coefficient)
- `P(away covers +1.5) = 1 - home_cover_prob`

### 3. Total Runs O/U
- Estimate expected total from team R/G stats and park factor
- `P(over T) = sigmoid((expected_total - T) / scale)`
- Thresholds: 7.5, 8.5, 9.5

### 4. First 5 Innings
- Dampened moneyline: `home_f5 = 0.5 + (home_prob - 0.5) * 0.75`
- Accounts for starter-heavy phase

### 5. Team Total Runs
- Home team O/U at 3.5, 4.5, 5.5
- Based on home R/G adjusted for opposing pitcher ERA

### 6. Both Teams Score
- `P(both score) = 1 - P(home shutout) * P(away shutout)`
- Shutout prob estimated from team pitching stats

### Confidence Levels

| Level | Threshold |
|-------|-----------|
| High | Model probability > 0.65 |
| Medium | 0.55–0.65 |
| Low | < 0.55 |

### Value Bet Detection

`edge = model_prob - (1 / decimal_odds)` → flag if edge > 0.02

## API Design

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/baseball/predict` | Single game prediction |
| `GET` | `/baseball/games` | Upcoming games |
| `GET` | `/baseball/series` | Grouped series |
| `GET` | `/baseball/predictions/{series_id}` | Series predictions |

### Request — POST /baseball/predict

```json
{
  "home_team": "NYY",
  "away_team": "BOS",
  "date": "2025-07-15",
  "home_pitcher_id": "605288",
  "away_pitcher_id": "605141",
  "odds": {"home_decimal": 1.85, "away_decimal": 2.10}
}
```

### Response — POST /baseball/predict

```json
{
  "game_id": "baseball_NYY_BOS_20250715",
  "markets": {
    "moneyline": {"home_prob": 0.55, "away_prob": 0.45},
    "run_line": {"home_cover_prob": 0.42, "away_cover_prob": 0.58},
    "total_runs": {"over_7.5": 0.52, "over_8.5": 0.38, "over_9.5": 0.25},
    "first_5_innings": {"home_lead_prob": 0.53, "away_lead_prob": 0.47},
    "team_total_runs": {"home_over_4.5": 0.48, "away_over_4.5": 0.44},
    "both_teams_score": {"yes_prob": 0.82, "no_prob": 0.18}
  },
  "value_bets": [...],
  "key_factors": [...],
  "confidence": 0.62,
  "unconfirmed_starter": false,
  "model_version": "2025-07-01"
}
```

### Caching

- Fixture data: 1 hour TTL (live data changes frequently)
- Historical data: permanent cache (immutable past seasons)
- Model: in-memory cache, reload on file change detection

## Frontend Architecture

### Component Tree

```
BaseballPredictionPage
├── BaseballSeriesView (groups games by series)
│   └── BaseballGameCard (one per game)
│       ├── Team logos + names + pitchers (or TBD)
│       ├── Date/venue/time
│       └── Quick moneyline summary
├── BaseballMarketsPanel (6-market grid)
│   └── BaseballMarketCard (one per market)
│       ├── Probability bars
│       ├── Value bet badge (green >5%, yellow 2-5%)
│       └── Threshold selector (for O/U markets)
└── BaseballKeyFactors
    └── Factor list (feature name, value, direction)
```

### State Management

Zustand store (same pattern as tennis):
- `useBaseballStore`: games, predictions, loading, error, selected series
- Actions: `fetchGames()`, `fetchPredictions(seriesId)`, `selectGame()`

### Responsive Design

| Breakpoint | Layout |
|------------|--------|
| Desktop (>1024px) | 2-column game card grid |
| Tablet (768–1024px) | 1-column full-width |
| Mobile (<768px) | Stacked, collapsible market panels |

## File Changes

### New Files

| File | Description |
|------|-------------|
| `backend/src/domain/entities/baseball_game.py` | BaseballGame dataclass |
| `backend/src/domain/services/baseball_feature_extractor.py` | 46-feature extraction |
| `backend/src/domain/services/baseball_prediction_service.py` | Prediction + market generation |
| `backend/src/infrastructure/data_sources/retrosheet_data_source.py` | Retrosheet CSV fetching |
| `backend/src/infrastructure/data_sources/mlb_fixture_source.py` | MLB Stats API fixtures |
| `backend/src/api/routers/baseball_router.py` | 4 API endpoints |
| `backend/src/api/dtos/baseball_dtos.py` | Pydantic request/response models |
| `frontend/src/presentation/components/BaseballPrediction/BaseballPredictionPage.tsx` | Main page |
| `frontend/src/presentation/components/BaseballPrediction/BaseballGameCard.tsx` | Game card |
| `frontend/src/presentation/components/BaseballPrediction/BaseballMarketsPanel.tsx` | Markets grid |
| `frontend/src/presentation/components/BaseballPrediction/BaseballMarketCard.tsx` | Single market |
| `frontend/src/presentation/components/BaseballPrediction/BaseballKeyFactors.tsx` | Key factors |
| `frontend/src/presentation/components/BaseballPrediction/BaseballSeriesView.tsx` | Series view |
| `frontend/src/presentation/components/BaseballPrediction/index.ts` | Barrel exports |

### Modified Files

| File | Change |
|------|--------|
| `frontend/src/App.tsx` | Add `/baseball` route |
| `backend/src/api/routers/` (router registry) | Register baseball router |

### Dependencies Between Files

```
baseball_game.py
    ← retrosheet_data_source.py (constructs BaseballGame from CSV)
    ← mlb_fixture_source.py (constructs BaseballGame from API)
    ← baseball_feature_extractor.py (consumes BaseballGame)
    ← baseball_prediction_service.py (orchestrates)
    ← baseball_router.py (API layer)
    ← baseball_dtos.py (validation)

baseball_feature_extractor.py
    ← baseball_prediction_service.py (calls extract)

baseball_prediction_service.py
    ← baseball_router.py (instantiates service)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Feature extractor: all 46 features, missing data fallbacks | pytest, mock historical data, verify no NaN/inf |
| Unit | Market generation: probability ranges, confidence levels | pytest with known model outputs |
| Unit | Team name mapping (Retrosheet → MLB) | Table-driven tests |
| Integration | Prediction service: full flow from BaseballGame → response | pytest with real model file |
| Integration | Data source: CSV parsing, caching | pytest with fixture CSVs |
| API | All 4 endpoints: request/response validation | FastAPI TestClient |
| Frontend | Component rendering, market display | React Testing Library |
| Frontend | Responsive layout | Storybook + viewport tests |

## Migration / Deployment

1. **Model Training**: Run `python scripts/train_baseball_model.py` to generate `models/baseball_classifier.pkl`
2. **Data Seeding**: Retrosheet CSVs auto-download on first use; cache in `backend/data/cache/retrosheet/`
3. **Rollout**: Deploy backend first (model + API), then frontend (route + components)
4. **Rollback**: Disable `/baseball` route; no data migration needed (new module, no existing data)

## Open Questions

- [ ] Retrosheet CSV URL format — need to verify exact download paths for gameinfo/teamstats/batting/pitching files
- [ ] Park factor lookup table source — MLB Stats API or hardcoded constants?
- [ ] Travel distance calculation — use city coordinates or pre-computed matrix?
