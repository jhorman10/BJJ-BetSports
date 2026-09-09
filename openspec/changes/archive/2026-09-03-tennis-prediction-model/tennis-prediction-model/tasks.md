# Tasks: Tennis Prediction Model

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~130 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |
| Decision needed before apply | No |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Add tennis-specific schema fields to PredictionModel | Single PR | Tennis fields only, backward compat |
| 2 | Update domain Prediction entity for tennis | Single PR | Entity updates with tennis fields |
| 3 | Update frontend prediction types for tennis | Single PR | TypeScript type updates |
| 4 | Ensure endpoint sport filtering & backward compat | Single PR | Verify ?sport=tennis and default soccer |

## Phase 1: Schema Updates (~40 lines)

- [x] 1.1 Add `set_over_under_probabilities` field to `PredictionModel` in
      `backend/src/api/schemas/predictions.py`: `list[dict]` with per-set
      over/under probabilities (e.g., `{"set": 1, "over_probability": 0.55}`)
- [x] 1.2 Add `game_probabilities` field to `PredictionModel` in
      `backend/src/api/schemas/predictions.py`: `list[dict]` with per-game win
      probabilities
- [x] 1.3 Keep existing `draw_probability` field for soccer backward compatibility
- [x] 1.4 Add `tennis_specific` discriminant or conditional logic note: when
      `sport=tennis`, `draw_probability` should be omitted/ignored by consumers

## Phase 2: Domain Entity Updates (~40 lines)

- [x] 2.1 Add `set_over_under_probabilities` and `game_probabilities` fields to
      `Prediction` entity in `backend/src/domain/entities/entities.py`
- [x] 2.2 Keep existing `draw_probability` for soccer backward compatibility
- [x] 2.3 Add `tennis_sports_mark` or similar marker field to distinguish tennis
      predictions in serialization (optional, for future model training phase)

## Phase 3: Frontend Type Updates (~30 lines)

- [x] 3.1 Add `setOverUnderProbabilities?: SetOverUnderProbability[]` and
      `gameProbabilities?: GameProbability[]` to `Prediction` interface in
      `frontend/src/domain/entities/prediction.ts`
- [x] 3.2 Keep existing `drawProbability` for backward compatibility
- [x] 3.3 Ensure types compile without errors

## Phase 4: Endpoint Sport Filtering & Verification (~20 lines)

- [x] 4.1 Verify `/api/v1/predictions/league/{league_id}?sport=tennis` returns only
      tennis predictions, defaults to soccer when no sport param
- [x] 4.2 Verify `/api/v1/predictions/match/{match_id}` properly reads document`sport`
      field and defaults to soccer (`DEFAULT_SPORT = "soccer"`) when absent
- [x] 4.3 Run type check: `poetry run mypy` (or equivalent) to ensure no type
      errors across schema, entity, and frontend type changes
- [x] 4.4 Manual verification: test that existing soccer predictions are unchanged
      when calling endpoints without `?sport=tennis`

## Dependency Graph

```
Phase 1 (Schema)  →  Phase 2 (Domain Entity)  →  Phase 3 (Frontend Types)
     └─────────────────────┬─────────────────────┘
                            Phase 4 (Endpoint Verification)
```

All tasks fit within a single PR with ~130 total changed lines, well under the
400-line budget. No chained PRs needed — this is plumbing-only (endpoints + types
+ API filter), follow-on: tennis model training + data sources.

### Review Workload Forecast (plain-text guard lines)

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low