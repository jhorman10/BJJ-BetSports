# live-match-stats Specification

## Purpose

Live stats and predictions shown for in-play matches must reflect the current ESPN live source (minute, corners, cards, shots, fouls, offsides), never stale backend documents or fabricated values. Backend `/live` endpoints serve only genuinely in-progress fixtures; the pre-calculated prediction fallback binds only to the same fixture instance; the UI never presents a fabricated default prediction as a real "Predicción Pre-Partido".

## Requirements

### Requirement: ESPN-first merge precedence for live stats

The frontend merge (`infrastructure/api/live.ts:93-108`) MUST treat ESPN live data as the base/truth for ALL live stats — corners, yellow cards, red cards, shots, fouls, offsides — when ESPN provides a value. Backend prediction-doc values MUST be used ONLY as per-stat fallback when ESPN lacks that stat. Minute and status MUST come from ESPN. When ESPN returns zero live matches, the merge MUST return an empty list (ESPN-verified-live-only behavior preserved).

#### Scenario: ESPN stats win when both sources present

- GIVEN an ESPN live match (event 401903297) with corners=1, yellows=0 AND a backend doc for the same fixture with corners=4, yellows=3
- WHEN the merge runs
- THEN the merged match shows ESPN values (1 corner, 0 yellows)
- AND minute/status come from ESPN, not the backend doc

#### Scenario: Backend fills only ESPN gaps

- GIVEN ESPN provides corners/cards but lacks fouls, while the backend doc has fouls
- WHEN the merge runs
- THEN fouls take the backend value
- AND every stat ESPN provides keeps the ESPN value

#### Scenario: Backend unavailable

- GIVEN the backend request fails or returns empty
- WHEN the merge runs
- THEN ESPN matches are still returned
- AND no fabricated stats or zero-stubs are injected for missing values

#### Scenario: No ESPN live data

- GIVEN ESPN returns zero live matches
- WHEN the merge runs
- THEN the result is empty (no matches shown)

### Requirement: Live endpoints serve only in-progress matches

`GET /api/v1/matches/live` and `GET /api/v1/matches/live/with-predictions` MUST return only documents whose match status is in the live set (`1H`, `2H`, `HT`, `LIVE`, `IN_PLAY`, `PAUSED`). Documents with finished status (`FT`, `AET`, `PEN`, `FINISHED`, `post`) or not-started status (`NS`, `TIMED`, `SCHEDULED`, `pre`) MUST NOT be served, even when `expires_at` is still in the future.

#### Scenario: Finished doc excluded

- GIVEN a prediction doc with status `FT` and future `expires_at`
- WHEN `GET /live/with-predictions` is called
- THEN the doc is absent from the response

#### Scenario: Not-started doc excluded

- GIVEN a prediction doc with status `NS` (or `pre`) and future `expires_at`
- WHEN `GET /live` is called
- THEN the doc is absent from the response

#### Scenario: In-progress doc included

- GIVEN a prediction doc with status `1H` and future `expires_at`
- WHEN either live endpoint is called
- THEN the doc is returned unchanged in shape

### Requirement: Name fallback binds only the same fixture

The pre-calculated name fallback (`live_predictions_use_case.py:1064-1074`) MUST bind a prediction doc found by normalized team names ONLY when the doc's `match_date` matches the live match's date (same fixture instance). A same-name doc from a different match instance MUST NOT be bound; the use case MUST proceed to the real-time inference fallback.

#### Scenario: Same fixture binds

- GIVEN a live match and a stored doc with identical normalized names and equal match_date
- WHEN the name fallback runs
- THEN the doc is bound and returned as the pre-calculated DTO

#### Scenario: Same names, different date rejected

- GIVEN a stored doc with identical normalized names but a match_date different from the live match's date (e.g., next week's fixture)
- WHEN the name fallback runs
- THEN the doc is NOT bound
- AND the flow continues to the real-time prediction fallback

#### Scenario: ID lookup unaffected

- GIVEN a doc found by exact match id in the pre-calculated map
- WHEN the pre-calculated lookup runs
- THEN binding succeeds without date comparison

### Requirement: Fabricated predictions never shown as real

The scoreline-derived fallback probabilities (`matchMatching.ts:29-57`: 33/34/33 for 0-0, 55/25/20, 20/25/55) MUST NOT be presented as a real pre-match prediction. A prediction whose probabilities originate solely from the fabricated fallback MUST render the no-prediction state in `PreMatchPrediction.tsx` ("No hay predicción pre-partido disponible para este evento.") instead of percentage bars.

#### Scenario: 0-0 live match without real prediction

- GIVEN a 0-0 live match with no genuine prediction (fallback probabilities only)
- WHEN the match detail modal renders
- THEN the no-prediction state is shown
- AND 33%/33% (or any fallback percentage) never appear as a pre-match prediction

#### Scenario: Real prediction unchanged

- GIVEN a live match with a genuine prediction
- WHEN the match detail modal renders
- THEN the full pre-match prediction UI renders as before

## Non-Goals

- `MatchPredictionModel`/`MatchModel` schema extension (minute, shots, possession, fouls, offsides fields) — deferred
- Backend ESPN stats parsing (`espn.py`) — deferred; unneeded once merge prefers ESPN
- Stats-vs-minute sanity guard — follow-up
- `/daily` endpoint status guard — separate change
- IndexedDB zombie hydration and legacy `useLiveMatches.ts` path — separate change

## Verification

- Merge unit test: ESPN stats win when both present; backend fills only missing stats (success criteria 1)
- Backend test: `/live/with-predictions` never returns finished/not-started docs (success criteria 2)
- Backend test: name fallback rejects same-name doc with different match_date (success criteria 3)
- Frontend test: 0-0 live match shows no-prediction state, never 33/33 (success criteria 4)
- Manual: event 401903297 renders ESPN values (1 corner, 0 yellows)
