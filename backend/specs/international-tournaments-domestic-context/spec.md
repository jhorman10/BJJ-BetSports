---
title: Contexto doméstico real para torneos internacionales
author: GitHub Copilot
date: 2026-04-28
status: proposed
tags: [backend, ml, training, predictions, tournaments, data-quality]
---

Resumen ejecutivo
------------------
Esta intervención corrige un problema estructural del backend ML: el sistema ya reconoce
torneos internacionales como `LIB`, `SUD`, `UCL`, `UEL`, `UECL`, `EURO` y `WC`, pero no
garantiza todavía un flujo end-to-end que alimente al modelo con contexto real y suficiente
de cada equipo para esos torneos.

La validación del código actual muestra tres brechas concretas:
- `TrainingDataService.fetch_comprehensive_training_data()` trae partidos de las ligas
  solicitadas y los unifica por fuente, pero no hace cross-fetch doméstico por equipo cuando
  el objetivo es un torneo internacional.
- `StatisticsService` sí tiene soporte parcial para separar `domestic_stats` e
  `international_stats`, pero la ruta estándar de predicción sigue usando
  `calculate_team_statistics()`, que devuelve estadísticas planas.
- `MLFeatureExtractor` ya define features doméstico-vs-internacional, pero el entrenamiento
  del clasificador de picks hoy llama `extract_features(pick)` sin `match`, `home_stats` ni
  `away_stats`, por lo que esas señales no se aprenden realmente.

El objetivo de este cambio es que cualquier partido internacional use contexto real del equipo
participante, sin inventar datos, y que el contrato de features sea idéntico entre
entrenamiento e inferencia.

Estado actual verificado
------------------------
- `backend/src/application/services/training_data_service.py`
  - Orquesta GitHub dataset, CSV/Football-Data UK, Football-Data.org, ESPN y OpenFootball.
  - El dataset final se arma solo con las ligas pedidas en la invocación.
  - No existe una fase explícita de "resolver liga doméstica del participante" ni un corpus
    de soporte separado para contexto.
- `backend/src/domain/services/match_aggregator_service.py`
  - Agrega historia por liga/fuente y hace merge profundo.
  - Tiene soporte especial para torneos europeos en comentarios y ventanas de tiempo, pero no
    implementa fetch cruzado doméstico por participante.
  - `get_upcoming_matches()` trata como torneos extendidos a `UCL`, `UEL`, `UECL`, `EURO`,
    `WC`, pero no incluye `LIB` ni `SUD` en esa lista.
- `backend/src/domain/services/statistics_service.py`
  - `calculate_team_statistics()` produce un `TeamStatistics` plano y es el camino usado por
    varias rutas de predicción.
  - `update_team_stats_dict()` sí separa `domestic_stats` e `international_stats` para
    `UCL`, `UEL`, `UECL`, `WC`, `EURO`, `LIB`, `SUD`.
  - `convert_to_domain_stats()` preserva esos sub-bloques en la entidad de dominio.
- `backend/src/domain/entities/entities.py`
  - `TeamStatistics` ya contiene `domestic_stats` e `international_stats`, lo que confirma
    que la intención del diseño ya existía pero quedó incompleta.
- `backend/src/domain/services/ml_feature_extractor.py`
  - Ya incorpora features derivadas de `domestic_stats` e `international_stats`.
  - Esas features dependen de recibir `home_stats` y `away_stats` contextualizados.
- `backend/src/application/services/ml_training_orchestrator.py`
  - El entrenamiento mantiene un cache incremental por equipo con `update_team_stats_dict()`.
  - Sin embargo, al crear las features del clasificador de picks usa `extract_features(pick)`
    sin contexto de partido/equipo, anulando en la práctica las features nuevas.
- `backend/src/application/use_cases/use_cases.py`,
  `backend/src/application/use_cases/live_predictions_use_case.py` y
  `backend/src/application/use_cases/suggested_picks_use_case.py`
  - Siguen usando `calculate_team_statistics()` sobre historia agregada, lo que rompe la
    paridad con el camino incremental del entrenamiento.

Problema a resolver
-------------------
Para torneos internacionales de clubes, el modelo necesita dos contextos reales y distintos:
- historial del equipo en su liga doméstica reciente;
- historial del equipo en competiciones internacionales relevantes, idealmente distinguiendo el
  torneo objetivo del resto.

