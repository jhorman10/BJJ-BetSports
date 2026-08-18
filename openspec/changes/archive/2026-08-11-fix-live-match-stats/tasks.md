# Tasks: Fix Live Match Stats

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~425 (additions + deletions) |
| 400-line budget risk | Medium (~425 est., slightly over default) |
| Chained PRs recommended | No — user-approved D2 budget (800 lines) absorbs it |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium
```

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All 4 fixes + 4 test files (est. ~425 lines) | PR 1 | Single PR; user approved 800-line budget (D2). No chain. |

## Phase 1: Frontend ESPN-first stats pipeline

- [x] 1.1 `frontend/src/infrastructure/external/espn.ts:74-87` — change `extractStat` return type to `number | undefined`; return `undefined` (not 0) when boxscore/team/stat missing; guard possession `+ "%"` concat against undefined. Done: defined value (incl. 0) = data, `undefined` = gap.
- [x] 1.2 `frontend/src/infrastructure/api/live.ts:93-108` — invert merge: base on `espnMatch.match`; per stat (`home/away_corners, yellow_cards, red_cards, total_shots, shots_on_target, fouls, offsides, possession, goals`) use `espn !== undefined ? espn : backend`; minute/status always ESPN; keep backend `prediction`, odds, spi, events, `isProcessing: false`. Done: ESPN wins incl. 0, backend fills gaps only.

## Phase 2: Backend guards

- [x] 2.1 `backend/src/api/routers/matches.py` — add module constant `LIVE_STATUSES = {"1H","2H","HT","LIVE","IN_PLAY","PAUSED"}`; extend both `find()` queries (lines 21, 43) with `"data.match.status": {"$in": list(LIVE_STATUSES)}` alongside `expires_at`. Done: FT/NS docs excluded, 1H served by both endpoints.
- [x] 2.2 `backend/src/application/use_cases/live_predictions_use_case.py:1064-1074` — in name-fallback branch, parse doc `match_date` and live `match.match_date` ISO (`.replace("Z","+00:00")`) and bind only when `.date()` equal; mismatch → skip binding, fall through to real-time inference. ID lookup path (1053-1062) untouched. Done: same-name/diff-date → `None`.

## Phase 3: Prediction honesty gate

- [x] 3.1 `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx:49-50` — `isPredictionAvailable` additionally requires `!prediction.data_sources?.includes("live_match_fallback")`. Done: fallback-only prediction renders "No hay predicción pre-partido…" via `PreMatchPrediction.tsx`.

## Phase 4: Tests (alongside fixes, no TDD gate)

- [x] 4.1 Create `frontend/src/infrastructure/api/live.test.ts` — mock `apiClient` + `fetchESPNLiveMatches`; assert: ESPN wins when both present (incl. genuine 0), backend fills only `undefined` gaps, backend failure → ESPN list only, empty ESPN → `[]`. Run: `npx vitest run src/infrastructure/api/live.test.ts`. Done: 6 tests pass.
- [x] 4.2 Create `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.test.tsx` — mock `useLiveStore`/`useUIStore`; `data_sources: ["live_match_fallback"]` with hwp 0.33 → no-prediction state, never 33%; real source → bars render. Run: `npx vitest run src/presentation/components/MatchDetails/LiveMatchDetailsModal.test.tsx`. Done: 3 tests pass.
- [x] 4.3 Create `backend/tests/unit/test_matches_live_endpoints.py` — monkeypatch repo `find` returning FT + NS + 1H docs with future `expires_at`; assert both `/live` and `/live/with-predictions` serve only 1H. Run: `pytest tests/unit/test_matches_live_endpoints.py`. Done: 3 tests pass.
- [x] 4.4 Modify `backend/tests/unit/test_live_predictions_use_case.py` — add date-guard tests for `_try_get_precalculated_dto`: same-name doc + different `match_date` → `None`; equal date → DTO; exact-id path binds without date check. Run: `pytest tests/unit/test_live_predictions_use_case.py`. Done: 4 new tests pass (incl. Z-suffix tolerance).

## Phase 5: Verification

- [x] 5.1 Full suites: `pytest` (backend/) and `npx vitest run` (frontend/); frontend `npm run lint` + `tsc -b`. Done: all pass, no regressions. Manual: event 401903297 shows ESPN values (1 corner, 0 yellows).

## Constraints

- No schema changes, no new services, no refactors beyond the 4 fixes + `extractStat` tweak. Non-goals stay untouched (espn.py parsing, `/daily`, `useLiveMatches.ts`, schema extension).
