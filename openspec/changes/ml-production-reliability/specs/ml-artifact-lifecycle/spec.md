# Delta for ml-artifact-lifecycle

## ADDED Requirements

### Requirement: Serving-artifact preservation across runs

Cleanup and pre-training reset entry points (`cmd_train`, `cmd_cleanup`, `cleanup_model_artifacts`, pipeline final step) MUST NOT destroy the currently-serving model artifact — the versioned target of the serving pointer, or the legacy fixed-key blob when no pointer exists — before a replacement has been successfully promoted. Resetting predictions or transient caches before training is permitted; deleting the serving model first is not. A failed or interrupted run MUST leave the prior artifact intact and loadable.

#### Scenario: Pre-train reset keeps serving model

- GIVEN a training run starts with model V1 serving
- WHEN any data-reset step executes before training completes
- THEN binary_artifacts still contains V1 (or its pointer) and it loads successfully

#### Scenario: Failed run leaves prior model serving

- GIVEN training fails or is interrupted after cleanup ran
- WHEN serving loads the model
- THEN the previous artifact resolves and loads; no silent heuristic-only state occurs without logged degradation

## MODIFIED Requirements

### Requirement: Expanded disk artifact cleanup coverage

`cleanup_model_artifacts` MUST remove `data/*.joblib` (MODEL_FILE_PATH), `output/*.json`, and `tmp/*` files, and MUST clear `.cache_data` via the cache provider's `clear()`. It MUST NOT remove runtime JSON assets — `data/team_logos.json` and `data/team_short_names.json` — which are read at runtime by `team_service`. Cleanup MUST NOT remove an on-disk artifact that currently backs the serving key while it remains the active promoted version; superseded disk artifacts MAY be purged only after their replacement has been successfully promoted.
(Previously: cleanup unconditionally removed all matching joblib/output/tmp/cache targets with no preservation rule for the currently-serving artifact.)

#### Scenario: Joblib model removed from data

- GIVEN `backend/data/ml_picks_classifier.joblib` exists after a training run
- WHEN cleanup executes
- THEN the joblib file is deleted and counted as removed

#### Scenario: Runtime JSON preserved

- GIVEN `data/team_logos.json` and `data/team_short_names.json` exist
- WHEN cleanup executes
- THEN both files remain untouched

#### Scenario: Output and tmp cleaned

- GIVEN `output/baseline_90d.json` and `tmp/benchmark_*.json` exist
- WHEN cleanup executes
- THEN those artifact files are deleted

#### Scenario: Serving artifact survives cleanup before promotion

- GIVEN the disk joblib is the artifact backing the currently-serving key and no successor has been promoted
- WHEN cleanup executes
- THEN that backing artifact is preserved (skipped or deferred), and removal of stale versions happens only post-promotion
