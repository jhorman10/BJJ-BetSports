# Design: Reduce ML Artifact Footprint

## Technical Approach

Swap the worker's ~120MB training cache payload for the lightweight result already posted to MongoDB; add idempotent Mongo TTL indexes so expired docs self-purge; extend disk-artifact cleanup globs (`data/`, `output/`, `tmp/` + cache clear); add non-fatal cleanup to pipeline and scheduler. Covers specs `ml-artifact-lifecycle` + `data-retention`. No `openspec/config.yaml` exists → no `rules.design` applied.

## Architecture Decisions

### D1: Cache swap requires audit consumer migration

| Option | Tradeoff | Decision |
|---|---|---|
| Cache lightweight in both keys, no consumer change | `audit_service.py:49` reads `match_history` → all leagues "missing" → force-retrain loop (`audit_service.py:115-127`) | ✗ |
| Swap + re-source audit from Mongo | Coverage from `self.orchestrator.persistence_repo.get_all_active_predictions()` (league_id; 7d TTL ⇒ no false retrain at 08:00). No deps signature change | ✓ |

Verified: `"ml_training_result"` has **zero readers**; `"ml_training_result_data"` (`ml_training_orchestrator.py:684`) read by `audit_service.py:40` (match_history → retrain trigger) and `live_predictions_use_case.py:59` (team_stats, guarded by `if "team_stats" in training_results` → graceful). `GetLivePredictionsUseCase` is not wired to any router (grep: no src instantiation) → degradation acceptable. `match_predictions.data` = `MatchPredictionDTO.model_dump()` (`use_cases.py:860`) — integrity check reuses `picks` keys defensively.

### D2: TTL `expireAfterSeconds=0` (spec deviation)

| Option | Tradeoff | Decision |
|---|---|---|
| 604800/3600 (spec literal) | Index offsets `expires_at` → purge at `expires_at+offset` (8d/2h); "no expired docs" criterion unmet | ✗ |
| `0` | Purge exactly at `expires_at`, matching `is_future_time` runtime gate. Mixed `api_cache` TTLs (3600–604800, `football_data_org.py`) each purge at own deadline — proposal's "premature purge" concern unfounded either way | ✓ |

### D3: Idempotent TTL creation

`create_index` with identical spec is a no-op; conflicting options raise `OperationFailure`. Helper: try create → on failure `drop_index("expires_at_1")` + recreate. Sync init `mongo_repository.py:65-70`; async `_ensure_indexes` `async_mongo_repository.py:125-144`.

### D4: Cleanup globs preserve runtime JSON

Add `DATA_DIR/*.joblib` (covers `MODEL_FILE_PATH`, `paths.py:14`), `output/*.json`, `tmp/*` (files only); keep root/`ml_models/` globs. `team_logos.json`/`team_short_names.json` are `.json` — never matched; runtime readers verified: `team_service.py:19-21`, `canonicalizer.py:18`, `validators.py:104`. `output/baseline_90d.json` verified **write-only**: `generate_baseline_90d.py:160`; `metrics.py:11` computes from Mongo (`metrics_baseline.py:21`).

### D5: Scheduler hook ≠ `cache.clear()`

Step-3 forecasts (TTL 86400) serve the API between runs; `cache.clear()` would wipe them. Scheduler runs `cleanup_model_artifacts()` only; the batch pipeline runs both.

## Data Flow

```
training ──► lightweight dict ──► cache (2 keys, <5MB) + Mongo training_results/latest_daily
   ├─► Mongo match_predictions (expires_at, 7d) ──TTL(0)──► auto-purge
   ├─► Mongo api_cache (expires_at, mixed TTL) ──TTL(0)──► auto-purge
   └─► disk: data/*.joblib, output/*.json, tmp/* ──cleanup (pipeline final + scheduler step 5)──► deleted
audit ──► get_all_active_predictions()  (was: cache match_history)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/src/scheduler.py:117-163` | Modify | Cache `lightweight_training_result` in both keys; delete 26-line `training_data` build |
| `backend/src/scheduler.py:252` | Modify | Step 5: `try: cleanup_model_artifacts(logger)` non-fatal; **no** cache.clear |
| `backend/src/domain/services/audit_service.py:38-75` | Modify | Re-source coverage/integrity from Mongo active predictions |
| `backend/src/infrastructure/repositories/mongo_repository.py:65-70` | Modify | `_ensure_ttl_index` helper + 2 TTL indexes |
| `backend/src/infrastructure/repositories/async_mongo_repository.py:125-144` | Modify | Await TTL create; collision drop+recreate |
| `backend/src/core/model_artifacts.py:10-22` | Modify | Extend globs; `cleanup_model_artifacts(logger, cache=None)` |
| `backend/scripts/local_mlops_pipeline.sh:17` | Modify | Final step `cache.clear()` + cleanup, `|| true` (set -e safe) |
| `.gitignore` | Modify | +6 entries (dev-dist/, .mypy_cache/, .ruff_cache/, .venv-black/, .atl/, *.tsbuildinfo) |
| `README.md` | Modify | Document `docker builder prune -a` / `docker image prune -a` (no CHANGELOG exists) |
| `frontend/dev-dist/` | Delete | `git rm` 3 stale PWA files |

## Interfaces

```python
# model_artifacts.py
def cleanup_model_artifacts(logger, cache: "CacheService | None" = None) -> None
# mongo_repository.py (sync; async mirrors with await)
def _ensure_ttl_index(collection, field: str = "expires_at", seconds: int = 0) -> None
# audit_service.py — no signature change (uses self.orchestrator.persistence_repo)
```

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | Cleanup globs | monkeypatch `BACKEND_ROOT`/`DATA_DIR` → tmp_path; assert joblib/json/tmp removed, runtime JSON preserved |
| Unit | cache param | Fake provider; `clear()` called; OSError non-fatal |
| Unit | TTL idempotent/collision | Extend `_FakeCollection` (`test_async_mongo_repository.py:15`) with `expireAfterSeconds`/`drop_index`; 2nd init no-op; conflict → drop+recreate |
| Unit | Scheduler payload | `cache.set` called without `match_history`/`team_stats` |
| Unit | Audit re-source | Fake repo; empty → missing_leagues; picks integrity |
| Integration | Real purge (optional) | Real Mongo, past `expires_at`, wait TTL monitor; skip if CI lacks Mongo |

## Migration / Rollout

No data migration. Indexes created lazily on repo init; Mongo purges existing expired docs within one monitor cycle (~60s) after creation.

## Rollback (per deliverable)

| Deliverable | Rollback |
|---|---|
| D1 | `git revert`; restore full dict; audit restore cache read |
| D2 | `db.match_predictions.drop_index("expires_at_1")` (same `api_cache`) |
| D3/D4 | `git revert` model_artifacts.py / pipeline / scheduler |
| Fase 0 | `git checkout -- frontend/dev-dist`; prunes irreversible (space only) |

## Open Questions

- [ ] D2: adopt `expireAfterSeconds=0` (recommended) vs spec literal 604800/3600 — decide at verify
- [ ] Audit integrity check assumes `data` payload `picks` keys — confirm `MatchPredictionDTO` shape at apply
- [ ] Zero-reader `ml_training_result` key: keep lightweight or drop second `cache.set`?

## Line Estimate

D1 ~107 (incl. ~40 tests) · D2 ~59 · D3 ~65 · D4 ~28 · Fase 0 ~17 → **~276 total**, single PR. `400-line budget risk: Low`.
