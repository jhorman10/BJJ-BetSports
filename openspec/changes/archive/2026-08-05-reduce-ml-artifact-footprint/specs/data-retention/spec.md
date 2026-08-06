# Delta Spec: data-retention

Source: `openspec/changes/reduce-ml-artifact-footprint/proposal.md` (Fase 0 + Fase 1).
Applies to NEW capability: `data-retention` (full text in `openspec/specs/data-retention/spec.md`).

## ADDED Requirements

### Requirement: TTL index on match_predictions.expires_at

Both `MongoRepository` and `AsyncMongoRepository` MUST create a TTL index on `match_predictions.expires_at` with `expireAfterSeconds=0` at initialization, idempotently. MongoDB MUST physically delete documents whose `expires_at` has passed.

> **Accepted implementation (D2, resolved at verify 2026-08-05)**: the TTL index is implemented with `expireAfterSeconds=0`, so MongoDB physically deletes each document exactly when its `expires_at` is reached (purge at `expires_at`, not `expires_at + offset`). The literal `604800` (7 days) is the application-side maximum retention offset — `expires_at` is written as `now + ttl_seconds` (e.g. `ttl_seconds: 86400*7` in use_cases.py:860) — NOT an additional purge offset. With `0` the index stays neutral and preserves the per-document TTL; with the literal, MongoDB would purge at `expires_at + 7d`, contradicting the "no expired documents" criterion.

> **Partial index (C1, resolved at apply 2026-08-05)**: the `match_predictions` TTL index is PARTIAL (`partialFilterExpression: {"labeled": {"$ne": True}}`). Only unlabeled documents are purged at `expires_at`; documents already labeled by the auto-labeler are preserved for analytics (e.g. `/api/v1/metrics/baseline90d` sourced from `metrics_baseline.py` via `find({"labeled": True})`).

#### Scenario: Expired prediction physically purged

- GIVEN a match_predictions document with expires_at older than 7 days
- WHEN the MongoDB TTL monitor runs
- THEN the document is physically removed from the collection

### Requirement: TTL index on api_cache.expires_at

Both repositories MUST create a TTL index on `api_cache.expires_at` with `expireAfterSeconds=0` at initialization, idempotently.

> **Accepted implementation (D2, resolved at verify 2026-08-05)**: the TTL index is implemented with `expireAfterSeconds=0`, so MongoDB purges each cache entry exactly when its `expires_at` is reached. The literal `3600` (1 hour) is the maximum retention offset applied by the application for `api_cache` entries — `api_cache` carries mixed per-source TTLs (3600–604800, e.g. `football_data_org.py`), each written into `expires_at` — NOT an additional purge offset. With `0` the index is neutral and each entry purges at its own `expires_at` deadline. Unlike `match_predictions`, `api_cache` keeps a simple (non-partial) TTL index.

#### Scenario: Expired cache entry purged

- GIVEN an api_cache document with expires_at older than 1 hour
- WHEN the MongoDB TTL monitor runs
- THEN the document is physically removed

### Requirement: Fase 0 repository housekeeping

(Change-scoped, operational — not merged into capability specs)

`.gitignore` MUST ignore `frontend/dev-dist/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-black/`, `.atl/`, `*.tsbuildinfo`; `frontend/dev-dist/` MUST be removed from git tracking; Docker prunes (`docker builder prune -a`, `docker image prune -a`) MUST be documented in changelog/README.

#### Scenario: dev-dist untracked

- GIVEN `frontend/dev-dist/` is removed from git
- WHEN a fresh `git status` runs
- THEN the directory no longer appears as tracked content

#### Scenario: Prune commands documented

- GIVEN the changelog/README documents the prune commands
- WHEN an operator follows them
- THEN `docker builder prune -a` and `docker image prune -a` run without error
