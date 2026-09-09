# Design: Best Bet Combination

## Technical Approach

Hexagonal: new `POST /api/v1/best-combination` router → `BestCombinationUseCase` → `CombinationOptimizer` reusing `KellySizer`, `RiskManager`, `ContinuousLearning`. Prerequisite refactor unifies the 4 sports' pick shapes into `UnifiedPick` (sport + match_id). `ParleyService`/`GetParleysUseCase` are football-only + unwired; **not** reused (ADR-5), left untouched.

## Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **ADR-1 "Best" objective** | **Max EV** (ties→probability) | EV joins edge + stake value; per spec |
| **ADR-2 Neg-EV + forced 4-leg** | **409 `no_positive_ev`** | Enforce spec on forced-4-leg result |
| **ADR-3 Mixed-odds rule** | **Confirm spec**: product market odds only if ALL 4 legs market; else `1/total_p` | Fair legs un-hedgeable; flag for verify |
| **ADR-4 Shape unification** | **New `UnifiedPick` + per-sport adapter** in optimizer | Additive; avoids invasive cross-sport edits |
| **ADR-5 ParleyService** | **New `CombinationOptimizer`**; leave ParleyService | ParleyService football-typed (`MatchPrediction`); generalization too heavy for v1 |
| **ADR-6 Response DTO shape (ACCEPTED DEVIATION from spec table)** | `stake` object (`risk_level`, `suggested_stake_pct`, `kelly_fraction`) separate from `aggregate`; `independence_disclaimer` at top level | Stake sizing is a distinct concern from combined probability/odds/EV metrics; top-level disclaimer mirrors `warnings`/`generated_at` placement and is easier for clients to consume. This shape is what the live API returns, the frontend mirrors it field-for-field, and it is deliberately NOT relocated into `aggregate`. |

## Data Flow

```
POST /api/v1/best-combination  (min_probability?, exclude_leagues?)
   │  router (422 on bad filters)
   ▼
BestCombinationUseCase.execute  → fetch per-sport upcoming picks
   ▼
CombinationOptimizer.aggregate_pools → [UnifiedPick] (sport+match_id; drop missing)
   ▼
build_combination → per sport: high-conf pool → best (priority_score, probability)
   │  empty pool → best available + confidence_warning
   ▼
compute_totals: total_p=Πp; total_odds=Πodds(all market) else 1/total_p; EV=total_p*total_odds−1
   ▼   EV<0 → 409 no_positive_ev
KellySizer + RiskManager cap → suggested_stake_pct, risk_level
   ▼
BestCombinationResponse  (legs[] + aggregate + independence_disclaimer)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/domain/entities/unified_pick.py` | Create | Immutable `UnifiedPick` dataclass (sport, match_id, labels, probability, odds, confidence, is_recommended, quality flags) |
| `backend/src/domain/services/combination_optimizer.py` | Create | Pool aggregation + single-best selection + totals/EV math + fallbacks |
| `backend/src/application/use_cases/best_combination_use_case.py` | Create | Orchestration: fetch per-sport, delegate to optimizer, size stake |
| `backend/src/api/dtos/best_combination_dtos.py` | Create | Pydantic v2 request/response DTOs |
| `backend/src/api/routers/best_combination.py` | Create | Router registering `POST /api/v1/best-combination` |
| `backend/src/api/main.py` | Modify | `include_router(best_combination_router)` |
| `backend/src/dependencies.py` | Modify | Provide `KellySizer`, `RiskManager`, `CombinationOptimizer` deps if needed |
| `backend/src/domain/services/kelly_sizer.py` | Modify (minor) | Add `apply_combined_kelly(total_p, total_odds)` if not already covered |
| `frontend/src/types/bestCombination.ts` | Create | `BestCombinationRequest/Leg/Response` mirroring backend DTO |
| `frontend/src/config/constants.ts` | Modify | Add `BEST_COMBINATION` endpoint |
| `frontend/src/services/api.ts` | Modify | Add `getBestCombination()` |
| `frontend/src/presentation/components/BestCombination/BestCombinationPage.tsx` | Create | Page: loading/error/empty states, 4 legs, aggregate, warnings |
| `frontend/src/presentation/components/Layout/MainLayout.tsx` | Modify | Add nav entry `/best-combination` ("Mejor Combinación") |
| `frontend/src/App.tsx` | Modify | Add `/best-combination` route |

## Interfaces / Contracts

