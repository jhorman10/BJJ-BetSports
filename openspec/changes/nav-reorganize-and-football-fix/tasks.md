# Tasks: Navigation Reorganization & Football Bug Fix

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 40–60 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low

## Phase 1: Backend — Fix Football Visibility Bug

- [x] 1.1 In `backend/src/infrastructure/repositories/mongo_repository.py`, update `get_league_ids_with_predictions` (lines 173–174): replace `match_stage["sport"] = sport` with `match_stage["$or"] = [{"sport": sport}, {"sport": {"$exists": False}}]`
  - Done: code matches pattern
  - Verify: `GET /api/v1/leagues/active?socer` returns leagues from old documents missing `sport` field

- [x] 1.2 In same file, update `get_all_active_predictions` (lines 330–331): replace `query["sport"] = sport` with `query["$or"] = [{"sport": sport}, {"sport": {"$exists": False}}]`
  - Done: code matches pattern
  - Verify: `GET /api/v1/predictions?sport=soccer` returns old documents with no `sport` field

## Phase 2: Frontend — Remove Sport Toggle from LeagueSelector

- [x] 2.1 In `frontend/src/presentation/components/LeagueSelector/LeagueSelector.tsx`, remove imports: `ToggleButton`, `ToggleButtonGroup`, `SPORTS`, `Sport` (lines 17–18, 25–26)
  - Done: unused imports removed
  - Verify: no TypeScript errors on unused imports

- [x] 2.2 Remove `handleSportChange` function (lines 55–68)
  - Done: handler deleted
  - Verify: no references to `handleSportChange` remain in file

- [x] 2.3 Remove the entire `{/* Sport Toggle */}` block (lines 164–203): the `<Box>` containing `<ToggleButtonGroup>`
  - Done: toggle UI removed
  - Verify: LeagueSelector renders only country/league selectors and live toggle

- [x] 2.4 Remove `selectedSport` and `setSport` from the `useUIStore()` destructuring on line 49 (keep `showLive` and `toggleShowLive`)
  - Done: store destructuring cleaned
  - Verify: no unused variable warnings

## Phase 3: Frontend — Remove Basketball from Constants

- [x] 3.1 In `frontend/src/config/constants.ts`, remove `{ value: "basketball", label: "Baloncesto" }` from `SPORTS` array (line 65)
  - Done: basketball entry removed
  - Verify: `SPORTS` array contains only soccer, tennis, baseball

- [x] 3.2 Update `Sport` type (line 59) to remove `"basketball"`: change to `"soccer" | "tennis" | "baseball"`
  - Done: type union narrowed
  - Verify: TypeScript compiles cleanly, no basketball references remain

## Phase 4: Verify & Cleanup

- [x] 4.1 Run `grep -r "basketball" frontend/src/` to confirm no remaining references
  - Done: zero matches or only comments
  - Verify: no broken imports

- [ ] 4.2 Start dev server, navigate to `/`, `/tennis`, `/baseball` — confirm all three routes load without errors
  - Done: all routes render
  - Verify: manual smoke test passes

- [ ] 4.3 On `/` route, verify football predictions appear including old documents (missing `sport` field) — confirm the backend fix works end-to-end
  - Done: old predictions visible
  - Verify: predictions list is not empty
