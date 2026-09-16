# Tasks: Baseball Prediction Module

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650–750 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (within 800 budget) |
| Delivery strategy | single-pr-default |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full baseball prediction module | PR 1 | Backend entity → data → ML → API → frontend → routing. Single PR within 800-line budget. |

---

## Phase 1: Foundation (P0)

- [ ] T001.1 Create `backend/src/domain/entities/baseball_game.py` — `BaseballGame` dataclass mirroring `tennis_match.py`. Fields: game_id, date, home_team, away_team, home_score, away_score, venue, day_night, optional pitcher IDs/names, season, series_id, odds. Include `to_dict()` and Pydantic validation. (~65 lines)
- [ ] T001.2 Create `backend/src/api/dtos/baseball_dtos.py` — Pydantic request/response models: `BaseballPredictRequest`, `BaseballPredictResponse`, `BaseballGamesResponse`, `BaseballSeriesResponse`, `BaseballSeriesPredictionsResponse`. Mirror tennis DTO pattern. (~55 lines)
- [ ] T001.3 Create `frontend/src/types/baseball.ts` — TypeScript interfaces: `BaseballGame`, `BaseballSeries`, `BaseballMarket`, `BaseballPrediction`, `BaseballPredictionResponse`, `BaseballGamesResponse`, `BaseballSeriesResponse`. Mirror tennis types pattern. (~70 lines)

## Phase 2: Data Layer (P0)

- [ ] T002.1 Create `backend/src/infrastructure/data_sources/retrosheet_data_source.py` — `RetrosheetDataSource` class. Fetch Retrosheet CSVs (gameinfo, teamstats, batting, pitching). HTTP retry with exponential backoff (3 retries). Cache in `backend/data/cache/retrosheet/`. Team name mapping table (NYA→NYY, etc.). `fetch_season(year)`, `fetch_range(start, end)`, `get_team_stats(team, date_range)` methods. (~120 lines)
- [ ] T002.2 Create `backend/src/infrastructure/data_sources/mlb_fixture_source.py` — `MLBFixtureSource` class. Fetch from `statsapi.mlb.com` schedule endpoint. Resolve probable pitchers. Group games into series. Demo fallback data when API unavailable. Rate limiting (100ms delay). `get_upcoming_games(days=7, team=None)`, `get_series(days=14)` methods. (~100 lines)

## Phase 3: ML Layer (P0)

- [ ] T003.1 Create `backend/src/domain/services/baseball_feature_extractor.py` — `BaseballFeatureExtractor` class. 46 features across 7 groups: pitcher matchup (8), team batting (10), bullpen/pitching (8), recent form (6), head-to-head (3), context (8), betting odds (3). Missing data fallbacks per category. Z-score normalization support. `extract(game, historical_data)`, `get_feature_names()` methods. (~150 lines)
- [ ] T003.2 Create `backend/src/domain/services/baseball_prediction_service.py` — `BaseballPredictionService` class. Load RandomForest model from joblib file. 8-step prediction flow. 6 market generators: moneyline, run_line, total_runs, first_5_innings, team_total_runs, both_teams_score. Value bet detection (edge > 0.02). Key factors extraction (top 3-5). Model file change detection. (~130 lines)
- [ ] T003.3 Create `scripts/train_baseball_model.py` — Training script. Load Retrosheet data 2015–2024. Extract 46 features. Train RandomForestClassifier (n_estimators=200, max_depth=12). 80/20 temporal split. Save model+scaler to `models/baseball_classifier.pkl`. (~80 lines)

## Phase 4: API Layer (P0)

- [ ] T004.1 Create `backend/src/api/routers/baseball_router.py` — 4 endpoints: `POST /baseball/predict`, `GET /baseball/games`, `GET /baseball/series`, `GET /baseball/predictions/{series_id}`. Singleton service pattern (mirror tennis_router). Error handling with HTTPException. (~110 lines)
- [ ] T004.2 Modify `backend/src/api/main.py` — Import and register `baseball_router` via `app.include_router()`. (~3 lines)

## Phase 5: Frontend Types & Config (P0)

- [ ] T005.1 Add baseball TypeScript interfaces to `frontend/src/types/index.ts` — Import from `./baseball`. (~5 lines)
- [ ] T005.2 Add baseball API endpoints to `frontend/src/config/constants.ts` — `BASEBALL_PREDICT`, `BASEBALL_GAMES`, `BASEBALL_SERIES`, `BASEBALL_SERIES_PREDICTIONS`. (~8 lines)
- [ ] T005.3 Add baseball API methods to `frontend/src/services/api.ts` — `predictBaseball()`, `getBaseballGames()`, `getBaseballSeries()`, `getBaseballSeriesPredictions()`. (~35 lines)

## Phase 6: Frontend Components (P0)

