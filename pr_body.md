## Summary
Production reliability for the event training + prediction ML subsystem.

## Changes
- **Atomic versioned artifacts**: `models/picks_classifier/<ts>-<sha8>` saved under fresh key, promoted via `find_one_and_update` pointer swap in `app_state`; `clear_all_data` never deletes serving artifact before promotion.
- **Gated evaluation**: chronological holdout (last 20%), log loss + multiclass Brier vs odds-implied always-favorite baseline; FAIL preserves prior model + persists GateReport.
- **Metadata envelope**: sklearn_version, feature_schema_hash, git_sha, trained_at, metrics; loud load-time validation on mismatch.
- **classes_ alignment**: `outcome_probability_map` / `positive_class_probability` in ensemble (PredictionService) + refinement (PicksService); no bare `except: pass`.
- **Fallback observability**: `serving_mode` / `fallback_reason` markers + `[ML_FALLBACK]` structured logs on every heuristic transition.
- **CI parity**: both `ci.yml` and `ci-pr.yml` install `requirements-worker.txt` so sklearn paths execute.
- **CLI fixes**: removed sklearn warning suppression, fixed cleanup order, injected `git_sha`.
- **Tests**: 4 new suites (gate, repo lifecycle, serving validation, deployment integration) + existing suite green (160 passed).

## Non-goals
- Leakage fix (expanding-window averages) → follow-up `ml-training-data-integrity`.
- Pipeline unification, drift monitoring, external experiment tracking.

## Size
~1675 changed lines (impl ~727 + new modules/tests ~948). Exceeds 800-line budget → `size:exception` granted.

## Verification
- 160 backend tests pass
- 60 frontend tests pass
- Ruff clean, Black formatted, imports sorted

Closes ml-production-reliability