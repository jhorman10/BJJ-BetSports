# Archive Report: frontend-api-key-auth

**Archived**: 2026-08-05
**Mode**: hybrid (openspec filesystem + Engram persistence)
**Archived to**: `openspec/changes/archive/2026-08-05-frontend-api-key-auth/`
**Branch**: `perf/frontend-api-key-auth` (from `develop`)

## Final State

| Artifact | Path / Observation | Status |
|----------|--------------------|--------|
| proposal | `proposal.md` (Engram #955) | ✅ Present |
| delta spec (api-client) | `specs/api-client/spec.md` (Engram #956) | ✅ Present — 4 ADDED + 2 MODIFIED requirements |
| design | `design.md` (Engram #957) | ✅ Present |
| tasks | `tasks.md` (Engram #958; apply-progress #959) | ✅ 12/12 complete |
| verify-report | `verify-report.md` (Engram #961) | ✅ Verdict PASS |
| exploration (pre-proposal) | Engram #954 | ✅ Traceable |

## Task Completion Gate

- Persisted `tasks.md`: 12/12 `[x]`, 0 unchecked — gate passed, no stale-checkbox reconciliation needed.
- No CRITICAL issues in verify-report (0 CRITICAL, 3 WARNING, 2 SUGGESTION) — archive allowed.
- All artifacts present — no partial archive of artifacts.

## Spec Sync — DEFERRED (intentional-with-warnings)

**Capability**: `api-client` — **NO filesystem sync performed on this branch.**

The delta spec targets the `api-client` capability whose canonical spec
(`openspec/specs/api-client/spec.md`) was created on the **unify branch**
(`perf/unify-frontend-api-clients`, PR #44) and archived there as a NEW
capability (unify archive report, Engram #950). Unify is **NOT yet merged** into
`develop`, and `openspec/specs/api-client/` does NOT exist on this branch.

Per orchestrator directive, the generic archive fallback ("main spec missing →
promote delta to canonical") does NOT apply: this delta is a true delta
(`## ADDED Requirements` / `## MODIFIED Requirements` format), NOT a full spec.
Promoting it verbatim would create a malformed canonical (delta headers inside a
canonical) and would conflict with unify's canonical when #44 merges.

**Sync state**: DEFERRED — the 2 MODIFIED requirements (Single canonical axios
instance + request interceptor; API_ENDPOINTS single source) must be merged into
`openspec/specs/api-client/spec.md` **after unify #44 lands**.

### Deferred sync follow-up (REQUIRED after unify merges)

1. Merge the delta's 4 ADDED requirements into the canonical spec:
   - X-API-Key header injection (conditional)
   - Admin API key environment typing
   - Dead training code removal
   - Production parity configuration
2. Apply the 2 MODIFIED requirement blocks to their canonical counterparts:
   - `Single canonical axios instance` — gains the request interceptor (X-API-Key injection)
   - `API_ENDPOINTS single source` — dead `PARLEYS`/`TOP_ML_PICKS` removal + TRAIN re-point are unify-scope; this delta's requirement (TRAIN/TRAINING_TIMEOUT remain, `/train` special-case removed) is the additional part
3. Re-run the archive spec sync on the merged branch and update this report.

## Merge Order Coordination (CRITICAL — cross-PR)

**Merge ORDER: unify (#44) FIRST, then this change (`frontend-api-key-auth`).**

- W1/W2 (verify): on `develop`, `axios.create` exists in BOTH
  `frontend/src/infrastructure/api/client.ts:10` and `frontend/src/services/api.ts:28`.
  Unify #44's `services/api.ts` refactor creates a **second axios instance WITHOUT
  the X-API-Key interceptor** (unify S2 finding).
- If this change merges first and unify second, unify's `client.ts` change could
  drop the interceptor this change added — admin training endpoints would
  silently lose `X-API-Key` auth in prod.
- **Action**: unify PR #44 MUST carry the request interceptor forward when it
  collapses the factories (delete `services/api.ts` `axios.create`, reuse the
  canonical client instance). Verify `X-API-Key` survives after both merges.

This is a merge-order coordination item — NOT a code fix for this change.

## Verification Result

- **Verdict**: PASS (0 CRITICAL, 3 WARNING, 2 SUGGESTION)
- Build: ✅ `tsc -b && vite build` exit 0
- Tests: ✅ 21/21 (9 files) — `client.test.ts` 6 (3 defaults + 3 header scenarios)
- Lint: ✅ eslint `--max-warnings 0` exit 0
- Type-check: ✅ `tsc --noEmit` exit 0
- Spec compliance: 6/6 delta scenarios compliant (ADDED fully verified; MODIFIED
  verified on unify-branch state by definition — cross-PR WARNING, not FAIL)

## Warnings (recorded from verify-report, non-blocking)

- **W1 (cross-PR)**: `axios.create` in both client.ts and services/api.ts —
  single-factory is unify #44 scope. Delta-relevant part (interceptor on
  canonical client, 14 `api` exports preserved) verified.
- **W2 (cross-PR)**: hardcoded `/api/v1` literals + `TRAIN=/api/v1/train` on this
  branch — unify-scope. Delta requirement (TRAIN + TRAINING_TIMEOUT remain; no
  `/train` timeout special-case) satisfied.
- **W3 (doc drift)**: design.md D4 cites `constants.test.ts` which only exists on
  unify branch — verified against `constants.ts` directly. No action.

## Suggestions (future, non-blocking)

- S1: "Key never logged" has no automated test (absence property, statically
  verified) — optional console-spy test.
- S2: services/api.ts second axios instance lacks the interceptor — resolved by
  the merge-order action above.

## Engram Traceability

- `sdd/frontend-api-key-auth/explore` → #954
- `sdd/frontend-api-key-auth/proposal` → #955
- `sdd/frontend-api-key-auth/spec` → #956
- `sdd/frontend-api-key-auth/design` → #957
- `sdd/frontend-api-key-auth/tasks` → #958
- `sdd/frontend-api-key-auth/apply-progress` → #959
- `sdd/frontend-api-key-auth/verify-report` → #961
- `sdd/unify-frontend-api-clients/archive-report` (canonical origin) → #950
- `sdd/frontend-api-key-auth/archive-report` → this observation (upsert)

## SDD Cycle

Complete (with deferred spec sync). The change was planned, specified, designed,
implemented, verified, and archived. Implementation code (interceptor, env
typing, dead-code removal, prod parity) is fully verified. The canonical spec
merge is deferred until unify #44 lands, per merge-order coordination above. Full
audit trail lives at `openspec/changes/archive/2026-08-05-frontend-api-key-auth/`.
