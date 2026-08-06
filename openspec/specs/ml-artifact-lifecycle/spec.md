# ml-artifact-lifecycle Specification

## Purpose

Governs the lifecycle of ML artifacts produced during training and prediction: worker cache payloads, on-disk model files, and post-run cleanup hooks. Only training results persist in MongoDB; disk artifacts are deleted after posting; disk cache stays small.

## Requirements

### Requirement: Lightweight worker cache after training

After the training step completes, the worker MUST cache only the lightweight training result dict (metrics + `market_stats`, without `match_history` and `team_stats`) in both cache keys (`ml_training_result` and `orchestrator.CACHE_KEY_RESULT`). The full ~120MB training payload MUST NOT be persisted to the disk cache; the per-run `.cache_data` footprint SHOULD remain under 5MB.

#### Scenario: Lightweight payload cached after training

- GIVEN a completed training run with match_history (500 items) and team_stats available
- WHEN `run_daily_orchestrated_job` caches the training result in both keys
- THEN each cache key holds only the lightweight dict also posted to MongoDB
- AND no cache entry contains `match_history` or `team_stats`

#### Scenario: Downstream consumers keep expected fields

- GIVEN a consumer reads `ml_training_result` (e.g. audit_service)
- WHEN the lightweight dict is retrieved
- THEN previously exposed fields (accuracy, roi, profit_units, market_stats, pick_efficiency) remain present

### Requirement: Expanded disk artifact cleanup coverage

`cleanup_model_artifacts` MUST remove `data/*.joblib` (MODEL_FILE_PATH), `output/*.json`, and `tmp/*` files, and MUST clear `.cache_data` via the cache provider's `clear()`. It MUST NOT remove runtime JSON assets — `data/team_logos.json` and `data/team_short_names.json` — which are read at runtime by `team_service`.

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

### Requirement: Post-pipeline and post-run cleanup

The local MLOps pipeline script MUST run `cache.clear()` and `cleanup_model_artifacts()` as the final step after top-picks, and MUST NOT fail the pipeline when nothing is found to clean or cleanup raises. The scheduler SHOULD invoke artifact cleanup after the daily inference run.

#### Scenario: Cleanup as final pipeline step

- GIVEN the pipeline ran top-picks successfully
- WHEN the pipeline reaches its final step
- THEN `cache.clear()` and `cleanup_model_artifacts()` execute
- AND the pipeline exits 0

#### Scenario: Cleanup failure is non-fatal

- GIVEN artifact cleanup raises an exception
- WHEN the pipeline runs the final step
- THEN the pipeline still exits 0 with the failure logged