Para torneos de selecciones, el equivalente del contexto doméstico no es la liga del club,
porque ese dato no corresponde semánticamente al objeto a predecir. En ese caso se necesita:
- historial reciente de la selección fuera del torneo objetivo (clasificatorias, amistosos,
  Nations League u otras competiciones oficiales si la fuente lo permite);
- historial de la selección dentro del torneo objetivo o de su misma familia competitiva.

Hoy el sistema mezcla o pierde estos contextos de forma inconsistente. El resultado visible es
una señal pobre para torneos internacionales: picks muy homogéneos, poca diferenciación real
entre equipos y ausencia de una fuente de verdad consistente entre entrenamiento e inferencia.

Objetivos
---------
- Garantizar contexto real por equipo para todos los torneos internacionales soportados:
  `LIB`, `SUD`, `UCL`, `UEL`, `UECL`, `EURO`, `WC`.
- Mantener un dataset etiquetado limpio: los partidos objetivo del torneo siguen siendo el
  corpus de entrenamiento del ejemplo; el contexto adicional se usa para construir features,
  no para contaminar las etiquetas del torneo objetivo.
- Unificar entrenamiento e inferencia bajo el mismo contrato estadístico y el mismo contrato
  de features.
- No inventar contexto cuando el sistema no pueda resolverlo. Ante ambigüedad, degradar con
  datos reales disponibles y marcar la cobertura como incompleta.
- Asegurar trazabilidad y pruebas suficientes para que la mejora no rompa ligas domésticas ya
  estables.

Fuera de alcance
----------------
- Reescribir la heurística de picks o la lógica de negocio de cuotas.
- Añadir nuevas casas de apuestas o mercados.
- Cambios de UI fuera de pequeños ajustes de listas/taxonomías si se necesitan más adelante.
- Resolver deuda histórica no relacionada del repo fuera de los slices tocados.

Definiciones operativas
-----------------------
- `target match`: partido del torneo que se quiere predecir o usar como ejemplo etiquetado.
- `target corpus`: conjunto de partidos del torneo objetivo usados como ejemplos de
  entrenamiento para ese slice.
- `support corpus`: partidos adicionales usados solo para construir contexto estadístico del
  equipo. No son ejemplos etiquetados del torneo objetivo.
- `club international tournament`: `LIB`, `SUD`, `UCL`, `UEL`, `UECL`.
- `national team tournament`: `EURO`, `WC`.
- `resolver coverage`: señal de cuántos equipos tuvieron contexto resuelto correctamente y de
  qué tipo.

Requisitos funcionales
----------------------
1. El sistema debe distinguir entre torneos internacionales de clubes y torneos de selecciones.
2. Para torneos internacionales de clubes, el contexto del equipo debe incluir:
   - partidos recientes en su liga doméstica principal;
   - partidos recientes en competiciones internacionales de clubes;
   - historial específico del torneo objetivo si existe.
3. Para `EURO` y `WC`, el contexto del equipo debe incluir:
   - partidos recientes de la selección fuera del torneo objetivo;
   - historial específico del torneo objetivo o de su familia competitiva cuando exista.
4. El entrenamiento debe seguir usando como ejemplos etiquetados los partidos del torneo
   objetivo, pero debe construir las features a partir del contexto enriquecido del equipo.
5. La inferencia debe usar exactamente el mismo contrato de estadísticas y features que el
   entrenamiento.
6. Si el sistema no puede resolver la liga doméstica o el contexto equivalente del equipo,
   debe degradar con datos reales disponibles y registrar esa falta de cobertura.
7. El merge multi-fuente debe seguir deduplicando por fecha + nombres normalizados y no puede
   duplicar partidos entre corpus objetivo y corpus de soporte.

Requisitos no funcionales
-------------------------
- Sin datos sintéticos ni defaults inventados fuera de ceros/fallbacks explícitos ya
  aceptados por el dominio.
- Compatibilidad hacia atrás para ligas domésticas que no usan contexto internacional.
- Cambios pequeños y verificables por slice.
- Instrumentación suficiente para auditar cobertura de contexto por torneo y por equipo.

