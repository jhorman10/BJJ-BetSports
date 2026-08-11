# Apply Progress: Frontend Code Quality Fixes

**Mode**: Standard (non-TDD)
**Artifact store**: openspec

## Status: complete

## Completed Phases

### Phase 1: Fix Critical Bugs (3/3)
- [x] 1.1 `MatchCard.tsx:803` — Fixed TS error: `sanitizeText(recPick.suggested_stake)` → `recPick.suggested_stake.toFixed(2)`. Also removed all other `sanitizeText` calls (9 sites) and the import.
- [x] 1.2 `SuggestedPicksTab.tsx:363-370` — Wrapped `setCurrentTab`/`setInitialized` in `useEffect` with `queueMicrotask` to satisfy `react-hooks/set-state-in-effect`.
- [x] 1.3 `MatchCard.tsx:293` + `PreMatchPrediction.tsx:297` — Added `rel="noopener noreferrer"` to `target="_blank"` links.

### Phase 2: Remove Dead Code (2/2)
- [x] 2.1 Consolidated ErrorBoundary — Kept `common/ErrorBoundary.tsx`; updated `App.tsx` import; deleted `ErrorBoundary/ErrorBoundary.tsx` and empty dir.
- [x] 2.2 Removed commented-out dead code (was in deleted ErrorBoundary file).

### Phase 3: Extract Shared Utilities (4/4)
- [x] 3.1 Added `getMarketCategory(marketType: string): string` to `utils/marketUtils.ts`; moved `SuggestedPick` import to top; added return type to `getUniquePicks`.
- [x] 3.2 Replaced `getCategory()` in `BotDashboard.tsx` with `getMarketCategory()`; updated `categories` keys to uppercase.
- [x] 3.3 Verified `MatchHistoryTable.tsx` — `MARKET_TYPE_LABELS` is display-label-only, no duplicate categorization.
- [x] 3.4 Replaced `getPickCategory()` in `SuggestedPicksTab.tsx` with `getMarketCategory()`.

### Phase 4: Fix React Anti-Patterns (3/3)
- [x] 4.1 Replaced all `key={index}`/`key={i}`/`key={idx}` with stable composite keys across 11 files (13 sites).
- [x] 4.2 Wrapped `LiveMatchCard` in `memo()` in `LiveMatches.tsx`.
- [x] 4.3 Fixed import ordering in `SuggestedPicksTab.tsx` (consolidated two `@mui/icons-material` imports).

### Phase 5: Fix sanitizeText Misuse (2/2)
- [x] 5.1 Removed all `sanitizeText` calls from JSX in `MatchCard.tsx` (9 call sites).
- [x] 5.2 Deleted `utils/sanitize.ts` — verified no remaining callers.

### Phase 6: Expand ESLint Rules (2/2)
- [x] 6.1 Added to `eslint.config.js`:
  - `no-console`: `['warn', { allow: ['warn', 'error'] }]`
  - `import/order`: `['error', { groups: [...], newlines-between: 'always', pathGroups: [...] }]` — installed `eslint-plugin-import@2.32.0`
  - `@typescript-eslint/explicit-function-return-type`: `['warn', { allowExpressions: true, allowTypedFunctionExpressions: true }]`
  - ESLint `--fix` applied for import ordering
  - Fixed 6 auto-fixable errors (main.tsx import group, unused `index` params x4, set-state-in-effect)
- [x] 6.2 Fixed all 56 `explicit-function-return-type` warnings across 29 files:
  - Added `: void`, `: string`, `: number`, `: boolean`, `: Promise<void>`, `: React.ReactElement`, `: React.ReactElement[] | undefined`, `: React.ReactElement` return types
  - Added complex inline return types for hooks (useGoalDetection, useLiveMatches, usePWAInstall, usePredictions x3, useSmartPolling, useTeamSearch)
  - Added `MatchPrediction` import to `usePredictions.ts`
  - Wrapped `isTopML` with `Boolean()` for type safety in SuggestedPicksTab.tsx
  - Replaced `JSX.Element` with `React.ReactElement` in MatchHistoryTable.tsx (JSX namespace not available)

