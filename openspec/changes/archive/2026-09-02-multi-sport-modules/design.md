# Design: Multi-Sport Modules — Plumbing

## Technical Approach

Wire a `sport` dimension end-to-end (Exploration Approach 1): unified dataset `leagues_global.json` gains per-league `sport` field + new sport sections; loader, API, Mongo docs, and frontend all carry/filter on `sport`. Existing football data defaults to `"soccer"`; no `?sport=` param returns soccer (backward compatible). `league_id` stays the global PK, prefixed by sport (`B_MLB`, `T_WTA_001`, `K_NBA`) to keep cache keys and `match_id` uniqueness.

Scope is plumbing only — no new data sources or prediction-model changes. `PredictionModel` stays football-shaped; new sports map `draw_probability`→0 and over/under→optional (explicit, not silent).

## Architecture Decisions

| Decision | Options | Choice / Rationale |
|----------|---------|--------------------|
| Dataset structure | (A) unified+`sport` discriminator, (B) per-sport files | **A**. One loader, one schema version; `league_id` PK preserved. B duplicates loader/router boilerplate — overkill for plumbing. |
| Sport routing surface | (A) `?sport=` query param, (B) per-sport routers | **A**. Additive param, backward compatible. B explodes endpoint count. |
| Domain entities | (A) keep football `PredictionModel`, (B) polymorphic `Sport` entities | **A** now. B is a follow-on change (Approach 3) to avoid scope explosion. New sports: draw=0, over/under optional. |
| Sport state location | `useUIStore.selectedSport` vs `usePredictionStore` | **useUIStore** — global view dimension (like `currentView`), not prediction data. `usePredictionStore` reads it for fetch params. |
| Sport enum source | Backend `constants.py` + frontend `constants.ts` | Both, mirroring existing pattern (no shared package; YAGNI). |

## Data Flow

```
leagues_global.json (sport field)
  └─ league_loader.py (LeagueDataset.get_by_sport, sport on league)
       └─ constants.py LEAGUES_METADATA (sport-aware)
            ├─ leagues.py ?sport= → build_leagues_response(sport)
            └─ prediction_mapper (embeds league w/ sport)

Mongo match_predictions (doc.sport, default "soccer")
  └─ repo.get_leagues_ids_with_predictions(sport) / get_all_active_predictions(sport)
       └─ predictions.py ?sport=

Frontend:
  useUIStore.selectedSport ──► usePredictionStore.fetchLeagues(sport)/fetchPredictions(sport)
        └─► leaguesApi.getActiveLeagues(sport) ──► GET ?sport=
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/infrastructure/data/leagues_global.json` | Modify | Add `"sport":"soccer"` to existing leagues + `sport` top-level; add `tennis`/`baseball`/`basketball` sections with `continents→countries→leagues` shape; placeholder leagues/teams; bump `_metadata` version + counts |
| `backend/src/infrastructure/data/league_loader.py` | Modify | Multi-sport indexing; inherit sport (default `"soccer"`); add `get_by_sport(sport)`; sport in `to_leagues_metadata` |
| `backend/src/domain/constants.py` | Modify | Add `Sport` enum (`soccer|tennis|baseball|basketball`); sport-aware `LEAGUES_METADATA`, `to_leagues_metadata(sport=)` |
| `backend/src/api/mappers/league_mapper.py` | Modify | `build_leagues_response(sport="soccer")`, `find_league(id, sport)` filter; sport on `LeagueModel` |
| `backend/src/api/routers/leagues.py` | Modify | `?sport=` param on `GET /leagues`, `/leagues/active`, `/{league_id}` |
| `backend/src/api/routers/predictions.py` | Modify | `?sport=` filter on `GET /predictions/league/{league_id}` |
| `backend/src/api/schemas/leagues.py` | Modify | `sport` on `LeagueModel`, `LeaguesResponse` |
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modify | `sport` on writes, `sport` filter in queries, default `"soccer"` via `doc.get` |
| `backend/src/infrastructure/repositories/async_mongo_adapter.py` | Modify | `sport` propagate through async paths |
| `backend/src/infrastructure/repositories/async_mongo_repository.py` | Modify | `sport` in pipeline/query builders |
| `frontend/src/domain/entities/match.ts` | Modify | `sport` on `League`; `Sport` union type |
| `frontend/src/config/constants.ts` | Modify | `SPORTS` list, `sport` in `API_ENDPOINTS` |
| `frontend/src/infrastructure/api/leagues.ts` | Modify | `sport` param on `getLeagues`/`getActiveLeagues` (optional, default `"soccer"`) |
| `frontend/src/application/stores/useUIStore.ts` | Modify | `selectedSport` + `setSport` |
| `frontend/src/application/stores/usePredictionStore.ts` | Modify | Read `selectedSport`, pass to fetch calls |
| `frontend/src/presentation/components/LeagueSelector/` | Modify | Sport toggle (segmented control / chips); sport-aware country/league lists |

## Interfaces / Contracts

```python
# backend/src/domain/constants.py
class Sport(str, Enum):
    SOCCER = "soccer"; TENNIS = "tennis"
    BASEBALL = "baseball"; BASKETBALL = "basketball"

# repository query filter (all three repos)
def get_all_active_predictions(skip=0, limit=100, league_id=None, sport="soccer"):
    query = {"expires_at": {"$gt": now}}
    if league_id: query["league_id"] = league_id
    if sport:     query["sport"] = sport  # doc stored at top level
```

```typescript
// frontend/src/domain/entities/match.ts
export type Sport = "soccer" | "tennis" | "baseball" | "basketball";
export interface League { id: string; name: string; country: string; sport?: Sport; ... }
```

Mongo doc gains top-level `sport` (default via `doc.get("sport","soccer")`); embedded `data.match.league` also carries `sport`.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (backend) | `get_by_sport`, sport default on missing field, enum parsing | pytest `test_league_loader`, `test_constants` |
| Unit (frontend) | sport toggle + store fetch param wiring | Vitest `usePredictionStore`, LeagueSelector |
| Integration | `GET /leagues?sport=tennis` returns tennis only; no param → soccer | httpx/TestClient against repo stub |
| Backward compat | existing docs without `sport` return as soccer | seed Mongo doc w/o sport, assert default |

## Migration / Rollout

No destructive migration. Existing Mongo docs lack `sport` → default `"soccer"` at read. New writes include `sport`. Optional one-shot backfill script to `$set sport:"soccer"` on existing docs (additive, non-blocking). All changes additive; rollback = revert PR.

## Open Questions

- [ ] Tennis/baseball/basketball: which section shape for placeholder teams (reuse `continents→countries→leagues` vs. flatter per-sport top key)? Design favors reusing the nested shape for loader reuse.
- [ ] Confirm whether `getActiveLeagues` should filter by sport on the repo aggregate or filter returned metadata client-side.
