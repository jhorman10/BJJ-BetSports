# Proposal: Best Bet Combination

## Intent

User wants to "ask the model" which single bet combination is most likely to win. Deliver one recommended 4-leg combination — one high-confidence pick per sport (soccer, tennis, baseball, basketball) — computed server-side, surfaced via a new interface. Follows exploration Option A: backend optimizer endpoint + thin frontend, reusing `KellySizer`/`RiskManager`/continuous-learning confidence.

## Scope

### In Scope
- Unified pick DTO with `sport` + `match_id` back-reference (prerequisite: tennis/baseball/basketball `markets[]` lack both)
- `POST /api/v1/best-combination`: best high-confidence pick per sport, aggregated
- Single-combination optimizer reusing `KellySizer` / `RiskManager.apply_portfolio_constraints` / `continuous_learning`
- Frontend "ask the model" page + nav entry + API client method
- pytest + vitest coverage; Spanish UI copy (neutral/professional); artifacts stay in English

### Out of Scope
- Ranked list / portfolio of combinations
- Variable combination size (fixed 4 legs)
- Correlation modeling (deferred, YAGNI)
- User accounts / bankroll tracking

## Capabilities

> Contract for sdd-spec. Research source: `openspec/specs/`.

### New Capabilities
- `best-combination`: backend endpoint, optimizer, unified pick aggregation, frontend interface

### Modified Capabilities
- `api-client`: add best-combination endpoint path in `API_ENDPOINTS` + API method

## Approach

Exploration Option A. New `BestCombinationUseCase` → `CombinationOptimizer` domain service reusing `KellySizer.kelly_with_confidence`, `RiskManager.apply_portfolio_constraints`, and continuous-learning confidence. Generalize and wire existing `ParleyService`/`GetParleysUseCase` (currently unwired). Optimizer takes best high-confidence pick per sport; combination probability = product of legs (independence assumption, documented upper bound); fair-odds fallback `1/p` when real odds missing. Frontend: `BestCombination/` page + nav entry; renders 4 legs, total odds/probability, stake recommendation, per-leg confidence warnings.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/api/routers/best_combination.py` | New | Endpoint |
| `backend/src/application/use_cases/best_combination_use_case.py` | New | Orchestration |
| `backend/src/domain/services/combination_optimizer.py` | New | Optimizer |
| `backend/src/domain/entities/suggested_pick.py` + per-sport routers | Modified | Add `sport`/`match_id`; emit unified picks |
| `parley_service.py` / `get_parleys_use_case.py` | Modified | Generalize to 4 sports, wire to router |
| `frontend`: `BestCombination/`, `constants.ts`, `api.ts`, `MainLayout.tsx` | New/Modified | UI + endpoint |

## Business Rules & Edge Cases

- **No high-confidence pick in a sport**: include that sport's best available pick with explicit confidence warning. Keeps the fixed 4-leg scope (all 4 sports required); transparency over silent quality drop.
- **Missing real odds**: fair-odds fallback `1/p` per leg; response flags `odds_source: market|fair`; UI shows warning.
- **Combination probability**: product of legs assuming independence — documented upper bound.
- **Stake sizing**: Kelly on combined probability vs bookmaker combined odds, capped by existing `max_stake_pct` / daily exposure.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Independence assumption overstates probability | Med | Document upper bound; cap stakes; RiskManager per-league exposure |
| Missing real odds degrades EV | Med | Fair-odds fallback + `odds_source` flag |
| Shape mismatch blocks aggregation | High | Unified DTO in scope (prerequisite) |
| `ParleyService` unwired | Med | Wire/replace within this change |

## Rollback Plan

Remove endpoint, frontend page, and nav entry. DTO field additions stay (additive, backward compatible). No destructive migration; frontend degrades gracefully if endpoint absent.

## Dependencies

- Existing per-sport pick generation; no new data sources or services.

## Success Criteria

- [ ] Endpoint returns exactly one combination: 4 legs, one per sport, all high-confidence or confidence-flagged
- [ ] Frontend renders combination with odds/probability, stake, warnings
- [ ] pytest + vitest pass