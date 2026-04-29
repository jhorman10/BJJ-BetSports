# Plan de Migración y Auditoría — Async Mongo (Motor)

## Objetivo
Entregar una implementación nativa async de la capa MongoDB, validar su rendimiento
en staging y desplegarla gradualmente a producción sin impactar a los usuarios.

## Fases y estimaciones

1) Baseline y preparación — 1 día ✓
   - Recolectar métricas actuales (p50/p95, throughput) para endpoints críticos. **(deferido a post-deploy)**
   - Identificar queries más consumidas y hotspots (N+1, full collection scans).

2) Implementación `AsyncMongoRepository` — 2-3 días ✓
   - Implementar clase Motor-native con paridad de API. **COMPLETO**
   - Escribir tests unitarios focalizados del repo async. **COMPLETO**

3) Integración y migración incremental — 1-2 días ✓
   - Actualizar DI (`dependencies.py`) y migrar call-sites críticos. **COMPLETO**
   - Mantener `AsyncMongoAdapter` durante esta fase para fallback. **COMPLETO**

4) Pruebas y benchmarking en staging — 1 día
   - Ejecutar scripts de carga y comparar con baseline. **(pendiente en staging/endpoints)**
   - Verificar errores y latencias bajo concurrencia. **(pendiente en staging/endpoints)**
   - Harness listo: `scripts/benchmark_async.py --base-url ... --header ...` **(ya preparado y validado localmente)**
   - Intento contra despliegue publicado en Render capturado en `backend/tmp/benchmark_summary.json`: bloqueado por `503` en `/api/v1/predictions/league/E0` y `429` en `/api/v1/predictions/match/m_1001` y `/api/v1/suggested-picks/match/m_1001`. **(requiere host sano o bypass para continuar)**

5) Staged rollout y monitoreo — 1 día
   - Desplegar a un subconjunto de instancias (canary) o habilitar `MONGO_ASYNC_MODE`. **(pendiente)**
   - Monitorear métricas (latencia, errores, CPU, mem) por 1-2 horas. **(pendiente)**
   - Runbook preparado en `backend/specs/async-mongo-migration/canary-runbook.md`. **(completo a nivel documental)**

6) Cleanup y remoción de fallback — 0.5-1 día
   - Precondición: baseline/canary/promotion validados con el runbook actual. **(pendiente)**
   - Colapsar `get_async_mongo_repository()` a un path Motor-only y retirar las ramas `MONGO_ASYNC_MODE=off` y auto-fallback. **(pendiente)**
   - Eliminar `AsyncMongoAdapter`, su `_sync_repo` y los `asyncio.to_thread(...)` usados solo para envolver `MongoRepository`. **(pendiente)**
   - Mantener estable la superficie de import `get_async_mongo_repository()` en esta pasada para evitar churn innecesario en consumers ya migrados. **(pendiente)**
   - Actualizar tests/docs para reflejar que el fallback sync deja de existir como comportamiento soportado. **(pendiente)**
   - Dejar explícito que los `asyncio.to_thread(...)` remanentes en predicción/caché quedan fuera de esta spec porque no son deuda de Mongo async. **(pendiente)**

## Entregables por fase
- Scripts de benchmark reproducibles
- `AsyncMongoRepository` con tests
- PR de migración con lista de call-sites actualizados
- Dashboard de métricas comparativas

## Criterios para avanzar a la siguiente fase
- Tests unitarios y de integración pasan en CI.
- Benchmarks en staging muestran latencias aceptables o mejoras.
- No errores críticos en logs durante periodo de canary.

## Progreso reciente
- Se añadió cobertura unitaria dedicada en `backend/tests/unit/test_async_mongo_repository.py`.
- `AsyncMongoRepository` ahora garantiza paridad de índices con `MongoRepository` y espera la inicialización de índices también cuando se construye dentro de un event loop.
- El script `scripts/benchmark_async_mongo.py` ahora pre-siembra documentos de lectura y persiste resultados async/sync usando el mismo payload de prueba.
- Se detectó y corrigió un bug de TTL por comparación entre `datetime` naive/aware en lecturas sync/async (`get_match_prediction`, `get_cached_response`).
- Se ejecutó un benchmark local ampliado async vs sync con Mongo disponible y se guardaron artefactos en `backend/tmp/benchmark_async_mongo.json` y `backend/tmp/benchmark_async_mongo_full_local.json`.
- `scripts/benchmark_async.py` ahora soporta modo `external` con `--base-url`, `--header` y `--timeout`, validado end-to-end contra un HTTP server local controlado.
- El primer intento de benchmark contra un despliegue real ya quedó guardado, pero mostró bloqueo del entorno externo (`503`/`429`) en vez de métricas de aplicación útiles.
- El preflight repetido el 2026-04-29 confirmó que el bloqueo externo sigue activo y es más específico: Render responde `Service Suspended` (`x-render-routing: suspend`) en `/health` y `/api/v1/predictions/*`, mientras `suggested-picks` cae en challenge `403` de Cloudflare.
- Ya existe runbook de canary/rollback para el siguiente paso operativo, incluyendo la precondición de `MONGO_URI`/`MONGO_DB_NAME` antes de usar `MONGO_ASYNC_MODE=on`.
- `get_async_mongo_repository()` ahora falla rápido si `MONGO_ASYNC_MODE` está explícito y falta `MONGO_URI`, evitando fallback silencioso a `localhost`; esto quedó cubierto en `tests/unit/test_async_mongo_adapter.py`.
- El footprint del cleanup ya quedó acotado: no hay consumers directos de `AsyncMongoAdapter`; los consumers async importan `get_async_mongo_repository()` y el shim se concentra en `src/infrastructure/repositories/async_mongo_adapter.py`.
- También quedó separado el ruido: los `asyncio.to_thread(...)` remanentes en `use_cases`, `live_predictions_use_case`, `suggested_picks_use_case` y `cache_service` responden a trabajo CPU/cache sync, no al fallback Mongo.
- La siguiente fase real ya no es “escribir tests”, sino ejecutar benchmark de endpoints en staging y producir evidencia de rollout/canary.
