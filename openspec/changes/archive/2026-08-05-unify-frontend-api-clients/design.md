# Design: Unify Frontend API Clients

## Technical Approach

Consolidate all HTTP transport onto the existing canonical client in `infrastructure/api/client.ts`. `services/api.ts` stops creating its own axios instance and imports the shared `apiClient` singleton, re-pointing its 12 hardcoded paths to `API_ENDPOINTS` while keeping its 14-member export surface (12 endpoint methods + generic `post`/`get`, plus `default`) byte-compatible. Timeout/limit policy becomes centralized constants in `APP_CONFIG`. Dead modules deleted. `useLiveMatches.ts` drops ~150 lines of inline ESPN code for `fetchESPNLiveMatches()` + a pure flat adapter. Three stores share one `isNetworkError` util. Maps to proposal approach steps 1–4 and all api-client spec requirements.

## Architecture Decisions

### D1: Canonical client export shape
| Option | Tradeoff | Decision |
|---|---|---|
| Keep `export const apiClient = createApiClient()` singleton | Existing pattern; 5 modules already import by name | ✅ Chosen |
| Export factory only | Callers could create extra instances (violates single-instance) | Rejected |
| Default export | Breaks named imports in live/predictions/leagues/matches | Rejected |

`client.ts` keeps its internal factory; the configured singleton remains the export. `services/api.ts` deletes its duplicate `createApiClient` + `API_BASE_URL` (lines 22–49).

### D2: Per-method timeouts
| Option | Tradeoff | Decision |
|---|---|---|
| Axios per-request `timeout` config | Native; never mutates shared instance | ✅ Chosen |
| Instance default 30s | Would shorten 90s picks / 5min train | Rejected |
| Clone instances per timeout | Violates one-instance spec | Rejected |

Instance default stays 60s via `APP_CONFIG.API_DEFAULT_TIMEOUT`; long-running endpoints pass `{ timeout }` per request (D4).

### D3: Endpoint constants
`API_ENDPOINTS` stays in `config/constants.ts`. Remove `PARLEYS`, `TOP_ML_PICKS`; fix `TRAIN: "/api/v1/train/run-now"`. `services/api.ts` re-points all 12 paths. `post()`'s `/train` special-case becomes a constant-driven map `{ "/train/run-now": APP_CONFIG.TRAINING_TIMEOUT }` — grep confirms no caller passes `/train` today.

### D4: Timeout/limit policy (normalized)
| Constant | Value | Applies to |
|---|---|---|
| `LIVE_API_TIMEOUT` | 30000 | live.ts (was 10s → 30s) + `getLiveMatchesWithPredictions` (already 30s) |
| `SUGGESTED_PICKS_TIMEOUT` | 90000 | both paths; predictions.ts currently inherits 60s default → 90s (documented) |
| `TRAINING_TIMEOUT` | 300000 | unchanged; now also drives `post()` |
| `DEFAULT_PREDICTIONS_LIMIT` | 30 | predictions.ts default (was 10) |
| `API_DEFAULT_TIMEOUT` | 60000 | client.ts instance default |

`APP_CONFIG.API_TIMEOUT` (10s, used only by live.ts) is replaced by `LIVE_API_TIMEOUT`.

### D5: ESPN adapter
Delete inline ESPN interfaces/`batchFetch`/`fetchPublicLiveMatches`/`extractStat`/cache from `useLiveMatches.ts`; import `fetchESPNLiveMatches`. Add exported pure `toLiveMatch(espn: LiveMatchPrediction): LiveMatch` in the hook module (Adapter at the consumption boundary — transport stays nested, UI stays flat). Mapping: `minute` via `Number.parseInt((m.minute ?? "0").replace("'", ""), 10) || 0` (entity `minute?: string` is `"45:00"`/`"45'"`; flat `LiveMatch.minute: number`); `status` `"HT"` → `"HT"` else `"LIVE"`; team objects passed through (`LiveMatch` accepts `string | object`); league flattened to `league_id`/`league_name`; corners/cards passed through.

### D6: Shared network error classification
`utils/apiErrors.ts`: `isNetworkError(error: unknown): boolean` — `message === "Network Error"` || `code === "ERR_NETWORK"` || `code === "ECONNABORTED"`. Replaces 5 inline blocks across useBotStore/useLiveStore/usePredictionStore. Normalization note: two usePredictionStore blocks currently omit `ECONNABORTED` — they now classify timeouts as network errors (intended).

## Data Flow

```
stores ──► services/api.ts ─┐
stores ──► infrastructure/api/* ─┴──► apiClient (client.ts — sole axios.create) ──► FastAPI :8000

useLiveMatches ──► api.getLiveMatches() ──► backend
             └─ fallback: fetchESPNLiveMatches() ──► toLiveMatch() ──► flat LiveMatch[]
```

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/utils/apiErrors.ts` | Create | `isNetworkError` util |
| `frontend/src/services/api.ts` | Modify | Import `apiClient` + `API_ENDPOINTS`; drop axios/baseURL; re-point paths; post() timeout map |
| `frontend/src/config/constants.ts` | Modify | Fix TRAIN; drop PARLEYS/TOP_ML_PICKS; add timeout/limit constants |
| `frontend/src/infrastructure/api/client.ts` | Modify | Default timeout from `APP_CONFIG.API_DEFAULT_TIMEOUT` |
| `frontend/src/infrastructure/api/live.ts` | Modify | `APP_CONFIG.LIVE_API_TIMEOUT` (30s) |
| `frontend/src/infrastructure/api/predictions.ts` | Modify | Limit default 30; suggested-picks 90s |
| `frontend/src/hooks/useLiveMatches.ts` | Modify | Remove inline ESPN; add `toLiveMatch` |
| `useBotStore.ts`, `useLiveStore.ts`, `usePredictionStore.ts` | Modify | Use `isNetworkError` |
| `frontend/src/infrastructure/api/parleys.ts`, `analytics.ts` | Delete | Zero consumers (grep-verified); parley UI store untouched |
| 4 new colocated tests (below) | Create | Coverage per spec |

## Interfaces / Contracts

```ts
// utils/apiErrors.ts
export function isNetworkError(error: unknown): boolean;

// hooks/useLiveMatches.ts — exported for unit tests
export function toLiveMatch(espn: LiveMatchPrediction): LiveMatch;
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit (existing) | Store tests mock `services/api` (`{ api: { get, post } }`); LiveMatchesList mocks named + default | Frozen surface keeps these green — regression net |
| Unit (new) | `infrastructure/api/client.test.ts` — baseURL, default timeout, headers | Inspect instance defaults |
| Unit (new) | `config/constants.test.ts` — TRAIN path, no PARLEYS/TOP_ML_PICKS, timeout/limit values | Direct assertions |
| Unit (new) | `hooks/useLiveMatches.test.ts` — adapter shape: `"45:00"` and `"45'"`, HT/LIVE, flat fields | `toLiveMatch` unit tests |
| Unit (new) | `services/api.surface.test.ts` — 14 exports; no `/api/v1` literal, no `axios.create`, no parleys/analytics refs in source | Surface + source-scan assertions |

Locations: colocated `*.test.ts` beside source (existing convention). Vitest is the runner.

## Migration / Rollout

No data migration. Per-commit slices: client swap → endpoint re-pointing → dead-code deletion → ESPN dedupe → store error util. Each slice is independently revertible (one-line reverts for timeout/limit values).

## Open Questions

- [ ] None blocking. (D5 `minute` parse tolerates both `"45'"` and `"45:00"` ESPN formats.)
