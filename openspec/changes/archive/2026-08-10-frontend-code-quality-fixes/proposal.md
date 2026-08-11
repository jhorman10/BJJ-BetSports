# Proposal: Frontend Code Quality Fixes

## Intent

Systematic cleanup of 15 issues identified in a comprehensive frontend code quality audit. The audit analyzed 109 source files (React 19 + TypeScript + Vite + Zustand + MUI), running `tsc --noEmit` (1 error), `eslint` (0 violations, minimal config), and `vitest` (38/38 passing). Findings span 2 critical bugs, 3 dead code items, 7 bad practices, 2 incompatibilities, and 3 performance issues. This proposal scopes the P0/P1 fixes into a single deliverable.

## Scope

### In Scope
1. Fix TypeScript compile error in `MatchCard.tsx` (BUG-001)
2. Fix React state-update-during-render in `SuggestedPicksTab.tsx` (BUG-002)
3. Add `rel="noopener noreferrer"` to 2 external links (Security)
4. Consolidate duplicate `ErrorBoundary` components into one (DEAD-001)
5. Remove commented-out dead code in `ErrorBoundary.tsx` (DEAD-002)
6. Extract duplicated market categorization logic to `utils/marketUtils.ts` (PRACTICE-001)
7. Replace `key={index}` with stable keys in 15 instances across 10 files (PRACTICE-002, PERF-002)
8. Fix import ordering in `SuggestedPicksTab.tsx` (PRACTICE-003)
9. Fix `sanitizeText` misuse — remove redundant HTML encoding in JSX contexts (PRACTICE-005)
10. Add `React.memo` to `LiveMatchCard` (PERF-001)
11. Add missing ESLint rules for `no-console`, `import/order`, `explicit-function-return-type` (COMPAT-001)

### Out of Scope
- Refactoring large components (>500 lines) into sub-components (PRACTICE-006) — deferred to separate change
- Migrating `React.FC` to plain functions across 38 files (PRACTICE-007) — deferred to separate change
- Consolidating type definitions between `types/index.ts` and `domain/entities/` (COMPAT-002) — deferred to separate change
- Standardizing `React.useState` vs `{ useState }` import patterns (PRACTICE-004) — deferred to separate change
- Removing `.kilo/` directory from repo root

## Capabilities

### Modified Capabilities
- `frontend`: ESLint config, React patterns, import ordering
- `code-quality`: Clean Code adherence, dead code removal, DRY
- `linting`: ESLint rule expansion

## Approach

1. Phase 1: Fix critical bugs (TS error, state-during-render, security links)
2. Phase 2: Remove dead code (duplicate ErrorBoundary, commented code)
3. Phase 3: Extract shared utilities (market categorization, `isNetworkError` if needed)
4. Phase 4: Fix React anti-patterns (keys, memo, import ordering)
5. Phase 5: Fix `sanitizeText` misuse
6. Phase 6: Expand ESLint rules
7. Phase 7: Verification (tsc, eslint, vitest all green)

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `MatchCard.tsx` | Modified | Fix TS error at line 803; add `rel` to external link at line 293 |
| `SuggestedPicksTab.tsx` | Modified | Fix state-during-render (lines 363-370); fix import ordering (line 19) |
| `PreMatchPrediction.tsx` | Modified | Add `rel` to external link at line 297 |
| `ErrorBoundary/` + `common/` | Modified | Consolidate to single implementation |
| `utils/marketUtils.ts` | Modified | Add `getMarketCategory()` to consolidate 3 duplicated implementations |
| `BotDashboard.tsx` | Modified | Use shared `getMarketCategory()` |
| `MatchHistoryTable.tsx` | Modified | Use shared `getMarketCategory()`; fix `key={index}` |
| `LiveMatches.tsx` | Modified | Fix `key={i}`; add `React.memo` to `LiveMatchCard` |
| `PredictionGrid.tsx` | Modified | Fix `key={index}` |
| `LiveScoreBoard.tsx` | Modified | Fix `key={i}` |
| `ScoreMatrixModal.tsx` | Modified | Fix `key` patterns |
| `SystemInitializationScreen.tsx` | Modified | Fix `key={idx}` |
| `PreMatchPrediction.tsx` | Modified | Fix `key={index}` |
| `MatchCard.tsx` | Modified | Fix `key={index}` |
| `DashboardSkeleton.tsx` | Modified | Fix `key={i}` |
| `eslint.config.js` | Modified | Add `no-console`, `import/order`, `explicit-function-return-type` |
| `utils/sanitize.ts` | Modified | Remove or rework `sanitizeText` — unnecessary with React JSX escaping |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Consolidating ErrorBoundary changes visual | Low | Review both implementations; keep the richer one from `common/` |
| Extracted `getMarketCategory` breaks tab logic | Med | Comprehensive testing of pick filtering; the two implementations have different return formats (uppercase vs lowercase) |
| Removing `sanitizeText` calls introduces XSS | Low | React JSX auto-escapes text content and attributes; no `dangerouslySetInnerHTML` used anywhere |
| ESLint rule expansion causes new violations | Low | Run with `--max-warnings 0` and fix any new violations |

## Rollback Plan

Each fix is an independent sub-change. Use work-unit commits so each can be reverted individually. The most sensitive change (ErrorBoundary consolidation) can be reverted by restoring either implementation.

## Dependencies

None external. Existing Vitest suite (38 tests) serves as regression net. Additional tsc + eslint verification.

## Success Criteria

- [ ] `tsc --noEmit` passes with 0 errors
- [ ] `eslint` passes with 0 errors, 0 warnings
- [ ] `vitest run` — all 38 tests pass
- [ ] Zero `key={index}` / `key={i}` / `key={idx}` patterns remain in `.map()` callbacks
- [ ] Single `ErrorBoundary` implementation (no duplicate file)
- [ ] No commented-out code in production source files
- [ ] `sanitizeText` not called on `number` type
- [ ] `rel="noopener noreferrer"` on all `target="_blank"` links
- [ ] Market categorization logic exists in exactly one place
- [ ] `React.memo` applied to all components rendered in lists
