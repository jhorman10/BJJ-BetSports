# Proposal: Fix Live Match Stats

## Intent

Live UI showed impossible stats at minute 2' (Boca vs Deportivo Recoleta): Córners 4/2, T. Amarillas 3/0, Tiros 0/6, plus fabricated "Predicción Pre-Partido 33%/33%" — while ESPN was clean (1 corner, 0 yellows at 11'). Frontend merge prefers stale backend stats over ESPN live (`live.ts:93-108`); backend serves prediction docs with no status/date guard (`matches.py:16-55`, `live_predictions_use_case.py:1064-1074`); fabricated fallback shown as real (`matchMatching.ts:29-57`).

## Scope

### In Scope
- `live.ts:93-108`: ESPN live stats (corners/cards/shots/fouls/offsides) as base; backend only as fallback.
- `matches.py:16-33, 36-55`: filter `match_predictions` to in-progress matches.
- `live_predictions_use_case.py:1064-1074`: validate match date before name-fallback binding.
- `matchMatching.ts:29-57` + `PreMatchPrediction.tsx`: no-prediction state instead of 33/33.

### Out of Scope
- `MatchPredictionModel` schema extension + backend `espn.py` stats parsing — deferred (unneeded once merge prefers ESPN).
- Stats-vs-minute guard — nice-to-have, follow-up.
- IndexedDB hydration; legacy `useLiveMatches.ts`; `/daily` endpoint.

## Capabilities

### New Capabilities
- `live-match-stats`: stats truth — ESPN-first merge, backend live-doc guards (status + date), prediction honesty.

### Modified Capabilities
None. `api-client` spec covers transport only; merge semantics are new.

## Approach

Fix precedence at the single frontend merge point (ESPN = truth for live stats); add two small backend guards so stale/finished/foreign-fixture docs are never served or bound; remove fabricated prediction display. Localized; no schema migration.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/infrastructure/api/live.ts` | Modified | ESPN-first stats merge |
| `backend/src/api/routers/matches.py` | Modified | Status filter on `/live` endpoints |
| `backend/src/application/use_cases/live_predictions_use_case.py` | Modified | Date validation in name fallback |
| `frontend/src/utils/matchMatching.ts` | Modified | No fabricated fallback |
| `frontend/src/presentation/components/MatchDetails/PreMatchPrediction.tsx` | Modified | No-prediction state |
| Backend + frontend test suites | New | Regression coverage |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Backend-only matches still show stale stats | Med | Guards reduce exposure; full fix deferred |
| Status filter hides valid docs | Low | Verify stored statuses in tests |
| ESPN placeholder stats at kickoff | Low | ESPN verified clean live; guard is follow-up |

## Rollback Plan

Four independent revertible changes (merge precedence, status filter, date check, prediction display). `git revert` of the branch restores prior behavior; no data migration.

## Dependencies

- ESPN scoreboard/summary APIs (existing).

## Success Criteria

- [ ] Merge unit test: ESPN stats win when both present; backend only when ESPN lacks a stat.
- [ ] Backend test: `/live/with-predictions` never returns finished/not-live docs.
- [ ] Backend test: name fallback rejects fixtures with different match date.
- [ ] Frontend test: 0-0 live match shows no-prediction state, never 33/33.
- [ ] Manual: event 401903297 renders ESPN values (1 corner, 0 yellows).
