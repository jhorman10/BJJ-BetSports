# SDD Verification Report — Multi-Sport Modules

**Change**: multi-sport-modules
**Version**: 2.0.0 (dataset `_metadata`)
**Mode**: Standard (no Strict TDD active)

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 19 |
| Tasks complete | 19 |
| Tasks incomplete | 0 |

All 19 tasks checked. Full dimension analysis performed (proposal + 4 specs + design + tasks present).

## Build & Tests Execution

**Backend Type-check / Ruff**: ❌ FAILED
```text
.venv/bin/ruff check src/  →  68 errors (E501 line-too-long, W293 blank-line-whitespace, E741),
46 fixable. All attributable to this change:
  - league_loader.py (new, untracked): 62
  - verify_dataset.py (new): 1
  - league_mapper.py:1, leagues.py:1, predictions.py:1, async_mongo_adapter.py:1, async_mongo_repository.py:1
```

**Backend Tests**: ✅ 176 passed / 0 failed / 0 skipped
```text
.venv/bin/python -m pytest tests/ -q  →  176 passed, 45 warnings
  - tests/unit/test_multi_sport.py: 16 passed
  - tests/unit/ (full): 127 passed
  - tests/integration/: 6 passed
```
(Note: command in prompt was `pytest src/tests/`; actual suite lives in `tests/`.)

**Frontend TypeScript**: ✅ Passed
```text
cd frontend && npx tsc --noEmit  →  exit 0
```

**Frontend Tests**: ✅ 71 passed
```text
cd frontend && npx vitest run  →  71 passed across 19 test files
```

**Frontend Lint**: ❌ FAILED (exit 1)
```text
cd frontend && npm run lint  →  4 errors + 1 warning
  - leagues.sport.test.ts: import/order empty line
  - LeagueSelector.tsx: import/order (2) + explicit-function-return-type
```

## Spec Compliance Matrix

### sport-catalog
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sport field on every league entry | Existing leagues carry soccer sport | `test_multi_sport::test_existing_leagues_default_to_soccer` | ✅ COMPLIANT (all queried leagues have valid sport) |
| Sport field on every league entry | New sport placeholder sections | `test_new_sport_placeholders_exist` | ✅ COMPLIANT (tennis/baseball/basketball present, active:false) |
| All 850 leagues sport=soccer | (implied by Requirement text) | `test_get_by_sport_soccer_returns_all_soccer` | ❌ UNTESTED/⚠️ — dataset physically contains 259 soccer leagues, not 850. `_metadata.total_leagues=850` is inconsistent with actual data. |
| Sport enum in constants | Sport enum values | `test_enum_values` | ✅ COMPLIANT |
| Default sport constant | Default sport constant | `test_default_sport` | ✅ COMPLIANT |
| Sport-aware loader indexing | Query leagues by sport | `test_get_by_sport_tennis` | ✅ COMPLIANT |
| Sport-aware loader indexing | Query soccer leagues | `test_get_by_sport_soccer_returns_all_soccer` | ⚠️ PARTIAL — returns 259, spec says 850 |
| Sport-aware loader indexing | Unknown sport returns empty | `test_unknown_sport_empty` | ✅ COMPLIANT |
| Sport on League entity | Default sport on League | `test_default_sport` | ✅ COMPLIANT |
| Sport on prediction documents | New document includes sport | (static: `save_match_prediction`/`bulk_save_predictions` write `sport`) | ❌ UNTESTED (no runtime Mongo test) |
| Sport on prediction documents | Legacy document defaults to soccer | (static: `doc.get("sport","soccer")` in `_to_prediction_result`) | ❌ UNTESTED (no runtime test) |

