# Design: ML Production Reliability

## Technical Approach

Versioned artifacts live in the existing `binary_artifacts` collection; the serving pointer is a document in the existing `app_state` collection. The evaluation gate is a pure-function module invoked by the orchestrator between model fit and persistence. Loaders validate a metadata envelope before use and map probabilities through `model.classes_`. No new infrastructure — reuses pymongo atomic single-document semantics.

## Architecture Decisions

### D1: Artifact key layout, pointer shape, atomicity, retention

**Choice**: Version keys `models/picks_classifier/<UTC-compact>-<sha8>` (e.g. `models/picks_classifier/20260821T141530Z-a1b2c3d4`), written insert-once, never overwritten. Serving pointer = `app_state` doc:

```json
{"key": "ml_picks_classifier/serving",
 "data": {"artifact_key": "models/picks_classifier/...",
          "version": "20260821T141530Z-a1b2c3d4",
          "promoted_at": "...", 
          "metrics": {"log_loss": 0.0, "brier": 0.0, "n_holdout": 0}}}
```

Swap via new `MongoRepository.promote_serving_pointer(...)` using `find_one_and_update(..., upsert=True)` — exactly one atomic document update; readers resolving via `get_app_state` always observe complete old or new state.
**Alternatives**: dedicated collection (more code); overwrite-in-place (non-atomic, rejected by spec).
**Rationale**: reuses existing collections/accessors; find-and-modify pins atomicity per spec.
**Retention**: keep last N=3 versions; prune older keys post-promotion (best-effort, never pointer target or legacy blob).

### D2: Metadata envelope schema + validation-on-load

Stored in the SAME document as bytes: `meta{sklearn_version, feature_schema_hash, git_sha, trained_at, metrics{log_loss,brier,n_holdout}, legacy:false}`.
Validation on load: `sklearn.__version__` equality check; `feature_schema_hash == sha256(MLFeatureExtractor.schema_signature())[:16]` (new deterministic classmethod). Mismatch → structured error log naming stored vs runtime values, fallback reason set — no silent path. `git_sha` injected by CLI (`git rev-parse --short HEAD`, default `"unknown"`).

### D3: Evaluation gate placement & mechanics

New module `backend/src/application/services/ml_evaluation_gate.py`:
- `chronological_split(sample_dates, ratio=0.2)` → train/holdout index pairs, holdout strictly later dates.
- `run_gate(model, X_holdout, y_holdout, baseline_probs) -> GateReport(passed, log_loss, brier, baseline_log_loss, baseline_brier, reason)`.
- Metrics: sklearn `log_loss`; multiclass Brier = mean over holdout of Σ_classes (p−y)². Baseline = odds-implied normalized probabilities per holdout match (uniform 1/3 when odds absent). PASS iff strictly better on BOTH metrics; `n_holdout < 30` → FAIL("insufficient_data").

Wiring: `prepare_datasets` additionally returns parallel `sample_meta[{date, odds_triple}]` (one entry per feature row). Orchestrator splits BEFORE fit, fits on train indices only, gates on holdout, saves+promotes only on PASS. GateReport persists to `training_results` regardless of outcome; FAIL leaves pointer untouched.

### D4: Legacy blob transition policy

Loader resolution order: pointer → versioned bytes (validated). If no pointer: legacy fixed key `ml_picks_classifier.joblib` loads read-only with deprecation warning; metadata validation skipped (no envelope exists). First gated PASS promotes V1 under a versioned key and swaps pointer; legacy blob never written again by this system. `orchestrator_cli.py` removes the sklearn/InconsistentVersionWarning suppression (L34–36) so version drift on legacy blobs surfaces visibly.

### D5: Class alignment via classes_

Both blend sites (`prediction_service.py` ensemble L1503–1507, `picks_service._apply_ml_refinement` L928–947) build `label→prob` from `dict(zip(model.classes_, proba))` using outcome-label constants instead of positional indices. Bare `except: pass` at prediction_service L1525–1527 replaced with logged handler (Poisson-only continues, context logged). Audit `use_cases.py` batch path (L395–415) for the same assumption during apply.

### D6: Heuristic-fallback observability (minimal)

