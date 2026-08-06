# Verify Report: unify-frontend-api-clients

## Verification Report

**Change**: unify-frontend-api-clients
**Version**: delta spec api-client (v1)
**Mode**: Standard (Strict TDD not active — no strict_tdd flag/cache found)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 17 |
| Tasks complete | 17 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed
```text
npm run build  →  tsc -b && vite build  →  exit 0 (dist/ emitted, compression ok)
npx tsc --noEmit  →  exit 0
```

**Tests**: ✅ 38 passed / 0 failed / 0 skipped
```text
npm test -- --run  →  vitest v4.0.16 — Test Files 12 passed (12), Tests 38 passed (38)
```

**Lint**: ✅ clean — `npm run lint` (eslint --max-warnings 0) exit 0, zero warnings

**Coverage**: ➖ Not available — no coverage config/thresholds in `frontend/vite.config.ts` `test` block

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| REQ-01 Single canonical axios instance | One axios factory | `api.surface.test.ts > does not create its own axios instance` + `client.test.ts` + grep sweep | ✅ COMPLIANT |
| REQ-01 | Consumers unaffected | `tsc --noEmit` exit 0; build pass; 38/38 store/component tests | ✅ COMPLIANT |
| REQ-02 API_ENDPOINTS single source | No hardcoded paths | `api.surface.test.ts > contains zero hardcoded /api/v1 literals` | ✅ COMPLIANT |
| REQ-02 | Train path corrected | `constants.test.ts > routes training triggers to run-now` (runtime); predictionsApi.train → `API_ENDPOINTS.TRAIN` + `TRAINING_TIMEOUT`, `post()` → `POST_TIMEOUTS` map + `API_V1_PREFIX` (source-verified, constant-driven) | ✅ COMPLIANT |
| REQ-03 Dead modules removed | Zero dangling references | `api.surface.test.ts > no parleys/analytics refs` + `rg` sweep (0 refs) + tsc/lint | ✅ COMPLIANT |
| REQ-04 ESPN single source | No inline ESPN calls | source scan: 0 `site.api.espn.com`/`fetch(` in hook (was 4); 369→137 lines | ✅ COMPLIANT |
| REQ-04 | Flat shape preserved | `useLiveMatches.test.ts` (8 tests: `"45:00"`, `"45'"`, HT/LIVE, flat league, numeric fields, prediction carry) | ✅ COMPLIANT |
| REQ-05 Normalized timeout/limit | Timeouts aligned | `constants.test.ts > LIVE_API_TIMEOUT 30000`; both `live.ts` and `services/api.ts` reference the constant | ✅ COMPLIANT |
| REQ-05 | Limit aligned | `constants.test.ts > DEFAULT_PREDICTIONS_LIMIT 30`; both `getPredictions` default params reference the constant | ✅ COMPLIANT |
| REQ-06 Shared network error | Uniform classification | (no covering test found) | ⚠️ UNTESTED |
| REQ-07 Regression coverage | Client config verified | `client.test.ts` (baseURL, APP_CONFIG timeout, Content-Type header) | ✅ COMPLIANT |
| REQ-07 | Regression coverage | 38/38 tests including 4 new files (surface, constants, client, adapter) | ✅ COMPLIANT |

