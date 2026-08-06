# Delta for api-client

## ADDED Requirements

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

### Requirement: Dead training code removal

`predictionsApi.train()` (predictions.ts) and the `POST_TIMEOUTS["/train/run-now"]` entry (services/api.ts) MUST be deleted after verifying zero consumers. After removal, no module MAY reference `predictionsApi.train`, and type-check/lint MUST pass. `API_ENDPOINTS.TRAIN` and `APP_CONFIG.TRAINING_TIMEOUT` MUST remain.

#### Scenario: Zero dangling references

- GIVEN the change applied
- WHEN the codebase is searched for `predictionsApi.train` and the `/train/run-now` timeout entry
- THEN only git history matches
- AND type-check and lint pass

### Requirement: Production parity configuration

`render.yaml` frontend service `envVars` MUST declare `VITE_ADMIN_API_KEY` with `sync: false`. `frontend/.env.example` SHOULD document it; `frontend/.env` MUST remain gitignored.

#### Scenario: Deployment parity

- GIVEN render.yaml frontend envVars
- WHEN inspected
- THEN `VITE_ADMIN_API_KEY` is declared with `sync: false`
- AND `.env.example` documents it while `.env` stays gitignored

## MODIFIED Requirements

### Requirement: Single canonical axios instance

The frontend MUST create exactly one configured axios instance. `infrastructure/api/client.ts` MUST be the sole module calling `axios.create`; `services/api.ts` MUST reuse the exported instance. The shared instance MUST preserve baseURL (`VITE_API_URL` or `http://localhost:8000`), `Content-Type: application/json`, and the existing response interceptor (no global 404 logging). The instance MUST register a request interceptor that injects `X-API-Key` from `VITE_ADMIN_API_KEY` when set and skips injection when absent. All methods exported by `services/api.ts` (12 endpoint methods plus generic `post` and `get`) MUST keep their exact export names and return shapes, so consumers compile unchanged.
(Previously: instance had no auth request interceptor.)

#### Scenario: One axios factory

- GIVEN the refactored API layer
- WHEN the codebase is scanned for `axios.create`
- THEN only `infrastructure/api/client.ts` contains it
- AND `services/api.ts` uses the exported instance

#### Scenario: Consumers unaffected

- GIVEN existing `api` consumers
- WHEN the refactor lands
- THEN they compile unchanged

#### Scenario: Auth header injected when configured

- GIVEN the canonical client with `VITE_ADMIN_API_KEY` set
- WHEN any request is issued
- THEN the `X-API-Key` header is present
- AND baseURL, timeout, content-type defaults are unchanged

### Requirement: API_ENDPOINTS single source of paths

`API_ENDPOINTS` MUST be the only source of endpoint paths; `services/api.ts` MUST contain zero hardcoded `/api/v1` strings. Dead entries `PARLEYS`, `TOP_ML_PICKS` MUST be removed. `TRAIN` MUST resolve to `/api/v1/train/run-now`; the `POST_TIMEOUTS["/train/run-now"]` entry MUST be removed, so the `/train` special-case in `post()` no longer exists.
(Previously: special-case to be removed or re-pointed; `predictionsApi.train` was a live trigger.)

#### Scenario: No hardcoded paths

- GIVEN `services/api.ts` after refactor
- WHEN searched for `/api/v1` literals
- THEN none exist outside `API_ENDPOINTS`

#### Scenario: Train path corrected

- GIVEN the change applied
- WHEN `API_ENDPOINTS.TRAIN` is resolved
- THEN it equals `/api/v1/train/run-now`
- AND `predictionsApi.train` is gone
- AND no `/train/run-now` timeout entry remains
