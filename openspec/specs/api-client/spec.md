# api-client Specification

## Purpose

Consolidates frontend HTTP transport onto a single canonical path: one configured axios instance, one source of endpoint paths (`API_ENDPOINTS`), a normalized timeout/limit policy centralized in `APP_CONFIG`, shared network-error classification, honest admin auth via `X-API-Key`, and regression coverage. Eliminates the drifting parallel API stacks in `services/api.ts` (legacy) and `infrastructure/api/*` (canonical).

## Requirements

### Requirement: Single canonical axios instance

The frontend MUST create exactly one configured axios instance. `infrastructure/api/client.ts` MUST be the sole module calling `axios.create`; `services/api.ts` MUST reuse the instance it exports. The shared instance MUST preserve baseURL (`VITE_API_URL` or `http://localhost:8000`), `Content-Type: application/json`, and the existing response interceptor (no global 404 logging). The instance MUST register a request interceptor that injects `X-API-Key` from `VITE_ADMIN_API_KEY` when set and skips injection when absent. All methods exported by `services/api.ts` (12 endpoint methods plus generic `post` and `get`) MUST keep their exact export names and return shapes, so consumers compile unchanged.

#### Scenario: One axios factory

- GIVEN the refactored API layer
- WHEN the codebase is scanned for `axios.create`
- THEN only `infrastructure/api/client.ts` contains it
- AND `services/api.ts` uses the exported instance

#### Scenario: Consumers unaffected

- GIVEN existing `api` consumers
- WHEN the refactor lands
- THEN they compile unchanged

### Requirement: API_ENDPOINTS single source of paths

`API_ENDPOINTS` MUST be the only source of endpoint paths; `services/api.ts` MUST contain zero hardcoded `/api/v1` strings. Dead entries `PARLEYS`, `TOP_ML_PICKS` MUST be removed. `TRAIN` MUST resolve to `/api/v1/train/run-now`; the `/train` special-case in `post()` MUST be removed (`POST_TIMEOUTS["/train/run-now"]` deleted), so no per-endpoint timeout map remains.

#### Scenario: No hardcoded paths

- GIVEN `services/api.ts` after refactor
- WHEN searched for `/api/v1` literals
- THEN none exist outside `API_ENDPOINTS`

#### Scenario: Train path corrected

- GIVEN a training trigger via `api.post`
- WHEN the request is issued
- THEN it targets `/api/v1/train/run-now`
- AND the 5-minute timeout comes only from the centralized constant
- AND `predictionsApi.train` is gone

### Requirement: Dead modules removed

`infrastructure/api/parleys.ts` and `infrastructure/api/analytics.ts` MUST be deleted. Zero consumers MUST be verified first; afterward, no module MAY reference `parleysApi`, `analyticsApi`, `TOP_ML_PICKS`, or `PARLEYS`. Local-only parley UI state (`useParleyStore`) MUST remain unchanged.

#### Scenario: Zero dangling references

- GIVEN the change applied
- WHEN the codebase is searched for `parleysApi`, `analyticsApi`, `TOP_ML_PICKS`
- THEN only git history matches, and type-check/lint pass

### Requirement: ESPN single source

`useLiveMatches.ts` MUST use `fetchESPNLiveMatches` from `infrastructure/external/espn.ts`; its inline ESPN fetch, batching, and stat-extraction MUST be removed. The hook MUST preserve the flat `LiveMatch` shape via a documented adapter from `LiveMatchPrediction[]`, or by matching return types deliberately.

#### Scenario: No inline ESPN calls

- GIVEN `useLiveMatches.ts` after refactor
- WHEN inspected for `site.api.espn.com` or `fetch(`
- THEN no ESPN URL or fetch call remains in the hook

#### Scenario: Flat shape preserved

- GIVEN the ESPN fallback returns `LiveMatchPrediction[]`
- WHEN the hook resolves
- THEN every item conforms to `LiveMatch` (flat teams, numeric score/minute/corners/cards)
- AND the adapter mapping is unit-tested

### Requirement: Normalized timeout and limit policy

Live-with-predictions requests MUST time out at 30s on both the `services/api.ts` and `infrastructure/api/live.ts` paths. Predictions default limit MUST be 30 on both. Suggested-picks timeout MUST remain 90s; training timeout MUST remain 5 min. Values MUST be centralized in `config/constants.ts` (`APP_CONFIG`) with rationale documented.

#### Scenario: Timeouts aligned

- GIVEN a live-with-predictions request from either path
- WHEN it exceeds 30s
- THEN both paths abort with a timeout error

#### Scenario: Limit aligned

- GIVEN `getPredictions(leagueId)` without an explicit limit
- WHEN the request is issued
- THEN the `limit` query param equals 30

### Requirement: Shared network error classification

A shared `isNetworkError` helper MUST live in `utils/apiErrors.ts`, classifying "Network Error", `ERR_NETWORK`, and `ECONNABORTED`. `useBotStore`, `useLiveStore`, and `usePredictionStore` MUST use it instead of inline checks.

#### Scenario: Uniform classification

- GIVEN an axios error with `code: "ECONNABORTED"` in any store
- WHEN the store handles it
- THEN `isNetworkError` returns true and backend availability updates consistently

### Requirement: Regression coverage

Existing store and component tests MUST pass. New tests MUST cover client factory config (baseURL, timeout, headers), absence of dead-module imports, endpoint consistency with `API_ENDPOINTS`, and the ESPN-to-LiveMatch adapter.

#### Scenario: Client config verified

- GIVEN the unified client factory
- WHEN a test inspects the instance
- THEN baseURL, timeout, and headers match canonical values

### Requirement: X-API-Key header injection (conditional)

The frontend MUST attach an `X-API-Key` header equal to `VITE_ADMIN_API_KEY` on every request when that variable is set at build time. When absent, it MUST NOT send the header, MUST NOT crash, and MUST render normally — keyless builds and the local dev bypass stay unchanged. The header value MUST NOT appear in logs.

#### Scenario: Header attached when configured

- GIVEN `VITE_ADMIN_API_KEY` is set at build time
- WHEN any request is issued (e.g. training capabilities, jobs, results/latest)
- THEN the request carries `X-API-Key` equal to the variable value

#### Scenario: Keyless build unaffected

- GIVEN no `VITE_ADMIN_API_KEY`
- WHEN the app loads and issues requests
- THEN no `X-API-Key` header is sent
- AND requests complete and the UI renders

#### Scenario: Key never logged

- GIVEN a configured build
- WHEN requests log headers or errors
- THEN the `X-API-Key` value never appears in logs

### Requirement: Admin API key environment typing

`frontend/src/vite-env.d.ts` MUST declare `VITE_ADMIN_API_KEY` as an optional readonly string on `ImportMetaEnv`. Type-checking MUST pass with or without the variable set.

#### Scenario: Typed and optional

- GIVEN `VITE_ADMIN_API_KEY?: string` in `ImportMetaEnv`
- WHEN `tsc` runs with and without the variable set
- THEN both pass and `import.meta.env.VITE_ADMIN_API_KEY` is `string | undefined`

### Requirement: Production parity configuration

`render.yaml` frontend service `envVars` MUST declare `VITE_ADMIN_API_KEY` with `sync: false`. `frontend/.env.example` SHOULD document it; `frontend/.env` MUST remain gitignored.

#### Scenario: Deployment parity

- GIVEN render.yaml frontend envVars
- WHEN inspected
- THEN `VITE_ADMIN_API_KEY` is declared with `sync: false`
- AND `.env.example` documents it while `.env` stays gitignored
