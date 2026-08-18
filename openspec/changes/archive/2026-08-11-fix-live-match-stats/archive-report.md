# Archive Report: Fix Live Match Stats

## Change

- **Name**: `fix-live-match-stats`
- **Mode**: openspec
- **Archived by**: sdd-archive sub-agent (executor)
- **Archived on**: 2026-08-11
- **Archive location**: `openspec/changes/archive/2026-08-11-fix-live-match-stats/`
- **Verdict at archive**: PASS (verify-report, no CRITICAL/WARNING findings)
- **Archive type**: clean (no intentional-with-warnings markers; no overrides applied)

## What Shipped

Bug fix for user-visible live stats corruption: Boca Juniors vs Deportivo Recoleta showed
impossible stats at minute 2' (Córners 4/2, T. Amarillas 3/0, Tiros 0/6) and a fabricated
"Predicción Pre-Partido 33%/33%" while ESPN was clean (1 corner, 0 yellows). Four surgical fixes:

1. **R1 — ESPN-first merge precedence** (`frontend/src/infrastructure/api/live.ts`):
   ESPN live data is now the base/truth for all live stats; backend prediction-doc values fill
   only per-stat gaps. Minute/status always from ESPN. Empty-ESPN guard preserved (returns `[]`).
   Enabling tweak in `espn.ts`: `extractStat` returns `undefined` (not `0`) when a stat is absent,
   so "ESPN says 0" (genuine) is distinguishable from "ESPN lacks this stat" (gap).
2. **R2 — Live endpoints serve only in-progress matches** (`backend/src/api/routers/matches.py`):
   `LIVE_STATUSES = {"1H","2H","HT","LIVE","IN_PLAY","PAUSED"}`; both `/live` and
   `/live/with-predictions` queries now filter `data.match.status $in LIVE_STATUSES` alongside
   `expires_at`. Finished (`FT`, `AET`, `PEN`, `FINISHED`, `post`) and not-started (`NS`, `TIMED`,
   `SCHEDULED`, `pre`) docs are never served even with future `expires_at`.
3. **R3 — Name fallback binds only the same fixture** (`backend/src/application/use_cases/live_predictions_use_case.py`):
   new `_is_same_fixture_date` helper (calendar-date equality, ISO `Z`→`+00:00` normalization,
   unparsable→False) applied in the name-fallback branch only; exact-ID path untouched.
4. **R4 — Fabricated predictions never shown as real** (`frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx`):
   `isPredictionAvailable` additionally requires the prediction to NOT carry the
   `live_match_fallback` `data_sources` marker; fallback-only predictions render the no-prediction
   state ("No hay predicción pre-partido disponible para este evento.") instead of percentage bars.

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/src/infrastructure/external/espn.ts` | Modified | `extractStat` → `number \| undefined`; new `extractPossession` helper (guarded `%` concat) |
| `frontend/src/infrastructure/api/live.ts` | Modified | ESPN-first per-stat merge with backend fallback; `isProcessing: false` |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx` | Modified | Honesty gate on `live_match_fallback` marker |
| `backend/src/api/routers/matches.py` | Modified | `LIVE_STATUSES` constant + status filter on both `/live` queries |
| `backend/src/application/use_cases/live_predictions_use_case.py` | Modified | `_is_same_fixture_date` helper + name-fallback date guard |
| `frontend/src/infrastructure/api/live.test.ts` | Created | 6 merge-precedence tests |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.test.tsx` | Created | 3 honesty-gate tests |
| `backend/tests/unit/test_matches_live_endpoints.py` | Created | 3 status-filter endpoint tests |
| `backend/tests/unit/test_live_predictions_use_case.py` | Modified | +4 date-guard tests (incl. Z-suffix tolerance) |
| `backend/tests/test_matches_picks.py` | Modified | Sample doc updated to production shape (`data` wrapper + status `1H`) |

## Spec Sync

- Delta spec `specs/live-match-stats/spec.md` was verified **identical** to the main spec
  `openspec/specs/live-match-stats/spec.md` (new capability — full-spec copy, 4 requirements,
  12 scenarios). No merge needed; main spec is current as of 2026-08-11 17:21.
- `rules.archive` compliance: no destructive delta (nothing removed/renamed); no change-scoped
  operational requirements to preserve (capability spec only).

## Verification Evidence (from verify-report, fresh runs)

| Check | Result |
|-------|--------|
| Backend tests | 134 passed (37 pre-existing deprecation warnings) |
| Frontend tests | 47 passed (14 files), 0 failed |
| Frontend lint | 0 errors, 0 warnings |
| Frontend types | `tsc --noEmit` clean |
| Scenario coverage | 12/12 automated; scenario 13 (manual event 401903297) pending human confirmation |

No regressions; counts match apply-report exactly. No CRITICAL or WARNING findings.

## Engram Traceability (observation IDs)

| Artifact | Observation ID |
|----------|----------------|
| exploration | #1019 |
| proposal | #1020 |
| session summary (proposal) | #1021 |
| spec | #1022 |
| design | #1023 |
| tasks | #1024 |
| apply-progress | #1025 |
| discovery (ENOSPC environment issue) | #1026 |
| verify-report | #1027 |

## Follow-ups (from verify-report suggestions)

1. **Missing-status doc case untested** — docs without `data.match.status` are excluded only by
   Mongo `$in` semantics; the FakeRepo mirrors the filter (tautology). Add a mongomock-based test
   or an explicit no-status doc fixture to lock the behavior.
2. **`match_date` semantics flip** — merged output now carries ESPN fetch-time `match_date`
   instead of the backend kickoff date. Display-neutral today (no live UI renders `match_date`),
   but data semantics changed silently. Consider keeping `backend.match_date` when present.
3. **Manual scenario 13** — event 401903297 rendering ESPN values (1 corner, 0 yellows) needs a
   human check against a live ESPN fixture with the app running.
4. **Dead code** — `usedBackendIds` in `live.ts:69` remains unused (pre-existing, out of scope).
5. **Edge-case test gaps** — unparsable `match_date` / both-sources-missing adversarial paths
   lack dedicated tests (behavior correct by code inspection).

## Accepted Risks

- Legacy docs without `data.match.status` silently disappear from `/live` endpoints (design D3).
- Midnight-crossing matches (kickoff 23:00 → 00:30) fail exact-date equality → degrade to
  real-time inference (design D6).

## Cycle Status

SDD cycle complete: explore → propose → spec → design → tasks → apply → verify → archive.
The change has been fully planned, implemented, verified, and archived. Ready for the next change.
