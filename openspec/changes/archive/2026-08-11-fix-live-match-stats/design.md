# Design: Fix Live Match Stats

## Technical Approach

Four independent surgical fixes at the two data-binding points:

1. **Frontend merge** (`live.ts:93-108`) — invert precedence: ESPN is the base/truth for all live stats; backend prediction doc fills only per-stat gaps.
2. **Backend `/live` endpoints** (`matches.py:21,43`) — filter the Mongo query to in-progress statuses.
3. **Backend name fallback** (`live_predictions_use_case.py:1064-1074`) — require `match_date` equality before binding a same-name doc.
4. **Prediction honesty** (`LiveMatchDetailsModal.tsx:49-50`) — gate availability on the fabricated-fallback marker.

No new abstractions, no schema changes, no new services. One enabling tweak: `espn.ts` `extractStat` must return `undefined` (not `0`) when a stat is absent, so the merge can distinguish "ESPN lacks this stat" from "ESPN says 0" (spec scenario: backend fills only ESPN gaps).

## Architecture Decisions

| # | Decision | Options | Choice | Rationale |
|---|----------|---------|--------|-----------|
| D1 | Merge precedence | Backend-first (status quo) vs ESPN-first | **ESPN-first, per stat** | ESPN is the verified live source; backend docs are stale (bug: corners 4/2 at 2' vs 1/0 at 11') |
| D2 | "ESPN has data" semantics | null vs 0 vs undefined | **Defined value (incl. 0) = data; `undefined` = gap** | ESPN's genuine 0 yellows must beat backend's stale 3; `undefined` opens backend fallback for that stat only |
| D3 | Status filter expression | Python post-filter vs Mongo `$in` query | **Mongo query on `"data.match.status"`** | Doc shape verified: `save_match_prediction` stores payload under `data` → `data.match.status`; cheapest, matches proposal wording |
| D4 | Status vocabulary | — | **LIVE = {1H, 2H, HT, LIVE, IN_PLAY, PAUSED}**; excluded: FT, AET, PEN, FINISHED, post, NS, TIMED, SCHEDULED, pre | Per spec; `expires_at` alone is insufficient — finished docs keep future TTL |
| D5 | Fixture identity (name fallback) | Event-id vs teams+date | **Teams (existing key) + calendar-date equality** | ID namespaces differ (ESPN event id vs backend match_id) — not comparable; date kills next-week same-name docs |
| D6 | Date tolerance | Exact date vs ±1 day window | **Exact calendar date (`YYYY-MM-DD`), no tolerance** | Spec scenario demands rejecting next-week fixtures; mismatch falls through to real-time inference (graceful). Midnight-crossing edge accepted |
| D7 | Prediction honesty | Zero-out fallback probabilities vs gate on marker | **Gate `isPredictionAvailable` on `data_sources` marker** | `buildPrediction` already stamps `["live_match_fallback"]` (string exists only in matchMatching.ts, never in backend `data_sources`); one-line boolean, matching internals untouched |

## Data Flow

```
ESPN scoreboard ─► espn.ts extractStat (undefined when stat absent) ─┐
backend /live/with-predictions ──► (status-filtered docs) ────────────┴─► live.ts merge
    per stat: ESPN value defined ? ESPN : backend    (minute/status always ESPN)
    ▼
LiveMatchesList ─► matchLiveWithPrediction (unchanged) ─► LiveMatchDetailsModal
    ▼
isPredictionAvailable = (hwp > 0 || conf > 0) && !data_sources.includes("live_match_fallback")
    ├─ true  → real PreMatchPrediction + SuggestedPicks
    └─ false → "No hay predicción pre-partido disponible para este evento."
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/infrastructure/api/live.ts` | Modify | Merge (93-108): start from ESPN match, override stat only when ESPN value `!== undefined`; minute/status always ESPN; backend prediction preserved |
| `frontend/src/infrastructure/external/espn.ts` | Modify | `extractStat` returns `undefined` when boxscore/team/stat missing; guard possession `+ "%"` concat |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.tsx` | Modify | Availability gate (49-50) also excludes fallback-only predictions |
| `backend/src/api/routers/matches.py` | Modify | Add `LIVE_STATUSES` constant; both queries (21, 43) gain `"data.match.status": {"$in": ...}` |
| `backend/src/application/use_cases/live_predictions_use_case.py` | Modify | Name-fallback branch (1068): parse both `match_date` ISO strings, require equal `.date()`; mismatch → don't bind → real-time fallback |
| `frontend/src/infrastructure/api/live.test.ts` | Create | Merge precedence unit tests |
| `frontend/src/presentation/components/MatchDetails/LiveMatchDetailsModal.test.tsx` | Create | No-prediction state test |
| `backend/tests/unit/test_matches_live_endpoints.py` | Create | Status filter endpoint tests |
| `backend/tests/unit/test_live_predictions_use_case.py` | Modify | Date-guard tests |

## Interfaces / Contracts

```python
# matches.py — module constant, single source of truth
LIVE_STATUSES = {"1H", "2H", "HT", "LIVE", "IN_PLAY", "PAUSED"}
# query: {"expires_at": {"$gt": now}, "data.match.status": {"$in": list(LIVE_STATUSES)}}
```

Merge contract (`live.ts`): for each stat key, `merged[stat] = espn[stat] !== undefined ? espn[stat] : backend[stat]`. Stat keys: `home_goals, away_goals, home_corners, away_corners, home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards, home_total_shots, away_total_shots, home_shots_on_target, away_shots_on_target, home_fouls, away_fouls, home_offsides, away_offsides, home_possession, away_possession`. Non-live fields (odds, spi, events) keep backend values.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (frontend) | Merge precedence | Mock `apiClient` + `fetchESPNLiveMatches`; assert: ESPN wins when both present (incl. 0), backend fills only `undefined` gaps, empty ESPN → `[]`, backend failure → ESPN list only |
| Unit (frontend) | Modal honesty | Mock `useLiveStore`/`useUIStore`; prediction with `data_sources: ["live_match_fallback"]`, hwp 0.33 → renders "No hay predicción…"; `["Rigorous ML"]` → renders bars |
| Unit (backend) | Status filter | Monkeypatch repo `find` returning FT + NS + 1H docs; assert only 1H served, both `/live` endpoints |
| Unit (backend) | Date guard | Call `_try_get_precalculated_dto`: same-name doc + different `match_date` → `None`; equal date → DTO; exact-id path unaffected (no date check) |

## Migration / Rollout

No migration. Four independently revertible changes; `git revert` of the branch restores prior behavior. Query filter may exclude legacy docs lacking `data.match.status` — accepted (can't prove them live).

## Open Questions

- Midnight-crossing matches (kickoff 23:00, now 00:30 next day) fail exact-date equality → real-time inference path serves them. Acceptable per spec; flag if false negatives appear in practice.
