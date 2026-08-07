# Design: Frontend X-API-Key Auth for Admin Training Endpoints

## Technical Approach

One axios request interceptor in `createApiClient()` (client.ts) that reads `import.meta.env.VITE_ADMIN_API_KEY` at **request time**, trims it, and attaches `X-API-Key` when non-empty; passes through unchanged otherwise. Covers all 7 admin endpoints plus future ones with zero changes to consumers. Env typed in `vite-env.d.ts`, documented in `.env.example` + render.yaml, and two confirmed-dead training paths deleted. Matches delta specs: api-client (header injection, env typing, dead code, prod parity).

## Architecture Decisions

| # | Decision | Options / Tradeoff | Choice |
|---|----------|--------------------|--------|
| D1 | Interceptor placement | In `createApiClient()` after `axios.create` vs. wrapper module | In-factory. Request/response queues are independent in axios, so order is cosmetic; register request first for top-down read. Single factory stays the only `axios.create` (spec: one factory). |
| D2 | When to read env | At module load (capture) vs. at request time (read inside handler) | Request-time read. Singleton `apiClient` freezes a load-time capture, blocking `vi.stubEnv` in tests; request-time read makes the 3 header scenarios testable against the exported singleton. Same runtime cost. |
| D3 | Defensive behavior | Send raw vs. trim + skip empty | Trim + skip empty. Prevents `" "` placeholder from `.env.example` being sent; keyless build behavior identical to today (spec: absent → no header, no crash). |
| D4 | Dead-code scope | Remove `POST_TIMEOUTS` lookup entirely vs. re-point it | Remove. Live training trigger is `api.post("/training/jobs", …)` (useBotStore:178, useTrainingJobsStore:144) — never in `POST_TIMEOUTS`, so no live-path change. `API_ENDPOINTS.TRAIN` and `APP_CONFIG.TRAINING_TIMEOUT` stay (constants.test.ts:6,25). |
| D5 | Test mechanism | Mock adapter vs. invoke interceptor handler directly | Invoke handler directly with a minimal config. No new deps (YAGNI); tests black-box the interceptor via `vi.stubEnv`. |

## Security Design

- **Protected**: 7 frontend calls to backend admin endpoints (backend `security.py:90`, 11 endpoints total) now carry the header in prod.
- **Not protected**: key is build-time inlined into the static bundle — extractable by anyone. Accepted (proposal §Security Tradeoff): admin-only training ops, personal project, rotation policy. Not authz; documented as such.
- **No-log guarantee**: interceptor contains zero logging; the existing response interceptor only re-throws. Key can never appear in app logs.
- **Leak vectors**: bundle (accepted), browser devtools (inherent to client-side keys), git (prevented — `frontend/.env` confirmed gitignored via `git check-ignore`; `.env.example` ships empty), Render dashboard (operator-held, `sync: false`).

## Data Flow

```
VITE_ADMIN_API_KEY (build env) ──> import.meta.env ──> request interceptor (trim; skip if empty)
                                                          │  present?  ── yes ──> config.headers["X-API-Key"] = key
                                                          └  absent/blank ── no header, request unchanged
api.post/get ──> apiClient ──> [req: X-API-Key] ──> backend security.py (X-API-Key check on admin routes)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/infrastructure/api/client.ts` | Modify | Request interceptor (~6 lines) registered before response interceptor |
| `frontend/src/vite-env.d.ts` | Modify | `readonly VITE_ADMIN_API_KEY?: string;` on `ImportMetaEnv` |
| `frontend/.env` | Modify | Add `VITE_ADMIN_API_KEY=` (gitignored — verified) |
| `frontend/.env.example` | Create | Document optional var; does not exist today |
| `frontend/src/infrastructure/api/client.test.ts` | Modify | Header present/absent/blank scenarios |
| `frontend/src/infrastructure/api/predictions.ts` | Modify | Delete `train()` (lines 77–87, zero refs) |
| `frontend/src/services/api.ts` | Modify | Delete `POST_TIMEOUTS` (25–31) + lookup/branch (174–178); `post<T>` signature unchanged |
| `render.yaml` | Modify | Frontend envVars: `VITE_ADMIN_API_KEY`, `sync: false` |

## Interfaces / Contracts

```ts
// client.ts — interceptor (exact shape)
client.interceptors.request.use((config) => {
  const apiKey = import.meta.env.VITE_ADMIN_API_KEY?.trim();
  if (apiKey) {
    config.headers = config.headers ?? {};
    config.headers["X-API-Key"] = apiKey;
  }
  return config;
});

// vite-env.d.ts
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_ADMIN_API_KEY?: string; // optional → string | undefined
}

// render.yaml frontend envVars
- key: VITE_ADMIN_API_KEY
  sync: false
```

`.env.example`: `# Optional: admin key for X-API-Key protected training endpoints. Omit for keyless/local-bypass builds.\nVITE_ADMIN_API_KEY=` — no placeholder value.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit | Header injected when env set | `vi.stubEnv("VITE_ADMIN_API_KEY", "test-key")` → invoke request handler with `{ headers: {} }` → assert `config.headers["X-API-Key"] === "test-key"`; `vi.unstubAllEnvs()` |
| Unit | Header absent when unset | Stub env to `""` / unset → handler → assert no `X-API-Key` in headers |
| Unit | Header absent when blank/whitespace | `vi.stubEnv("VITE_ADMIN_API_KEY", "   ")` → assert absent (trim path) |
| Unit | Existing defaults preserved | Keep current 3 tests (baseURL, timeout, content-type) — no changes |

## Migration / Rollout

No data migration. Feature-flag = presence of `VITE_ADMIN_API_KEY` at build. Rollout: set var in Render frontend env (build-time inlined, `sync: false`) → redeploy. Rollback: revert single commit, redeploy; backend untouched. Note: `APP_CONFIG.TRAINING_TIMEOUT` becomes test-referenced only after deletion — kept by policy (constants.test.ts:25).

## Open Questions

- None blocking. Non-blocking from proposal: distinct "training unavailable" banner (product polish), quarterly key rotation cadence (ops).
