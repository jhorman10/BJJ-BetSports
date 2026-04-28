# Execution Order — Contexto doméstico real para torneos internacionales

Objetivo
--------
Convertir el spec en una secuencia de implementación archivo por archivo, minimizando riesgo,
manteniendo slices verificables y evitando mezclar a la vez datos, estadísticas, features y
use cases sin una base contractual estable.

Reglas de ejecución
-------------------
- No tocar entrenamiento e inferencia en el mismo patch inicial. Primero cerrar contratos.
- Cada fase debe terminar con pruebas focalizadas antes de pasar a la siguiente.
- No introducir features nuevas hasta que el constructor contextual de estadísticas exista.
- No reutilizar `calculate_team_statistics()` plano en rutas internacionales una vez exista el
  constructor contextual.

Fase 0 — Taxonomía y contratos base
-----------------------------------

### Archivos a editar
- `backend/src/domain/constants.py`
- `backend/src/core/constants.py`

### Trabajo exacto
1. Centralizar conjuntos como:
   - `CLUB_INTERNATIONAL_LEAGUES`
   - `NATIONAL_TEAM_TOURNAMENTS`
   - `ALL_INTERNATIONAL_TOURNAMENTS`
2. Confirmar que `LIB`, `SUD`, `UCL`, `UEL`, `UECL`, `EURO`, `WC` queden en la misma fuente de
   verdad.
3. Sustituir listas hardcodeadas repetidas en el resto del backend por imports desde esta capa.

### Validación focalizada
- `pytest backend/tests/unit/test_train_model_optimized.py -q`
- Si se toca mapeo de ligas visible para API: `pytest backend/tests/unit/test_league_mapper.py -q`

### Resultado de salida
- Una sola taxonomía internacional, sin duplicidad semántica.

Fase 1 — Resolver contexto por participante
-------------------------------------------

### Archivos a crear
- `backend/src/domain/services/team_competition_context_resolver.py`
- `backend/tests/unit/test_team_competition_context_resolver.py`

### Archivos a editar
- `backend/src/domain/services/__init__.py`
- `backend/src/domain/services/statistics_service.py`

### Trabajo exacto
1. Crear un resolvedor explícito para distinguir `club` vs `national_team`.
2. Implementar resolución de competencia base para clubes con nombre normalizado, frecuencia,
   recencia y consistencia temporal.
3. Para selecciones, impedir el uso de ligas de clubes como pseudo-contexto.
4. Definir el contrato de salida del resolvedor:
   - tipo de participante
   - competencia base
   - competencias de soporte
   - score o nivel de confianza
   - metadata de evidencia

### Validación focalizada
- `pytest backend/tests/unit/test_team_competition_context_resolver.py -q`
- `mypy backend/src/domain/services/team_competition_context_resolver.py`

### Resultado de salida
- Un resolvedor estable y testeado que todavía no toca entrenamiento ni use cases.

Fase 2 — Bundle contextual de datos
-----------------------------------

### Archivos a editar
- `backend/src/domain/entities/entities.py`
- `backend/src/application/services/training_data_service.py`

### Archivos a crear
- `backend/tests/unit/test_training_data_service_international_context.py`

### Trabajo exacto
1. Definir un contrato explícito para separar:
   - `target_matches`
   - `support_matches`
   - `support_matches_by_team`
   - `coverage_report`
2. Mantener compatibilidad para ligas domésticas normales.
3. Para torneos internacionales de clubes:
   - extraer participantes del corpus objetivo;
   - resolver liga doméstica por participante;
   - traer soporte doméstico e internacional real.
4. Para `EURO` y `WC`:
   - construir soporte nacional real, no de clubes.

### Validación focalizada
- `pytest backend/tests/unit/test_training_data_service_international_context.py -q`
- `mypy backend/src/application/services/training_data_service.py`

### Resultado de salida
- `TrainingDataService` deja de devolver un universo ambiguo cuando el torneo es internacional.

Fase 3 — Constructor contextual de estadísticas
-----------------------------------------------

### Archivos a editar
- `backend/src/domain/entities/entities.py`
- `backend/src/domain/services/statistics_service.py`

### Archivos a crear
- `backend/tests/unit/test_statistics_service_international_context.py`

### Trabajo exacto
1. Completar `TeamStatistics` con:
   - `target_competition_stats`
   - metadata de cobertura o resolución
2. Añadir una función model-facing nueva, por ejemplo:
   - `build_contextual_team_statistics(...)`
3. Reusar la lógica base existente en vez de reescribir fórmulas.
4. Mantener `calculate_team_statistics()` como contrato legacy solo donde siga siendo válido.

### Validación focalizada
- `pytest backend/tests/unit/test_statistics_service_international_context.py -q`
- `mypy backend/src/domain/services/statistics_service.py`

### Resultado de salida
- Ya existe una entidad de estadísticas apta para entrenamiento e inferencia internacional.

Fase 4 — Match aggregation y rutas de historia
----------------------------------------------

### Archivos a editar
- `backend/src/domain/services/match_aggregator_service.py`
- `backend/src/application/use_cases/use_cases.py`
- `backend/src/application/use_cases/live_predictions_use_case.py`
- `backend/src/application/use_cases/suggested_picks_use_case.py`

