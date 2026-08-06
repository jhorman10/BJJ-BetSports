# Tasks: Unify Frontend API Clients

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~600–750 (additions + deletions) |
| 400-line budget risk | High — exceeds 400, within pre-approved D2 800-line budget |
| Chained PRs recommended | No |
| Suggested split | Single PR (work-unit commits inside) |
| Delivery strategy | single-pr |
| Chain strategy | pending (not applicable — single PR) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Full unification: transport, endpoints, dead code, ESPN, stores, tests | PR 1 | Base `main`. Commit order: constants → client → services → dead-code → ESPN → stores → tests |

## Phase 1: Foundation (constants + shared utils)

- [x] 1.1 `config/constants.ts`: fix `TRAIN` → `/api/v1/train/run-now`; delete `PARLEYS`, `TOP_ML_PICKS`; add `LIVE_API_TIMEOUT=30000`, `SUGGESTED_PICKS_TIMEOUT=90000`, `DEFAULT_PREDICTIONS_LIMIT=30`, `API_DEFAULT_TIMEOUT=60000`; replace `API_TIMEOUT`. Verify: new `config/constants.test.ts`
- [x] 1.2 Create `utils/apiErrors.ts`: `isNetworkError(error: unknown): boolean` — message `"Network Error"` || code `ERR_NETWORK` || `ECONNABORTED`. Verify: store tests (Phase 3) use it
- [x] 1.3 `infrastructure/api/client.ts`: default timeout from `APP_CONFIG.API_DEFAULT_TIMEOUT`; keep sole `axios.create`. Verify: new `client.test.ts`

## Phase 2: Core (canonical transport + endpoints)

- [x] 2.1 `services/api.ts`: delete duplicate `createApiClient`/`API_BASE_URL` (lines 22–49); import `apiClient` from `infrastructure/api/client.ts` + `API_ENDPOINTS`; re-point all 12 paths; keep 14-member export surface (12 methods + `post`/`get` + default) so consumers compile unchanged. Verify: new `api.surface.test.ts`; existing store/component tests
- [x] 2.2 `services/api.ts` `post()`: replace `/train` string special-case with constant map `{ "/train/run-now": APP_CONFIG.TRAINING_TIMEOUT }`. Verify: spec train scenario targets `/api/v1/train/run-now`
- [x] 2.3 `infrastructure/api/live.ts`: timeout → `APP_CONFIG.LIVE_API_TIMEOUT` (30s). Verify: constants test + 30s on both paths
- [x] 2.4 `infrastructure/api/predictions.ts`: default limit → `DEFAULT_PREDICTIONS_LIMIT` (30); suggested-picks timeout → `SUGGESTED_PICKS_TIMEOUT` (90s). Verify: constants test
- [x] 2.5 Delete `infrastructure/api/parleys.ts` + `analytics.ts` after grep confirms zero refs (`parleysApi`, `analyticsApi`, `PARLEYS`, `TOP_ML_PICKS`); `useParleyStore.ts` untouched. Verify: surface-test absence scan + `tsc`

## Phase 3: Integration (ESPN dedupe + stores)

- [x] 3.1 `hooks/useLiveMatches.ts`: delete inline ESPN fetch/batch/`extractStat`/cache; import `fetchESPNLiveMatches`; add exported pure `toLiveMatch(espn: LiveMatchPrediction): LiveMatch` (minute parse `"45'"`/`"45:00"`, HT→HT else LIVE, flat fields per D5). Verify: new adapter unit tests
- [x] 3.2 `useBotStore.ts`, `useLiveStore.ts`, `usePredictionStore.ts`: replace 5 inline network checks with `isNetworkError`; two prediction blocks now classify `ECONNABORTED` as network error (intended, per D6). Verify: existing store tests pass

## Phase 4: Testing (new coverage per spec)

- [x] 4.1 Create `infrastructure/api/client.test.ts`: baseURL, default timeout, Content-Type header
- [x] 4.2 Create `config/constants.test.ts`: TRAIN path, PARLEYS/TOP_ML_PICKS absent, timeout/limit values
- [x] 4.3 Create `hooks/useLiveMatches.test.ts`: `toLiveMatch` shape — `"45'"`/`"45:00"`, HT/LIVE, numeric score/minute/corners/cards
- [x] 4.4 Create `services/api.surface.test.ts`: 14 exports; zero `/api/v1` literal; zero `axios.create`; zero parleys/analytics refs in source

## Phase 5: Verification

- [x] 5.1 `npm test` (frontend Vitest) — full suite green; existing store/component tests are the regression net
- [x] 5.2 `npm run lint` + `npm run build` (tsc -b && vite build) pass
- [x] 5.3 Grep sweep: `axios.create` only in `client.ts`; no `site.api.espn.com`/`fetch(` ESPN call in hook; zero dead-module refs
