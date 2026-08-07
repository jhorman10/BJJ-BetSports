# Tasks: Frontend X-API-Key Auth for Admin Training Endpoints

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~40–70 (additions + deletions) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending (not applicable — single PR) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full change: interceptor + env typing + tests + dead-code + prod parity | PR 1 | Base `main`. Commit order: vite-env → client.ts → tests → env files → render.yaml → dead-code |

## Phase 1: Foundation (env typing + configuration)

- [x] 1.1 `frontend/src/vite-env.d.ts`: add `readonly VITE_ADMIN_API_KEY?: string;` to `ImportMetaEnv`. Verify: `tsc` passes with and without var set
- [x] 1.2 `frontend/.env`: add empty `VITE_ADMIN_API_KEY=` entry (gitignored — confirmed). Verify: `git check-ignore frontend/.env` still true
- [x] 1.3 Create `frontend/.env.example`: comment `# Optional: admin key for X-API-Key protected training endpoints. Omit for keyless/local-bypass builds.` + empty `VITE_ADMIN_API_KEY=`. Verify: file exists, no placeholder value
- [x] 1.4 `render.yaml`: frontend service `envVars` (next to `VITE_API_URL`, line ~44) — add `- key: VITE_ADMIN_API_KEY` with `sync: false`. Verify: yaml parses; var documented for prod parity

## Phase 2: Core Implementation (request interceptor)

- [x] 2.1 `frontend/src/infrastructure/api/client.ts` `createApiClient()`: register request interceptor before response interceptor — read `import.meta.env.VITE_ADMIN_API_KEY` at request time, `.trim()`, set `config.headers["X-API-Key"]` only when non-empty; zero logging. Verify: Phase 3 scenarios
- [x] 2.2 Preserve baseURL, `APP_CONFIG.API_DEFAULT_TIMEOUT`, `Content-Type`, response interceptor unchanged. Verify: existing 3 client.test.ts assertions still pass unedited

## Phase 3: Testing (spec scenarios)

- [x] 3.1 `frontend/src/infrastructure/api/client.test.ts`: `vi.stubEnv("VITE_ADMIN_API_KEY", "test-key")` → invoke request handler with `{ headers: {} }` → assert `X-API-Key === "test-key"`; `vi.unstubAllEnvs()`
- [x] 3.2 Same file: env unset/`""` → assert no `X-API-Key` in headers (keyless build unaffected)
- [x] 3.3 Same file: `vi.stubEnv("VITE_ADMIN_API_KEY", "   ")` → assert no header (trim + skip-empty path). Verify: `npm test` green

## Phase 4: Cleanup (dead training code)

- [x] 4.1 `frontend/src/infrastructure/api/predictions.ts`: delete `train()` (lines ~77–87, zero refs confirmed). Verify: grep `predictionsApi.train` → zero matches
- [x] 4.2 `frontend/src/services/api.ts`: delete `POST_TIMEOUTS` const (lines ~25–31) + lookup/branch in `post()` (lines ~174–178); keep `API_ENDPOINTS.TRAIN` + `APP_CONFIG.TRAINING_TIMEOUT`. Verify: grep `POST_TIMEOUTS` → zero matches; `tsc` passes

## Phase 5: Verification

- [x] 5.1 `npm test` (frontend Vitest) — full suite green (constants.test.ts regression net)
- [x] 5.2 `npm run lint` + `npm run build` (tsc -b && vite build) pass
- [x] 5.3 Grep sweep: no `X-API-Key` logging anywhere; `.env` gitignored; `.env.example` value empty; `axios.create` still only in client.ts