**Compliance summary**: 11/12 scenarios compliant (1 untested)

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| REQ-01 Canonical client + frozen export surface | ✅ Implemented | `client.ts:11` sole `axios.create`; `services/api.ts:9` imports `apiClient`; 14 exports (12 methods + `post`/`get`) + `default`; baseURL/timeout/Content-Type/interceptor preserved |
| REQ-02 API_ENDPOINTS single source + TRAIN fix | ✅ Implemented | zero `/api/v1` literals in `services/api.ts`; `PARLEYS`/`TOP_ML_PICKS` removed (`constants.ts`); `TRAIN = "/api/v1/train/run-now"` (`constants.ts:33`); `post()` constant map + `API_V1_PREFIX` |
| REQ-03 Dead modules removed | ✅ Implemented | `parleys.ts`/`analytics.ts` deleted; zero refs; `useParleyStore.ts` untouched (imports zustand + entities only) |
| REQ-04 ESPN single source + flat adapter | ✅ Implemented | hook imports `fetchESPNLiveMatches` (`espn.ts:90`); pure exported `toLiveMatch` (`useLiveMatches.ts:43`); minute parse `"45'"`/`"45:00"` per D5; HT→HT else LIVE |
| REQ-05 Normalized timeouts/limits | ✅ Implemented | LIVE 30s both paths (`services/api.ts:112`, `live.ts:32`), picks 90s, train 5min, limit 30 both paths, instance default 60s; all centralized in `APP_CONFIG` with rationale; bare `API_TIMEOUT` (10s) fully removed |
| REQ-06 Shared isNetworkError | ✅ Implemented | `utils/apiErrors.ts:6-14` classifies "Network Error"/`ERR_NETWORK`/`ECONNABORTED`; all 3 stores use it (5 inline blocks replaced); `ECONNABORTED` now network error in 2 prediction blocks (intended per D6) |
| REQ-07 Test coverage | ✅ Implemented | 4 new colocated test files present and green |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1 Canonical client export shape | ✅ Yes | singleton `apiClient` remains the export; duplicate `createApiClient`/`API_BASE_URL` removed from `services/api.ts` |
| D2 Per-method timeouts | ✅ Yes | instance default 60s via `APP_CONFIG.API_DEFAULT_TIMEOUT`; live/picks/train pass per-request `{ timeout }` |
| D3 Endpoint constants | ✅ Yes | `POST_TIMEOUTS = { "/train/run-now": APP_CONFIG.TRAINING_TIMEOUT }`; grep confirms no caller passes bare `/train` |
| D4 Timeout/limit policy | ✅ Yes | all constants centralized with documented rationale; `API_TIMEOUT` replaced by `LIVE_API_TIMEOUT` |
| D5 ESPN adapter | ✅ Yes | `toLiveMatch` exported pure adapter; minute parse, HT/LIVE, flat fields exactly per D5 mapping |
| D6 Shared network error | ✅ Yes | `isNetworkError` in 3 stores; 5 inline blocks replaced; ECONNABORTED reclassification intended |

### Issues Found
**CRITICAL**: None

**WARNING**:
1. REQ-06 "Uniform classification" scenario has no runtime covering test — no `utils/apiErrors.test.ts` and no store test feeds `ECONNABORTED`/`ERR_NETWORK`/`"Network Error"`. The implementation is statically verified correct (`utils/apiErrors.ts:6-14`; all 3 stores wired) and store regression tests pass, but the scenario's classification behavior lacks runtime proof. Note: REQ-07's mandated test list does not include apiErrors, so this is a spec/test-plan gap rather than an implementation defect. A 3-assertion colocated unit test resolves it. (If the orchestrator treats scenario-level coverage as strictly mandatory, per the sdd-verify gate this escalates to CRITICAL-UNTESTED and blocks archive until the test lands.)

**SUGGESTION**:
1. `POST_TIMEOUTS` key `/train/run-now` is currently dormant — no caller passes it today (`predictionsApi.train` is the active train path via `API_ENDPOINTS.TRAIN`). Either add a surface test asserting the wiring or drop the map.
2. Vitest has no coverage thresholds configured (`vite.config.ts` test block) — consider adding coverage for the new client/config/adapter surface.
3. Untracked `docs/migration-npm-to-bun.md` (npm→bun migration plan) at repo root is unrelated to this change — ensure it is not swept into the PR.

### Verdict
PASS
(All 17 tasks complete; 38/38 tests, lint, build, tsc clean; 11/12 spec scenarios runtime-compliant (1 coverage gap reported as WARNING); zero backend files touched; design D1–D6 followed.)
