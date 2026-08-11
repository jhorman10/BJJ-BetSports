# Verify Report: Fix Live Match Stats

## Change

- **Name**: `fix-live-match-stats`
- **Mode**: openspec
- **Verified by**: sdd-verify sub-agent (executor) — adversarial validation, fresh run of all suites
- **Date**: 2026-08-11
- **Strict TDD**: inactive (standard verify)

## Completeness

| Artifact | Status |
|----------|--------|
| Proposal | Not required for verify (not part of required reading set) |
| Spec | Read — `openspec/changes/fix-live-match-stats/specs/live-match-stats/spec.md` (4 requirements, 12 scenarios) |
| Design | Skipped — not in required reading set; coherence inferred from tasks + apply-progress (recorded as skipped dimension) |
| Tasks | Read — all 11 tasks checked `[x]` |
| Apply progress | Read — claims all tasks done, no deviations |
| Implementation | Source-inspected for all 4 fixes |

**Task completion**: 11/11 checked. No unchecked implementation tasks → no CRITICAL block on tasks.

## Build / Tests / Coverage Evidence (fresh runs)

| Check | Command | Result |
|-------|---------|--------|
| Backend tests | `cd backend && .venv/bin/pytest -q` | **134 passed**, 37 warnings (pre-existing deprecations), 10.26s |
| Frontend tests | `cd frontend && npx vitest run` | **47 passed** (14 files), 0 failed, 13.35s |
| Frontend lint | `cd frontend && npx eslint . --ext ts,tsx --max-warnings 0` | exit 0, **0 errors, 0 warnings** |
| Frontend types | `cd frontend && npx tsc --noEmit` | exit 0, **clean** |

Counts match the apply report exactly (backend 127 baseline + 7 new; frontend 38 baseline + 9 new). No regressions.

## Verdicts per Requirement

| Req | Verdict | Evidence |
|-----|---------|----------|
| R1 ESPN-first per-stat merge | **PASS** | `live.ts:97-98` `stat()` = `espn[key] !== undefined ? espn[key] : backend[key]`; base spread `...espn` (`live.ts:103`) puts minute/status/`match_date` from ESPN; empty-ESPN guard returns `[]` (`live.ts:62-66`); `espn.ts:75-88` `extractStat` returns `undefined` on missing (0 = genuine), `extractPossession` guards `"%"` concat. Tests: `live.test.ts` 6/6 |
| R2 Status filter on /live endpoints | **PASS** | `matches.py:18` `LIVE_STATUSES = {"1H","2H","HT","LIVE","IN_PLAY","PAUSED"}` (exact spec set); both queries `matches.py:29,56` add `"data.match.status": {"$in": list(LIVE_STATUSES)}` alongside `expires_at`. Mongo `$in` excludes missing-status docs by semantics. Tests: `test_matches_live_endpoints.py` 3/3 |
| R3 Fixture date guard in name fallback | **PASS** | `live_predictions_use_case.py:46-60` `_is_same_fixture_date` (calendar-date equality, ISO `Z`→`+00:00` normalization, unparsable→False); applied only in name-fallback branch `:1089`; ID path (`:1070-1079`) untouched. Tests: `test_live_predictions_use_case.py` 4 new |
| R4 No fabricated prediction surfaced | **PASS** | `LiveMatchDetailsModal.tsx:52-54` `isPredictionAvailable` requires `!prediction.data_sources?.includes("live_match_fallback")`; `matchMatching.ts:124` stamps the marker only when no partial prediction provides `data_sources`; `PreMatchPrediction.tsx:25-33` renders "No hay predicción pre-partido disponible para este evento." Tests: `LiveMatchDetailsModal.test.tsx` 3/3 |

## Scenario Coverage Matrix (13 items from mission prompt)