### Archivos a crear o extender
- `backend/tests/unit/test_live_predictions_use_case.py`
- `backend/tests/unit/test_use_cases_helpers.py`

### Trabajo exacto
1. Reemplazar listas limitadas a UEFA por la nueva taxonomía común.
2. Hacer que `LIB` y `SUD` reciban el mismo tratamiento operativo que `UCL`, `UEL`, `UECL`.
3. Dejar de depender solo de historia por `match.league.id` cuando el match sea internacional.
4. Pasar a usar el bundle contextual y el constructor contextual de estadísticas en las rutas
   model-facing.

### Validación focalizada
- `pytest backend/tests/unit/test_live_predictions_use_case.py -q`
- `pytest backend/tests/unit/test_use_cases_helpers.py -q`

### Resultado de salida
- Las rutas internacionales ya no trabajan con historia plana por torneo aislado.

Fase 5 — Restaurar paridad de features en entrenamiento
------------------------------------------------------

### Archivos a editar
- `backend/src/application/services/ml_training_orchestrator.py`
- `backend/src/application/services/ml_training_orchestrator_helper.py`
- `backend/src/domain/services/ml_feature_extractor.py`

### Archivos a crear o extender
- `backend/tests/unit/test_ml_training_orchestrator.py`
- `backend/tests/unit/test_ml_feature_extractor.py`

### Trabajo exacto
1. Hacer que el entrenamiento del clasificador de picks deje de llamar:
   - `extract_features(pick)`
2. Pasar `match`, `home_stats` y `away_stats` reales al extractor.
3. Añadir una constante o guard de longitud del vector de features.
4. Asegurar que el modelo vea durante entrenamiento las mismas señales que verá en inferencia.

### Validación focalizada
- `pytest backend/tests/unit/test_ml_training_orchestrator.py -q`
- `pytest backend/tests/unit/test_ml_feature_extractor.py -q`
- `mypy backend/src/application/services/ml_training_orchestrator.py`
- `mypy backend/src/domain/services/ml_feature_extractor.py`

### Resultado de salida
- Fin del skew entre entrenamiento e inferencia para el clasificador de picks.

Fase 6 — Refinamiento ML en inferencia
--------------------------------------

### Archivos a editar
- `backend/src/domain/services/picks_service.py`
- `backend/src/domain/services/ai_picks_service.py`
- `backend/src/domain/services/prediction_service.py`

### Archivos a crear o extender
- `backend/tests/unit/test_prediction_service_ml_context.py`
- `backend/tests/unit/test_picks_service_ml_context.py`

### Trabajo exacto
1. Garantizar que todas las rutas que llaman `MLFeatureExtractor.extract_features()` usen el
   mismo contrato contextual.
2. Revisar refinement en batch e individual para que no vuelvan a caer en `extract_features(p)`
   sin contexto cuando el modelo lo requiera.
3. Mantener fallback estadístico solo cuando falte modelo o falte contexto real suficiente.

### Validación focalizada
- `pytest backend/tests/unit/test_prediction_service_ml_context.py -q`
- `pytest backend/tests/unit/test_picks_service_ml_context.py -q`

### Resultado de salida
- Todas las rutas model-facing quedan alineadas con el contrato de features cerrado en Fase 5.

Fase 7 — Observabilidad y trazabilidad
--------------------------------------

### Archivos a editar
- `backend/src/application/services/ml_training_orchestrator.py`
- `backend/src/application/services/training_data_service.py`
- `backend/src/domain/services/match_aggregator_service.py`

### Archivos a crear o extender
- `backend/tests/unit/test_ml_traceability.py`

### Trabajo exacto
1. Añadir counters y metadata de cobertura:
   - equipos con contexto completo;
   - equipos con resolución ambigua;
   - equipos sin contexto doméstico;
   - selecciones con baseline nacional insuficiente.
2. Persistir o loggear esta señal donde ya existan reportes de entrenamiento.

### Validación focalizada
- `pytest backend/tests/unit/test_ml_traceability.py -q`

### Resultado de salida
- El sistema puede demostrar qué tan bien enriqueció cada torneo.

Fase 8 — Integración y no regresión
-----------------------------------

### Archivos a crear o extender
- `backend/tests/integration/test_international_tournament_context.py`
- `backend/tests/integration/test_suggested_picks_feedback.py`

### Casos mínimos
1. `LIB` con dos clubes de ligas domésticas distintas.
2. `SUD` con cobertura parcial pero degradación real, no inventada.
3. `UCL` con mezcla doméstica + internacional del club.
4. `EURO` o `WC` con baseline nacional y sin contaminación de clubes.
5. Regresión doméstica simple (`E0` o `SP1`) para confirmar que el cambio no rompe ligas ya
   estables.

### Validación focalizada
- `pytest backend/tests/integration/test_international_tournament_context.py -q`

Fase 9 — Gate final
-------------------

### Comandos de cierre
- `pytest backend/tests/unit -q`
- `pytest backend/tests/integration -q`
- `bash scripts/quality_gate.sh backend`

### Condición de terminado
- No hay rutas internacionales model-facing que dependan de stats planas si ya existe el
  constructor contextual.
- El entrenamiento del clasificador de picks usa el mismo contrato de features que la
  inferencia.
- `LIB` y `SUD` quedan cubiertos explícitamente como torneos internacionales de primera clase.