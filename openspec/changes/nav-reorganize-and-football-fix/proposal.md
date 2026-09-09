# Proposal: Navigation Reorganization & Football Bug Fix

## Intent

Football predictions are invisible to users because old documents in MongoDB lack the `sport` field. The `{"sport": "soccer"}` query filter silently drops them. Separately, navigation is inconsistent: tennis and baseball have dedicated pages, but the sport toggle lives inside the page body instead of the navbar, and basketball is defined in code with zero implementation.

## Scope

### In Scope
1. **Fix football visibility bug** — Update MongoDB queries to match documents where `sport` field is missing or `"soccer"`
2. **Remove sport toggle from LeagueSelector** — The `ToggleButtonGroup` (lines 164-189 of `LeagueSelector.tsx`) moves sport selection to navbar
3. **Remove basketball from SPORTS array** — No route, page, or backend exists; removing prevents dead UI
4. **Add basketball to navbar** — Placeholder route or remove from SPORTS entirely (decision: remove)

### Out of Scope
- Basketball feature (new sport, new backend, new pages) — separate feature request
- Tennis/baseball navigation restructuring (already working)
- Backend sport field migration (optional future enhancement)

## Capabilities

### New Capabilities
None — this is a bug fix + UI cleanup, not a new feature.

### Modified Capabilities
- `football-predictions`: Fix sport filter queries to include documents with missing `sport` field
- `navigation`: Restructure navbar to show all active sports, remove body-level sport toggle

## Approach

### Backend Bug Fix
In `mongo_repository.py`, both query functions need updating:
- `get_league_ids_with_predictions` (line 170-181): Change `match_stage["sport"] = sport` to use `$in` operator
- `get_all_active_predictions` (line 320-333): Same pattern

**Query fix pattern**:
```python
if sport:
    match_stage["$or"] = [
        {"sport": sport},
        {"sport": {"$exists": False}},
    ]
```

### Frontend Navigation
1. **LeagueSelector.tsx**: Remove `ToggleButtonGroup` sport toggle (lines 164-189), remove `handleSportChange` handler (lines 55-68), keep only country/league selectors
2. **MainLayout.tsx**: Add sport-specific nav items to `NAV_ITEMS` — currently only shows Predicciones/Tenis/Béisbol/Calculadora
3. **constants.ts**: Remove `basketball` from `SPORTS` array (line 65)

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modified | Fix sport filter queries at lines 170-181 and 320-333 |
| `frontend/src/config/constants.ts` | Modified | Remove basketball from SPORTS array |
| `frontend/src/presentation/components/LeagueSelector/LeagueSelector.tsx` | Modified | Remove sport toggle UI and handler |
| `frontend/src/presentation/components/Layout/MainLayout.tsx` | Modified | Ensure nav shows all 3 active sports |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Query fix affects other sports' documents | Low | MongoDB `$or` is additive; existing sport docs unaffected |
| Removing sport toggle breaks Zustand state | Low | `selectedSport` state remains in UIStore; only UI removed |
| Basketball removal breaks imports | Low | Grep for basketball references before removing |

## Rollback Plan

1. **Backend**: Revert `mongo_repository.py` changes (git checkout)
2. **Frontend**: Revert `LeagueSelector.tsx`, `MainLayout.tsx`, `constants.ts` changes
3. No data migration needed — old documents unchanged, query logic reverts cleanly

## Dependencies

- None — this is a standalone fix/reorganization

## Success Criteria

- [ ] Football predictions appear on `/` route for old documents (missing `sport` field)
- [ ] Sport toggle removed from LeagueSelector body
- [ ] Basketball removed from SPORTS constant and navigation
- [ ] Navbar shows: Predicciones (Fútbol), Tenis, Béisbol, Calculadora
- [ ] No TypeScript errors or broken imports
