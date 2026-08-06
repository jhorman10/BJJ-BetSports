# data-retention Specification

## Purpose

Defines MongoDB TTL retention so expired documents are physically purged by the database instead of accumulating until a manual `clear_all_data()`.

## Requirements

### Requirement: TTL index on match_predictions.expires_at

Both `MongoRepository` and `AsyncMongoRepository` MUST create a TTL index on `match_predictions.expires_at` with `expireAfterSeconds=604800` (7 days) during repository initialization, idempotently. MongoDB MUST physically delete documents whose `expires_at` has passed.

> **Accepted implementation (D2, resolved at verify 2026-08-05)**: the TTL index is implemented with `expireAfterSeconds=0`, so MongoDB physically deletes each document exactly when its `expires_at` is reached (purge at `expires_at`, not `expires_at + offset`). The literal `604800` (7 days) is the application-side maximum retention offset — `expires_at` is written as `now + ttl_seconds` (e.g. `ttl_seconds: 86400*7` in use_cases.py:860) — NOT an additional purge offset. With `0` the index stays neutral and preserves the per-document TTL; with the literal, MongoDB would purge at `expires_at + 7d`, contradicting the "no expired documents" criterion.

> **Partial index (C1, corrected at fix 2026-08-06)**: the `match_predictions` TTL index is PARTIAL (`partialFilterExpression: {"labeled": {"$eq": False}}`). Only unlabeled documents are purged at `expires_at`; documents already labeled by the auto-labeler survive for analytics (e.g. `/api/v1/metrics/baseline90d` sourced from `metrics_baseline.py` via `find({"labeled": True})`), otherwise the TTL would destroy the labeler's output before it is consumed. MongoDB partial indexes do NOT support `$ne`, `$not`, or `$exists:False` — only `$eq`, `$exists:True`, `$type`, `$in`, and `$and`. `save_match_prediction` and `bulk_save_predictions` set `"labeled": False` via `$setOnInsert` on document creation; the auto-labeler overwrites to `"labeled": True` afterward. `{"labeled": {"$eq": False}}` precisely targets unlabeled docs using a supported operator.

#### Scenario: Expired prediction physically purged

- GIVEN a match_predictions document with expires_at older than 7 days
- WHEN the MongoDB TTL monitor runs (default ~60s cycle)
- THEN the document is physically removed from the collection

#### Scenario: Idempotent index initialization

- GIVEN the repository initializes with the TTL index already present
- WHEN initialization runs again
- THEN `create_index` succeeds without error and without duplicate indexes

### Requirement: TTL index on api_cache.expires_at

Both repositories MUST create a TTL index on `api_cache.expires_at` with `expireAfterSeconds=3600` (1 hour) at initialization, idempotently.

> **Accepted implementation (D2, resolved at verify 2026-08-05)**: the TTL index is implemented with `expireAfterSeconds=0`, so MongoDB purges each cache entry exactly when its `expires_at` is reached. The literal `3600` (1 hour) is the maximum retention offset applied by the application for `api_cache` entries — `api_cache` carries mixed per-source TTLs (3600–604800, e.g. `football_data_org.py`), each written into `expires_at` — NOT an additional purge offset. With `0` the index is neutral and each entry purges at its own `expires_at` deadline. Unlike `match_predictions`, `api_cache` keeps a simple (non-partial) TTL index.

#### Scenario: Expired cache entry purged

- GIVEN an api_cache document with expires_at older than 1 hour
- WHEN the MongoDB TTL monitor runs
- THEN the document is physically removed

#### Scenario: No reliance on manual clear

- GIVEN `clear_all_data()` is no longer the purge mechanism
- WHEN expired entries accumulate
- THEN the TTL monitor purges them automatically
