# Tasks: ML Production Reliability (Training + Prediction)

Single PR target (`single-pr-default`). Budget: 800 changed lines. All verification via `.venv/bin/pytest tests/ -q` from `backend/`. Descope ladder (design D8) armed: drop retention pruning → log-only fallback marker → uniform baseline. NEVER descoped: gate, pointer swap, metadata envelope, CI parity, `classes_` alignment.

## Suggested Work Units

| Unit | Goal | Est. lines |
|------|------|-----------|
| U1 | Repo layer: versioned artifacts + atomic pointer + safe cleanup | ~135 |
| U2 | Eval gate module + orchestrator wiring + honest metrics | ~245 |
| U3 | Serving path: validated load, `classes_` blend, fallback markers | ~165 |
| U4 | CLI fixes + CI parity | ~43 |
| U5 | Tests (unit + integration) | ~340 |
| Total | ≈810 raw → ~760 after D8 trims | fits 800 single-PR budget |

## Phase 1 — Repository Layer

- [x] **1.1** Versioned artifact save/get — `backend/src/infrastructure/repositories/mongo_repository.py` (extend near L385–400). Add `save_binary_artifact_versioned(key, version, data, meta)` (insert-once, rejects duplicate version, bytes+meta in one doc) and `get_versioned_artifact(key, version) -> (bytes, meta|None)`. AC: fresh unique key per run; previously promoted version byte-identical afterwards (spec ml-model-deployment: "Candidate saved under fresh version key"); envelope carries sklearn_version/git_sha/trained_at/metrics ("Promoted artifact carries full metadata"). Verify: 6.2. Deps: none. (~55 ln)
- [x] **1.2** Atomic promotion — same file. Add `promote_serving_pointer(pointer_key="ml_picks_classifier/serving", artifact_key, version, metrics) -> dict` using `find_one_and_update(..., upsert=True)` writing D1 pointer shape `{artifact_key, version, promoted_at, metrics}`. AC: exactly one atomic document update; readers via `get_app_state` observe complete old-or-new, never partial/null ("Promotion swaps pointer atomically", "Reader never sees missing artifact during swap"). Verify: 6.2 fake-repo old/new assertion. Deps: none. (~30 ln)
- [x] **1.3** Non-destructive `clear_all_data` — same file L355. Reorder: transient cache/prediction reset may run first, but MUST NOT delete the pointer-target artifact or legacy blob `ml_picks_classifier.joblib`; preserve the serving pointer doc in `app_state`; only superseded versions deletable. AC: ml-artifact-lifecycle "Pre-train reset keeps serving model", "Failed run leaves prior model serving"; ml-model-deployment "Serving-artifact preservation before promotion". Verify: 6.2. Deps: none. (~25 ln)
- [x] **1.4** Retention helpers — same file. Add `list_versions(key_prefix)` + `delete_binary_artifact(key)`; prune oldest beyond N=3 post-promotion, never pointer target or legacy key (D1). Verify: 6.2. Deps: 1.2. NOTE: first D8 descope item — drop entirely if over budget. (~20 ln)
- [x] **1.5** Audit `async_mongo_repository.py` L451–491 for mirrored versioned/pointer methods needed by API-triggered training call sites (design open question); implement mirror only if an active call site exists, else record finding in apply-progress. Verify: grep call sites. Deps: 1.1–1.2. (~0–30 ln) FINDING: no async training call site — scheduler.py + audit_service.py use sync MongoRepository via get_ml_training_orchestrator(); no mirror implemented.

## Phase 2 — Evaluation Gate + Orchestrator Wiring

