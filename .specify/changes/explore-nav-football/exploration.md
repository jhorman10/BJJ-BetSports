# Exploration: Navigation Structure & Football Predictions Bug

## Task 1: Navigation Structure

### Current State

**Main Navigation** (`frontend/src/presentation/components/Layout/MainLayout.tsx`):
| Route | Label | Icon | Page Component |
|-------|-------|------|----------------|
| `/` | Predicciones | SportsSoccer | LeagueSelector + PredictionGrid |
| `/tennis` | Tenis | SportsTennis | TennisPredictionPage |
| `/baseball` | Béisbol | SportsBaseball | BaseballUpcomingPage |
| `/parley-calculator` | Calculadora | Calculate | ParleyCalculatorPage |
| `/bot` | Bot | SmartToy | BotDashboard (conditional) |

**Sport Selector** (inside `LeagueSelector` component, home page only):
- `ToggleButtonGroup` with 4 sports: Fútbol, Tenis, Béisbol, Baloncesto
- Selected sport stored in `useUIStore.selectedSport` (persisted to localStorage)
- When sport changes → clears country/league → refetches leagues for new sport

**Sport constants** (`frontend/src/config/constants.ts`):
```ts
export const SPORTS = [
  { value: "soccer", label: "Fútbol" },
  { value: "tennis", label: "Tenis" },
  { value: "baseball", label: "Béisbol" },
  { value: "basketball", label: "Baloncesto" },
];
```

### Issues Found

1. **Basketball is a dead option**: Defined in SPORTS constant and shown in toggle, but has:
   - NO route in App.tsx
   - NO page component
   - NO backend router (`backend/src/api/routers/` has no basketball_router.py)
   - NO prediction service
   - Selecting it shows empty leagues (no basketball leagues with predictions in DB)

2. **Inconsistent sport navigation patterns**:
   - Tennis → dedicated route `/tennis` with its own page
   - Baseball → dedicated route `/baseball` with its own page
   - Football → default route `/` with shared LeagueSelector+PredictionGrid
   - Basketball → nothing

3. **Sport toggle only on home page**: The sport ToggleButtonGroup is inside LeagueSelector, which only renders on `/`. If user navigates to `/tennis`, there's no way to switch back to football without going to `/` first.

### Affected Files
- `frontend/src/presentation/components/Layout/MainLayout.tsx` — NAV_ITEMS array (line 40-45)
- `frontend/src/App.tsx` — Route definitions (line 65-157)
- `frontend/src/config/constants.ts` — SPORTS array (line 61-66)
- `frontend/src/presentation/components/LeagueSelector/LeagueSelector.tsx` — Sport toggle (line 164-203)
- `frontend/src/application/stores/useUIStore.ts` — selectedSport state

---

## Task 2: Football Predictions Bug

### Root Cause

The multi-sport commit (`ebc3839`) added sport filtering to MongoDB queries. **Old football predictions in MongoDB likely lack the `sport` field**, causing them to be excluded by the new queries.

**The problem chain**:

1. **Backend query** (`backend/src/infrastructure/repositories/mongo_repository.py:170-181`):
   ```python
   def get_league_ids_with_predictions(self, sport: str | None = None):
       match_stage = {"expires_at": {"$gt": get_current_time()}}
       if sport:
           match_stage["sport"] = sport  # Adds {"sport": "soccer"}
       pipeline = [
           {"$match": match_stage},
           {"$group": {"_id": "$league_id"}},
       ]
   ```
   MongoDB `{"sport": "soccer"}` does NOT match documents where the `sport` field is absent. Only documents explicitly containing `"sport": "soccer"` are returned.

2. **Old predictions saved without sport field**: Before commit ebc3839, `bulk_save_predictions` did NOT set a `sport` field. The `$set` operation only included `league_id`, `data`, `expires_at`, `last_updated`. The `sport` parameter was added in the same commit.

3. **League selector shows empty**: `GET /api/v1/leagues/active?sport=soccer` calls `get_league_ids_with_predictions(sport="soccer")` → returns empty list → frontend shows no leagues → user can't select a league → "No hay predicciones disponibles"

4. **Predictions endpoint also affected**: `GET /api/v1/predictions/league/{id}?sport=soccer` calls `get_all_active_predictions(sport="soccer")` → filters out old predictions → returns empty list.

### Secondary Issue: find_league validation

`find_league(league_id, sport=sport)` now validates that the league's sport matches the query sport. If `LEAGUES_METADATA` is loaded from the dataset, leagues have `"sport"` keys. But if the fallback metadata is used, leagues lack `"sport"` and default to `"soccer"`, which could cause false 404s for non-soccer leagues.

### Affected Files

**Backend (root cause)**:
- `backend/src/infrastructure/repositories/mongo_repository.py:170-181` — `get_league_ids_with_predictions` sport filter
- `backend/src/infrastructure/repositories/mongo_repository.py:320-333` — `get_all_active_predictions` sport filter
- `backend/src/infrastructure/repositories/mongo_repository.py:274-318` — `bulk_save_predictions` (now sets sport, but old docs don't have it)
- `backend/src/api/routers/predictions.py:21-79` — predictions endpoint sport param
- `backend/src/api/routers/leagues.py:21-56` — leagues/active endpoint sport param
- `backend/src/api/mappers/league_mapper.py:37-49` — `find_league` sport validation

**Frontend (secondary)**:
- `frontend/src/presentation/components/LeagueSelector/LeagueSelector.tsx:49,55-68` — sport toggle handler
- `frontend/src/application/stores/usePredictionStore.ts:91-133` — fetchLeagues reads sport from UIStore
- `frontend/src/application/stores/usePredictionStore.ts:158-201` — fetchPredictions reads sport from UIStore

### Recommended Fix

**Option A — Backfill existing predictions** (recommended):
Run a MongoDB migration to add `"sport": "soccer"` to all existing predictions that lack the field:
```javascript
db.match_predictions.updateMany(
  { sport: { $exists: false } },
  { $set: { sport: "soccer" } }
)
```
This is safe because all pre-multi-sport predictions were soccer.

**Option B — Make queries sport-optional**:
Change the queries to also match documents where `sport` field is absent:
```python
if sport:
    match_stage["$or"] = [{"sport": sport}, {"sport": {"$exists": false}}]
```
Less clean but doesn't require a migration.

**Option C — Both**: Run the migration AND make queries resilient to missing sport field.

### Ready for Proposal
Yes — the root cause is clear. The orchestrator should recommend Option A (backfill) as the primary fix, with Option B as a defensive measure.