| # | Scenario | Covering test | Status |
|---|----------|---------------|--------|
| 1 | ESPN stats win when both present (incl. genuine 0) + minute/status from ESPN | `live.test.ts:121` "keeps ESPN stats (incl. genuine 0) and ESPN minute/status…" | ✅ PASS |
| 2 | Backend fills only ESPN gaps | `live.test.ts:142` "fills only ESPN gaps with backend values" | ✅ PASS |
| 3 | Backend unavailable → ESPN still returned, no zero-stubs | `live.test.ts:175` + `live.test.ts:189` (gaps stay undefined) | ✅ PASS |
| 4 | No ESPN live data → empty list | `live.test.ts:204` "returns an empty list when ESPN has no live matches" | ✅ PASS |
| 5 | Finished doc (FT, future `expires_at`) excluded from `/live/with-predictions` | `test_matches_live_endpoints.py:100` | ✅ PASS |
| 6 | Not-started doc (NS/pre) excluded from `/live` | `test_matches_live_endpoints.py:86` | ✅ PASS |
| 7 | In-progress doc (1H) served by both endpoints, shape unchanged | `test_matches_live_endpoints.py:86` + `:100` (only `live-1` served; id key shapes asserted) | ✅ PASS |
| 8 | Same fixture binds (equal names + equal date) | `test_live_predictions_use_case.py:391` | ✅ PASS |
| 9 | Same names, different date rejected → real-time fallback | `test_live_predictions_use_case.py:380` (returns `None` → flow continues) | ✅ PASS |
| 10 | ID lookup binds without date comparison | `test_live_predictions_use_case.py:414` | ✅ PASS |
| 11 | 0-0 live match, fallback-only → no-prediction state, never 33% | `LiveMatchDetailsModal.test.tsx:94` (also asserts no "33%", no suggested picks) | ✅ PASS |
| 12 | Real prediction unchanged (bars render) | `LiveMatchDetailsModal.test.tsx:110` | ✅ PASS |
| 13 | Manual: event 401903297 renders ESPN values (1 corner, 0 yellows) | Claimed done in apply-progress 5.1; **not executable in this environment** (requires live ESPN API + running app) | ⚠️ MANUAL — pending human confirmation |

**Automated coverage: 12/12 scenarios. No scenario without coverage.**

## Adversarial Checks (beyond the tests)

| Edge case | Result |
|-----------|--------|
| ESPN match lacking stats entirely (no boxscore) | `extractStat(undefined, …)` → `undefined` → `stat()` falls back to backend; both missing → `undefined` (never 0-stub). Correct by code inspection; gap case partially covered by `live.test.ts:189`. |
| Backend doc without `data.match.status` | Mongo `$in` does not match missing field → excluded. Correct by query semantics; not explicitly unit-tested (FakeRepo mirrors semantics → implicit). |
| Both sources missing per-stat | `stat()` returns `undefined` (no stub). Correct; no dedicated test. |
| Fallback prediction carrying other `data_sources` markers | Marker set only when `partialPrediction.data_sources` absent (`matchMatching.ts:124`); backend DTOs never stamp it; live-store valid predictions (`confidence>0`) always carry real sources → **no genuine prediction wrongly gated**. Traced end-to-end through `LiveMatchesList.tsx:56` → `matchLiveWithPrediction` → modal. |
| Midnight-crossing match (kickoff 23:00 → 00:30) | Fails exact-date equality → degrades to real-time inference. Accepted per design D6, documented in apply-progress risks. |
| Doc `match_date` unparsable | `_is_same_fixture_date` catches `TypeError/ValueError` → `False` → no bind. Correct; no dedicated test. |

## Correctness / Design Coherence

- No design doc read (not in required set); tasks + apply-progress show implementation matches the planned approach (merge inversion, LIVE_STATUSES, `_is_same_fixture_date`, modal gate). No deviations found between claimed and actual code.
- Changed files match the files-changed table in apply-progress exactly (verified via `git status`).

## Findings

### CRITICAL
None.

### WARNING
None.

### SUGGESTION
1. **Missing-status doc case untested** — a doc with no `data.match.status` is excluded only by Mongo `$in` semantics; the FakeRepo in `test_matches_live_endpoints.py:22-35` mirrors the filter (tautology). A `mongomock`-based test or an explicit no-status doc in the fixture would lock the behavior.
2. **`match_date` source silently flipped in merge** — merged output now carries ESPN's fetch-time `match_date` (`espn.ts:217` `new Date().toISOString()`) instead of the backend kickoff date. Display-neutral today (no live UI component renders `match_date` — verified), but the data semantics changed without a spec mention. Consider keeping `backend.match_date` when present.
3. **Manual scenario 13 unverified in this environment** — the apply report claims event 401903297 renders ESPN values; needs a human check against a live ESPN fixture with the app running.
4. **`usedBackendIds` dead code** in `live.ts:69` remains (pre-existing; noted in apply-progress as out of scope).
5. **Unparsable `match_date` / both-missing-stats** adversarial paths lack dedicated tests (behavior correct by inspection).

## Final Verdict

**PASS**

All 4 requirements verified against source + fresh runtime evidence; 12/12 spec scenarios have passing covering tests; full suites green (backend 134, frontend 47, lint 0, tsc clean); no regressions; no CRITICAL or WARNING findings. Suggestions only.

## Risks

- Legacy docs without `data.match.status` silently disappear from `/live` endpoints (accepted per design D3; surfaced in apply-progress).
- Midnight-crossing matches degrade to real-time inference (accepted per D6).
- Scenario 13 manual verification outstanding.
