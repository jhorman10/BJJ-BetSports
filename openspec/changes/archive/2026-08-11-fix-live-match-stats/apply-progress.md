# Apply Progress: Fix Live Match Stats

## Status

All 11 tasks complete. Standard mode (strict_tdd disabled). Delivery: single-pr (user-approved size:exception, 800-line budget; actual change ~700 lines incl. tests).

## Completed Tasks

| Task | Description | Result |
|------|-------------|--------|
| 1.1 | espn.ts `extractStat` → `number \| undefined`; undefined on missing; possession concat guarded via new `extractPossession` helper | Done — 7 call sites updated, possession helper used for both teams |
| 1.2 | live.ts merge inverted: base `...espnMatch.match`, per-stat `espn !== undefined ? espn : backend` for all 18 stat keys; minute/status via ESPN base; backend odds/spi/events preserved; `isProcessing: false` | Done |
| 2.1 | matches.py `LIVE_STATUSES = {"1H","2H","HT","LIVE","IN_PLAY","PAUSED"}`; both /live queries gain `"data.match.status": {"$in": list(LIVE_STATUSES)}` | Done |
| 2.2 | use case name fallback: module helper `_is_same_fixture_date` (calendar-date equality, ISO `.replace("Z","+00:00")`); candidate bound only on date match; ID path untouched | Done |
| 3.1 | Modal `isPredictionAvailable` also requires `!prediction.data_sources?.includes("live_match_fallback")` | Done |
| 4.1 | Created `frontend/src/infrastructure/api/live.test.ts` — 6 tests: ESPN wins incl. 0 + minute/status; backend fills gaps; backend-only fields survive; backend fail → ESPN only; gaps stay undefined; empty ESPN → [] | 6/6 pass |
| 4.2 | Created `LiveMatchDetailsModal.test.tsx` — 3 tests: fallback marker → no-prediction state (never 33%), real source → bars, live-store fallback stub still gated | 3/3 pass |
| 4.3 | Created `backend/tests/unit/test_matches_live_endpoints.py` — FakeRepo applies query filters; FT+NS+1H docs with future expires_at → only 1H served by both endpoints; query carries status filter | 3/3 pass |
| 4.4 | Extended `test_live_predictions_use_case.py` — 4 tests: diff date → None, equal date → DTO, Z-suffix tolerance, exact-id binds without date check | 4/4 pass |
| 5.1 | Full suites run | backend 134 passed; frontend 47 passed (14 files); lint 0 errors; tsc clean |

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/src/infrastructure/external/espn.ts` | Modified | extractStat → `number \| undefined`; new extractPossession helper |
| `frontend/src/infrastructure/api/live.ts` | Modified | ESPN-first per-stat merge with backend fallback |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx` | Modified | Honesty gate on `live_match_fallback` marker |
| `backend/src/api/routers/matches.py` | Modified | LIVE_STATUSES + status filter on both /live queries |
| `backend/src/application/use_cases/live_predictions_use_case.py` | Modified | `_is_same_fixture_date` helper + name-fallback date guard |
| `frontend/src/infrastructure/api/live.test.ts` | Created | 6 merge-precedence tests |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.test.tsx` | Created | 3 honesty-gate tests |
| `backend/tests/unit/test_matches_live_endpoints.py` | Created | 3 status-filter endpoint tests |
| `backend/tests/unit/test_live_predictions_use_case.py` | Modified | +4 date-guard tests |
| `backend/tests/test_matches_picks.py` | Modified | sample doc updated to production shape (data wrapper + status 1H) |

## Deviations from Design

None — implementation matches design. One note: mission prompt listed `frontend/src/services/api/live.ts`/`espn.ts` paths, but actual files live at `frontend/src/infrastructure/api/live.ts` and `frontend/src/infrastructure/external/espn.ts` (as tasks.md/design.md correctly state). Implemented at the real paths.

## Issues Found

- Frontend `node_modules` was missing and disk was 100% full (ENOSPC) — cleaned npm cache + VSCode ShipIt cache (~3GB), ran `npm ci` in frontend. Not a code issue; environment only.
- `test_matches_picks.py::test_live_matches_with_doc` used a legacy doc shape (top-level `prediction` key, status "scheduled") inconsistent with production storage (`data` key). Updated to production shape with live status so the test remains meaningful under the new status filter.

## Test Results (exact)

- Backend: `pytest -q` → **134 passed** (127 baseline + 7 new), 37 warnings (pre-existing deprecations)
- Frontend: `npx vitest run` → **47 passed** (38 baseline + 9 new), 14 files, 0 failed
- Frontend lint: `npm run lint` → **0 errors, 0 warnings**
- Frontend types: `npx tsc --noEmit` → **clean**

## Risks

- Docs stored under legacy top-level `prediction` key (no `data.match.status`) are now excluded from /live endpoints — accepted per design D3 (can't prove them live).
- Midnight-crossing matches (kickoff 23:00 → 00:30) fail exact-date equality in name fallback → real-time inference path serves them — accepted per design D6.
- `usedBackendIds` in live.ts remains unused (pre-existing dead code) — untouched per scope guard.
