# Tasks (Checklist) — Async Mongo Migration

## Preparación
- [x] Recolectar baseline de latencias y throughput (script + dashboard) — **NOTA: deferido a fase de bencharmk post-implementación**
- [x] Añadir `motor` como dependencia en `requirements.txt` — **ya presente: motor>=3.2.0**

## Implementación
- [x] Crear `backend/src/infrastructure/repositories/async_mongo_repository.py` (Motor-native)
  - [x] Implementar métodos: `get_match_prediction`, `get_match_predictions_bulk`, `save_match_prediction`, `bulk_save_predictions`, `get_training_result_with_timestamp`, `save_training_result`, `get_cached_response`, `save_cached_response`.
  - [x] Asegurar que los nombres de colecciones e índices coinciden con la impl. síncrona.
- [x] Escribir tests unitarios para `AsyncMongoRepository`.

## Integración
- [x] Exponer `get_async_mongo_repository()` en `backend/src/dependencies.py` — **ya expuesto via async_mongo_adapter**
- [x] Migrar call-sites críticos (confirmar ya migrados):
  - [x] `backend/src/application/use_cases/use_cases.py` (caching/persist) — ya migrado
  - [x] `backend/src/infrastructure/data_sources/football_data_org.py` — ya migrado
  - [x] `backend/src/application/use_cases/live_predictions_use_case.py` — ya migrado
  - [x] `backend/src/api/services/data_loader.py` — **NO migrar: usado en contexto sync (DataLoader es sync)**
  - [x] Buscar referencias a `get_mongo_repository()` — **restantes consumers son sync context: matches.py, worker.py, router/labeler.py**

## Pruebas y Benchmark
- [x] Añadir/ajustar fixtures `pytest-asyncio` para nuevos tests async — **ya configurado en pyproject.toml (asyncio_mode=auto)**
- [x] Preparar harness de benchmark reproducible para repositorio y endpoints (`scripts/benchmark_async_mongo.py`, `scripts/benchmark_async.py`).
- [x] Ejecutar benchmark local del repositorio y guardar resultados async/sync (`backend/tmp/benchmark_async_mongo.json`, `backend/tmp/benchmark_async_mongo_full_local.json`).
- [ ] Ejecutar pruebas de carga/benchmark de endpoints en staging y guardar resultados (p50/p95, errors). — **PENDIENTE; ya se intentó contra el host publicado en Render y respondió `503`/`429`, así que falta un host sano o bypass antes de obtener métricas válidas**

## Despliegue y Rollout
- [x] Añadir `MONGO_ASYNC_MODE` env flag (documentar comportamiento). — **IMPLEMENTADO: auto/on/off en async_mongo_adapter.py**
  - `MONGO_ASYNC_MODE=on`: fuerza Motor-native (fails si no disponible)
  - `MONGO_ASYNC_MODE=off`: fuerza sync fallback
  - `MONGO_ASYNC_MODE=` (empty): auto-detect basado en motor disponible
- [x] Declarar contrato de env Mongo en despliegue/documentación (`MONGO_URI`, `MONGO_DB_NAME`, baseline `MONGO_ASYNC_MODE=off`). — **COMPLETO: `render.yaml`, `backend/.env.example`, `backend/README.md`**
- [x] Fallar rápido si `MONGO_ASYNC_MODE` explícito no tiene `MONGO_URI` válido. — **COMPLETO: `async_mongo_adapter.py` + `tests/unit/test_async_mongo_adapter.py`**
- [x] Preparar runbook de canary/rollback para `MONGO_ASYNC_MODE` y Render. — **COMPLETO: `backend/specs/async-mongo-migration/canary-runbook.md`**
- [ ] Desplegar en canary y monitorizar; si OK, habilitar globalmente. — **PENDIENTE**

## Cleanup
- [ ] Ejecutar cleanup post-validación del shim Mongo. — **PENDIENTE post-canary/promotion**
  - [ ] Reducir `get_async_mongo_repository()` a factory Motor-only en `src/infrastructure/repositories/async_mongo_adapter.py`.
  - [ ] Eliminar ramas `MONGO_ASYNC_MODE=off` y auto-fallback del factory.
  - [ ] Eliminar la clase `AsyncMongoAdapter`, `_sync_repo` y los `asyncio.to_thread(...)` usados solo para envolver `MongoRepository`.
  - [ ] Mantener estable el import path `get_async_mongo_repository()` en esta pasada para no reabrir churn en consumers ya migrados.
  - [ ] Sustituir `tests/unit/test_async_mongo_adapter.py` por pruebas del factory final Motor-only o integrar esa cobertura en `test_async_mongo_repository.py`.
  - [ ] Verificar con búsqueda que no queden referencias de runtime a `AsyncMongoAdapter` ni wrappers `asyncio.to_thread(...self._sync_repo...)`.
- [ ] Actualizar docs y eliminar código muerto. — **PENDIENTE**
  - [ ] Limpiar referencias en `spec.md`, `plan.md`, `tasks.md` y runbook para que `MONGO_ASYNC_MODE=off` quede como evidencia histórica de rollout y no como modo permanente soportado.
  - [ ] Declarar explícitamente que los `asyncio.to_thread(...)` remanentes en `suggested_picks_use_case`, `live_predictions_use_case`, `use_cases.py` y `cache_service.py` no forman parte de este cleanup porque no envuelven Mongo sync.

## PRs y reviewers
- [ ] Crear PR: `feat(async-mongo): implement AsyncMongoRepository + tests`
  - Reviewers: `@maintainer`, `@principal-backend`

---

**Artefactos añadidos:**
- `backend/scripts/benchmark_async_mongo.py` — Script de benchmark dedicado MongoDB
- `docker-compose.dev.yml` — Añadido `MONGO_ASYNC_MODE` env var
- `backend/tests/unit/test_async_mongo_repository.py` — Cobertura unitaria directa del repo async
