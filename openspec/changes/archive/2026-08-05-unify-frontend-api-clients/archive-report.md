# Archive Report: unify-frontend-api-clients

**Archived**: 2026-08-05
**Mode**: hybrid (openspec filesystem + Engram persistence)
**Archived to**: `openspec/changes/archive/2026-08-05-unify-frontend-api-clients/`

## Final State

| Artifact | Path / Observation | Status |
|----------|--------------------|--------|
| proposal | `proposal.md` (Engram #943) | ✅ Present |
| delta spec (api-client) | `specs/api-client/spec.md` | ✅ Present |
| design | `design.md` (Engram #945) | ✅ Present |
| tasks | `tasks.md` (Engram #946, #947 apply-progress) | ✅ 17/17 complete |
| verify-report | `verify-report.md` (Engram #949) | ✅ Verdict PASS |
| discovery (spec-phase facts) | Engram #944 | ✅ Traceable |

## Spec Sync

**Capability**: `api-client` (NEW — no prior main spec at `openspec/specs/api-client/`)

Per the archive contract for a NEW capability, the delta spec was promoted to the canonical capability spec (ADD semantics, not merge/modify):

- `openspec/changes/.../specs/api-client/spec.md` → `openspec/specs/api-client/spec.md` (canonical form: `# api-client Specification`, `## Purpose`, `## Requirements`)
- 7 requirements synced: Single canonical axios instance, API_ENDPOINTS single source, Dead modules removed, ESPN single source, Normalized timeout/limit policy, Shared network error classification, Regression coverage
- 11 scenarios preserved verbatim
- No MODIFIED/REMOVED/RENAMED sections — nothing else touched
- Config rule "preserve change-scoped operational requirements" applied: the delta contains no change-scoped operational requirements; all 7 are capability requirements and were merged.
- No destructive merge — no confirmation needed per `rules.archive`

## Verification Result

- **Verdict**: PASS (0 CRITICAL, 1 WARNING, 3 SUGGESTIONS)
- Build: ✅ `tsc -b && vite build`, `tsc --noEmit` exit 0
- Tests: ✅ 38/38 (12 files) via Vitest
- Lint: ✅ eslint `--max-warnings 0` exit 0
- Spec compliance: 11/12 scenarios runtime-compliant

## Follow-up Item (recorded from verify WARNING)

**REQ-06 test gap**: the "Uniform classification" scenario of the Shared network error classification requirement has no runtime covering test. Implementation is statically verified (`utils/apiErrors.ts:6-14`; all 3 stores wired; store regression tests pass), but the scenario lacks runtime proof.

**Action**: add `frontend/src/utils/apiErrors.test.ts` with 3 assertions covering `ERR_NETWORK`, `ECONNABORTED`, and `"Network Error"` inputs to `isNetworkError`. Resolves the gap; no implementation change required.

Minor (non-blocking, from verify SUGGESTIONs, for future reference): dormant `POST_TIMEOUTS` key `/train/run-now` could get a surface assertion or be dropped; Vitest has no coverage thresholds; untracked `docs/migration-npm-to-bun.md` at repo root is unrelated to this change.

## Task Completion Gate

- Persisted `tasks.md`: 17/17 `[x]`, 0 unchecked — gate passed, no stale-checkbox reconciliation needed.
- No CRITICAL issues in verify-report — archive allowed.
- No artifacts missing — no partial archive.

## Engram Traceability

- `sdd/unify-frontend-api-clients/proposal` → #943
- `sdd/unify-frontend-api-clients/design` → #945
- `sdd/unify-frontend-api-clients/tasks` → #946
- apply-progress (all tasks complete) → #947
- `sdd/unify-frontend-api-clients/verify-report` → #949
- spec-phase discovery → #944
- `sdd/unify-frontend-api-clients/archive-report` → this observation (upsert)

## SDD Cycle

Complete. The change was planned, specified, designed, implemented, verified, and archived. Source of truth now lives at `openspec/specs/api-client/spec.md`; the full audit trail lives at `openspec/changes/archive/2026-08-05-unify-frontend-api-clients/`.