Diseño propuesto
----------------

### 1. Centralizar taxonomía de torneos internacionales

Crear una fuente de verdad explícita en dominio o core, por ejemplo:
- `CLUB_INTERNATIONAL_LEAGUES = {"LIB", "SUD", "UCL", "UEL", "UECL"}`
- `NATIONAL_TEAM_TOURNAMENTS = {"EURO", "WC"}`
- `ALL_INTERNATIONAL_TOURNAMENTS = CLUB_INTERNATIONAL_LEAGUES | NATIONAL_TEAM_TOURNAMENTS`

Esto debe reemplazar listas hardcodeadas dispersas en:
- `StatisticsService.update_team_stats_dict()`
- `MatchAggregatorService.get_upcoming_matches()`
- use cases que relajan `min_matches`
- cualquier otra heurística que hoy solo contempla `UCL`, `UEL`, `UECL`

Resultado esperado:
- `LIB` y `SUD` pasan a tener el mismo trato explícito que los torneos UEFA.
- `EURO` y `WC` quedan soportados con una semántica distinta a clubes.

### 2. Introducir un resolvedor de contexto competitivo por equipo

Agregar un nuevo servicio, por ejemplo `TeamCompetitionContextResolver`, responsable de
responder para cada equipo y partido objetivo:
- tipo de participante: `club` o `national_team`;
- competencia base principal;
- competencias secundarias válidas para contexto;
- nivel de confianza de la resolución;
- evidencia usada para resolver.

#### 2.1. Resolución para torneos de clubes

Algoritmo propuesto:
1. Normalizar el nombre del equipo con la misma estrategia usada por `StatisticsService`.
2. Buscar partidos recientes no internacionales del club dentro del universo de ligas
   domésticas soportadas.
3. Inferir la liga doméstica dominante por frecuencia, recencia y consistencia estacional.
4. Si el equipo aparece en varias ligas por ascenso/descenso o cambio de temporada, elegir la
   competencia dominante en la ventana temporal más cercana al `target match`.
5. Si la inferencia sigue ambigua, no inventar una liga: usar solo historial internacional y
   marcar cobertura incompleta.

#### 2.2. Resolución para torneos de selecciones

No se debe usar la liga de los clubes como pseudo-contexto de una selección.

Regla propuesta:
- `baseline_context` = partidos reales de la selección fuera del torneo objetivo dentro de una
  ventana temporal razonable.
- `competition_context` = partidos de la selección dentro del torneo objetivo o su familia.

Esto requiere que el resolvedor identifique al participante como selección nacional y no como
club, evitando contaminación del contexto.

### 3. Separar corpus objetivo y corpus de soporte

La raíz del problema no se resuelve metiendo partidos domésticos como si fueran ejemplos del
torneo internacional. Eso mezclaría etiquetas distintas.

Se propone que `TrainingDataService` y las rutas de predicción construyan dos niveles de datos:

#### 3.1. Target corpus
- partidos del torneo solicitado;
- siguen siendo la fuente de etiquetas y el orden natural del entrenamiento/predicción.

#### 3.2. Support corpus
- historial doméstico de los participantes resueltos;
- historial internacional adicional del mismo club o selección;
- partidos equivalentes no-target para selecciones (`EURO`, `WC`).

#### 3.3. Contrato sugerido

En vez de devolver solo `List[Match]`, introducir un contenedor explícito, por ejemplo:

```python
@dataclass
class CompetitionContextBundle:
    target_matches: list[Match]
    support_matches: list[Match]
    support_matches_by_team: dict[str, list[Match]]
    coverage_report: dict[str, Any]
```

No es obligatorio usar exactamente ese nombre, pero sí separar semánticamente ambos universos.

### 4. Cambios en `TrainingDataService`

`fetch_comprehensive_training_data()` debe evolucionar para soportar contexto internacional real.

#### 4.1. Comportamiento deseado para ligas domésticas
- no cambia materialmente;
- sigue trayendo la liga objetivo y unificando fuentes como hoy.

