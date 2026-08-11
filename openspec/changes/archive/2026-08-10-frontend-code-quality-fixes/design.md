# Design: Frontend Code Quality Fixes

## Technical Approach

Apply P0/P1 fixes from the code quality audit in a phased manner. Each fix is an independent sub-change with its own verification step. No new features are introduced; all changes are cleanup, bug fixes, and pattern enforcement.

## Architecture Decisions

### D1: ErrorBoundary consolidation — keep the rich version
| Option | Tradeoff | Decision |
|---|---|---|
| Keep `common/ErrorBoundary.tsx` (161-line polished) | Already in production use at `main.tsx:16`; richer UX | ✅ Chosen |
| Keep `ErrorBoundary/ErrorBoundary.tsx` (51-line simple) | Simpler but less user-friendly | Rejected |

`App.tsx:21` updates import to `./presentation/components/common/ErrorBoundary`; old file deleted.

### D2: Market categorization — single source with normalized output
| Option | Tradeoff | Decision |
|---|---|---|
| Single `getMarketCategory()` returning uppercase keys | Consistent with `SuggestedPicksTab.tsx` pattern | ✅ Chosen |
| Return lowercase | Matches `BotDashboard.tsx` pattern | Deferred — callers map case |
| Return i18n keys | Over-engineering for current scope | Rejected |

`utils/marketUtils.ts` gets `getMarketCategory(marketType: string): string`. `BotDashboard.tsx` and `MatchHistoryTable.tsx` adapt their existing calls to the new return format. `SuggestedPicksTab.tsx` already uses uppercase, so minimal changes there.

### D3: Key replacement strategy
| Key context | Strategy |
|---|---|
| Score probabilities list (`MatchCard.tsx:623`) | No unique ID — use `${score.home_goals}-${score.away_goals}` |
| Pick chips (`MatchHistoryTable.tsx:778`) | `pick.market_type` (unique per pick in context) |
| Pick rows (`SuggestedPicksTab.tsx:525`) | Already composite `pick-${currentTab}-${index}` — replace with pick ID if available |
| Skeleton items (`DashboardSkeleton.tsx:70,183`) | Use `skeleton-${i}` with `i` as fallback (skeletons have no identity) |
| Matrix cells (`ScoreMatrixModal.tsx`) | Already composite keys — no change needed |
| LiveMatches grid (`LiveMatches.tsx:542`) | `match.id` available |
| Options lists | Already use `model.key`, `league.key` etc. — no change needed |
| SystemInitialization steps (`SystemInitializationScreen.tsx:124`) | Already uses `idx` for static steps — acceptable for static UI |

### D4: sanitizeText removal — rely on React escaping
| Option | Tradeoff | Decision |
|---|---|---|
| Remove `sanitizeText` calls in JSX text/attr contexts | React already escapes; avoids double-encoding | ✅ Chosen |
| Keep `sanitizeText` for `alt` attributes | `alt` is already safe (not HTML context) | Removed — redundant |
| Keep function for potential future `dangerouslySetInnerHTML` | YAGNI — no `dangerouslySetInnerHTML` in codebase | Function deleted if all callers removed |

### D5: ESLint rule selection
New rules to add:
- `'no-console': ['warn', { allow: ['warn', 'error'] }]` — catches `console.log` in production
- `'import/order': ['error', { ... }]` — enforces import grouping
- `'@typescript-eslint/explicit-function-return-type': 'warn'` — enforces return types on exported functions

## Data Flow

```
Before: 3 copies of market categorization → 3 different output formats
After:  1 copy in utils/marketUtils.ts → consistent output format
        Callers adapt to the single format

Before: 2 ErrorBoundary files → inconsistent error UX
After:  1 ErrorBoundary file → consistent error UX

Before: sanitizeText double-encodes HTML entities in JSX
After:  React's native escaping handles it → correct display
```

## File Changes

| File | Action | Description |
|---|---|---|
| `MatchCard.tsx` | Modify | Fix `sanitizeText` type error (line 803); add `rel` to link (line 293); fix `key={index}` (line 623) |
| `SuggestedPicksTab.tsx` | Modify | Fix state-during-render (lines 363-370); fix import order (line 19); use shared `getMarketCategory` |
| `PreMatchPrediction.tsx` | Modify | Add `rel` to link (line 297); fix `key={index}` (lines 189, 220) |
| `common/ErrorBoundary.tsx` | Keep | Retained as the single ErrorBoundary |
| `ErrorBoundary/ErrorBoundary.tsx` | Delete | Replaced by `common/ErrorBoundary.tsx` |
| `App.tsx` | Modify | Update import to `common/ErrorBoundary` |
| `utils/marketUtils.ts` | Modify | Add `getMarketCategory()` function |
| `BotDashboard.tsx` | Modify | Use `getMarketCategory()`; remove `getCategory()` |
| `MatchHistoryTable.tsx` | Modify | Use `getMarketCategory()`; fix `key={index}` (lines 433, 778) |
| `LiveMatches.tsx` | Modify | Fix `key={i}` (line 542); wrap `LiveMatchCard` in `memo` |
| `MatchCard.tsx` | Modify | Fix `key={index}` (line 623) — already in file above |
| `LiveScoreBoard.tsx` | Modify | Fix `key={i}` (line 47) |
| `PreMatchPrediction.tsx` | Modify | Fix `key={index}` (lines 189, 220) — already in file above |
| `ScoreMatrixModal.tsx` | Modify | Verify keys — already composite, may need no change |
| `SystemInitializationScreen.tsx` | Modify | Fix `key={idx}` (line 124) |
| `DashboardSkeleton.tsx` | Modify | Fix `key={i}` (lines 70, 183) |
| `PredictionGrid.tsx` | Modify | Fix `key={index}` (line 252) |
| `utils/sanitize.ts` | Delete | Remove if all callers eliminated |
| `eslint.config.js` | Modify | Add `no-console`, `import/order`, `explicit-function-return-type` |

## Testing Strategy

| Test | What | Approach |
|---|---|---|
| Regression | Existing 38 tests | Run `vitest run` — all must still pass |
| Type check | `tsc --noEmit` | Must pass with 0 errors |
| Lint | `eslint` | Must pass with 0 errors, 0 warnings |
| Key audit | No `key={index}` | Grep sweep post-fix |
| Security audit | All `target="_blank"` have `rel` | Grep sweep post-fix |
| Dead code audit | No commented-out code | Grep sweep post-fix |
| Single ErrorBoundary | Only one file exists | `find -name ErrorBoundary` post-fix |

## Migration / Rollout

Independent sub-changes, each verifiable. Order: bugs → dead code → shared utils → React patterns → ESLint expansion. Final verification: tsc + eslint + vitest all green.

## Open Questions

- [ ] `SuggestedPicksTab.tsx:getPickCategory` uses uppercase return values (`"CORNERS"`, `"BTTS"`, etc.) while `BotDashboard.tsx:getCategory` uses lowercase (`"corners"`, `"btts"`). `getMarketCategory` will use uppercase. `BotDashboard.tsx` must adapt its UI rendering to uppercase.
