# Runbook — Canary y Rollback de Async Mongo

## Objetivo

Dejar listo el rollout controlado de `AsyncMongoRepository` usando
`MONGO_ASYNC_MODE` sin asumir infraestructura que el repo no define hoy.

## Hechos verificados en este repo

- El backend publicado en `render.yaml` es un solo servicio web:
  `football-prediction-api`.
- `render.yaml` ya declara el contrato mínimo de rollout para Mongo:
  - `MONGO_URI` como env var manual (`sync: false`)
  - `MONGO_DB_NAME=bjj_betsports` ya preconfigurado
  - `MONGO_ASYNC_MODE=off` como baseline seguro inicial
- El flag de control real es `MONGO_ASYNC_MODE` en
  `src/infrastructure/repositories/async_mongo_adapter.py`.
  - `on`: exige `AsyncMongoRepository` y falla si no puede inicializarse.
  - `off`: fuerza `AsyncMongoAdapter` con fallback sync.
  - vacío/no definido: autodetecta `motor` y hace fallback si falla.
- Cuando `MONGO_ASYNC_MODE` se fuerza explícitamente en `on` u `off`, el factory
  ya no permite fallback silencioso al default local: exige `MONGO_URI`
  explícito y pasa `mongo_uri/db_name` al repo seleccionado.
- Aunque `render.yaml` ya declara `MONGO_DB_NAME` y el baseline
  `MONGO_ASYNC_MODE=off`, `MONGO_URI` sigue siendo manual; poner
  `MONGO_ASYNC_MODE=on` sin completarlo con un valor real puede tumbar el
  servicio.
- El host público descubierto en `render.yaml`
  (`https://football-prediction-api-x4pm.onrender.com`) no está benchmarkable
  ahora mismo.
  - Evidencia previa: el intento externo guardado en
    `backend/tmp/benchmark_summary.json` devolvió `503`/`429`.
  - Evidencia más reciente (2026-04-29):
    - `/health` y los endpoints `/api/v1/predictions/*` responden `503` con
      `x-render-routing: suspend` y body `Service Suspended`.
    - `/api/v1/suggested-picks/match/m_1001` responde `403` con body
      `Just a moment...`, consistente con challenge de Cloudflare.

## Qué significa "canary" en el estado actual

Esto NO es un canary con reparto porcentual de tráfico. El repo solo define un
backend publicado y no define un segundo servicio paralelo ni una estrategia de
traffic splitting.

El rollout disponible hoy es un rollout protegido de instancia única:

1. baseline con `MONGO_ASYNC_MODE=off`
2. cambio controlado a `MONGO_ASYNC_MODE=on`
3. smoke + benchmark + observación corta
4. rollback inmediato a `off` si aparece cualquier regresión

Si se quiere un canary real, hace falta un segundo servicio/host de staging o
una topología con tráfico separable.

## Criterios para empezar

No empezar el canary hasta cumplir TODO esto:

- El host objetivo responde `200` en `/health`.
- El host objetivo no devuelve challenge/rate-limit (`429`) a los endpoints del
  benchmark.
- Existen valores válidos de `MONGO_URI` y `MONGO_DB_NAME` en el entorno del
  servicio.
  - En Render esto significa, como mínimo, completar `MONGO_URI`; `MONGO_DB_NAME`
    ya puede quedarse en `bjj_betsports`.
- Hay acceso a logs del servicio desplegado.
- Existe al menos un `match_id` y `league_id` válidos para smoke/benchmark.

## Artefactos que se deben guardar

- baseline sync:
  `backend/tmp/benchmark_summary_sync_baseline.json`
- canary async:
  `backend/tmp/benchmark_summary_async_canary.json`
- si hay rollback:
  `backend/tmp/benchmark_summary_post_rollback.json`

Como `scripts/benchmark_async.py` escribe por defecto `backend/tmp/benchmark_summary.json`,
hay que copiar el archivo inmediatamente después de cada corrida.

## Fase 0 — Preparar entorno benchmarkable

### 0.1 Verificar salud del host

```bash
cd backend
source .venv/bin/activate

python - <<'PY'
import httpx
base = 'https://<staging-host>'
for path in ('/health', '/api/v1/predictions/league/<league_id>', '/api/v1/predictions/match/<match_id>'):
    try:
        response = httpx.get(f'{base}{path}', follow_redirects=True, timeout=20.0)
        print(path, response.status_code)
    except Exception as exc:
        print(path, type(exc).__name__, exc)
PY
```

### 0.2 Verificar env vars antes de activar async estricto

En Render o en el entorno equivalente, comprobar que el servicio backend tiene:

- `MONGO_URI`
- `MONGO_DB_NAME`
- `MONGO_ASYNC_MODE=off` para baseline inicial

