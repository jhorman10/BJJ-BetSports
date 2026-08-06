# Tasks: Reduce ML Artifact Footprint

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~276 (D1 ~107 · D2/D3 ~124 · D4 ~28 · Fase 0 ~17; incl. ~60-80 de tests nuevos) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (276 < 800) |
| Delivery strategy | single-pr-default |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

D2 (`expireAfterSeconds=0` vs spec literal 604800/3600) es **decisión pendiente para sdd-verify** (design Open Questions), NO bloquea apply. Ningún tamaño requiere size:exception.

## Phase 1: Fase 0 — Housekeeping (operativo, sin código app)

- [x] 1.1 `.gitignore` — añadir `frontend/dev-dist/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-black/`, `.atl/` (`*.tsbuildinfo` ya existe desde 1bf6a8c — verificar). Done: 5 entradas presentes. Verify: `grep -n "dev-dist\|\.atl" .gitignore`
- [x] 1.2 `git rm -r frontend/dev-dist` (registerSW.js, sw.js, workbox-6fc00345.js). Done: untracked. Verify: `git ls-files frontend/dev-dist | wc -l` → 0
- [x] 1.3 README.md — documentar `docker builder prune -a` y `docker image prune -a` (no existe CHANGELOG). Done: README contiene ambos. Verify: `grep -n "docker builder prune" README.md`

## Phase 2: Core — Cache, TTL, Cleanup

- [x] 2.1 **D1** scheduler.py:117-148 — eliminar build de `training_data` (26 líneas con match_history/team_stats) y cachear `lightweight_training_result` en ambas keys (`ml_training_result` + `orchestrator.CACHE_KEY_RESULT`). Done: `cache.set` solo con dict liviano; 0 refs a `training_data`. Verify: `grep -rn "training_data" backend/src/scheduler.py` → 0 + test 3.3
- [x] 2.2 **D1** audit_service.py:38-75 — reemplazar `cache.get(CACHE_KEY_RESULT).get("match_history")` (líneas 40-49) por `self.orchestrator.persistence_repo.get_all_active_predictions()`; coverage por `league_id`, integrity defensiva sobre `picks` (shape MatchPredictionDTO, use_cases.py:860). Dep: 2.1. Done: audit sin dependencia de cache; vacío → missing_leagues; sin retrain falso. Verify: test 3.4
- [x] 2.3 **D2+D3** mongo_repository.py:65-70 — helper `_ensure_ttl_index(collection, field="expires_at", seconds=0)` (try create → OperationFailure → `drop_index("expires_at_1")` + recreate); crear en `match_predictions` y `api_cache` con `expireAfterSeconds=0` (**decisión pendiente D2 — desviación del spec, se decide en verify**). Done: init idempotente, 2º init no-op. Verify: test 3.2
- [x] 2.4 **D2+D3** async_mongo_repository.py:125-144 — en `_ensure_indexes`, await TTL creates (mismos campos, seconds=0) con drop+recreate en colisión. Dep: 2.3 (mismo helper semántico). Done: idem async. Verify: test 3.2
- [x] 2.5 **D4** model_artifacts.py:10-22,25-54 — extender globs: `DATA_DIR/*.joblib` (MODEL_FILE_PATH, paths.py:14), `output/*.json`, `tmp/*` (solo archivos); conservar raíz/ml_models. Firmar `cleanup_model_artifacts(logger, cache=None)`; con cache → `cache.clear()`; OSError no fatal. Done: joblib/output/tmp removidos; `team_logos.json`/`team_short_names.json` intactos (`.json` no matchean `*.joblib`). Verify: test 3.1
- [x] 2.6 **D5** scheduler.py tras línea 252 (Step 5) — hook post-inferencia: `try: cleanup_model_artifacts(logger) except: log`; **sin** `cache.clear()` (forecasts TTL 86400 sirven API entre runs). Dep: 2.5. Done: cleanup no fatal, cache intacta. Verify: `grep -n "cleanup_model_artifacts" backend/src/scheduler.py` + test 3.3
- [x] 2.7 local_mlops_pipeline.sh:17 — paso final tras top-picks: `cache.clear()` + `cleanup_model_artifacts()`, no fatal (`|| true`, set -e safe). Dep: 2.5. Done: exit 0 con/sin artefactos y con fallo de cleanup. Verify: `bash -n backend/scripts/local_mlops_pipeline.sh`

## Phase 3: Tests

- [x] 3.1 Nuevo `backend/tests/unit/test_model_artifacts.py` — monkeypatch BACKEND_ROOT/DATA_DIR → tmp_path; removidos joblib/output/tmp; runtime JSON preservado; Fake cache → `clear()` llamado; OSError no fatal. Verify: `.venv/bin/pytest tests/unit/test_model_artifacts.py -q`
- [x] 3.2 Extender `backend/tests/unit/test_async_mongo_repository.py:15,49` — `_FakeCollection`/`_FakeAsyncCollection` con `expireAfterSeconds`+`drop_index`; 2º init no-op; colisión → drop+recreate. Verify: `.venv/bin/pytest tests/unit/test_async_mongo_repository.py -q`
- [x] 3.3 Nuevo `backend/tests/unit/test_scheduler_cache.py` — `cache.set` en ambas keys sin `match_history`/`team_stats`; Step 5 invoca cleanup sin clear. Verify: `.venv/bin/pytest tests/unit/test_scheduler_cache.py -q`
- [x] 3.4 Nuevo `backend/tests/unit/test_audit_service.py` — Fake repo: vacío → `missing_leagues`+reparación; con `picks` válidos → integrity 0; sin match_history en cache. Verify: `.venv/bin/pytest tests/unit/test_audit_service.py -q`

## Phase 4: Verificación integrada

- [x] 4.1 Suite completa backend verde. Verify: `.venv/bin/pytest tests/ -q` (desde backend/, venv .venv). Resultado: 107 passed, 1 failed (`test_api_admin_security::test_trigger_training_allows_local_dev_browser_without_api_key` — **fallo preexistente** ajeno al cambio: `main_mod._training_running` no existe en HEAD; verificado con `git show HEAD:backend/src/api/main.py` → 0 ocurrencias, y el archivo no fue tocado por apply)
- [x] 4.2 Smoke: `git status` sin frontend/dev-dist ni `.atl/`/cachés; `grep -rn "match_history" backend/src/scheduler.py` → 0. Verify: comandos grep. Resultado: dev-dist fuera de git (0), `match_history` en scheduler → 0, `.atl/` ignorado vía .gitignore
- [x] 4.3 Marcar estado D2 (`expireAfterSeconds=0` aplicado) en tasks.md para resolución en sdd-verify. Done: nota presente

## Estado D2 (registrado por sdd-apply)

- **D2 aplicado**: `expireAfterSeconds=0` en `match_predictions.expires_at` y `api_cache.expires_at` (sync `mongo_repository.py` + async `async_mongo_repository.py`).
- **Desviación del spec literal (604800/3600)**: documentada en design.md Open Questions — **decisión pendiente para sdd-verify**. Con `0`, Mongo purga exactamente en `expires_at`; con el offset literal, purgaría en `expires_at + offset`.
- **Rollback inmediato**: `db.match_predictions.drop_index("expires_at_1")` y `db.api_cache.drop_index("expires_at_1")` (los repos reintentan crear el índice TTL en el próximo init).
