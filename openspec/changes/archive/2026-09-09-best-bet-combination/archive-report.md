# Archive Report — Best Bet Combination

**Change**: best-bet-combination
**Archived**: 2026-09-09
**Artifact Store Mode**: openspec
**SDD Cycle Phase**: archive

---

## Summary of Changes

This change delivered a server-side "ask the model" `POST /api/v1/best-combination` endpoint. It aggregates soccer, tennis, baseball, and basketball pick pools; selects the single best high-confidence leg per sport via a new `CombinationOptimizer`; and returns one 4-leg combination with combined probability/odds/EV, fractional-Kelly stake guidance, and explicit confidence/odds warnings. A unified `UnifiedPick` DTO was added and all four sport services were adapted to emit `sport`, `match_id`, and `odds` on every pick. The frontend added a `/best-combination` page ("Mejor Combinación") with loading/error/empty/data states and neutral, professional Spanish copy.

The change was implemented, verified (PASS), and merged to `main` via **PR #59** (merge commit `acd246a05c241bca5c6890cf6fee2c18df0f3118`).

All 33 implementation tasks were completed and verified. The change is backward compatible — existing per-sport endpoints keep their shapes, and `ParleyService`/`GetParleysUseCase` remain untouched (ADR-5).

---

## Files Modified (Active → Archive)

| Source | Destination | Description |
|--------|-------------|-------------|
| `openspec/changes/best-bet-combination/` | `openspec/changes/archive/2026-09-09-best-bet-combination/` | Entire change folder moved to archive with ISO date prefix via `git mv` (history preserved) |
| `openspec/specs/best-combination/spec.md` | Created | New best-combination specification copied from delta spec (no existing main spec) |
| `openspec/specs/api-client/spec.md` | Merged | ADDED requirement "Best combination endpoint constant and typed client method" merged from delta spec |

---

## Specs Synced (Delta → Main Specs)

| Domain | Action | Details |
|--------|--------|---------|
| best-combination | Created | Full spec copied (no existing main spec) |
| api-client | Updated | One new requirement added: Best combination endpoint constant and typed client method |

> The `archive` rule "Preserve change-scoped operational requirements (do not merge into capability specs)" was reviewed. The best-combination endpoint constant and typed client method are genuine api-client capability requirements, not change-scoped operational notes, so merging them into the main `api-client` spec follows the established repo convention.

---

## Archive Contents

- `proposal.md` ✅ — Change intent, scope, approach (engram #1214)
- `design.md` ✅ — Technical approach, architecture decisions (ADRs), data flow
- `tasks.md` ✅ — 33/33 tasks complete (all checked, 0 unchecked)
  - Phase 1 Prerequisite Refactor — Unified Pick DTO (6 tasks): ✅
  - Phase 2 Backend Core (10 tasks): ✅
  - Phase 3 Backend Tests (4 tasks): ✅
  - Phase 4 Frontend (8 tasks): ✅
  - Phase 5 Quality Gate (5 tasks): ✅
- `verify-report.md` ✅ — Verification report archived, verdict PASS (engram #1219)
- `specs/` ✅ — 2 domain specs (best-combination, api-client)
- `archive-report.md` ✅ — This report (engram #1221)

---

## Verified Archive Confirmations

- [x] Main specs updated correctly (best-combination created; api-client merged)
- [x] Change folder moved to archive (`openspec/changes/archive/2026-09-09-best-bet-combination/`)
- [x] Archive contains all artifacts (proposal, specs, design, tasks, verify-report, archive-report)
- [x] Archived `tasks.md` has no unchecked implementation tasks (33/33 complete)
- [x] Active changes directory no longer has this change
- [x] No `openspec/changes/README.md` index exists — nothing to update

---

## Verification (Verdict PASS)

| Metric | Value |
|--------|-------|
| Verdict | **PASS** |
| Tasks complete | 33/33 |
| Backend tests (`pytest tests/`) | **297 passed** |
| Frontend tests (`vitest`) | **82 passed** |
| Type-check | `tsc` clean |
| Lint | `ruff`/`black`/`isort`/`mypy` clean (backend), `eslint` 0 errors (frontend) |
| Spec compliance | 18/18 scenarios compliant |
| CRITICAL issues | None |
| API smoke | 200 (real 4-leg combo) / 409 (insufficient_pool, no_positive_ev) / 422 (invalid filters) contract-correct |

The verify-report on disk is the canonical-template version (rewritten during pass 2; the canonical file was brought onto `main` from `feat/best-bet-combination` before archiving, since the branch contained the final canonical report that was not part of PR #59's merge).

---

## Merge Reference

- **PR**: #59 — https://github.com/jhorman10/BJJ-BetSports/pull/59
- **Merge commit**: `acd246a05c241bca5c6890cf6fee2c18df0f3118` (on `main`)
- **Branch**: `feat/best-bet-combination` (deleted on remote after merge; local copy retained the 5 canonical verify-report commits, which were reconciled onto `main` before this archive)

---

## Follow-Ups

1. **S-1 (from verify-report)** — Add dedicated per-service unit tests asserting soccer/tennis/baseball/basketball services emit `sport`/`match_id`/`odds` on their market dicts. Currently covered by live smoke + static evidence; dedicated unit tests should close this gap.

---

## SDD Cycle Status

**Complete**: The change has been fully planned (proposal #1214), specified (spec #1215), designed (design), tasked (tasks #1217), implemented (apply #1218), verified (verify #1219, PASS), and archived (this report).

**Ready for next change**: The SDD cycle is complete. The change is archived in `openspec/changes/archive/2026-09-09-best-bet-combination/`. The source-of-truth specs have been updated. Ready for the next change.

---

## Engram Traceability

| Artifact | Engram Observation ID |
|----------|-----------------------|
| Explore | #1211 |
| Proposal | #1214 |
| Spec | #1215 |
| Tasks | #1217 |
| Apply progress | #1218 |
| Verify report | #1219 |
| Archive report | #1221 |