Si `MONGO_ASYNC_MODE` está explícito y `MONGO_URI` falta, el servicio debe
fallar rápido en vez de intentar `localhost`.

## Fase 1 — Baseline con fallback sync

### 1.1 Fijar modo sync explícito

Configurar en el servicio:

- `MONGO_ASYNC_MODE=off`

Redeploy del servicio y confirmar en logs esta línea:

```text
get_async_mongo_repository: MONGO_ASYNC_MODE=off, using AsyncMongoAdapter (sync)
```

### 1.2 Smoke baseline

```bash
cd backend
source .venv/bin/activate

python scripts/benchmark_async.py \
  --base-url https://<staging-host> \
  --header "Authorization: Bearer <token>" \
  --endpoints \
    /api/v1/suggested-picks/match/<match_id> \
    /api/v1/predictions/league/<league_id> \
    /api/v1/predictions/match/<match_id> \
  -n 20 -c 5

cp tmp/benchmark_summary.json tmp/benchmark_summary_sync_baseline.json
```

No avanzar si cualquier endpoint queda con `ok=0`, `errors>0`, `429` o `5xx`.

## Fase 2 — Canary protegido con async nativo

### 2.1 Activar async estricto

Configurar en el servicio:

- `MONGO_ASYNC_MODE=on`

Mantener `MONGO_URI` y `MONGO_DB_NAME` apuntando al Mongo real.

Redeploy del servicio y revisar logs.

Línea esperada de éxito:

```text
get_async_mongo_repository: MONGO_ASYNC_MODE=on, using AsyncMongoRepository (Motor)
```

Línea de fallo que exige rollback inmediato:

```text
MONGO_ASYNC_MODE=on but AsyncMongoRepository failed: ...
```

Línea de fallo por configuración incompleta esperable:

```text
MONGO_ASYNC_MODE explicit requires MONGO_URI to be set explicitly.
```

### 2.2 Smoke canary

```bash
cd backend
source .venv/bin/activate

python scripts/benchmark_async.py \
  --base-url https://<staging-host> \
  --header "Authorization: Bearer <token>" \
  --endpoints \
    /api/v1/suggested-picks/match/<match_id> \
    /api/v1/predictions/league/<league_id> \
    /api/v1/predictions/match/<match_id> \
  -n 20 -c 5

cp tmp/benchmark_summary.json tmp/benchmark_summary_async_canary.json
```

## Criterios de éxito del canary

Mantener async activo solo si se cumple todo esto:

- `ok > 0` y `errors = 0` en todos los endpoints benchmarkeados.
- Sin `429`, `5xx` ni timeouts en smoke/benchmark.
- Sin errores de inicialización de `AsyncMongoRepository` en logs.
- Sin aumento material de errores operativos durante la ventana de observación.

## Ventana de observación

Como el rollout actual es de instancia única, observar al menos:

- 15 minutos si el tráfico es bajo y solo hay smoke controlado.
- 30-60 minutos si el servicio recibe tráfico real durante la ventana.

Mirar específicamente:

- logs de inicialización del repo async
- `5xx` en health y endpoints de predicción
- timeouts o caídas al resolver caché/predicciones

## Rollback inmediato

### Cuándo hacer rollback

Hacer rollback sin esperar más si aparece cualquiera de estos síntomas:

- startup failure al activar `MONGO_ASYNC_MODE=on`
- `503` o `5xx` nuevos tras el cambio
- `429`/challenge del proveedor frontal que impida benchmark útil
- errores de lectura/escritura Mongo en logs

### Cómo hacer rollback

1. Cambiar env var del servicio a `MONGO_ASYNC_MODE=off`.
2. Redeploy.
3. Confirmar en logs:

```text
get_async_mongo_repository: MONGO_ASYNC_MODE=off, using AsyncMongoAdapter (sync)
```

4. Repetir smoke:

```bash
cd backend
source .venv/bin/activate

python scripts/benchmark_async.py \
  --base-url https://<staging-host> \
  --header "Authorization: Bearer <token>" \
  --endpoints \
    /api/v1/suggested-picks/match/<match_id> \
    /api/v1/predictions/league/<league_id> \
    /api/v1/predictions/match/<match_id> \
  -n 20 -c 5

cp tmp/benchmark_summary.json tmp/benchmark_summary_post_rollback.json
```

## Cierre de la spec

La spec `async-mongo-migration` se puede cerrar solo cuando existan estos tres
artefactos con endpoints reales y entorno sano:

- baseline sync
- canary async exitoso
- rollback validado o promotion validada

Mientras el host publicado siga respondiendo `503`/`429`, el bloqueo es de
 entorno, no de implementación del harness.

Con la evidencia más reciente, el bloqueo concreto del host publicado es doble:

- servicio suspendido en Render para `/health` y `/api/v1/predictions/*`
- challenge 403 en Cloudflare para `/api/v1/suggested-picks/*`