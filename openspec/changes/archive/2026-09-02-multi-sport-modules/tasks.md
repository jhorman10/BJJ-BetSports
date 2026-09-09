# Tasks: Multi-Sport Modules — Plumbing

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900 (add+del) |
| 400-line budget risk | High |
| Chained PRs recommended | No (user: single PR) |
| Suggested split | Not needed (single PR) |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: High

> Single PR exceeds the 400-line budget (~900 lines, full-stack plumbing). Delivery `single-pr` requires `size:exception` approval before apply.

## Phase 1: Data Layer (~320 lines)

- [x] 1.1 `backend/src/infrastructure/data/leagues_global.json`: add `"sport":"soccer"` to all 850 leagues; bump `_metadata.version`; add `tennis`/`baseball`/`basketball` placeholder sections (`continents→countries→leagues`, `active:false`, sport-prefixed ids `T_`/`B_`/`K_`). Done: `python -c` JSON parse + count check. Verify: no `sport` missing.
- [x] 1.2 `league_loader.py`: init `_by_sport` index; default `league.setdefault("sport","soccer")` in `_index_league`; add `get_by_sport(sport)`; add `sport` to `to_metadata_format`/`to_leagues_metadata`. Verify: `dataset.get_by_sport("tennis")` non-empty, `"cricket"` empty.
- [x] 1.3 `backend/src/domain/constants.py`: add `Sport(str,Enum)` (SOCCER/TENNIS/BASEBALL/BASKETBALL) + `DEFAULT_SPORT="soccer"`. Verify: pytest `test_constants`.

## Phase 2: Backend — Repos, Mappers, Routers, Schemas (~360 lines)

- [x] 2.1 `backend/src/domain/entities/entities.py`: add `sport: str = "soccer"` to `League` dataclass. Verify: pytest default-sport.
- [x] 2.2 `mongo_repository.py`: `save_match_prediction`/`bulk_save_predictions` write `sport` (from league, default `"soccer"`); `get_all_active_predictions` accepts `sport=`; `get_league_ids_with_predictions(sport=)`. Verify: legacy doc w/o sport reads as soccer.
- [x] 2.3 `async_mongo_repository.py`: mirror `sport` writes + `sport=` filters on async paths. Verify: same as 2.2 async.
- [x] 2.4 `async_mongo_adapter.py`: propagate `sport` through async adapter methods. Verify: same as 2.2.
- [x] 2.5 `backend/src/api/schemas/leagues.py`: add `sport: str` to `LeagueModel`. Verify: schema includes field.
- [x] 2.6 `league_mapper.py`: `build_leagues_response(sport="soccer")`, `find_league(id, sport)` filter; set sport on `LeagueModel`. Verify: `?sport=tennis` returns tennis only.
- [x] 2.7 `routers/leagues.py`: add `sport: str = Query(DEFAULT_SPORT)` to `/`, `/active`, `/{league_id}`; pass to mapper/repo. Verify: no-param → soccer (backward compat).
- [x] 2.8 `routers/predictions.py`: add `sport=` filter to `GET /predictions/league/{league_id}`; verify league belongs to sport (404/empty on mismatch). Verify: eg `B_MLB?sport=baseball` ok, `?sport=soccer` empty.

## Phase 3: Frontend (~220 lines)

- [x] 3.1 `frontend/src/domain/entities/match.ts`: add `sport?: Sport` to `League`; export `type Sport = "soccer"|"tennis"|"baseball"|"basketball"`. Verify: `tsc --noEmit`.
- [x] 3.2 `frontend/src/config/constants.ts`: add `SPORTS` array w/ labels + `DEFAULT_SPORT`; annotate league endpoints support `?sport=`. Verify: `tsc --noEmit`.
- [x] 3.3 `frontend/src/infrastructure/api/leagues.ts`: add `sport?: string` to `getLeagues`/`getActiveLeagues`, append `?sport=` when set. Verify: Vitest URL contains param / omitted when unset.
- [x] 3.4 `useUIStore.ts`: add `selectedSport: Sport` (default `"soccer"`) + `setSport`, persisted to localStorage. Verify: Vitest reload restores sport.
- [x] 3.5 `usePredictionStore.ts`: `fetchLeagues`/`fetchPredictions` read `selectedSport` + pass to API; clear selection on sport change. Verify: Vitest `getActiveLeagues(sport)` called.
- [x] 3.6 `LeagueSelector/*`: render sport toggle chips (`setSport`, active highlight); country/league lists filter by `selectedSport`. Verify: Vitest toggle updates lists; manual no-reload switch.

## Phase 4: Tests + Docs (~40 lines)

- [x] 4.1 pytest: `get_by_sport`, sport default, enum parse, `?sport=` API scenarios (from specs). Verify: `.venv/bin/pytest tests/ -q`.
- [x] 4.2 Update `_metadata` counts + US/ES translation maps for new sports in `LeagueSelector/constants.ts`. Verify: manual render of tennis/baseball/basketball.

## Dependency Graph

Data(1.x) → Backend(2.x) → Frontend(3.x) → Verify(4.x). 1.1→1.2→1.3 serial; 2.2-2.4 parallel after 1.3; routers 2.7/2.8 after schema+repo; 3.4 before 3.5/3.6.