#### 4.2. Comportamiento deseado para torneos internacionales de clubes
1. Traer `target_matches` del torneo solicitado (`LIB`, `SUD`, `UCL`, `UEL`, `UECL`).
2. Extraer participantes únicos del corpus objetivo.
3. Resolver la liga doméstica dominante de cada participante con el nuevo resolver.
4. Traer historia doméstica real de esas ligas para esos equipos.
5. Traer historia internacional adicional del club.
6. Unificar y deduplicar el `support corpus` sin duplicar el `target corpus`.

#### 4.3. Comportamiento deseado para `EURO` y `WC`
1. Traer `target_matches` del torneo objetivo.
2. Extraer selecciones participantes.
3. Traer historial reciente de la selección fuera del torneo objetivo usando fuentes reales por
   equipo/nombre.
4. Traer historial del torneo objetivo o familia competitiva si existe.
5. Construir `support corpus` nacional, no doméstico de clubes.

#### 4.4. Fuentes y prioridad sugerida

Usar primero las fuentes ya integradas y verificadas en el repo:
- `GitHub dataset`
  - fuerte para `LIB`, `SUD`, `COL1`, `ARG1`, `BRA1`;
  - útil para profundidad histórica sin castigar rate limits.
- `Football-Data UK / CSV`
  - fuerte para ligas europeas y contexto doméstico clásico.
- `ESPN`
  - útil para torneos internacionales, fixtures recientes y stats avanzadas.
- `Football-Data.org`
  - útil como fuente secundaria y de team history, con cuidado por cobertura y rate limit.
- `OpenFootball`
  - fallback para historia donde aplique.

Regla obligatoria:
- la selección de fuente debe ser explícita por familia de torneo y registrarse en el reporte
  de cobertura.

### 5. Cambios en `MatchAggregatorService` y rutas de predicción

La ruta de predicción no puede seguir usando un contrato estadístico distinto al del
entrenamiento.

#### 5.1. Requisito

Las rutas que hoy llaman `_get_historical_matches()` o `calculate_team_statistics()` deben
reutilizar el mismo resolvedor y el mismo bundle contextual que el entrenamiento.

#### 5.2. Ajustes mínimos necesarios
- `get_upcoming_matches()` debe tratar `LIB` y `SUD` como torneos extendidos, igual que UEFA.
- la relajación de `min_matches` no puede quedarse solo en `UCL`, `UEL`, `UECL`; debe cubrir
  todo el conjunto internacional definido por la nueva taxonomía, con reglas diferenciadas si
  hace falta para selecciones.
- `_get_historical_matches()` y equivalentes deben dejar de depender solo de la liga del partido
  objetivo cuando este sea internacional.

### 6. Evolución de `TeamStatistics`

`TeamStatistics` ya tiene `domestic_stats` e `international_stats`, pero falta cerrar el
modelo para que represente de forma útil el contexto del torneo objetivo.

#### 6.1. Mantener compatibilidad, pero completar semántica

Se propone añadir un bloque adicional explícito, por ejemplo:
- `target_competition_stats`
- `context_resolution_metadata`

Ejemplo conceptual:

```python
target_competition_stats: Optional[dict[str, Any]] = None
context_resolution_metadata: Optional[dict[str, Any]] = None
```

#### 6.2. Significado esperado por tipo de torneo
- Club internacional:
  - `domestic_stats`: liga/copa doméstica del club;
  - `international_stats`: historial internacional agregado del club;
  - `target_competition_stats`: historial específico en `LIB`, `SUD`, `UCL`, etc.
- Selección nacional:
  - `domestic_stats`: `None` o bloque vacío, no se usa como señal de clubes;
  - `international_stats`: historial internacional agregado de la selección;
  - `target_competition_stats`: historial específico en `EURO` o `WC`.

#### 6.3. Nueva función model-facing

No seguir usando `calculate_team_statistics()` como única entrada para ML en torneos
internacionales.

Agregar una función explícita, por ejemplo:
- `build_contextual_team_statistics(team_name, target_match, target_matches, support_matches)`

Responsabilidades:
- construir stats globales del equipo con el contexto correcto;
- llenar `domestic_stats`, `international_stats` y `target_competition_stats`;
- adjuntar metadata de cobertura.

### 7. Cambios en `StatisticsService`

`StatisticsService` debe seguir siendo la fuente de verdad de agregación, pero con una capa
contextual model-facing encima.