- [ ] T006.1 Create `frontend/src/presentation/components/BaseballPrediction/BaseballPredictionPage.tsx` — Main page. Header with gradient title. Fetches games on mount. Renders BaseballSeriesView. Loading skeleton + error state + demo banner. (~60 lines)
- [ ] T006.2 Create `frontend/src/presentation/components/BaseballPrediction/BaseballSeriesView.tsx` — Groups games by series. Series header (e.g., "NYY vs BOS — 3 game series"). Maps games to BaseballGameCard. (~45 lines)
- [ ] T006.3 Create `frontend/src/presentation/components/BaseballPrediction/BaseballGameCard.tsx` — Game card: teams, date/venue/time, probable pitchers (or TBD), quick moneyline summary. Click opens modal. Dark theme, mirror tennis card style. (~100 lines)
- [ ] T006.4 Create `frontend/src/presentation/components/BaseballPrediction/BaseballMarketsPanel.tsx` — 6-market grid layout. Maps market data to BaseballMarketCard components. (~35 lines)
- [ ] T006.5 Create `frontend/src/presentation/components/BaseballPrediction/BaseballMarketCard.tsx` — Single market: probability bars, value bet badge (green >5%, yellow 2-5%), threshold selector for O/U markets. (~80 lines)
- [ ] T006.6 Create `frontend/src/presentation/components/BaseballPrediction/BaseballKeyFactors.tsx` — Factor list: feature name, value, direction. Star icon per factor. (~30 lines)
- [ ] T006.7 Create `frontend/src/presentation/components/BaseballPrediction/baseballMarketUtils.ts` — Market category mapping, icons, confidence/probability color helpers, threshold options. (~50 lines)
- [ ] T006.8 Create `frontend/src/presentation/components/BaseballPrediction/index.ts` — Barrel exports for all components. (~10 lines)

## Phase 7: Integration (P0)

- [ ] T007.1 Modify `frontend/src/App.tsx` — Import BaseballPredictionPage, add `/baseball` route. (~4 lines)
- [ ] T007.2 Verify baseball router loads without import errors. Start backend, hit `/baseball/games` endpoint.

## Phase 8: Polish (P1)

- [ ] T008.1 Add responsive breakpoints to BaseballPredictionPage — 2-column grid desktop, 1-column tablet/mobile. (~15 lines)
- [ ] T008.2 Add loading skeletons to BaseballGameCard — MUI Skeleton components during fetch. (~20 lines)
- [ ] T008.3 Add demo mode banner to BaseballPredictionPage — "Demo Data" banner when API returns demo flag. (~10 lines)

## Phase 9: Testing (P1)

- [ ] T009.1 Write unit tests for `baseball_feature_extractor.py` — Test all 46 features, missing data fallbacks, no NaN/inf output. (~80 lines)
- [ ] T009.2 Write unit tests for `baseball_prediction_service.py` — Test market generation, value bet detection, confidence levels. (~60 lines)
- [ ] T009.3 Write unit tests for `retrosheet_data_source.py` — Test CSV parsing, team name mapping, cache behavior. (~50 lines)
- [ ] T009.4 Write API integration tests for baseball endpoints — Test all 4 endpoints with TestClient. (~70 lines)

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1 | 3 | Foundation — entity, DTOs, TS types |
| Phase 2 | 2 | Data Layer — Retrosheet CSV, MLB fixtures |
| Phase 3 | 3 | ML Layer — 46-feature extractor, prediction service, training script |
| Phase 4 | 2 | API Layer — router, endpoint registration |
| Phase 5 | 3 | Frontend config — types, endpoints, API methods |
| Phase 6 | 8 | Frontend components — page, cards, markets, utils |
| Phase 7 | 2 | Integration — routing, verification |
| Phase 8 | 3 | Polish — responsive, skeletons, demo banner |
| Phase 9 | 4 | Testing — unit + integration tests |
| **Total** | **30** | |

### Implementation Order
1. **Phase 1** first — entity defines the data contract everything depends on
2. **Phase 2** next — data sources feed the ML layer
3. **Phase 3** after — feature extractor and prediction service consume data
4. **Phase 4** — API exposes the prediction service
5. **Phase 5** — frontend types and config before components
6. **Phase 6** — frontend components consume the API
7. **Phase 7** — wire everything together
8. **Phase 8–9** — polish and tests after core works

### Review Workload Forecast
- Total files to create: 17
- Total files to modify: 3 (`main.py`, `App.tsx`, `constants.ts` + `types/index.ts` + `api.ts`)
- Estimated total changed lines: 650–750
- Chained PRs recommended: No
- 400-line budget risk: Medium (single PR within 800-line budget)
- Delivery strategy: single-pr-default
- Decision needed before apply: No
- Suggested work-unit PR split: Not needed — single PR

### Next Step
Ready for implementation (`sdd-apply`). No chained PR decision needed — within 800-line budget as single PR.
