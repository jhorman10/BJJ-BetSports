# ml-evaluation-gate Specification

## Purpose

Governs pre-promotion model quality control: every candidate pick-classifier MUST pass an out-of-time evaluation against a trivial baseline before it may serve. Guarantees reported metrics distinguish honest out-of-time performance from in-sample fit. All requirements testable via `.venv/bin/pytest tests/ -q` from `backend/`.

## Requirements

### Requirement: Chronological holdout before promotion

Training MUST evaluate each candidate on a chronological (time-ordered) holdout split — later events held out, earlier events used for fitting — BEFORE any promotion decision. Evaluation on shuffled or in-sample-only data does not satisfy this requirement. No artifact is promoted without a recorded holdout evaluation.

#### Scenario: Holdout evaluated before save/promote

- GIVEN a fitted candidate model
- WHEN the orchestrator reaches the save step
- THEN holdout metrics exist for that candidate before promotion executes

#### Scenario: Holdout respects event chronology

- GIVEN training samples ordered by event date
- WHEN the holdout split is applied
- THEN every holdout sample is dated after every training sample

### Requirement: Required gate metrics

The gate MUST compute, on the out-of-time holdout: multiclass log loss and multiclass Brier score of the candidate. Both metrics MUST be computed from calibrated probability outputs over the same holdout set.

#### Scenario: Both metrics computed out-of-time

- GIVEN a candidate and its chronological holdout
- WHEN evaluation runs
- THEN log loss and Brier score are computed on holdout predictions only

### Requirement: Baseline comparison rule

The candidate MUST outperform an always-favorite baseline (predicting the historical favorite probabilities for each holdout match) on BOTH required metrics to pass the gate. Ties or losses against the baseline fail the gate.

#### Scenario: Candidate beats baseline promotes

- GIVEN candidate log loss and Brier are both better than always-favorite baseline values
- WHEN the gate evaluates the candidate
- THEN the gate result is PASS and promotion proceeds

#### Scenario: Candidate worse than baseline blocked

- GIVEN candidate Brier score is worse than baseline while log loss is better
- WHEN the gate evaluates the candidate
- THEN the gate result is FAIL and promotion does not execute

### Requirement: Fail keeps previous model with persisted reason

On gate failure (or missing/uncomputable evaluation), the system MUST keep the previously promoted model serving unchanged and MUST persist the failure — gate result, failing metrics vs baseline, and human-readable reason — to `training_results`. The previous model MUST remain loadable and serving after a failed promotion attempt.

#### Scenario: Failed gate preserves serving state

- GIVEN version V1 is serving and candidate V2 fails the gate
- WHEN the run concludes
- THEN the serving pointer still resolves to V1 and V2 was never promoted

#### Scenario: Failure reason persisted

- GIVEN V2 failed with log loss L and baseline B
- WHEN results are persisted
- THEN `training_results` contains the FAIL status, L vs B comparison, and a reason string

### Requirement: Honest metric reporting

Persisted `training_results` MUST distinguish in-sample metrics from out-of-time metrics explicitly (separate fields or labels). Reported daily ROI MUST be derived from actual payout odds of resolved picks; hardcoded per-win return constants MUST NOT be used in daily ROI computation. Any metric that cannot be honestly computed MUST be omitted or null-flagged, not fabricated.

#### Scenario: Metrics separated by sample origin

- GIVEN a completed gated training run
- WHEN `training_results` is inspected
- THEN accuracy/log-loss fields identify whether they were measured in-sample or out-of-time

#### Scenario: Daily ROI uses real payouts

- GIVEN picks resolved with known bookmaker odds
- WHEN daily stats are recomputed
- THEN ROI equals payout-based profit over staked units, with no constant-per-win substitution

#### Scenario: Unresolvable metric not fabricated

- GIVEN no resolved odds exist for a day
- WHEN daily stats are built
- THEN ROI for that day is omitted/null-flagged rather than defaulted
