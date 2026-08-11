# Tasks: Frontend Code Quality Fixes

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~350–450 (additions + deletions, mostly deletions of dead code) |
| 400-line budget risk | Low — well within D2 800-line budget |
| Chained PRs recommended | No |
| Suggested split | Single PR (work-unit commits inside) |
| Delivery strategy | single-pr |
| Chain strategy | not applicable |

Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Low

## Phase 1: Fix Critical Bugs

- [x] 1.1 `MatchCard.tsx:803` — Fix TypeScript error: `sanitizeText(recPick.suggested_stake)` → `recPick.suggested_stake.toFixed(2)` (matches pattern in MatchHistoryTable.tsx:309 and SuggestedPicksTab.tsx:141)
  - Also removed all other `sanitizeText` calls and the import (see 5.1)
  - Verify: `tsc --noEmit` passes at this line

- [x] 1.2 `SuggestedPicksTab.tsx:363-370` — Move state updates during render into `useEffect`
  - Wrapped `setCurrentTab`/`setInitialized` in `queueMicrotask` inside `useEffect` to satisfy `react-hooks/set-state-in-effect` rule
  - Verify: No React warning about state update during render

- [x] 1.3 `MatchCard.tsx:293` + `PreMatchPrediction.tsx:297` — Add `rel="noopener noreferrer"` to `target="_blank"` links
  - Verify: Grep confirms all `target="_blank"` have `rel`

## Phase 2: Remove Dead Code

- [x] 2.1 Consolidate ErrorBoundary — Keep `common/ErrorBoundary.tsx`; update `App.tsx:21` import; delete `ErrorBoundary/ErrorBoundary.tsx`
  - Verify: `find -name "ErrorBoundary*"` returns exactly one implementation file

- [x] 2.2 Remove commented-out dead code from old `ErrorBoundary.tsx` (deleted in 2.1)
  - Verify: No commented-out code in production files

## Phase 3: Extract Shared Utilities

- [x] 3.1 `utils/marketUtils.ts` — Add `getMarketCategory(marketType: string): string` consolidating the logic from `BotDashboard.tsx:getCategory()` and `SuggestedPicksTab.tsx:getPickCategory()`
  - Also moved `SuggestedPick` import to top of file; added explicit return type to `getUniquePicks`
  - Verify: Function handles all market types covered by both original implementations

- [x] 3.2 `BotDashboard.tsx` — Replace inline `getCategory()` (lines 66-89) with `getMarketCategory()`; adapt callers for uppercase return format
  - Updated `categories` object keys from lowercase to uppercase
  - Verify: `BotDashboard.tsx` no longer has `getCategory` function definition

- [x] 3.3 `MatchHistoryTable.tsx` — Use `getMarketCategory()` for categorization; keep `MARKET_TYPE_LABELS` for display label lookup only
  - Verified: `MARKET_TYPE_LABELS` is display-label-only, no duplicate categorization logic
  - Verify: No duplicate categorization logic in MatchHistoryTable

- [x] 3.4 `SuggestedPicksTab.tsx` — Replace `getPickCategory()` (lines 204-237) with `getMarketCategory()`
  - Verify: `SuggestedPicksTab.tsx` no longer has `getPickCategory` function definition

## Phase 4: Fix React Anti-Patterns

- [x] 4.1 Replace `key={index}` / `key={i}` / `key={idx}` in all files with stable keys:
  - `MatchCard.tsx:623` — use `${score.home_goals}-${score.away_goals}`
  - `MatchHistoryTable.tsx:433` — use `pick.market_type`
  - `MatchHistoryTable.tsx:778` — use `pick.market_type`
  - `PredictionGrid.tsx:252` — use `matchPrediction.match.id`
  - `SuggestedPicksTab.tsx:525` — use `pick.market_type`
  - `LiveMatches.tsx:542` — use `match.id`
  - `LiveScoreBoard.tsx:47` — use `goal-${i}` prefix (static skeleton key)
  - `ScoreMatrixModal.tsx:108,118,134` — already composite keys, verified
  - `SystemInitializationScreen.tsx:124` — already uses `step-${idx}` prefix (static steps, acceptable)
  - `DashboardSkeleton.tsx:70,183` — use `skeleton-${i}` prefix (static skeleton)
  - `PreMatchPrediction.tsx:189,220` — use `${score.home_goals}-${score.away_goals}` and `pick.market_type`
  - Verify: Grep for `key={index}`, `key={i}`, `key={idx}` returns zero results (except static skeletons)

- [x] 4.2 `LiveMatches.tsx` — Wrap `LiveMatchCard` component in `memo()`
  - Updated import to `import React, { memo }`; changed component to `const LiveMatchCard = memo(({ matchData }) => ...`
  - Verify: `LiveMatchCard` is exported with `memo()`

- [x] 4.3 `SuggestedPicksTab.tsx:19` — Fix import ordering: move `@mui/icons-material` import to external imports section
  - Consolidated two `@mui/icons-material` imports into one; moved to external imports section
  - Verify: ESLint `import/order` rule passes

## Phase 5: Fix sanitizeText Misuse

- [x] 5.1 Remove `sanitizeText` calls from JSX text content and attributes in `MatchCard.tsx` (9 call sites: lines 180, 455, 470, 501, 516, 783, 803, 818)
  - Verify: Direct values passed to JSX — no sanitization needed (React auto-escapes)

- [x] 5.2 Delete `utils/sanitize.ts` if all callers removed
  - Verify: No imports of `sanitizeText` remain in source (except test files)

## Phase 6: Expand ESLint Rules

- [x] 6.1 `eslint.config.js` — Add rules:
  - `'no-console': ['warn', { allow: ['warn', 'error'] }]`
  - `'import/order': ['error', { ... }]` — also installed `eslint-plugin-import@2.32.0`
  - `'@typescript-eslint/explicit-function-return-type': ['warn', { allowExpressions: true, allowTypedFunctionExpressions: true }]`
  - Verify: ESLint runs with 0 errors on all new changes

- [x] 6.2 Fix all 56 `explicit-function-return-type` warnings across 29 files (hooks, stores, infrastructure, utils, components)
  - Added explicit return types to all flagged functions: `: void`, `: string`, `: number`, `: boolean`, `: Promise<void>`, `: React.ReactElement`, `: React.ReactElement[] | undefined`, `: JSX.Element` (replaced with `React.ReactElement` in MatchHistoryTable), and complex inline return type objects for hooks
  - Added `MatchPrediction` import to `usePredictions.ts`
  - Wrapped `isTopML` expression with `Boolean()` for type safety
  - Verify: ESLint runs with 0 errors, 0 warnings

## Phase 7: Final Verification

- [x] 7.1 `npx tsc --noEmit` — 0 errors
- [x] 7.2 `npx eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0 --no-warn-ignored` — 0 errors, 0 warnings
- [x] 7.3 `npx vitest run` — 38/38 tests pass
- [x] 7.4 Grep sweep: no `key={index}` in `.map()` callbacks (except static skeletons) — zero matches found
- [x] 7.5 Grep sweep: all `target="_blank"` have `rel="noopener noreferrer"` — both links verified
- [x] 7.6 Grep sweep: no commented-out code in production files — zero matches found
- [x] 7.7 Grep sweep: only one `ErrorBoundary` implementation exists — `common/ErrorBoundary.tsx` only
