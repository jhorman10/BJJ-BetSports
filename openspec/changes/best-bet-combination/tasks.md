# Tasks: Best Bet Combination

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 750–950 |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: refactor + DTOs → PR 2: backend core → PR 3: backend tests → PR 4: frontend |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | UnifiedPick DTO + 4-sport adapter refactor | PR 1 | Base: main; tests included; ~120 lines |
| 2 | Backend core (optimizer, use case, router, DTOs, wiring) | PR 2 | Base: main after PR 1; ~380 lines |
| 3 | Backend tests (unit + integration) | PR 3 | Base: main after PR 2; ~180 lines |
| 4 | Frontend (types, api client, page, nav, tests) | PR 4 | Base: main after PR 3; ~200 lines |

## Phase 1: Prerequisite Refactor — Unified Pick DTO

- [x] 1.1 Create `backend/src/domain/entities/unified_pick.py`: frozen dataclass `UnifiedPick(sport, match_id, match_label, pick_label, probability, odds, confidence_level, is_recommended, priority_score, is_ml_confirmed, is_ia_confirmed)`
- [x] 1.2 Modify `backend/src/domain/entities/suggested_pick.py`: add optional `sport: str` and `match_id: str` fields (backward-compatible defaults)
- [x] 1.3 Modify `backend/src/domain/services/tennis_prediction_service.py`: adapt `_create_moneyline` (and similar builders) to emit `sport="tennis"`, `match_id`, and `odds` fields on each market dict
- [x] 1.4 Modify `backend/src/domain/services/baseball_prediction_service.py`: add `sport="baseball"`, `match_id`, `odds` to `generate_*_markets` output dicts
- [x] 1.5 Modify `backend/src/domain/services/basketball_prediction_service.py`: add `sport="basketball"`, `match_id`, `odds` to `generate_*_markets` output dicts
- [x] 1.6 Modify `backend/src/api/routers/picks.py` (football suggested-picks): ensure `SuggestedPick` responses include `sport="soccer"` and `match_id` back-reference

## Phase 2: Backend Core

- [x] 2.1 Create `backend/src/api/dtos/best_combination_dtos.py`: Pydantic v2 `BestCombinationRequest`, `BestCombinationLeg`, `BestCombinationAggregate`, `BestCombinationResponse`
- [x] 2.2 Create `backend/src/domain/services/combination_optimizer.py`: `aggregate_pools(per_sport_picks) → list[UnifiedPick]`; drop picks missing sport/match_id; quality filter per spec (soccer: `is_ml_confirmed` or `is_ia_confirmed`; others: `confidence_level=="high"` + `is_recommended`); apply `min_probability`/`exclude_leagues`
- [x] 2.3 Implement `build_combination(pools) → tuple[list[UnifiedPick], dict]`: per sport pick best by priority_score (tie: probability); fallback best-available + confidence_warning if pool empty; compute odds (market if >1.0 else fair 1/p); compute totals (product p; product market odds if ALL 4 market else 1/total_p); EV = total_p × total_odds − 1
- [x] 2.4 Implement neg-EV guard: raise/return 409 `no_positive_ev` when EV < 0
- [x] 2.5 Implement insufficient-pool errors: 409 `insufficient_pool` (with `missing_sports`) if <4 sports have any pick; 409 `no_picks_available` if all empty
- [x] 2.6 Wire `KellySizer.kelly_with_confidence` + `RiskManager.apply_portfolio_constraints` for stake sizing: fractional Kelly on combined probability/odds, capped at `max_stake_pct`; set `risk_level` and `suggested_stake_pct`
- [x] 2.7 Create `backend/src/application/use_cases/best_combination_use_case.py`: `execute(request) → BestCombinationResponse`; fetch per-sport upcoming events via existing sport services/routers, delegate to optimizer
- [x] 2.8 Create `backend/src/api/routers/best_combination.py`: `POST /api/v1/best-combination` with 422 on invalid filters; call use case; return response or 409/422 errors
- [x] 2.9 Modify `backend/src/api/main.py`: `include_router(best_combination_router)`
- [x] 2.10 Verify `parley_service.py` / `get_parleys_use_case.py` are NOT modified (ADR-5: leave untouched)

## Phase 3: Backend Tests

- [x] 3.1 Unit tests `backend/tests/unit/test_combination_optimizer.py`: pool aggregation, quality filter, fallback when pool empty, odds fallback (market vs fair), totals math, neg-EV rejection
- [x] 3.2 Unit tests `backend/tests/unit/test_best_combination_use_case.py`: mocked per-sport fetch → 200 happy path; mock 409 `insufficient_pool`; mock 409 `no_picks_available`; mock 409 `no_positive_ev`
- [x] 3.3 Unit test Kelly/RiskManager cap: stake capped at `max_stake_pct` when Kelly exceeds; risk_level correct
- [x] 3.4 Integration test `backend/tests/integration/test_best_combination_router.py`: FastAPI `TestClient` POST 200 with seeded sport data; 422 with bad filter; 409 insufficient pool

## Phase 4: Frontend

- [x] 4.1 Create `frontend/src/types/bestCombination.ts`: TS types `BestCombinationRequest`, `BestCombinationLeg`, `BestCombinationResponse` mirroring backend DTOs
- [x] 4.2 Modify `frontend/src/config/constants.ts`: add `BEST_COMBINATION: "/api/v1/best-combination"`
- [x] 4.3 Modify `frontend/src/services/api.ts`: add `getBestCombination(pool?: BestCombinationRequest): Promise<BestCombinationResponse>` (POST)
- [x] 4.4 Create `frontend/src/presentation/components/BestCombination/BestCombinationPage.tsx`: loading spinner, error state, empty state, 4-leg display (sport icon, match_label, pick_label, probability, odds), aggregate card (total odds, probability, EV, stake), confidence/odds warnings, "Pregúntale al modelo" CTA, Spanish neutral/professional UI copy
- [x] 4.5 Modify `frontend/src/App.tsx`: add `/best-combination` route with `BestCombinationPage`
- [x] 4.6 Modify `frontend/src/presentation/components/Layout/MainLayout.tsx`: add nav entry `{ path: "/best-combination", label: "Mejor Combinación", icon: SmartToy }` to `NAV_ITEMS`
- [x] 4.7 Vitest tests `frontend/src/presentation/components/BestCombination/BestCombinationPage.test.tsx`: test loading, error, empty, data-rendered states; test confidence/odds warning rendering
- [x] 4.8 Vitest test `frontend/src/services/api.test.ts`: test `getBestCombination` posts to correct endpoint with correct body

## Phase 5: Quality Gate

- [ ] 5.1 Run `ruff check backend/` + `black --check backend/` + `isort --check backend/` + `mypy backend/` on all touched backend files; fix any violations
- [ ] 5.2 Run `eslint frontend/src/` + `tsc --noEmit` on all touched frontend files; fix any violations
- [ ] 5.3 Run full `pytest backend/tests/` — all green
- [ ] 5.4 Run full `vitest` — all green
- [ ] 5.5 Verify no regressions: existing per-sport endpoints still return correct shapes (spot-check tennis/baseball/basketball market dicts now carry sport/match_id/odds)
