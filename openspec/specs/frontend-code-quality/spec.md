# Spec: Frontend Code Quality Fixes

## Overview

This specification covers the P0 and P1 fixes from the frontend code quality audit. It uses Given/When/Then format with RFC 2119 keywords.

## Capabilities

| Capability | Status | Description |
|---|---|---|
| `frontend-code-quality` | Modified | Fix bugs, dead code, anti-patterns, performance, and ESLint config in frontend |

## Requirements

### R1: TypeScript compile error fix

**GIVEN** `MatchCard.tsx` line 803 calls `sanitizeText(recPick.suggested_stake)` where `suggested_stake` is `number`
**WHEN** `tsc --noEmit` is run
**THEN** compilation MUST succeed with zero errors

**Fix**: Replace with `sanitizeText(String(recPick.suggested_stake))` or use `recPick.suggested_stake.toFixed(2)` directly (matching the pattern in `MatchHistoryTable.tsx:309` and `SuggestedPicksTab.tsx:141`).

### R2: React state-update-during-render fix

**GIVEN** `SuggestedPicksTab.tsx` lines 363-370 call `setCurrentTab()` and `setInitialized()` during render
**WHEN** the component renders with `!initialized && defaultTab && !currentTab`
**THEN** NO React warning about state updates during render SHOULD appear
**AND** the tab selection MUST still initialize correctly

**Fix**: Move the logic into a `useEffect` with dependencies `[defaultTab, loading, sortedPicks.length, initialized]`.

### R3: Security — external link rel attribute

**GIVEN** two `<a>` elements with `target="_blank"` in `MatchCard.tsx:293` and `PreMatchPrediction.tsx:297`
**WHEN** a user clicks the external link
**THEN** the link MUST open with `rel="noopener noreferrer"` to prevent tab-nabbing

**Fix**: Add `rel="noopener noreferrer"` to both `<a>`/Chip elements.

### R4: Duplicate ErrorBoundary consolidation

**GIVEN** two ErrorBoundary implementations exist
**WHEN** the consolidation is complete
**THEN** exactly ONE ErrorBoundary file SHALL exist
**AND** `App.tsx` and `main.tsx` MUST import from the same path

**Fix**: Keep `common/ErrorBoundary.tsx` (161-line rich version); update `App.tsx` to import from `common/`; delete `ErrorBoundary/ErrorBoundary.tsx`.

### R5: Remove commented-out dead code

**GIVEN** `ErrorBoundary/ErrorBoundary.tsx:28` contains `// console.error(...)`
**WHEN** the consolidation in R4 completes
**THEN** no commented-out code SHALL remain in the replaced file

### R6: Extract duplicated market categorization

**GIVEN** the same market-type-to-category mapping exists in `BotDashboard.tsx:getCategory()`, `SuggestedPicksTab.tsx:getPickCategory()`, and `MatchHistoryTable.tsx:MARKET_TYPE_LABELS`
**WHEN** a new market type is added
**THEN** it SHALL be defined in exactly one place

**Fix**: Create `getMarketCategory(marketType: string): string` in `utils/marketUtils.ts`. Both `getCategory` and `getPickCategory` SHALL use the same return format. `MatchHistoryTable.tsx` SHALL use the shared function for categorization (keeping `MARKET_TYPE_LABELS` for display label lookup only).

### R7: Replace index-based React keys

**GIVEN** 15 instances of `key={index}`, `key={i}`, or `key={idx}` in `.map()` callbacks
**WHEN** a list is re-rendered after reorder/filter/insert
**THEN** React SHALL associate the correct DOM element with the correct data item

**Fix**: Replace index-based keys with stable IDs. Where no stable ID exists, use a composite key (e.g., `${matchId}-${pickType}`).

### R8: Fix import ordering

**GIVEN** `SuggestedPicksTab.tsx:19` imports `@mui/icons-material` (external) after local imports
**WHEN** the import ordering rule `import/order` is applied
**THEN** all external imports MUST come before local imports

**Fix**: Move `import { CheckCircle, Cancel, HourglassEmpty } from "@mui/icons-material"` to the external imports section (before `../../../types`).

### R9: Fix sanitizeText misuse

**GIVEN** `sanitizeText` HTML-encodes strings but its output is used in JSX text content and attributes where React already escapes
**WHEN** a team name contains special characters (e.g., `O'Brien`)
**THEN** the UI MUST display `O'Brien`, not `O&#039;Brien`

**Fix**: Remove `sanitizeText` calls where output is used in JSX text content and attributes. Use plain values. Remove the function if no longer needed (no `dangerouslySetInnerHTML` exists in codebase).

### R10: Add React.memo to LiveMatchCard

**GIVEN** `LiveMatchCard` is rendered in a list inside `LiveMatches.tsx`
**WHEN** parent state changes trigger re-renders
**THEN** `LiveMatchCard` SHALL only re-render when its props change

**Fix**: Wrap `LiveMatchCard` component in `memo()`.

### R11: Expand ESLint rules

**GIVEN** ESLint config has only 5 rules
**WHEN** the expanded config is applied
**THEN** `no-console`, `import/order`, and `@typescript-eslint/explicit-function-return-type` violations SHALL be caught

**Fix**: Add rules to `frontend/eslint.config.js`. Fix any new violations introduced by the expanded rules.

## Non-Requirements (Explicitly Out of Scope)

- PRACTICE-006: Refactoring >150-line components (deferred)
- PRACTICE-007: Migrating `React.FC` to plain functions (deferred)
- PRACTICE-004: Standardizing `React.useState` vs `{ useState }` pattern (deferred)
- COMPAT-002: Type consolidation between `types/` and `domain/entities/` (deferred)
- Dead-code removal of `.kilo/` directory (not frontend scope)