- [x] **2.1** Create `backend/src/application/services/ml_evaluation_gate.py`: `GateReport(passed, log_loss, brier, baseline_log_loss, baseline_brier, n_holdout, reason)`; `chronological_split(sample_dates, ratio=0.2)` (holdout strictly later dates); `run_gate(model, X_holdout, y_holdout, baseline_probs)` — sklearn `log_loss` + multiclass Brier = mean Σ_classes(p−y)²; PASS iff strictly better on BOTH vs odds-implied normalized always-favorite baseline (uniform 1/3 when odds absent); `n_holdout < 30 → FAIL("insufficient_data")`. AC: ml-evaluation-gate "Holdout respects event chronology", "Both metrics computed out-of-time", "Candidate beats baseline promotes", "Candidate worse than baseline blocked". Verify: 6.1. Deps: none. (~90 ln)
- [x] **2.2** Add `MLFeatureExtractor.schema_signature()` deterministic classmethod (`sha256(...)[:16]`) — `backend/src/domain/services/ml_feature_extractor.py`. AC: stable across runs; changes iff feature schema changes; feeds envelope hash + load validation ("Feature schema mismatch fails loudly"). Verify: 6.3. Deps: none. (~15 ln)
- [x] **2.3** Wire gate into `backend/src/application/services/ml_training_orchestrator.py`: extend `prepare_datasets` (L484) to also return parallel `sample_meta[{date, odds_triple}]`; split BEFORE fit via `chronological_split`; fit on train indices only; `run_gate` on holdout; on PASS → `save_binary_artifact_versioned` + `promote_serving_pointer` (meta incl. git_sha, trained_at, gate metrics); on FAIL/ERROR → persist GateReport to `training_results`, pointer untouched. AC: "Holdout evaluated before save/promote", "Failed gate preserves serving state", "Failure reason persisted". Verify: 6.4 + full suite. Deps: 1.1, 1.2, 2.1, 2.2. (~90 ln)
- [x] **2.4** Honest metrics — same file: remove hardcoded `return += 2.0` (L303); derive daily ROI from resolved payout odds; persist accuracy/log-loss with separate in-sample vs out-of-time labels; omit/null-flag uncomputable daily ROI. AC: "Metrics separated by sample origin", "Daily ROI uses real payouts", "Unresolvable metric not fabricated". Verify: 6.4. Deps: 2.3. (~50 ln)

## Phase 3 — Serving Path

- [ ] **3.1** Validated pointer-aware load — `backend/src/domain/services/picks_service.py`: resolution order pointer → versioned bytes (validated) → legacy fixed-key blob read-only with deprecation warning (no pointer case); validate sklearn version equality + `feature_schema_hash == schema_signature()`; mismatch → structured error naming stored-vs-runtime values, `fallback_reason=version_mismatch|schema_mismatch`, NO silent path. Expose `serving_mode ∈ {ml, heuristic}`, `fallback_reason ∈ {load_failed, version_mismatch, schema_mismatch, absent, blend_failed}`, in-memory counter; log `[ML_FALLBACK] reason=...` on every transition. AC: "Version mismatch fails loudly", "Feature schema mismatch fails loudly", "Legacy blob loads read-only with warning", "Legacy path never written", "Fallback logged per response", "Normal serving marked ML-backed". Verify: 6.3. Deps: 1.1, 1.2, 2.2. (~80 ln)
- [ ] **3.2** `classes_` alignment, ensemble site — `backend/src/domain/services/prediction_service.py` L1502–1507: replace positional `probs[0]=Draw/probs[1]=Home/probs[2]=Away` with `label→prob` built from `dict(zip(model.classes_, proba))` keyed by outcome-label constants; replace bare `except Exception: pass` (L1525–1527) with logged handler — Poisson-only continues, context logged, `fallback_reason=blend_failed`. AC: "Probabilities mapped through classes_", "Blend failure never silent". Verify: 6.3 permutation test. Deps: none. (~35 ln)
- [ ] **3.3** `classes_` alignment, refinement site — `backend/src/domain/services/picks_service.py` L928–947: replace `ml_probs[0]/[1]/[2]` positional lookups with `classes_`-keyed map (same constants). AC: same scenarios as 3.2. Verify: 6.3. Deps: none. (~25 ln)
- [ ] **3.4** Response marker + batch audit — `backend/src/application/use_cases/use_cases.py`: copy `serving_mode`/`fallback_reason` into existing prediction response payload; audit batch predict path (~L395–415) for positional class assumptions, fix if found. AC: every response carries ML/heuristic marker + reason category. Verify: 6.3. Deps: 3.1. NOTE: D8 item 2 (log-only) if over budget. (~25 ln)

