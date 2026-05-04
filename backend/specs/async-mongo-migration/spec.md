---
title: Migración a MongoDB async (Motor) y Auditoría de Rendimiento
author: Equipo Backend (Pair: Principal Backend Engineer)
date: 2026-04-20
status: in-progress
tags: [performance, migration, async, mongodb, motor]
---

Resumen ejecutivo
------------------
Esta especificación describe la migración controlada de la capa de persistencia MongoDB
a una implementación nativa async basada en `motor` (AsyncIOMotorClient), junto con
un plan de auditoría de rendimiento y validación. Se busca eliminar llamadas bloqueantes
desde handlers/paths `async` (FastAPI), reducir latencias en endpoints críticos y
proveer un camino seguro de rollback usando un adaptador híbrido (`AsyncMongoAdapter`).

Contexto y motivación
----------------------
- Hoy la base de código expone llamadas síncronas a Mongo (PyMongo / repo síncrono)
  desde contextos `async`, lo que puede bloquear el event loop y causar latencias
  y problemas de concurrencia bajo carga.
- Ya se introdujeron parches de baja fricción: `asyncio.to_thread(...)`, batching
  de predicciones y un `AsyncMongoAdapter` que usa `motor` cuando está disponible
  o envuelve el repo síncrono usando `to_thread`.
- El objetivo ahora es completar la migración a una implementación `AsyncMongoRepository`
  basada en `motor`, formalizar la estrategia de despliegue y garantizar métricas de
  rendimiento aceptables antes de eliminar el fallback.

Alcance (in-scope)
-------------------
- Implementar `AsyncMongoRepository` (Motor-native) que ofrezca paridad de API con
  `MongoRepository` actual.
- Añadir/actualizar fábrica DI (`get_async_mongo_repository`) y ajustes en
  `dependencies.py` para exponer la dependencia en contextos async.
- Actualizar pruebas unitarias/integración y CI para soportar `motor`.
- Ejecutar auditoría de rendimiento y benchmark antes/después en endpoints críticos
  (`/suggested-picks`, `/live-predictions`, etc.).

Fuera de alcance (out-of-scope)
-----------------------------
- Reescribir la lógica ML o la arquitectura general de servicios.
- Reemplazar otras dependencias sync (p.ej. `diskcache`) por alternativas async en
  esta iteración (se evaluará en fases posteriores).

Requisitos y criterios de aceptación
-----------------------------------
- Los tests unitarios y de integración existentes pasan (sin introducir flakiness).
- No quedan llamadas síncronas a la base de datos ejecutadas directamente desde
  handlers `async` (detección por grep y revisión de code paths críticos).
- Los endpoints críticos muestran mejora o no empeoran significativamente: objetivo
  inicial: reducir p95 de latencia en 20-40% para `suggested-picks` bajo carga.
- Despliegue con `MONGO_ASYNC_MODE=true` (o similar) debe permitir activar Motor
  sin requerir rollback de esquema ni downtime mayor a X minutos.

Diseño propuesto
----------------
- Implementar `AsyncMongoRepository` (archivo: `backend/src/infrastructure/repositories/async_mongo_repository.py`) que:
  - Use `AsyncIOMotorClient` y colecciones equivalentes.
  - Exporte métodos `async` en paridad con `MongoRepository` (p.ej. `get_match_prediction`, `bulk_save_predictions`, `get_training_result_with_timestamp`, `save_training_result`, etc.).
  - Mantenga índices y nombres de colecciones consistentes con la impl. síncrona.
- Mantener el `AsyncMongoAdapter` como shim de compatibilidad durante migración.
- DI: En `dependencies.py` exponer `get_async_mongo_repository()` para uso en código async.
- Feature-flag / Env: `MONGO_ASYNC_MODE` o depender de la disponibilidad de `motor`.
- CI: Añadir `motor` a `pyproject.toml` extras / CI env; asegurar `pytest-asyncio` configurado.

Plan de migración (alto nivel)
-----------------------------
1. Baseline y métricas: medir latencias actuales y throughput en endpoints críticos.
2. Implementar `AsyncMongoRepository` con tests unitarios (local Motor client).
3. Integración: cambiar consumidores async para usar `get_async_mongo_repository()`.
4. Ejecutar pruebas y benchmarks en entorno de staging (Motor ON).
5. Staged rollout a producción con monitoreo (feature flag o env toggle).
6. Cleanup: eliminar `to_thread` wrappers innecesarios y el fallback cuando seguro.