#### 7.1. Mantener la lógica base estable
- No reescribir fórmulas básicas existentes.
- Reusar `create_empty_stats_dict()`, `_update_raw_stats_dict()` y
  `update_team_stats_dict()` donde sea razonable.

#### 7.2. Cambios obligatorios
- extraer helpers para acumular:
  - stats globales;
  - stats domésticas;
  - stats internacionales;
  - stats del torneo objetivo.
- soportar ventanas de contexto configurables por tipo de competencia.
- registrar cuando el equipo llega con:
  - cero historial del torneo objetivo;
  - historial doméstico incompleto;
  - resolución ambigua.

### 8. Cambios en `MLFeatureExtractor`

Las features internacionales deben existir de verdad en entrenamiento e inferencia.

#### 8.1. Requisito de paridad

Toda ruta que use el modelo debe llamar `extract_features()` con el mismo contrato:
- `pick`
- `match`
- `home_stats`
- `away_stats`

#### 8.2. Features mínimas nuevas o endurecidas
- `home_domestic_points_per_match`
- `away_domestic_points_per_match`
- `home_target_competition_points_per_match`
- `away_target_competition_points_per_match`
- `home_international_experience`
- `away_international_experience`
- `home_context_coverage`
- `away_context_coverage`
- diferenciales entre baseline, internacional agregada y torneo objetivo

#### 8.3. Guard de contrato

Definir una constante o método que permita verificar el tamaño esperado del vector de features,
por ejemplo:

```python
EXPECTED_PICK_FEATURE_COUNT = ...
```

Eso debe usarse en tests para impedir que entrenamiento e inferencia diverjan otra vez.

### 9. Corregir la ruptura de paridad entrenamiento/inferencia

Este punto es obligatorio. Si no se corrige, el resto del esfuerzo quedará incompleto.

#### 9.1. Entrenamiento

`prepare_datasets()` debe dejar de entrenar el clasificador de picks con:

```python
extract_features(pick)
```

Debe usar el contexto real del partido y del equipo. Si el pipeline actual necesita pasar
`home_stats` y `away_stats` al cómputo de métricas, hay que modificar el helper para que esas
entidades lleguen a `feature_extractor.extract_features()`.

#### 9.2. Inferencia

Las rutas de predicción y refinamiento ML deben usar el mismo constructor de estadísticas
contextuales. Eso aplica a:
- `PicksService._apply_ml_refinement()`
- use cases de predicción por liga
- live predictions
- top picks/suggested picks cuando dependan del mismo modelo

#### 9.3. Regla de cierre

No se considera terminado mientras exista una ruta model-facing que use stats planas y otra que
use stats contextuales para el mismo modelo.

### 10. Observabilidad y auditoría

Agregar métricas y logs estructurados para responder preguntas como:
- cuántos partidos internacionales se enriquecieron con contexto completo;
- cuántos equipos quedaron sin liga doméstica resuelta;
- cuántos ejemplos usaron solo historial internacional;
- cuántos ejemplos de `EURO`/`WC` tuvieron baseline nacional suficiente.

Esto debe persistirse al menos en logs y, si el pipeline ya guarda metadatos de entrenamiento,
en el resultado de entrenamiento o en reportes auxiliares.

### 11. Compatibilidad y rollout

Se recomienda rollout por fases:
1. primero clubes internacionales: `LIB`, `SUD`, `UCL`, `UEL`, `UECL`;
2. luego selecciones: `EURO`, `WC`.

El spec cubre ambos desde el diseño, pero la implementación puede activarse por bandera o por
slice para reducir riesgo.

Riesgos y mitigaciones
----------------------
- Riesgo: resolver mal la liga doméstica de un club y contaminar el contexto.
  Mitigación: resolvedor explícito con score de confianza y fallback sin inventar.
- Riesgo: inflar el dataset mezclando corpus objetivo y corpus de soporte.
  Mitigación: separar estructuras y contratos desde la capa de servicio.
- Riesgo: romper la longitud del vector de features.
  Mitigación: constante de contrato + tests de paridad entrenamiento/inferencia.
- Riesgo: torneos de selecciones queden mal modelados con semántica de clubes.
  Mitigación: reglas específicas para `EURO`/`WC` y prohibición de usar ligas de clubes como
  pseudo-contexto nacional.