## Phase 4 — CLI

- [ ] **4.1** `backend/scripts/orchestrator_cli.py`: delete sklearn/InconsistentVersionWarning suppression (L34–36) so legacy-blob drift surfaces visibly (D4); fix cleanup order in `cmd_train`/cleanup flow — serving artifacts (pointer target or legacy blob) never deleted before successor promotion succeeds; inject `git_sha = git rev-parse --short HEAD` (default `"unknown"`). AC: "Pre-train reset keeps serving model", "Failed run leaves prior model serving"; envelope carries real SHA; warnings no longer suppressed. Verify: 6.4 + manual smoke. Deps: 2.3. (~35 ln)

## Phase 5 — CI Parity

- [ ] **5.1** `.github/workflows/ci.yml` `backend-tests` job (L54 cache path, L57 install): install step → `python -m pip install -r requirements.txt -r requirements-worker.txt`; `cache-dependency-path` gains `backend/requirements-worker.txt`. Lint/types job untouched (D7). AC: ml-ci-test-parity "ML paths execute in CI", "Dependency sets stay consistent", "Local verification matches CI". Verify: YAML parse + CI run green. Deps: Phase 6 tests exist to exercise sklearn paths. (~4 ln)
- [ ] **5.2** Inspect `.github/workflows/ci-pr.yml` (L28–30, L52–55) for identical parity drift; apply the same two-line fix if it runs pytest (design scoped ci.yml — confirm scope at apply). Verify: diff inspection. Deps: 5.1. (~4 ln, conditional)

## Phase 6 — Tests (runnable via `.venv/bin/pytest tests/ -q`)

- [ ] **6.1** Unit: gate — `backend/tests/test_ml_evaluation_gate.py` (new): chronology invariant (every holdout date > every train date), hand-computed log loss/Brier, PASS/FAIL/tie-vs-baseline matrix, `insufficient_data` FAIL, uniform baseline when odds absent. Deps: 2.1. (~90 ln)
- [ ] **6.2** Unit: repo lifecycle — `backend/tests/test_mongo_artifact_lifecycle.py` (new, fake Mongo fixtures): versioned save immutability, promotion old-or-new read guarantee, `clear_all_data` preserves pointer+artifact+legacy blob, pruning never deletes pointer/legacy. Proves "Failed training keeps prior model serving". Deps: Phase 1. (~90 ln)
- [ ] **6.3** Unit: serving validation — `backend/tests/test_ml_serving_validation.py` (new): envelope sklearn/schema mismatch → loud structured errors naming both values, `classes_` permutation mapping at both blend sites, legacy deprecation warning, `[ML_FALLBACK]` emission + mode markers, no bare except around blending. Deps: Phase 3. (~100 ln)
- [ ] **6.4** Integration: `backend/tests/test_ml_deployment_integration.py` (new): failed/interrupted run keeps prior model loadable; full train→gate→PASS→save→promote→load roundtrip; FAIL persists GateReport to training_results and keeps V1 serving; whole suite exits 0 with zero ML ImportError skips. Deps: 2.3, 2.4, 4.1. (~60 ln)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ≈810 raw → ≈760 after D8 trims (impl ≈420 + tests ≈340) |
| 800-line budget risk | Medium (fits; thin margin, descope ladder armed) |
| Chained PRs recommended | No |
| Suggested split | Single PR — all units land together |
| Delivery strategy | single-pr-default |

Verdict: ≈760–810 changed lines vs 800 budget → single PR is viable but thin-margined. Safety valve during sdd-apply = D8 ladder in order (1.4 retention pruning → 3.4 log-only marker → simplify baseline). If raw diff would exceed 800 after the ladder, stop and obtain explicit `size:exception` — do not expand silently.

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: High

(Note: guard line above uses the skill's literal 400-line baseline — exceeded. Against this session's 800-line budget the risk is Medium and single-PR holds.)