Riesgos y mitigaciones
----------------------
- Riesgo: regresión de rendimiento por diseño de consultas async.
  - Mitigación: benchmarks y pruebas de carga; mantener `to_thread` fallback temporal.
- Riesgo: tests no cubren paths de concurrencia.
  - Mitigación: añadir tests de integración que simulen múltiples requests simultáneos.

Pruebas y validación
--------------------
- Unit tests para cada método nuevo en `AsyncMongoRepository`.
- Integration tests que ejecuten `live_predictions`/`suggested_picks` en staging.
- Benchmarks reproducibles:
  - repositorio Mongo: `scripts/benchmark_async_mongo.py`
  - endpoints HTTP: `scripts/benchmark_async.py` en modo local o `--base-url` para staging/canary.

Entregables
-----------
- `backend/specs/async-mongo-migration/spec.md` (este archivo)
- `backend/specs/async-mongo-migration/plan.md`
- `backend/specs/async-mongo-migration/tasks.md`
- `backend/specs/async-mongo-migration/canary-runbook.md`

Referencias
----------
- `backend/src/infrastructure/repositories/async_mongo_adapter.py` (ya presente)
- Parches aplicados: `use_cases` async migrations, `football_data_org` updates.

Estado actual verificado
-----------------------
- `AsyncMongoRepository` existe y ya tiene pruebas unitarias dedicadas para:
  - paridad de índices con el repo síncrono,
  - inicialización segura dentro de un event loop,
  - contrato de `save/get_match_prediction()` con `TTL` y `model_metadata`.
- Durante la validación del benchmark se detectó y corrigió un bug real de TTL en lecturas Mongo:
  `expires_at` podía volver desde Mongo como `datetime` naive y romper las lecturas con
  `TypeError: can't compare offset-naive and offset-aware datetimes` tanto en
  `MongoRepository` como en `AsyncMongoRepository` y `AsyncMongoAdapter`.
  - Fix aplicado con normalización compartida en `src/utils/time_utils.py:is_future_time(...)`.
  - Impacto validado: `get_match_prediction` y `get_cached_response` async/sync dejaron de fallar.
- Se ejecutó benchmark local ampliado con Mongo disponible usando
  `python scripts/benchmark_async_mongo.py -n 25 -c 5 --operations get_match_prediction get_match_predictions_bulk save_match_prediction bulk_save_predictions get_cached_response save_cached_response --sync --output tmp/benchmark_async_mongo_full_local.json`.
  - Async local (`errors=0` en todas las operaciones):
    - `get_match_prediction p50=0.63ms`
    - `get_match_predictions_bulk p50=0.52ms`
    - `save_match_prediction p50=1.40ms`
    - `bulk_save_predictions p50=1.15ms`
    - `get_cached_response p50=0.38ms`
    - `save_cached_response p50=0.79ms`
  - Sync local (`errors=0` en todas las operaciones):
    - `get_match_prediction p50=1.26ms`
    - `get_match_predictions_bulk p50=0.72ms`
    - `save_match_prediction p50=0.35ms`
    - `bulk_save_predictions p50=0.88ms`
    - `get_cached_response p50=0.61ms`
    - `save_cached_response p50=0.33ms`
  - Artefactos generados:
    - `backend/tmp/benchmark_async_mongo.json` (slice corto de validación)
    - `backend/tmp/benchmark_async_mongo_full_local.json` (corrida local ampliada)
- `scripts/benchmark_async.py` quedó listo para benchmark de staging/canary sin más cambios de código:
  - soporta `--base-url`, headers repetibles vía `--header "Name: Value"` y `--timeout`.
  - el modo `external` fue validado contra un HTTP server local controlado y deja `mode`, `base_url`, `requests` y `concurrency` en `backend/tmp/benchmark_summary.json`.
