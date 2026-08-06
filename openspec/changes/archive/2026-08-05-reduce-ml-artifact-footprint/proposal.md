# Proposal: Reduce ML Artifact Footprint

## Intent

The backend container and Docker daemon accumulate ML artifacts even though the trained model already lives in MongoDB (`binary_artifacts`, BytesIO, no disk write). Exploration (#925/#926/#928) pinpoints the real bloat: (1) the worker caches the full `training_data` dict (match_history 500 items + team_stats, ~120MB/run) in two diskcache keys with 24h TTL, never purged post-run; (2) Mongo has `expires_at` but NO TTL indexes → expired docs never physically purged; (3) `cleanup_model_artifacts` only covers `BACKEND_ROOT/*.joblib`, `*.csv`, `ml_models/` — misses `data/`, `output/`, `tmp/`, `.cache_data`; (4) neither the pipeline nor the worker cleans up after posting results. Goal: only training results stay in MongoDB; disk artifacts are deleted after posting; Docker cache is reclaimed.

## Scope

### In Scope

**Fase 0 — operativo (sin código app):**
- `docker builder prune -a` (~9GB) + `docker image prune -a` (~3.4GB) — comandos documentados en changelog/README
- `git rm -r frontend/dev-dist` (3 archivos PWA stale commiteados)
- `.gitignore` +: `frontend/dev-dist/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-black/`, `.atl/`, `*.tsbuildinfo`

**Fase 1 — núcleo (backend):**
1. `scheduler.py:125-163` — cachear `lightweight_training_result` (lo que ya se postea a Mongo) en ambas keys, no `training_data` completo → −~120MB/run.
2. `mongo_repository.py:65-70` + `async_mongo_repository.py` — TTL indexes: `match_predictions.expires_at` (7d), `api_cache.expires_at` (1h) → purga física, sin depender de `clear_all_data()`.
3. `model_artifacts.py:10-22` — ampliar cobertura: `backend/data/*.joblib` (MODEL_FILE_PATH), `backend/output/*.json`, `backend/tmp/`, `.cache_data` (diskcache). **NO** borrar todo `backend/data/` (team_logos.json es runtime).
4. `local_mlops_pipeline.sh` — paso final `cache.clear()` + `cleanup_model_artifacts()` tras top-picks; evaluar hook en `scheduler.run_daily_orchestrated_job` (scheduler.py:51) tras inferencia.

### Out of Scope

- Frontend (ya 100% API; verificado — no se toca)
- Fases 2–4: unificación clientes API (`services/api.ts` legacy), auth X-API-Key, split `Dockerfile.portable` monolito, deps obsoletas/drift requirements, `datetime.utcnow`, workflows duplicados (lint.yml/labeler.yml)

## Capabilities

> Contract con sdd-spec. `openspec/specs/` no existe aún (cambio primero de la tienda) — no hay specs previas que modificar.

### New Capabilities
- `ml-artifact-lifecycle`: cleanup de artefactos ML en disco (cobertura ampliada), cleanup post-pipeline y post-inferencia en worker, política de caché liviana de training results
- `data-retention`: TTL indexes en Mongo → purga física de docs expirados (match_predictions, api_cache)

### Modified Capabilities
- None

## Approach

Swap cache payload → añadir TTL indexes en init de repos → extender globs de cleanup → paso final en pipeline + hook en worker. Todo backend; frontend intacto. Fase 0 ejecutada manualmente (ops), documentada.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/src/scheduler.py` | Modified | Cache payload → lightweight; cleanup post-inferencia |
| `backend/src/core/model_artifacts.py` | Modified | Cobertura cleanup: data/output/tmp/.cache_data |
| `backend/src/infrastructure/repositories/mongo_repository.py` | Modified | TTL indexes match_predictions + api_cache |
| `backend/src/infrastructure/repositories/async_mongo_repository.py` | Modified | Ídem async |
| `backend/scripts/local_mlops_pipeline.sh` | Modified | Paso final cleanup |
| `.gitignore` | Modified | 6 entradas nuevas |
| `frontend/dev-dist/` | Removed | 3 archivos PWA stale (git rm) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Eliminar `.cache_data` sin conocer consumidores | Low | Caché regenerable; entrenamiento la rellena; tests |
| TTL borra predictions que el frontend lea | Low | Frontend 100% API; predictions se regeneran a diario; `expires_at` ya define 7d |
| Cleanup borra JSON runtime (`team_logos.json`) | Med | Scope explícito `data/*.joblib`; tests unitarios de `get_model_artifact_paths` |

## Rollback Plan

`git revert` del commit (cambios pequeños y localizados). TTL: `drop_index("expires_at_1")` en Mongo. Caché: restaurar payload completo en scheduler. dev-dist: `git checkout -- frontend/dev-dist`. Prunes Docker no reversibles pero solo espacio libre.

## Dependencies

- Mongo 6.0 (daemon local) soporta TTL indexes
- Ejecución manual de prunes Docker (Fase 0, acción operativa)

## Success Criteria

- [ ] Sin `.cache_data` > 5MB tras un run completo (hoy ~120MB/run)
- [ ] `match_predictions`/`api_cache` sin docs con `expires_at` vencido tras TTL (purga automática verificada)
- [ ] Cleanup post-pipeline ejecuta sin fallos; `data/*.joblib`, `output/`, `tmp/` vacíos tras run; `team_logos.json` intacto
- [ ] pytest backend verde + tests nuevos (TTL, cleanup paths, cache payload)
- [ ] Frontend sin regresión (Vitest + smoke `/api/v1/*`)
- [ ] Docker: ~9GB + ~3.4GB reclaimados; `frontend/dev-dist` fuera de git

## Delivery

~150–190 líneas cambiadas (incl. ~100 de tests). **No cruza 400 ni 800** → single PR, sin chaining. `400-line budget risk: Low`.
