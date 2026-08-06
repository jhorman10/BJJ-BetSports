# Proposal: Unify Frontend API Clients

## Intent

Two parallel API stacks drift: legacy `services/api.ts` (212 lines, 12 hardcoded paths, 7+ consumers) vs `infrastructure/api/*` (shared axios client, 2 stores). Same endpoint `matches/live/with-predictions`: 30s vs 10s timeout; predictions limit 30 vs 10; paths re-declared in `API_ENDPOINTS`; 3 modules hit non-existent routes; ~150 lines of ESPN logic duplicated. Slice 1: consolidate transport, kill dead code.

## Scope

### In Scope
- Canonical axios in `infrastructure/api/client.ts`; `services/api.ts` reuses it
- `API_ENDPOINTS` single source; remove `PARLEYS`, `TOP_ML_PICKS`; fix stale `TRAIN`
- Delete dead `parleys.ts`, `analytics.ts` (zero consumers, no routes)
- Fix stale `/train` special-case in `post()`
- ESPN dedupe: hook imports `fetchESPNLiveMatches`, drops inline copy
- Normalize (documented): live timeout → 30s; predictions limit → 30
- Shared `isNetworkError` util; 3 stores reuse it
- Type drift fixes in touched files only

### Out of Scope
Full consumer migration; type unification; X-API-Key auth; ESPN transport change; live-flow UI consolidation; backend changes.

## Capabilities

### New Capabilities
- `api-client`: one axios instance, canonical `API_ENDPOINTS`, normalized timeout/limit policy, shared error classification

### Modified Capabilities
- None

## Approach

1. `client.ts` = only axios factory; `services/api.ts` imports it, keeps export shape
2. Re-point hardcoded strings to `API_ENDPOINTS`; fix `TRAIN` → `/api/v1/train/run-now`
3. Hook imports `fetchESPNLiveMatches` with explicit shape map
4. Timeout/limit constants centralized, each change documented

## Scenario

Adding an endpoint = edit `API_ENDPOINTS` once, one client, one timeout policy. No guessing which instance/path is stale.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `infrastructure/api/client.ts` | Modified | Canonical axios instance |
| `services/api.ts` | Modified | Reuse client + endpoints; fix `/train` |
| `config/constants.ts` | Modified | Dead entries removed; timeout/limit constants |
| `infrastructure/api/parleys.ts` | Removed | Dead module |
| `infrastructure/api/analytics.ts` | Removed | Dead module |
| `infrastructure/api/live.ts` | Modified | 30s timeout |
| `infrastructure/api/predictions.ts` | Modified | Limit 30 |
| `hooks/useLiveMatches.ts` | Modified | Drop inline ESPN copy |
| 3 stores + `utils/apiErrors.ts` | Modified/New | Shared `isNetworkError` |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Limit 30 renders more rows | Med | Documented; legacy value preserved |
| ESPN shape map breaks rendering | Med | Mapper + unit tests |
| Legacy consumer breakage | Low | Export surface unchanged; existing tests |

## Rollback Plan

Per-sub-change commits; revert individual diffs. Export surface unchanged → instance swap invisible. Timeout/limit changes are one-line reverts.

## Dependencies

None external. Vitest suite as regression net.

## Success Criteria

- [ ] Only `client.ts` creates an axios instance
- [ ] Zero hardcoded `/api/v1` strings in `services/api.ts`
- [ ] `parleys.ts`, `analytics.ts`, `TOP_ML_PICKS` gone; zero refs
- [ ] No ESPN fetch code in `useLiveMatches.ts`
- [ ] Live timeout = 30s, limit = 30 on both paths
- [ ] Vitest passes

## Proposal question round

Assumptions pending answer: (1) Parley backend not near-term — module deleted, local-only UI kept; (2) suggested-picks timeout stays 90s (slow pick gen); (3) limit 30 in PredictionGrid acceptable (legacy behavior).