- Se ejecutó un intento de benchmark externo contra el despliegue publicado descubierto en `render.yaml`:
  `https://football-prediction-api-x4pm.onrender.com`.
  - Artefacto resumen: `backend/tmp/benchmark_summary.json`
  - Artefactos por endpoint:
    - `backend/tmp/benchmark_api_v1_predictions_league_E0.json`
    - `backend/tmp/benchmark_api_v1_predictions_match_m_1001.json`
    - `backend/tmp/benchmark_api_v1_suggested-picks_match_m_1001.json`
  - Resultado observado:
    - `/api/v1/predictions/league/E0` devolvió `503` en las 3/3 solicitudes.
    - `/api/v1/predictions/match/m_1001` devolvió `429` en las 3/3 solicitudes.
    - `/api/v1/suggested-picks/match/m_1001` devolvió `429` en las 3/3 solicitudes.
  - Conclusión: ya existe evidencia de benchmark externo, pero el despliegue actual no está sano ni libre de challenge/rate-limit para producir métricas útiles de aplicación.
- Se repitió el preflight operativo del runbook el 2026-04-29 contra el mismo host publicado.
  - `/health`, `/api/v1/predictions/league/E0` y `/api/v1/predictions/match/m_1001`
    devolvieron `503` con header `x-render-routing: suspend` y body
    `Service Suspended`.
  - `/api/v1/suggested-picks/match/m_1001` devolvió `403` con body
    `Just a moment...`, consistente con challenge de Cloudflare.
  - Conclusión actualizada: hoy no existe un host benchmarkable para baseline ni
    canary; el bloqueo es operativo/infraestructura externa, no del harness ni del
    repo.
- Se preparó el runbook operativo de canary/rollback en
  `backend/specs/async-mongo-migration/canary-runbook.md`.
  - Incluye precondiciones de entorno, baseline con `MONGO_ASYNC_MODE=off`,
    activación controlada con `MONGO_ASYNC_MODE=on`, señales exactas de logs y
    rollback inmediato.
  - El repo ya declara en `render.yaml` el contrato mínimo de despliegue para
    Mongo (`MONGO_URI`, `MONGO_DB_NAME=bjj_betsports`, `MONGO_ASYNC_MODE=off`),
    pero `MONGO_URI` sigue siendo manual y debe completarse con un valor real
    antes de activar `MONGO_ASYNC_MODE=on`.
- Se endureció el factory de `get_async_mongo_repository()` para que, cuando
  `MONGO_ASYNC_MODE` esté explícito en `on` u `off`, exija `MONGO_URI`
  explícito y deje de caer silenciosamente al default local `localhost`.
  - Cobertura añadida en `backend/tests/unit/test_async_mongo_adapter.py`.
- El cleanup post-validación ya quedó acotado por código real:
  - no hay consumers directos de `AsyncMongoAdapter` fuera del propio módulo,
    tests y documentación;
  - los consumers async actuales dependen del factory
    `get_async_mongo_repository()`;
  - los `asyncio.to_thread(...)` remanentes en `use_cases`,
    `live_predictions_use_case`, `suggested_picks_use_case` y `cache_service`
    no pertenecen a esta migración porque no envuelven `MongoRepository`.
- La migración sigue abierta porque el benchmark local del repositorio ya tiene evidencia, pero todavía faltan benchmark de endpoints/staging, canary y cleanup post-validación.

Siguientes pasos inmediatos
--------------------------
1. ✓ Crear `AsyncMongoRepository` con paridad de API.
2. ✓ Añadir `motor` a `requirements.txt` (ya presente).
3. ✓ Migrar call-sites async: use_cases, football_data_org, live_predictions.
4. ✓ Cubrir `AsyncMongoRepository` con pruebas unitarias focalizadas.
5. 🔄 Ejecutar benchmark de endpoints en staging con el harness ya preparado, guardar artefactos y usar ese resultado para preparar staged rollout/canary.
   - Comando base sugerido:
     `python scripts/benchmark_async.py --base-url https://<staging-host> --header "Authorization: Bearer <token>" --endpoints /api/v1/suggested-picks/match/<match_id> /api/v1/predictions/league/<league_id> /api/v1/predictions/match/<match_id> -n 50 -c 10`
  - Bloqueo actual: el host público descubierto en `render.yaml` responde `503`/`429`, así que hace falta un host staging sano o acceso/bypass que permita benchmark real.
  - Runbook listo: `backend/specs/async-mongo-migration/canary-runbook.md`
6. 🔲 Cleanup del fallback ya aterrizado para ejecución post-validación.
  - Colapsar el factory actual a Motor-only y eliminar `AsyncMongoAdapter`.
  - Mantener estable `get_async_mongo_repository()` en esta pasada para evitar churn en consumers ya migrados.
  - No mezclar en esta fase los `asyncio.to_thread(...)` de CPU/caché que no son deuda de Mongo.
