# Exploration: fix-live-match-stats

**Date**: 2026-08-11
**Change**: `fix-live-match-stats`
**Mode**: openspec

## Bug (user report)

Live match UI shows impossible stats at minute 2' (Boca Juniors vs Deportivo Recoleta, Copa Sudamericana):
Tiros 0/6, Córners 4/2, T. Amarillas 3/0, T. Rojas 0/0, Faltas 0, Offsides 0, Predicción Pre-Partido 33%/33%.

Live verification (2026-08-11 ~17:15, event `401903297`, now at 11'):
- ESPN scoreboard: `status.type.state=in`, `displayClock="11'"` → minute parses to 11.
- ESPN summary boxscore is CLEAN: Boca corners 1 / yellows 0 / shots 0; Recoleta corners 0 / yellows 0 / shots 1.
- Conclusion: the app displayed stats that do NOT come from the current ESPN boxscore.

## Flow map (end-to-end)

### Frontend render path
1. `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx:32-47` — match object = live store entry (`useLiveStore`), prediction = store prediction if valid else `selectedLiveMatch.prediction` (built fallback).
2. `LiveMatchDetailsModal.tsx:92-102` → `LiveScoreBoard.tsx:150-172` (renders `{match.minute}'`), `LiveMatchStats.tsx:82-202` (renders Tiros/Córners/Amarillas/Rojas/Faltas/Offsides with `?? 0` fallbacks), `PreMatchPrediction.tsx:74,101` (renders `home_win_probability*100` / `away_win_probability*100`).
3. `frontend/src/application/stores/useLiveStore.ts:40-73` — `fetchMatches()` → `liveApi.getLiveMatchesWithPredictions()`; store persisted to IndexedDB (`useLiveStore.ts:96-102`, key `live-matches-storage-v2`).
4. `frontend/src/infrastructure/api/live.ts:24-120` — merge: backend `/api/v1/matches/live/with-predictions` + ESPN fallback `fetchESPNLiveMatches()`:
   - `live.ts:93-108` — for a backend match matched by fuzzy team name (`live.ts:77-86`): **minute/status from ESPN, corners prefer BACKEND (`??`), yellow/red cards/shots ALWAYS from backend spread** — never refreshed from ESPN.
   - `live.ts:109-112` — no backend match → raw ESPN match (all stats from ESPN summary boxscore).
   - `live.ts:62-66` — if ESPN returns zero events, `[]` (no matches shown).
5. `frontend/src/infrastructure/external/espn.ts:90-297` — public ESPN fallback: scoreboard for 30+ leagues (`espn.ts:99-132`), summary enrichment for `in`/`ht` events (`espn.ts:157-173`), `extractStat` from `boxscore.teams[].statistics[]` by team id (`espn.ts:74-87`, corners `wonCorners`/`corners`, cards `yellowCards`/`redCards`, shots `totalShots`, fouls `foulsCommitted`, offsides `offsides`, `espn.ts:211-268`), minute `event.status.displayClock` (`espn.ts:231`). 10s module cache (`espn.ts:69-71`).
   - Verified stat names & `displayValue` format against live ESPN summary: `wonCorners='1'`, `yellowCards='0'`, `totalShots='0'` — parsing is correct.
6. `frontend/src/presentation/components/MatchDetails/LiveMatchesList.tsx:28-52` — store entries → `LiveMatchRaw`; click → `matchLiveWithPrediction()`.
7. `frontend/src/utils/matchMatching.ts:151-218` — **fabricates predictions**: `getFallbackOutcomeProbabilities` (`matchMatching.ts:29-57`) returns **33/34/33 for 0-0 scorelines** → `buildPrediction` (`matchMatching.ts:59-135`) — this is the "Predicción Pre-Partido 33%/33%" the user saw; it is NOT a real ML prediction (the live ESPN stub prediction is all zeros, so `isLivePredictionValid` false at `matchMatching.ts:171-179`).

### Backend API path
8. `backend/src/api/routers/matches.py:36-55` — `GET /api/v1/matches/live/with-predictions`: reads Mongo `match_predictions` with **only** `expires_at > now` — **NO status filter** (`matches.py:43`); same for `GET /api/v1/matches/live` (`matches.py:16-33`).
9. `backend/src/api/mappers/prediction_mapper.py:10-54` — `normalize_prediction_document` → `MatchPredictionModel.model_validate` — **Pydantic v2 `extra="ignore"` DROPS `minute`, `home_total_shots`, `home_shots_on_target`, `home_possession`, `home_fouls`, `home_offsides`** from the response (verified: `backend/src/api/schemas/predictions.py:18-34` has no such fields). Corners/cards survive. This is why backend-enriched matches always lack shots/possession/fouls/offsides/minute.
10. `backend/src/application/use_cases/live_predictions_use_case.py`:
    - `execute()` (447-527) → `_get_live_matches_or_cached` (292-349): FDO live (307) + ESPN fallback for uncovered leagues (315-342, SUD included — `backend/src/domain/constants.py:14`).
    - `espn.py:760-815` `get_live_matches` → `_parse_live_match` (`espn.py:817-888`): **parses NO stats** — corners/cards/shots always `None` for backend ESPN-sourced live matches.
    - `_try_get_precalculated_dto` (1042-1095): DB lookup by match id (`pre_calculated_map`), then **name-based fallback `f"{h_norm}_vs_{a_norm}"` (`1064-1074`) — matches by team names only, NO match-date/status validation**. On hit, refreshes ONLY `home_goals`, `away_goals`, `status`, `minute` (1084-1087) — **stats are never refreshed**.
    - `_persist_and_cache_response` (195-231): persists DTOs (including stale pre-calculated ones) to Mongo with `ttl_seconds=3600` + in-memory/disk cache `TTL_LIVE_MATCHES=30` (`cache_service.py:90`).

### Data sources
- ESPN (frontend `espn.ts` + backend `espn.py`) — real API, no mock in this path. `frontend/src/mock/` and `backend/sample_data/` are NOT wired to the live flow.
- Live verification of the exact match shows ESPN currently returns correct, near-zero stats — the bug values (4/2 corners, 3/0 yellows, 0/6 shots) do not match any current ESPN data for this event.

## Root-cause hypotheses (ranked)

1. **Stale backend prediction doc merged with fresh ESPN minute/status — stats never refreshed (HIGH likelihood).**
   - `live.ts:93-108`: backend corners/cards win over ESPN (`??`), only minute/status overridden from ESPN. A backend doc for this fixture (persisted by a prior live-predictions run or the 6h worker with a past/incorrect fixture whose team names match) carries old full-match stats (corners 4/2, yellows 3/0) while ESPN supplies the fresh minute (2').
   - Backend makes this worse: `matches.py:21,43` no status filter; `live_predictions_use_case.py:1064-1074` name-only fallback; `1084-1087` refreshes goals/status/minute only.
   - Note: shots (0/6) cannot survive the `MatchModel` drop in the current repo — either a deployment drift (older schema with shots), or the shots row came from the raw ESPN path while corners/cards came from backend — a MIXED source. Either way, the minute-vs-stats inconsistency is explained by backend-first merge.

2. **ESPN summary boxscore served stale/wrong stats at match start (MEDIUM likelihood, unverifiable retroactively).**
   - `espn.ts:179-230` trusts whatever the summary endpoint returns for the event; at ~2' ESPN may have served placeholder or previous-state values (corners 4/2, yellows 3/0, shots 0/6). Current boxscore is clean, but the app has no guard against physically-impossible stat values for the displayed minute.

3. **No stats sanity/availability guard anywhere (HIGH likelihood as contributing factor).**
   - `LiveMatchStats.tsx:82-202` renders `?? 0` unconditionally; nothing validates that corners/cards/shots are consistent with the match minute (e.g., ≥3 yellows before 5' is impossible) or that stats belong to the same match instance. Backend-enriched matches ALWAYS show shots/fouls/offsides as 0 (dropped fields) while ESPN matches show real values — inconsistent UI truth.

4. **IndexedDB-persisted zombie matches (LOW-MEDIUM likelihood).**
   - `useLiveStore.ts:96-102` persists `matches` to IndexedDB; Zustand hydrates before the first `fetchMatches()` completes, so a previous session's match list (same fixture, wrong stats) can flash/render in the modal briefly.

5. **Fabricated "Predicción Pre-Partido" (CONFIRMED behavior, not the main bug).**
   - `matchMatching.ts:29-57`: 33/34/33 fallback for 0-0 → `PreMatchPrediction.tsx:74,101` shows "33% / 33%" as if it were a real pre-match prediction. User-visible misleading data.

## Data truth (external provider)

- ESPN scoreboard (`/sports/soccer/{slug}/scoreboard`): `status.type.state` ∈ {pre, in, post}; `status.displayClock` e.g. `"11'"`; competitors carry `homeAway`, `team.id`, `score`.
- ESPN summary (`/sports/soccer/{slug}/summary?event={id}`): `boxscore.teams[].statistics[]` per team with names `wonCorners`, `yellowCards`, `redCards`, `totalShots`, `shotsOnTarget`, `foulsCommitted`, `offsides`, `possessionPct`; `displayValue` is a plain numeric string. Verified live for event 401903297.
- Backend `MatchModel` (`predictions.py:18-34`) cannot represent minute/shots/possession/fouls/offsides — silent data loss on every live endpoint.
- Backend ESPN `_parse_live_match` (`espn.py:817-888`) sets NO stats fields — backend-served live matches always have `None` corners/cards, so the frontend merge's `??` prefers... backend `None` → falls back to ESPN only for corners; yellows/reds from backend remain `undefined` → UI `?? 0`.

## Risk areas (same class of bug elsewhere)

- `matches.py:16-33` (`/live`) and `matches.py:58-118` (`/daily`) — same no-status-filter read of `match_predictions`; FT documents with future `expires_at` are served.
- `live.ts:93-108` merge — yellow/red cards and shots NEVER refreshed from ESPN; only corners/minute/status are.
- `live_predictions_use_case.py:1064-1074` name-only fallback — can bind a prediction from a past fixture with identical team names (no date/status check); `_deduplicate_and_merge` (`811-847`) also mixes stats across sources.
- `cache_service.py:90` 30s live cache + `_persist_and_cache_response` 3600s Mongo TTL — stale docs outlive the match (TTL measured from write, not match end).
- Frontend `espn.ts` 10s module cache + IndexedDB persistence (`useLiveStore.ts:96-102`).
- `matchMatching.ts` fabricated predictions shown as "Predicción Pre-Partido" in `PreMatchPrediction.tsx:74,101`.
- Legacy `LiveMatches.tsx`/`useLiveMatches.ts` path (`useLiveMatches.ts:67-95`, `mapBackendMatch` with `|| 0`) renders the same stats without guards.

## Recommendation for proposal phase

1. Frontend merge (`live.ts`): prefer ESPN live stats as the base for ALL live stats (corners, cards, shots, fouls, offsides) and only use backend values when ESPN lacks them; add a stats-consistency guard (e.g., hide stats when minute < 5 or when values are physically impossible for the elapsed minute).
2. Backend: filter live endpoints by match `status` (`matches.py:21,43`), add match-date validation to the name fallback (`live_predictions_use_case.py:1064-1074`), and refresh stats on pre-calculated DTOs (or stop persisting live DTOs to Mongo).
3. Add `minute`/extended stats to `MatchModel` (`predictions.py:18-34`) or stop dropping them — the schema loss is a silent data-truth bug.
4. `matchMatching.ts`: don't surface fabricated fallback predictions as "Predicción Pre-Partido" — show "no prediction" state instead.
5. Add tests: merge precedence (`live.ts`), backend stats refresh on pre-calculated DTOs, status filter on live endpoints.