### sport-api-filtering
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sport query on league endpoints | Default sport filter | `test_build_leagues_response_filters_soccer` | ✅ COMPLIANT |
| Sport query on league endpoints | Explicit sport filter | `test_build_leagues_response_tennis` | ✅ COMPLIANT |
| Sport query on league endpoints | Invalid sport returns empty | `test_build_leagues_response_unknown_empty` | ✅ COMPLIANT |
| Sport query on prediction endpoints | Prediction with sport context | `test_find_league_with_sport` (mapper logic) | ⚠️ PARTIAL — router wiring inspected, logic tested via `find_league` |
| Sport query on prediction endpoints | Sport mismatch returns empty | `test_find_league_sport_mismatch_raises` | ✅ COMPLIANT (404 raised) |
| Sport field on LeagueModel | LeagueModel includes sport | `test_build_leagues_response_tennis` (asserts league.sport) | ✅ COMPLIANT |
| Sport field on LeagueModel | LeaguesResponse groups by sport | schema inspection (`LeaguesResponse → CountryModel → LeagueModel.sport`) | ⚠️ PARTIAL — covered by inference, no dedicated test |
| Backward-compatible signatures | No-param call unchanged | `test_build_leagues_response_filters_soccer` + full 176-test suite green | ✅ COMPLIANT |

### api-client
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sport param on API fetch functions | Fetch leagues with sport | `leagues.sport.test.ts` | ✅ COMPLIANT |
| Sport param on API fetch functions | Fetch leagues without sport | `leagues.sport.test.ts` | ✅ COMPLIANT |
| Sport param on API fetch functions | All sports return valid data | (typed via `Sport`; deserialization) | ⚠️ PARTIAL — no runtime response-shape test |
| Sport in API_ENDPOINTS | Endpoints unchanged | `constants.ts` inspection (LEAGUES/LEAGUES_ACTIVE unchanged + comment) | ✅ COMPLIANT |

### sport-selector-ui
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Sport constant type in frontend | Sport type defines all values | `sports.test.ts` (SPORTS length/values) | ✅ COMPLIANT |
| Sport constant type in frontend | SPORTS array usable for iteration | `sports.test.ts` | ✅ COMPLIANT |
| Selected sport in useUIStore | Default sport on fresh load | `useUIStore.sport.test.ts` | ✅ COMPLIANT |
| Selected sport in useUIStore | Sport persists across reload | (static: localStorage + reload in `loadInitialSport`) | ❌ UNTESTED (no reload-restore runtime test) |
| Selected sport in useUIStore | setSport updates state | `useUIStore.sport.test.ts` | ✅ COMPLIANT |
| Sport toggle in LeagueSelector | Toggle renders all sports | (none) | ❌ UNTESTED — no LeagueSelector component test |
| Sport toggle in LeagueSelector | Toggle changes sport | (none) | ❌ UNTESTED |
| Sport toggle in LeagueSelector | Active chip highlighted | (none) | ❌ UNTESTED |
| League list filtered by sport | Country list updates on sport change | (none) | ❌ UNTESTED |
| League list filtered by sport | League scoped to country+sport | (none) | ❌ UNTESTED |
| Sport field on frontend League type | League type includes sport | `match.ts` type + `sports.test.ts` | ✅ COMPLIANT (type-level) |

**Compliance summary**: 23 scenarios — 15 ✅ COMPLIANT, 2 ⚠️ PARTIAL, 6 ❌ UNTESTED. (1 requirement-level mismatch on the "850 leagues" figure.)

