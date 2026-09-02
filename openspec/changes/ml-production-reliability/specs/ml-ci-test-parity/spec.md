# ci-test-parity Specification

## Purpose

Ensures continuous integration exercises the same dependency surface as production so ML code paths are actually tested. Today CI installs only the API requirements, so scikit-learn-dependent modules import-skip or diverge silently between CI and the worker environment. Placed as a new capability because no existing ops/CI spec exists in `openspec/specs/`. All requirements testable locally via `.venv/bin/pytest tests/ -q` from `backend/`.

## Requirements

### Requirement: CI installs worker dependencies

The CI workflow MUST install the worker requirements (including scikit-learn/joblib, e.g. `requirements-worker.txt`) in addition to the API requirements before running pytest. ML-dependent modules MUST import and execute under CI exactly as they do in the scheduled worker environment.

#### Scenario: ML paths execute in CI

- GIVEN CI provisions its Python environment
- WHEN the pytest suite runs
- THEN tests exercising sklearn-dependent training/prediction paths execute (not skipped for missing imports)
- AND the suite passes via the standard test command

#### Scenario: Dependency sets stay consistent

- GIVEN a library is added to worker requirements
- WHEN CI configuration is reviewed
- THEN CI installs that requirements file rather than a hand-copied subset, so parity cannot drift silently

### Requirement: Test suite green as merge gate

The full backend suite MUST be the acceptance gate for this change and future changes touching ML paths: `.venv/bin/pytest tests/ -q` from `backend/` exits 0 with no skipped ML-path tests attributable to missing dependencies.

#### Scenario: Local verification matches CI

- GIVEN a clean checkout with the venv provisioned
- WHEN `.venv/bin/pytest tests/ -q` runs from `backend/`
- THEN exit code is 0 and no failures cite ImportError for ML dependencies
