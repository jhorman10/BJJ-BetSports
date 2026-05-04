# Tasks — Contexto doméstico real para torneos internacionales

## Precondición
- [x] Seguir el orden de implementación definido en `backend/specs/international-tournaments-domestic-context/execution-order.md`.

## Implementación
- [x] Centralizar la taxonomía de torneos internacionales y reemplazar listas dispersas.
- [x] Incluir `LIB` y `SUD` en las rutas operativas que hoy solo tratan a torneos UEFA como
  especiales.
- [x] Crear `TeamCompetitionContextResolver` para distinguir clubes vs selecciones y resolver el
  contexto base de cada participante.
- [x] Diseñar e introducir un contrato explícito de `target corpus` y `support corpus` para el
  entrenamiento internacional.
- [x] Adaptar `TrainingDataService` para construir contexto doméstico/internacional real sin
  mezclar etiquetas del torneo objetivo.
- [x] Adaptar `MatchAggregatorService` y use cases model-facing para reutilizar el mismo bundle
  contextual en predicción.
- [x] Extender `TeamStatistics` con `target_competition_stats` y metadata de cobertura.
- [x] Añadir un constructor contextual model-facing en `StatisticsService` y reducir la
  dependencia de `calculate_team_statistics()` plano en rutas internacionales.
- [x] Corregir `prepare_datasets()` para que `MLFeatureExtractor.extract_features()` reciba
  `match`, `home_stats` y `away_stats` reales al entrenar el clasificador de picks.
- [x] Alinear todas las rutas de inferencia ML con ese mismo contrato de features.
- [x] Añadir observabilidad de cobertura y degradación de contexto.

## Validación
- [x] Añadir unit tests para `TrainingDataService` con separación `target/support corpus`.
- [x] Añadir unit tests para `TeamCompetitionContextResolver` con casos `LIB`, `SUD`, `UCL` y
  ambigüedad controlada.
- [x] Añadir unit tests para `StatisticsService` cubriendo `domestic_stats`,
  `international_stats` y `target_competition_stats`.
- [x] Añadir unit tests para `MLFeatureExtractor` que verifiquen paridad y longitud del vector.
- [x] Añadir integration tests para `LIB`, `SUD`, `UCL` y `EURO/WC`.
- [x] Añadir regresión para rutas domésticas ya estables.
- [x] Ejecutar `pytest` focalizado del slice tocado.
- [x] Ejecutar `mypy` focalizado del slice tocado.
- [x] Cerrar con `bash scripts/quality_gate.sh backend`.

## Cierre
- [x] Documentar cobertura lograda por torneo y limitaciones reales de fuente si persisten.
- [x] Guardar memoria del cambio cuando se implemente.