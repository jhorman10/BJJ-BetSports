# Proposal: Frontend X-API-Key Auth for Admin Training Endpoints

## Intent

Backend protects 11 admin endpoints with `X-API-Key` (security.py:90). Frontend calls 7 of them but never sends the header. In prod (`API_ONLY_MODE=true`, no bypass), all 7 return 403/503 — TrainingControlPanel and BotDashboard training are silently dead in the deployed app. Goal: honest auth — the deployed UI either works (key configured) or fails explicitly, never silently degrades.

## Problem

| Gap | Detail |
|-----|--------|
| 7 calls unauthenticated | capabilities, models, createJob, jobs list/detail/events (useTrainingJobsStore), results/latest + jobs (useBotStore), results/latest (usePredictionStore.checkTrainingStatus) |
| Bypass dead in prod | LOCAL_DEV_BYPASS requires `API_ONLY_MODE=false` + loopback; render.yaml sets `true` |
| Key not wired | `ADMIN_API_KEY` absent from render.yaml backend; frontend has no mechanism to send it |
| CORS OK | `allow_headers=["*"]` (main.py:48) — not a blocker |
| Dead code | `predictionsApi.train()` (predictions.ts:80, zero callers), `POST_TIMEOUTS["/train/run-now"]` (services/api.ts:29-30) |

## Scope

### In Scope
- Request interceptor in `frontend/src/infrastructure/api/client.ts` (~10 lines): inject `X-API-Key` when `VITE_ADMIN_API_KEY` set; skip when absent (local bypass unaffected, keyless prod still renders).
- `frontend/src/vite-env.d.ts`: type `VITE_ADMIN_API_KEY`.
- `frontend/.env` (gitignored) + optional `frontend/.env.example`.
- `client.test.ts`: header presence/absence assertion.
- `render.yaml` frontend `envVars`: `VITE_ADMIN_API_KEY` (sync: false).
- Delete dead `predictionsApi.train()` + `POST_TIMEOUTS["/train/run-now"]` (confirmed unreferenced).

### Out of Scope
- Switching `checkTrainingStatus` to public `/api/v1/train/status|cached` (payload shapes differ; needs backend + type change).
- Removing `LOCAL_DEV_BYPASS_ENABLED`.
- Admin key prompt UI.
- Backend proxy.
- Hiding training UI in prod behind a flag.
- Backend untouched.

## Capabilities

> Contract for sdd-spec. Research: `openspec/specs/api-client/spec.md` exists.

### New Capabilities
None — fits within existing `api-client` capability.

### Modified Capabilities
- `api-client`: add requirement — canonical client injects `X-API-Key` on all requests when `VITE_ADMIN_API_KEY` is set; never injects when absent. Remove `predictionsApi.train` + its timeout entry from scope.

## Approach

**Option 1** (approved): one axios request interceptor in `createApiClient()`. Reads `import.meta.env.VITE_ADMIN_API_KEY`; if set, adds `X-API-Key` header to every request (covers all 7 endpoints + future ones); if unset, passes through unchanged. Header injected at request time from build-time env; key lands in static bundle.

## Security Tradeoff (Accepted)

Key embedded in static JS bundle is extractable by anyone. Accepted: protected surface is admin-only training ops on a personal project. Mitigations: documented key rotation policy; optional var (absent → header skipped → local bypass + keyless rendering preserved). Not a substitute for real authz — documented as such.

## Scenario

Operator sets `VITE_ADMIN_API_KEY` at build → deployed UI shows training capabilities, jobs, events, results/latest. Without it → UI renders; training panel surfaces honest 403/503 error state (no silent hang).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/infrastructure/api/client.ts` | Modified | Add request interceptor |
| `frontend/src/vite-env.d.ts` | Modified | Env type |
| `frontend/.env` + `.env.example` | New | Key var (gitignored) |
| `frontend/src/infrastructure/api/client.test.ts` | Modified | Header assertion |
| `frontend/src/infrastructure/api/predictions.ts` | Modified | Remove `train()` |
| `frontend/src/services/api.ts` | Modified | Remove `POST_TIMEOUTS` entry |
| `render.yaml` | Modified | Frontend envVars |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Key extracted from bundle | High | Accepted; rotation policy; admin-only surface |
| Header sent to public endpoints | Low | Backend ignores it there; harmless |
| Keyless prod still 403s | Med | Honest error state + documented setup |

## Rollback Plan

Revert single commit: remove interceptor lines, env type, `.env`/`.env.example`, test assertion, render.yaml var; restore dead code only if a consumer appears (verified none today). Redeploy frontend; backend untouched.

## Dependencies

- `ADMIN_API_KEY` set on backend service in render.yaml (operator action, sync: false).

## Success Criteria

- [ ] Interceptor adds `X-API-Key` when var set; omits when unset (unit-tested)
- [ ] `predictionsApi.train` + `POST_TIMEOUTS["/train/run-now"]` gone; type-check/lint pass
- [ ] Local dev with bypass still works (no header sent)
- [ ] Deployed UI with key: training ops load; without key: honest error state
- [ ] render.yaml documents `VITE_ADMIN_API_KEY` for parity

## Open Questions (non-blocking)

1. Should keyless prod fail with a distinct "training unavailable — configure ADMIN_API_KEY" banner instead of generic error? (product polish, not blocking)
2. Is quarterly key rotation acceptable as the mitigation cadence for a personal project? (ops, not blocking)
