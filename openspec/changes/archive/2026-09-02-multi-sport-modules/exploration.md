# Exploration: Multi-Sport Modules (Tennis, Baseball, Basketball)

## Current State

The platform is **football-only end to end**. There is no `sport` concept anywhere in the codebase — the entire data model, domain layer, data ingestion, API, and frontend are hardcoded around football (soccer).

### Data Layer
- `backend/src/infrastructure/data/leagues_global.json` (124 KB / 4,347 lines, version 1.0.0) is a football-specific dataset with top-level keys `_metadata`, `continents`, `international`. Structure: `continents → confederation → countries → country(code, flag) → leagues[]`. Each league has `id, name, tier, type, format, teams, promotion, relegation, active, data_sources, aliases`. It holds 850 leagues across 211 countries, 6 continental confederations + FIFA international tournaments. **No `sport` field exists.**
- `backend/src/infrastructure/data/league_loader.py` — `LeagueDataset` singleton loads the JSON and builds indices by id/country/confederation/tier/type. Hardcodes `scope` to `"domestic"` / `"international"`. No sport dimension.

### Domain Layer
- `backend/src/domain/constants.py` — Hardcoded football tournament tuples (`UCL`, `UEL`, `EURO`, `WC`...) and `LEAGUES_METADATA` (lazily loaded from dataset) + `DEFAULT_LEAGUES`. Football-specific.
- `backend/src/domain/entities/entities.py` — `Team`, `League`, `Match`, `MatchEvent`, `Prediction`, `TeamStatistics`, `MatchPrediction`, `TeamH2HStatistics`. **Deeply football-shaped**: `draw_odds`, `over_25_probability`, `under_25_probability`, `match_outcome` with `DRAW`, `home_corners`, corners/cards/yellow/red probabilities, `points_per_match` (Win=3), `predicted_home_goals`, xG fields, etc. A draw/probability concept does not exist for tennis/baseball in the same way.

### MongoDB Schema
- `match_predictions` collection. Document shape (from `mongo_repository.py` `_to_prediction_result`):
  ```
  {
    match_id (unique),
    league_id,
    labeled: bool,          // TTL partial index on unlabeled docs
    expires_at,             // TTL field
    last_updated,
    data: { match: {...}, prediction: {...}, top_ml_picks: [...] }
  }
  ```
  Indexes: `match_id` unique, `(league_id, expires_at)`, partial TTL on `labeled:false`. `data.match` contains nested `league: {id,name,country}` (football-shaped). **No `sport` field.** League resolution is done at read-time via `LEAGUES_METADATA` (mappers embed league into the match object).

### Data Flow
```
MongoDB match_predictions
  → repositories (mongo_repository.py / async_mongo_adapter.py / async_mongo_repository.py)
    → API routers (leagues, predictions, matches, picks, labeler, training, metrics, monitor)
      → mappers (normalize_prediction_document embeds league via find_league)
        → frontend (fetch leagues → country/league selectors → fetch predictions)
```
- League catalog for the UI comes from `LEAGUES_METADATA` (dataset) filtered by leagues that actually have predictions (`get_league_ids_with_predictions`).
- Data sources (`infrastructure/data_sources/`): `football_data_org`, `football_data_uk`, `espn` (soccer-only BASE_URL), `thesportsdb`, `openfootball`, `api_football`, `github_dataset`, `club_elo`. All soccer-specific.

### API Layer
- `backend/src/api/routers/` — 8 routers: `leagues`, `predictions`, `matches`, `picks`, `labeler`, `training`, `metrics`, `monitor`. All operate on `league_id`. The `predictions` router exposes `GET /predictions/league/{league_id}` and `GET /predictions/match/{match_id}`. **No sport param.**
- Schemas: `LeagueModel{id,name,country}`, `CountryModel`, `LeaguesResponse`, `MatchModel`, `PredictionModel` (entirely football: win/draw/loss, over/under 2.5, corners, cards).

