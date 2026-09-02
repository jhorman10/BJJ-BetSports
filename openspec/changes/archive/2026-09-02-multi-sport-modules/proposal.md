# Proposal: Multi-Sport Modules — Plumbing

## Intent

The platform is football-only end to end. No `sport` concept exists in dataset, loader, API, or frontend. Adding tennis/baseball/basketball requires plumbing a sport dimension through the entire stack before any sport-specific data or models can be wired. This PR delivers that plumbing.

## Scope

### In Scope
- Add `sport` field to `leagues_global.json` (default `"soccer"`, plus `tennis`, `baseball`, `basketball` sections)
- Add sport-aware indexing to `league_loader.py` (`get_by_sport`, sport on `LeagueDataset`)
- Add `sport` field to MongoDB prediction documents (default `"soccer"` via `doc.get("sport", "soccer")`)
- Add `?sport=` query param to `GET /api/v1/leagues` and `GET /api/v1/predictions/league/{league_id}`
- Update API schemas (`LeagueModel`, `LeaguesResponse`) with sport field
- Update frontend TS types with sport field
- Add sport selector toggle to `LeagueSelector` (wired via `useUIStore.selectedSport`)
- Pass `?sport=` through frontend API layer and store fetch calls
- Create placeholder league/team structure for tennis, baseball, basketball

### Out of Scope
- Actual data sources/fetchers for new sports
- Sport-specific prediction models or training pipeline changes
- Polymorphic domain entities (draw-based `PredictionModel` stays as-is, new sports map draw/over-under to 0/optional)
- Sport-specific UI components (score displays, match cards)
- Live match stats adaptation for non-football sports

## Capabilities

### New Capabilities
- `sport-catalog`: Sport-aware dataset schema, loader indexing, and league catalog with sport dimension
- `sport-api-filtering`: `?sport=` query parameter on league/prediction endpoints, sport field on API schemas
- `sport-selector-ui`: Sport toggle in LeagueSelector, sport state in useUIStore, sport-aware league/country lists

### Modified Capabilities
- `api-client`: Add sport to `API_ENDPOINTS` paths and `getLeagues`/`getActiveLeagues` function signatures (backward compatible — sport param is optional, defaults to `"soccer"`)

## Approach

Unified dataset + `sport` field + `?sport=` query param (Exploration Approach 1). One dataset file, one loader, one schema version. `league_id` stays globally unique by sport prefix (`B_MLB`, `T_WTA_001`). Backward compatible — existing queries default to soccer.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/infrastructure/data/leagues_global.json` | Modified | Add `sport` field to leagues, new sport sections |
| `backend/src/infrastructure/data/league_loader.py` | Modified | Sport-aware indexing, `get_by_sport` method |
| `backend/src/api/routers/leagues.py` | Modified | `?sport=` query param on league endpoints |
| `backend/src/api/routers/predictions.py` | Modified | `?sport=` filter on league predictions |
| `backend/src/api/schemas/leagues.py` | Modified | `sport` field on `LeagueModel`, `LeaguesResponse` |
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modified | `sport` on doc writes/reads, default `"soccer"` |
| `frontend/src/domain/entities/*.ts` | Modified | `sport` field on `League`, `Prediction` types |
| `frontend/src/application/stores/useUIStore.ts` | Modified | `selectedSport` state |
| `frontend/src/application/stores/usePredictionStore.ts` | Modified | Pass `sport` to fetch calls |
| `frontend/src/presentation/components/LeagueSelector/` | Modified | Sport toggle, sport-aware filtering |
| `frontend/src/infrastructure/api/leagues.ts` | Modified | `sport` param on `getLeagues`, `getActiveLeagues` |
| `frontend/src/config/constants.ts` | Modified | Sport enum/constants |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Semantic mismatch (draw/over-under meaningless for tennis) | High | Map new sports: draw=0, over-under=optional. Explicit, not silent. Follow-on: polymorphic domain. |
| Dataset grows large | Medium | Keep unified with `sport` discriminator. Monitor size; split later if needed. |
| Existing prediction docs lack `sport` | High | Default via `doc.get("sport", "soccer")` in all mappers/queries. |
| Cache key collision | Low | League IDs prefixed by sport (`B_`, `T_`, `K_`) guarantee uniqueness. |

## Rollback Plan

Revert the PR. All changes are additive (new fields, new query params, new UI toggle). No migration — existing docs untouched, `sport` defaults to `"soccer"` everywhere. No data transformation required.

## Dependencies

- None (self-contained plumbing change)

## Success Criteria

- [ ] `GET /api/v1/leagues?sport=soccer` returns football leagues (backward compat)
- [ ] `GET /api/v1/leagues?sport=tennis` returns tennis leagues
- [ ] `GET /api/v1/predictions/league/{id}?sport=baseball` returns baseball predictions
- [ ] Frontend sport toggle switches league list without page reload
- [ ] Existing football flow works identically with no sport param (defaults to soccer)
- [ ] `pytest tests/ -q` passes
- [ ] Frontend type-check passes (`tsc --noEmit`)