PicksService exposes `serving_mode ∈ {ml, heuristic}` + `fallback_reason ∈ {load_failed, version_mismatch, schema_mismatch, absent, blend_failed}` plus an in-memory counter. Every mode transition logs `[ML_FALLBACK] reason=...`. use_cases copies mode+reason into existing response payload. No metrics stack, no new storage.

### D7: CI parity exact change

`.github/workflows/ci.yml` backend-tests job: install step becomes `python -m pip install -r requirements.txt -r requirements-worker.txt`; `cache-dependency-path` gains `backend/requirements-worker.txt`. Lint/types job unchanged (`--ignore-missing-imports` already absorbs absent sklearn there).

### D8: Descope ladder if >800 lines during apply

1. Drop retention pruning (versions accumulate; manual cleanup acceptable).
2. Fallback marker = log-only + counter (skip new response field reuse if costly).
3. Simplify baseline to uniform-favorite probabilities.
Never descoped: gate, pointer swap, envelope fields, CI parity, classes_ alignment (all spec-mandated).

### D9: Rollback plan

Revert PR. Runtime rollback without deploy: one `find_one_and_update` repoints the serving pointer to the prior version. Legacy read path keeps pre-change blobs loadable, so pre-change artifacts remain valid.

## Data Flow

```
Trainer: prepare_datasets(+sample_meta) → split → fit(train) → run_gate(holdout)
         → PASS? save versioned bytes+meta → find_one_and_update pointer
         → FAIL/GATE ERROR → persist GateReport, keep prior serving
Serving: pointer lookup → fetch versioned bytes → validate envelope
         → blend via classes_ | any failure → [ML_FALLBACK] marker + heuristics
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/application/services/ml_evaluation_gate.py` | Create | split, metrics, GateReport |
| `backend/src/application/services/ml_training_orchestrator.py` | Modify | gate wiring, sample_meta, versioned save+promote, honest TrainingResult fields |
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modify | versioned save/get w/ meta, promote_serving_pointer (find_and_modify), clear_all_data preserves artifacts + pointer |
| `backend/scripts/orchestrator_cli.py` | Modify | drop warning suppression, non-destructive cleanup order, inject git_sha |
| `backend/src/domain/services/ml_feature_extractor.py` | Modify | schema_signature() classmethod |
| `backend/src/domain/services/picks_service.py` | Modify | pointer-aware validated load, classes_ refinement, serving_mode |
| `backend/src/domain/services/prediction_service.py` | Modify | classes_ blend, remove bare except |
| `backend/src/application/use_cases/use_cases.py` | Modify | response mode/reason marker; audit batch predict |
| `.github/workflows/ci.yml` | Modify | worker requirements install |

## Interfaces / Contracts

```python
@dataclass
class GateReport:
    passed: bool; log_loss: float; brier: float
    baseline_log_loss: float; baseline_brier: float
    n_holdout: int; reason: str

# MongoRepository additions
def save_binary_artifact_versioned(key: str, version: str, data: bytes,
                                   meta: dict) -> None  # insert-once
def promote_serving_pointer(pointer_key: str, artifact_key: str,
                            version: str, metrics: dict) -> dict  # find_and_modify
def list_versions(key_prefix: str) -> list[str]
def delete_binary_artifact(key: str) -> None  # pruning only
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | split chronology invariant; log loss/Brier vs hand-computed; gate pass/fail/tie logic; envelope validation failures; classes_ permutation mapping; legacy warning | pytest, fake repo fixtures |
| Integration | failed training keeps prior model loadable; promotion swaps pointer atomically (fake repo asserting old-or-new reads); clear_all_data preserves pointer+artifacts | pytest, stubbed MongoRepository |
| E2E | full pipeline smoke: train→gate→promote→load roundtrip; suite green `.venv/bin/pytest tests/ -q` | backend test suite |

## Migration / Rollout

Single PR; no data migration. Existing prod blob covered by legacy acceptance until first gated promotion creates the pointer. Rollback per D9.

## Open Questions

- Does the async adapter (`async_mongo_adapter.py`) need a mirrored promote method for API-triggered training? Serving loads sync today — verify call sites at apply.
- Exact location of hardcoded per-win ROI constant (apply-time grep; replaced with payout-derived value or omitted/null-flagged per spec).
