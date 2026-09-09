# Proposal: ML Production Reliability (Training + Prediction)

## Intent

The event training+prediction subsystem is not production-safe: a failed training run deletes the serving model first (silent heuristic fallback), models ship with zero out-of-sample evaluation and inflated in-sample metrics (hardcoded 2.0/win ROI), and unversioned pickles load with version warnings suppressed. This change makes deployment atomic, evaluated, honest, and observable.

## Scope

### In Scope
- Atomic versioned artifact deployment: store candidates under versioned keys (`binary_artifacts/ml_picks_classifier/<version>`), promote via pointer-document swap; never delete the serving model before a successor is promoted.
- Evaluation gate before promotion: chronological holdout; log loss + Brier vs always-favorite baseline; fail → keep previous model.
- Artifact metadata (`sklearn_version`, `feature_schema_hash`, `git_sha`, `trained_at`); loud failure on load-time mismatch (no silent fallback).
- Honest metrics persisted to `training_results` (out-of-sample; remove hardcoded daily ROI).
- CI installs `requirements-worker.txt` so sklearn paths are tested.
- Class alignment via `model.classes_`; remove bare `except: pass` in ensemble blend.
- Structured log/metric when serving falls back to heuristics.

### Out of Scope (Non-goals)
- Unifying the two divergent training pipelines.
- Drift monitoring infra; external experiment tracking (MLflow/W&B/DVC).
- Retraining orchestration/scheduling changes; Render `API_ONLY_MODE` changes.
- Frontend/dashboard work beyond existing surfaces.
- **Leakage remediation** (expanding-window league averages; forbidding forecast-cache reuse as training rows): deferred to follow-up change `ml-training-data-integrity`. Rationale: the new eval gate converts leakage from silent corruption into measurable holdout degradation; bundling both risks blowing the 800-line single-PR budget. It is the designated first follow-up.
- EV math on calibrated probabilities (`prediction_service.py:1583-1592`).

## Capabilities

> Contract for sdd-spec.

### New Capabilities
- `ml-model-deployment`: versioned artifact storage, pointer-based atomic promotion, metadata binding, loud load-time validation, serving-fallback observability.
- `ml-evaluation-gate`: pre-promotion chronological holdout evaluation, baseline comparison, promote-or-keep decision, honest metric persistence.

### Modified Capabilities
- `ml-artifact-lifecycle`: cleanup MUST NOT destroy the currently-serving model artifact before promotion of a replacement; disk/cache cleanup requirements unchanged otherwise.

## Approach

Trainer evaluates on a time-ordered holdout before saving; passing candidates are written under a versioned key with metadata, then promoted by atomically swapping a pointer document (Mongo `find_and_modify`). Loader resolves pointer, validates metadata (sklearn/schema), fails loudly on mismatch. Legacy fixed-key blob accepted read-only during transition with deprecation warning.

## Affected Areas

| Area | Impact |
|---|---|
| `backend/src/application/services/ml_training_orchestrator.py` | Modified — eval gate, versioned save, honest metrics |
| `backend/scripts/orchestrator_cli.py` | Modified — non-destructive cleanup order, unsuppressed warning, inject git SHA |
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modified — versioned keys + pointer swap, legacy read path |
| `backend/src/domain/services/picks_service.py`, `prediction_service.py`; application `use_cases.py` | Modified — validated load, `classes_` alignment, no bare excepts, fallback logging |
| `.github/workflows/ci.yml` | Modified — install worker requirements |

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Gate blocks promotion initially (weak model exposed) | Intended: heuristics continue, now visible; tune thresholds after first runs |
| Holdout shrinks training data slightly | Acceptable; split sizing deferred to design |
| Legacy blobs lack metadata | Transitional read-only acceptance + warning |
| 800-line budget tight (~750 est.) | Descope ladder: fallback tracking → log-only; trim metadata fields |

## Rollback Plan

Revert PR. Runtime rollback: repoint artifact pointer to previous version (or restore legacy fixed-key blob); loader stays backward-compatible with pre-change artifacts.

## Success Criteria

- [ ] Simulated failed/interrupted training leaves prior model serving (test-proven).
- [ ] No artifact promoted without passing log loss + Brier vs favorite baseline on chronological holdout; failure keeps prior model.
- [ ] Promoted artifacts carry full metadata; mismatch → loud failure, not silent heuristic.
- [ ] `training_results` shows out-of-sample metrics; hardcoded ROI removed.
- [ ] CI installs sklearn deps; suite green: `.venv/bin/pytest tests/ -q`.
- [ ] Heuristic fallback emits distinguishable structured log.
- [ ] Total diff ≤ 800 changed lines.