### Frontend
- `frontend/src/domain/entities/match.ts`, `prediction.ts`, `index.ts` — Football-shaped TS types (`League{id,name,country}`, `Prediction` with `home_win_probability`, `draw_probability`, `over_25_probability`, corners/cards, `score_matrix`).
- `frontend/src/application/stores/usePredictionStore.ts` — Zustand store with `selectedCountry` / `selectedLeague` / `fetchLeagues` / `fetchPredictions`. No sport concept.
- `frontend/src/application/stores/useUIStore.ts` — holds `currentView` ("predictions"|"bot"), `showLive`. Natural place for a `selectedSport`.
- `frontend/src/presentation/components/LeagueSelector/` — `LeagueSelector.tsx` (card header + CountrySelect + LeagueSelect row + selected badge), `CountrySelect.tsx`, `LeagueSelect.tsx`, `constants.ts` (COUNTRY_DATA flags/ES names, LEAGUE_TRANSLATIONS ES names, SELECT_STYLES, MENU_PROPS). The selector is soccer-specific and uses `COUNTRY_DATA` for flag emojis.
- `frontend/src/infrastructure/api/leagues.ts` — `getLeagues()`, `getActiveLeagues()` (used by store), `getLeague(id)`.
- `frontend/src/config/constants.ts` — `API_ENDPOINTS` (soccer-shaped paths).

## Affected Areas

- `backend/src/infrastructure/data/leagues_global.json` — needs schema evolution to add `sport` (or a new top-level `sport` key with per-sport sub-datasets).
- `backend/src/infrastructure/data/league_loader.py` — needs sport-aware indexing + query methods (`get_by_sport`).
- `backend/src/domain/constants.py` — international tournament tuples and fallback metadata are football-only.
- `backend/src/domain/entities/entities.py` — `League`, `Team`, `Prediction`, `Match` are football-shaped (draw, over/under, goals, corners/cards).
- `backend/src/infrastructure/repositories/mongo_repository.py` / `async_mongo_adapter.py` / `async_mongo_repository.py` — documents keyed/queried by `league_id`; need `sport` on doc + queries.
- `backend/src/api/routers/leagues.py`, `predictions.py`, `matches.py` — need `?sport=` param or per-sport endpoints.
- `backend/src/api/mappers/league_mapper.py`, `prediction_mapper.py` — league metadata resolution is football-only.
- `backend/src/api/schemas/leagues.py`, `predictions.py` — schemas lack sport and are football-shaped.
- `backend/src/infrastructure/data_sources/*.py` — all soccer-specific sources; new sports need new/multi-sport fetchers.
- `frontend/src/domain/entities/*.ts`, `frontend/src/types/index.ts` — TS types lack sport and are football-shaped.
- `frontend/src/application/stores/usePredictionStore.ts`, `useUIStore.ts` — no selected sport.
- `frontend/src/presentation/components/LeagueSelector/*` — selector is soccer-only; needs sport toggle + sport-aware country/league lists + sport-specific translations.
- `frontend/src/infrastructure/api/leagues.ts`, `frontend/src/config/constants.ts` — endpoints lack sport.

## Approaches