```python
@dataclass(frozen=True)
class UnifiedPick:
    sport: str; match_id: str; match_label: str; pick_label: str
    probability: float; confidence_level: str
    odds: float                    # 0.0 → fair fallback 1/p
    is_recommended: bool; priority_score: float; is_ml_confirmed: bool = False

class BestCombinationRequest(BaseModel):      # pydantic v2
    min_probability: float | None = Field(None, gt=0, lt=1)
    exclude_leagues: list[str] = []

class BestCombinationLeg(BaseModel):
    sport; match_id; match_label; pick_label; probability; odds: float
    odds_source: Literal["market", "fair"]
    confidence_level: str; is_recommended: bool
    confidence_warning: bool = False; odds_warning: bool = False

class BestCombinationAggregate(BaseModel):
    total_probability; total_odds; expected_value; mixed_odds: bool

class BestCombinationStake(BaseModel):
    suggested_stake_pct: float; risk_level: int; kelly_fraction: float

class BestCombinationResponse(BaseModel):
    legs: list[BestCombinationLeg]    # exactly 4
    aggregate: BestCombinationAggregate
    stake: BestCombinationStake
    generated_at: str
    independence_disclaimer: str
    warnings: list[str]
```

Frontend `BestCombinationLeg`/`BestCombinationResponse` mirror these field-for-field.

> **ADR-6 note:** The spec response table originally placed `risk_level`,
> `suggested_stake_pct`, and `independence_disclaimer` inside `aggregate`. The
> implemented DTO (above) is an **accepted deviation**: stake sizing lives in a
> dedicated `stake` object and the disclaimer is top-level. The frontend types
> mirror this shape. Do not relocate the fields; the verify finding C-1 was
> resolved by documenting the deviation, not by refactoring the DTO.

## Algorithm (per sport)

1. **Build pool**: translate every pick to `UnifiedPick`; drop any lacking `sport`/`match_id`.
2. **Quality filter** (unless pool empty): soccer → `is_ml_confirmed`/`is_ia_confirmed`; others → `confidence_level=="high"` + `is_recommended`. Apply `min_probability`/`exclude_leagues`. `min_probability` thresholds ONLY this quality pool (ADR-6 relaxation, see W-3).
3. **Select leg**: highest `priority_score`; tie-break highest `probability`.
4. **Fallback** (empty pool): best available pick, `confidence_warning=true`, `is_recommended=false`. The fallback pool is NOT `min_probability`-filtered — coverage policy keeps the 4-leg scope, so a fallback leg MAY have probability below the requested threshold and always carries `confidence_warning: true`.
5. **Odds**: `market` if `odds>1.0` else fair `1/p` (`odds_source=fair`, `odds_warning=true`).
6. **Aggregate**: `total_p=Πp`; `total_odds` = product market odds only if all 4 legs `market`, else `1/total_p` (+ aggregate `odds_warning`). `EV=total_p*total_odds−1`.
7. **Neg EV** → 409 `no_positive_ev`.
8. **Stake**: fractional Kelly capped by `RiskManager` (`MAX_SINGLE_STAKE=0.05`, `MAX_DAILY_EXPOSURE=0.05`, and `MAX_LEAGUE_EXPOSURE=0.03` when the legs expose league info; single/daily caps apply when league is absent). `risk_level` from stake magnitude.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `CombinationOptimizer`: pooling, quality filter, fallback, odds/EV math | pytest — feed raw sport picks, assert unified/selected/totals |
| Unit | Use case: EV<0 → `no_positive_ev`; empty sport → `insufficient_pool`; all empty → `no_picks_available` | pytest with mocked per-sport fetch |
| Unit | Kelly/stake cap via RiskManager | pytest |
| Integration | Full request through router → 200/409/422 | FastAPI `TestClient` + seeded sport services |
| Frontend | `getBestCombination` posts correct body/endpoint; page renders loading/error/empty/data states | vitest (+MSW) |

## Migration / Rollout

No data migration. Backward-compatible additive change. Frontend degrades gracefully if endpoint absent (404 → error state). Rollback = remove route + nav entry + page.

## Open Questions

- [ ] Whether soccer's "quality" gate should use `is_ml_confirmed` **or** `is_ia_confirmed` alone, or either — spec says either; confirm preferred semantics.
- [ ] Confirm ADR-3 mixed-odds rule is acceptable (fair legs force `total_odds=1/total_p`, which drags EV toward ~0). Flag for verify.
