# Tasks: Tennis Model Implementation

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~380 |
| 400-line budget risk | High (size:exception approved) |
| Chained PRs recommended | No (single PR) |
| Delivery strategy | single-pr |
| Decision needed before apply | No |

### Phase 1: Data Structures (~90 lines)

- [ ] 1.1 Add tennis tournaments section to `leagues_global.json` with 8-10 tournament entries
- [ ] 1.2 Add `surface`, `tour`, `sets_won`, `aces`, `double_faults` fields to `Prediction` entity in `entities.py`
- [ ] 1.3 Add tennis-specific fields to `PredictionModel` schema in `schemas/predictions.py` (optional/noptional)
- [ ] 1.4 Update `league_loader.py` `get_by_sport("tennis")` to return tennis tournament data

### Phase 2: Basic Prediction Framework (~130 lines)

- [ ] 2.1 Add `?sport=tennis` filtering confirmed in repo queries (already implemented, verify)
- [ ] 2.2 Add tennis-specific fields to `prediction.py` TypeScript interface
- [ ] 2.3 Add `TennisPredictionDisplay` component framework (basic display, no ML)
- [ ] 2.3 Verify backward compat: soccer predictions sin `?sport=tennis` sin cambios

### Phase 3: Simple ML Model (~170 lines)

- [ ] 3.1 Add `sklearn` dependency (or use existing) for RandomForest
- [ ] 3.2 Implement `generate_tennis_prediction(match_id)` endpoint
- [ ] 3.3 Feature extraction: `first_serve_pct`, `break_points_converted`, `surface_performance`
- [ ] 3.4 Basic training pipeline that uses existing data infrastructure
- [ ] 3.5 Add tennis prediction tests (10-15 tests)

### Dependency Graph

```
Phase 1 (Data Structures)  →  Phase 2 (Basic Framework)  →  Phase 3 (Simple ML Model)
     └──────────────────────┬─────────────────────┘
                           Phase 2 verification
