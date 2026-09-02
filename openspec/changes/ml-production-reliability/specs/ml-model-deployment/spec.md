# ml-model-deployment Specification

## Purpose

Governs storage, promotion, loading, and observability of trained pick-classifier artifacts at serving time. Deployment MUST be atomic (pointer swap), traceable (metadata envelope), loud on incompatibility, transition-compatible with legacy blobs, and observable when degrading to heuristics. All requirements testable via `.venv/bin/pytest tests/ -q` from `backend/`.

## Requirements

### Requirement: Versioned artifact storage

The trainer MUST persist candidate models under versioned keys (`binary_artifacts/ml_picks_classifier/<version>`). Each version key SHALL be immutable once written; retraining produces a new key and MUST NOT overwrite a previously promoted artifact in place.

#### Scenario: Candidate saved under fresh version key

- GIVEN a training run completes successfully
- WHEN the candidate is persisted
- THEN bytes are written to a unique versioned key
- AND the previously promoted version remains byte-identical afterwards

### Requirement: Atomic promotion via pointer swap

Promotion MUST update a single Mongo pointer document mapping the serving key to the promoted version, using find-and-modify semantics — exactly one atomic document update. Readers resolving the serving key MUST always observe one complete old or new artifact, never partial or null state caused by promotion.

#### Scenario: Promotion swaps pointer atomically

- GIVEN the pointer resolves serving to V1
- WHEN V2 passes evaluation and is promoted
- THEN one find-and-modify update repoints serving from V1 to V2

#### Scenario: Reader never sees missing artifact during swap

- GIVEN promotion is in progress
- WHEN any reader resolves the serving key
- THEN it gets exactly one complete artifact (old or new)

### Requirement: Artifact metadata envelope

Every promoted artifact MUST carry metadata persisted alongside its bytes: `sklearn_version`, `feature_schema_hash`, `git_sha`, `trained_at`, evaluation `metrics`. The loader MUST validate sklearn version and feature schema hash against the serving runtime before use.

#### Scenario: Promoted artifact carries full metadata

- GIVEN training ran under sklearn S, git SHA G, schema hash H
- WHEN the artifact is promoted
- THEN its envelope reports S, G, H, trained_at, and gate metrics

#### Scenario: Version mismatch fails loudly

- GIVEN stored sklearn_version differs from the serving environment
- WHEN load is attempted
- THEN load fails with an explicit structured error naming both versions
- AND silent heuristic fallback without that error is prohibited

#### Scenario: Feature schema mismatch fails loudly

- GIVEN stored feature_schema_hash differs from current extractor signature
- WHEN validation runs
- THEN the artifact is refused via loud structured error naming the mismatched field

### Requirement: Transitional read-only legacy acceptance

The loader MUST accept pre-change artifacts under the legacy fixed unversioned key, read-only, emitting a deprecation warning on each read. Legacy blobs MUST NOT be overwritten or re-promoted in place by this system.

#### Scenario: Legacy blob loads read-only with warning

- GIVEN only the legacy fixed-key blob exists (no pointer)
- WHEN the loader resolves the model
- THEN the artifact loads successfully and a deprecation warning is logged

#### Scenario: Legacy path never written

- GIVEN a new training run finishes
- WHEN the candidate deploys
- THEN the legacy fixed key stays untouched

### Requirement: Serving-artifact preservation before promotion

Deployment MUST NOT delete the currently-serving artifact (pointer target or legacy blob) before a successor is successfully promoted; failed or interrupted runs leave the prior artifact serving.

#### Scenario: Failed training keeps prior model serving

- GIVEN V1 is serving
- WHEN training fails mid-run
- THEN V1 still resolves and loads for serving

### Requirement: Class alignment via model.classes_

Prediction code MUST align probabilities to outcome labels via `model.classes_`, not positional index assumptions. Alignment failures MUST surface as explicit handled errors with logged context; bare `except: pass` around ML blending is prohibited.

#### Scenario: Probabilities mapped through classes_

- GIVEN classes_ ordering differs from assumed label order
- WHEN predict_proba output blends into predictions
- THEN each probability maps to its label via classes_ indices

#### Scenario: Blend failure never silent

- GIVEN blending raises an exception
- WHEN the pipeline handles it
- THEN the error logs with context; no bare except swallows it

### Requirement: Heuristic-fallback observability

The serving layer MUST mark every prediction response with its mode — ML-backed or heuristic fallback plus reason category — via a structured log field or tracked signal, distinguishable without stack-trace inspection.

#### Scenario: Fallback logged per response

- GIVEN ML load or validation failed
- WHEN predictions serve from heuristics
- THEN each response carries a structured heuristic-mode marker and reason category

#### Scenario: Normal serving marked ML-backed

- GIVEN a validated model loads
- WHEN predictions serve
- THEN responses carry the ML-backed marker