- Riesgo: subida de costo/latencia por team history y cross-fetch.
  Mitigación: cache por equipo/competencia/ventana y prioridad de fuentes locales.

Criterios de aceptación
-----------------------
- Para un partido de `LIB` o `SUD`, el sistema puede demostrar que el contexto del club incluye
  historial doméstico real cuando ese historial existe en fuentes soportadas.
- Para un partido de `UCL`, `UEL` o `UECL`, el sistema puede distinguir entre baseline doméstica
  e historial internacional específico del club.
- Para `EURO` y `WC`, el sistema no usa ligas de clubes como sustituto de contexto de selección.
- `prepare_datasets()` y las rutas model-facing usan el mismo contrato de features.
- El modelo no recibe features contextuales en inferencia que nunca vio durante el entrenamiento.
- `LIB` y `SUD` quedan incluidos en la taxonomía de torneos con el mismo tratamiento operativo
  que hoy ya tienen parcialmente los torneos UEFA.
- Los fallbacks siguen usando solo datos reales y quedan auditables.

Estrategia de pruebas y calidad
-------------------------------

### 1. Unit tests obligatorios

- `TrainingDataService`
  - verifica separación entre `target corpus` y `support corpus`.
  - verifica que para `LIB`/`SUD` se dispare resolución de contexto doméstico.
- `TeamCompetitionContextResolver`
  - resuelve correctamente clubes de `ARG1`, `BRA1`, `COL1`.
  - detecta ambigüedad y degrada sin inventar.
  - distingue clubes de selecciones.
- `StatisticsService`
  - construye correctamente `domestic_stats`, `international_stats` y
    `target_competition_stats`.
  - no rompe el cálculo base de ligas domésticas.
- `MLFeatureExtractor`
  - garantiza tamaño estable del vector.
  - verifica que las features contextuales cambian cuando cambia el contexto real.

### 2. Integration tests obligatorios

- Caso `LIB`
  - un match de Libertadores entre clubes de países distintos debe usar contexto doméstico real
    de ambos equipos.
- Caso `SUD`
  - igual que el anterior, con torneo distinto y mismos principios.
- Caso `UCL`
  - debe mezclar contexto doméstico europeo + internacional del club.
- Caso `EURO`/`WC`
  - debe usar solo contexto de selección y no contexto de clubes.

### 3. Regression tests obligatorios

- prueba de paridad entrenamiento/inferencia del extractor de features.
- prueba que verifique que una ruta de predicción internacional ya no depende solo de
  `calculate_team_statistics()` plano.
- prueba de no-regresión para ligas domésticas ya estables (`E0`, `SP1` o equivalente).

### 4. Validación de calidad sugerida durante implementación

- `pytest` focalizado de los archivos nuevos/tocados del backend.
- `mypy` focalizado sobre `backend/src/...` tocado.
- cierre con el gate backend canónico del repo:
  - `bash scripts/quality_gate.sh backend`

No se debe dar por cerrado el cambio solo con diff o revisión manual.

Orden recomendado de implementación
-----------------------------------
1. Centralizar taxonomía internacional y listas dispersas.
2. Crear `TeamCompetitionContextResolver`.
3. Introducir `CompetitionContextBundle` o contrato equivalente.
4. Adaptar `TrainingDataService` para construir `target corpus` + `support corpus`.
5. Adaptar `MatchAggregatorService` y use cases de predicción para reutilizar el mismo bundle.
6. Completar `TeamStatistics` con `target_competition_stats` y metadata de cobertura.
7. Añadir constructor contextual model-facing en `StatisticsService`.
8. Corregir `prepare_datasets()` para entrenar con features contextuales reales.
9. Corregir rutas de inferencia para usar el mismo contrato.
10. Añadir tests unitarios, de integración y de regresión.
11. Cerrar con validación focalizada + gate backend.

Resultado esperado
------------------
Después de esta intervención, un partido internacional dejará de verse como un evento aislado
con historia insuficiente. El sistema podrá llegar a una predicción con contexto real del
equipo, distinguir entre desempeño doméstico y desempeño internacional, y usar exactamente esa
misma semántica tanto al entrenar como al inferir.