### 1. Unified dataset + `??sport=` query param (recommended incremental)
Add a `sport` field to each league in `leagues_global.json` (default `"soccer"`), plus a new top-level key per sport (e.g. `"tennis"`, `"baseball"`, `"basketball"`) that reuses the existing `continents → countries → leagues` shape. Add `sport` to the Mongo doc and to `LeagueModel`. Extend the league/prediction/matches routers with an optional `sport: str = Query("soccer")` filter. Frontend adds a sport toggle in `useUIStore` + `LeagueSelector` and passes `?sport=` through the API layer.
- Pros: One dataset file, one loader, one schema version; `league_id` stays globally unique by prefixing sport (e.g. `B_MLB`, `T_WTA_001`); minimal endpoint surface (add query param, not new routers); selector is one component with a toggle rather than N parallel views; backward compatible (defaults to soccer).
- Cons: Dataset becomes large (mixed sports in one file); sport-specific logic (data sources, prediction features) still diverges behind the scenes; domain entities still football-shaped for tennis/baseball (over/under goals don't apply).

### 2. Separate datasets + separate endpoints
Per-sport dataset files (`leagues_tennis.json`, `leagues_baseball.json`, `leagues_basketball.json`) and per-sport routers (`/api/v1/{sport}/...`).
- Pros: Clear isolation; datasets stay small; can version each sport independently.
- Cons: Duplicated loader/indexing logic; duplicated router/schema boilerplate; more endpoints to maintain; frontend needs separate views per sport; higher maintenance surface. Overkill for a first multi-sport push.

### 3. Sport-specific domain entities + prediction models
Design a polymorphic domain layer (`Sport`, `BaseballGame`, `TennisMatch`) with sport-specific `Prediction` submodels (no draw, no goals).
- Pros: Correct semantics per sport; enables high-quality per-sport predictions.
- Cons: Highest complexity — touches the entire domain, mappers, repositories, schemas, TS types, and UI. This is really a follow-on AFTER the data/API plumbing works. Risks scope explosion.

### Recommendation
**Recommended: Approach 1 first (unified dataset + `sport` field + `?sport=` query param), with the polymorphic domain layer (Approach 3) carved out as a separate follow-on change.**

Rationale:
- The platform's core value prop today is "predictions per league." To onboard tennis/baseball/basketball, the minimal viable slice is: (a) extend the **catalog** to carry a sport dimension, (b) add **sport to the persisted prediction doc + queries**, (c) expose **sport through the API**, (d) add a **sport toggle in the selector**. That is pure plumbing and unblocks the whole flow with backward compatibility.
- Approach 1 keeps `league_id` as the primary key (prefixed by sport) and reuses the existing router/mapper/repository/selector machinery — matching the "ponytail" minimal-solution and YAGNI principles.
- The genuinely football-specific code (draw probability, over/under goals, corners/cards) belongs to the **prediction semantics**, not the catalog. Fitting tennis into the existing draw-based `PredictionModel` as-is would be semantically wrong, so sports without a draw (tennis, basketball) should map: home_win_probability / away_win_probability with `draw_probability` conceptually ~0, and sport-specific markets expressed as optional fields. For baseball, run totals map to an over/under analog. This keeps the schema stable while allowing refinement.
- The dataset must grow; keeping it unified with a `sport` discriminator preserves the single-source-of-truth loader. Prefixing IDs (`B_`, `T_`, `K_`) guarantees no collisions, but note the hardcoded `DEFAULT_LEAGUES` and cache keys derive from league ids — those stay unique.

## Risks

- **Semantic mismatch (high)**: Tennis/baseball/basketball have no "draw", no "over 2.5 goals", no corners/cards. Forcing them into the football `PredictionModel` yields wrong/meaningless prediction fields. Medium-term the domain must become polymorphic (Approach 3). First slice can default draw_probability and over/under to 0/optional, but this must be explicit, not silent.
- **Dataset size and structure**: A 124 KB football-only file will grow and could get unwieldy as a single JSON. Consider whether a raw `sport` sub-key per country or per-child is cleanest; the loader's nested-`continents` assumption breaks unless each sport keeps the same nested shape.
- **Data sources**: Every existing fetcher is soccer-specific. Real tennis/baseball/basketball data needs new source integrations (e.g., ESPN multi-sport endpoints or sport-specific providers) — this is a significant hidden cost, not just a schema change.
- **Training/ML pipeline**: `TrainingCapabilityService`, model paths (`ml_models/{league_id}_{model_type}.joblib`), and feature extraction are football-specific. Multi-sport training models are a large follow-on.
- **Frontend scope**: Selector translations (`LEAGUE_TRANSLATIONS`, `COUNTRY_DATA`), live match statuses, and prediction cards are soccer-shaped. A sport toggle must also scope the match/prediction view components, not just the selector.
- **Backward compatibility**: existing prediction docs have no `sport` field; must default to `"soccer"` in queries/mappers (`doc.get("sport", "soccer")`) to avoid breaking current data.
- **Cache keys**: derived from `league_id`, still unique if IDs prefixed; but accuracy-history/count keys are league-scoped, fine.

## Ready for Proposal
**Yes.** This is a well-bounded, multi-layer change suitable for a proposal. The orchestrator should tell the user:
- Confirm the recommended approach (unified dataset + `sport` field + `?sport=` param, Approach 1) as the first delivery, with the polymorphic domain model (Approach 3) as a follow-on.
- Flag that real tennis/baseball/basketball **data sources + training models** are the larger hidden scope and should be sequenced separately from the catalog/API/frontend plumbing.
- Confirm whether to scope the first PR to plumbing only (catalog + API + selector toggle) vs. wiring actual new-sport data sources in the same change.