### Phase 7: Final Verification (all complete)
- [x] 7.1 `npx tsc --noEmit` — 0 errors
- [x] 7.2 `npx eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0 --no-warn-ignored` — 0 errors, 0 warnings
- [x] 7.3 `npx vitest run` — 38/38 tests pass
- [x] 7.4 Grep sweep: no `key={index}` in `.map()` callbacks — zero matches
- [x] 7.5 Grep sweep: all `target="_blank"` have `rel="noopener noreferrer"`
- [x] 7.6 Grep sweep: no commented-out code in production files
- [x] 7.7 Grep sweep: only one ErrorBoundary implementation (`common/ErrorBoundary.tsx`)

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `eslint.config.js` | Modified | Added `eslint-plugin-import`, 3 new rules |
| `src/utils/marketUtils.ts` | Modified | Added `getMarketCategory()`, moved `SuggestedPick` import, added return type to `getUniquePicks` |
| `src/utils/sanitize.ts` | Deleted | No remaining callers after MatchCard sanitizeText removal |
| `src/infrastructure/api/live.ts` | Modified | Added `: string` return type to `normalize` |
| `src/utils/pickValidationUtils.ts` | Modified | Added `: number` return type to `extractThreshold` |
| `src/presentation/components/LeagueSelector/constants.ts` | Modified | Added `: string` return type to `getLeagueName` |
| `src/presentation/components/MatchCard/MatchCard.tsx` | Modified | Removed `sanitizeText` import + 9 calls; fixed `key={index}`; added `: void` to mouse handlers; added `Record<string, unknown>` to `getCardSx`; added `rel="noopener noreferrer"` |
| `src/presentation/components/BotDashboard/BotDashboard.tsx` | Modified | Replaced `getCategory()` with `getMarketCategory()`; updated categories keys to uppercase; added `: void` return types to handlers |
| `src/presentation/components/BotDashboard/MatchHistoryTable.tsx` | Modified | Fixed keys in `.map()` callbacks; removed unused `index` params; added `React.ReactElement` return types to component functions; fixed import ordering |
| `src/presentation/components/LiveMatches/LiveMatches.tsx` | Modified | Wrapped `LiveMatchCard` in `memo()`; added `: void` return type; fixed `key={i}` in skeleton |
| `src/presentation/components/MatchDetails/SuggestedPicksTab.tsx` | Modified | Replaced `getPickCategory` with `getMarketCategory()`; fixed import ordering; moved state updates to `useEffect` with `queueMicrotask`; fixed `key={index}`; added `: boolean`/`: void` return types; wrapped `isTopML` with `Boolean()` |
| `src/presentation/components/MatchDetails/components/LiveScoreBoard.tsx` | Modified | Fixed `key={i}`; added `: React.ReactElement[] \| undefined` return type to `getGoalEvents` |
| `src/presentation/components/MatchDetails/components/PreMatchPrediction.tsx` | Modified | Fixed `key={index}` → composite keys; added `rel="noopener noreferrer"` |
| `src/presentation/components/Parley/ParleyCalculatorPage.tsx` | Modified | Fixed import ordering; added `: void` return types to handlers |
| `src/presentation/components/Parley/ParleySlip.tsx` | Modified | Added `: React.ReactElement` return type to `getPickIcon` |
| `src/presentation/components/PredictionGrid/PredictionGrid.tsx` | Modified | Fixed import ordering; added `: void`/`: Promise<void>` return types |
| `src/presentation/components/PredictionGrid/PredictionGridHeader.tsx` | Modified | Added `: void` return type to `handleSortChange` |
| `src/presentation/components/Training/TrainingControlPanel.tsx` | Modified | Added `: Promise<void>` return type to `handleSubmit` |
| `src/presentation/components/LeagueSelector/LeagueSelector.tsx` | Modified | Fixed import ordering; added `: void` return types to handlers |
| `src/presentation/components/common/ErrorBoundary.tsx` | Modified | Added return types to class methods: `: void` for `componentDidCatch`/`handleReset`, `: ReactNode` for `render` |
| `src/application/stores/useOfflineStore.ts` | Modified | Added `: void` return type to `recheckConnectivity` |
| `src/presentation/components/common/SystemInitializationScreen.tsx` | Modified | Fixed `key={idx}` → `step-${idx}` |
| `src/presentation/components/common/DashboardSkeleton.tsx` | Modified | Fixed `key={i}` → `skeleton-${i}` (2 sites) |
| `src/App.tsx` | Modified | Updated ErrorBoundary import path |
| `src/main.tsx` | Modified (auto-fix) | Consolidated import groups |
| `src/presentation/components/BotDashboard/MatchHistoryTable.tsx` | Modified | See above |
| `src/presentation/components/MatchCard/PredictionGridList.tsx` | Modified | Fixed `key={index}` → `matchPrediction.match.id` |
| `src/hooks/useAppVisibility.ts` | Modified | Added `: void` return types (2 functions) |
| `src/hooks/useGoalDetection.ts` | Modified | Added return type with inline interface |
| `src/hooks/useImageColor.ts` | Modified | Added `: string | null` return type |
| `src/hooks/useInitialization.ts` | Modified | Added `: void` return type |
| `src/hooks/useLiveMatches.ts` | Modified | Added inline return type object |
| `src/hooks/usePWAInstall.ts` | Modified | Added inline return type; `: void`/`: Promise<void>` return types |
| `src/hooks/usePredictions.ts` | Modified | Added return types to 3 `export function` declarations; added `MatchPrediction` import |
| `src/hooks/useSmartPolling.ts` | Modified | Added return type; `: void` return type |
| `src/hooks/useTeamSearch.ts` | Modified | Added return type; `: void` return type |
| `src/presentation/hooks/useMatchHistoryTable.ts` | Modified | Added `: void`/`: number` return types (7 functions) |

## Deviations from Design
None — implementation matches design.md.

## Issues Found
- `MatchHistoryTable.tsx` uses `JSX.Element` but the project's `tsconfig.json` doesn't expose `JSX` as a global namespace. Fixed by using `React.ReactElement` instead (React is already imported in that file).
- `usePredictions.ts` didn't import `MatchPrediction` — needed for the return type annotation. Added the import.
- `isTopML` in `SuggestedPicksTab.tsx` had a return type mismatch (`string | boolean` vs `boolean`) due to `&&` short-circuit evaluation on `p.reasoning`. Wrapped expression with `Boolean()` for type safety.
- `getCardSx` return type uses `Record<string, unknown>` for flexibility with MUI sx props — could be tightened to `SxProps<Theme>` if desired.

## Status
All phases complete. Ready for verify.