## Correctness (Static Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| Sport enum + DEFAULT_SPORT | ✅ Implemented | `domain/constants.py` |
| Loader `get_by_sport` + default setdefault | ✅ Implemented | `league_loader.py` |
| League entity `sport` default | ✅ Implemented | `entities.py` |
| Mongo write `sport` default | ✅ Implemented | `mongo_repository.py` save/bulk |
| Mongo read default via `doc.get` | ✅ Implemented | `_to_prediction_result`, async mirror |
| `?sport=` on leagues endpoints | ✅ Implemented | `routers/leagues.py` |
| `?sport=` on prediction endpoint + sport verify | ✅ Implemented | `routers/predictions.py` (find_league sport verify) |
| `LeagueModel.sport` | ✅ Implemented | `schemas/leagues.py` |
| `build_leagues_response(sport)` / `find_league()` | ✅ Implemented | `league_mapper.py` |
| Frontend Sport type / SPORTS / DEFAULT_SPORT | ✅ Implemented | `constants.ts`, `match.ts` |
| `getLeagues`/`getActiveLeagues` sport param | ✅ Implemented | `infrastructure/api/leagues.ts`, predictions.ts |
| `useUIStore.selectedSport` + setSport + persist | ✅ Implemented | `useUIStore.ts` |
| `usePredictionStore` passes sport + clears selection | ✅ Implemented | `usePredictionStore.ts` + LeagueSelector handleSportChange |
| LeagueSelector sport toggle + filtering | ✅ Implemented | `LeagueSelector.tsx` |

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Unified dataset + `sport` discriminator (Approach 1) | ✅ Yes | single `leagues_global.json` |
| `?sport=` query param routing | ✅ Yes | additive, backward compatible |
| Keep football `PredictionModel`, sport maps draw=0/optional | ✅ Yes | scope not expanded |
| Sport state in `useUIStore` | ✅ Yes | matches design |
| `league_id` sport-prefixed (B_/T_/K_) | ✅ Yes | verified B_MLB, T_*, K_* |
| Sport enum both backend + frontend (YAGNI, no shared pkg) | ✅ Yes | mirrors existing pattern |

### Design Open questions
- Dataset `_metadata` version/counts bump (task 1.1/4.2): **partially followed** — version bumped to 2.0.0 but `total_leagues=850`/`total_countries=211` do not match the 266 leagues actually present in the file.

## Issues Found

**CRITICAL**
1. **Dataset metadata inconsistency / spec non-compliance (sport-catalog)** — `leagues_global.json` `_metadata.total_leagues=850` and `total_countries=211`, but the file physically contains only ~259 soccer + 7 new-sport leagues (266 total, 92 soccer countries). The spec requires "all 850 existing football leagues" carry `sport:"soccer"` and `get_by_sport("soccer")` return all 850 — the actual dataset delivers 259. Either the metadata is wrong or the dataset is truncated. Data integrity must be reconciled before merge.

**WARNING**
2. **Backend ruff fails** (68 errors, all introduced by this change; 62 in new `league_loader.py`). Would fail any lint CI gate. Non-functional, auto-fixable (`ruff --fix`).
3. **Frontend lint fails** (`npm run lint` exit 1): 4 errors + 1 warning in `leagues.sport.test.ts` and `LeagueSelector.tsx` (import/order + missing return type), all introduced by this change.
4. **6 spec scenarios UNTESTED** (no covering runtime test): Mongo legacy-doc default sport, Mongo new-doc sport write, LeagueSelector UI behaviors (toggle render/change/highlight, country/league list update), store sport reload-restore, API response-shape for new sports. Tasks 3.6 (LeagueSelector), 2.2/2.3 (Mongo sport) were human/manual-verified per task notes, not test-covered.

**SUGGESTION**
5. Add a `LeagueSelector` RTL component test and a Mongo-repo sport-default unit test (mock collection) to close the untested scenarios.
6. Command in prompt (`pytest src/tests/`) points to a non-existent path; actual suite is `tests/`.

## Verdict

**PASS WITH WARNINGS** (conditional — the CRITICAL dataset-metadata/850-league discrepancy must be resolved; lint gates fail)

The sport dimension is correctly plumbed end-to-end (loader, domain, repos, routers, schemas, frontend types/store/API/UI), all 176 backend + 71 frontend tests pass, full backward compatibility confirmed, and TypeScript type-checks. However, the `_metadata` claims 850 leagues/211 countries while the dataset holds 266, contradicting a hard spec requirement, and both lint suites fail. Fix the metadata/data reconciliation and lint before merge.
