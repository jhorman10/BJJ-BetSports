# Tasks — Contexto doméstico real para torneos internacionales

## Precondición
- [ ] Seguir el orden de implementación definido en `backend/specs/international-tournaments-domestic-context/execution-order.md`.

## Implementación
- [ ] Centralizar la taxonomía de torneos internacionales y reemplazar listas dispersas.
- [ ] Incluir `LIB` y `SUD` en las rutas operativas que hoy solo tratan a torneos UEFA como
  especiales.
- [ ] Crear `TeamCompetitionContextResolver` para distinguir clubes vs selecciones y resolver el
  contexto base de cada participante.
- [ ] Diseñar e introducir un contrato explícito de `target corpus` y `support corpus` para el
  entrenamiento internacional.
- [ ] Adaptar `TrainingDataService` para construir contexto doméstico/internacional real sin
  mezclar etiquetas del torneo objetivo.
- [ ] Adaptar `MatchAggregatorService` y use cases model-facing para reutilizar el mismo bundle
  contextual en predicción.
- [ ] Extender `TeamStatistics` con `target_competition_stats` y metadata de cobertura.
- [ ] Añadir un constructor contextual model-facing en `StatisticsService` y reducir la
  dependencia de `calculate_team_statistics()` plano en rutas internacionales.
- [ ] Corregir `prepare_datasets()` para que `MLFeatureExtractor.extract_features()` reciba
  `match`, `home_stats` y `away_stats` reales al entrenar el clasificador de picks.
- [ ] Alinear todas las rutas de inferencia ML con ese mismo contrato de features.
- [ ] Añadir observabilidad de cobertura y degradación de contexto.

## Validación
- [ ] Añadir unit tests para `TrainingDataService` con separación `target/support corpus`.
- [ ] Añadir unit tests para `TeamCompetitionContextResolver` con casos `LIB`, `SUD`, `UCL` y
  ambigüedad controlada.
- [ ] Añadir unit tests para `StatisticsService` cubriendo `domestic_stats`,
  `international_stats` y `target_competition_stats`.
- [ ] Añadir unit tests para `MLFeatureExtractor` que verifiquen paridad y longitud del vector.
- [ ] Añadir integration tests para `LIB`, `SUD`, `UCL` y `EURO/WC`.
- [ ] Añadir regresión para rutas domésticas ya estables.
- [ ] Ejecutar `pytest` focalizado del slice tocado.
- [ ] Ejecutar `mypy` focalizado del slice tocado.
- [ ] Cerrar con `bash scripts/quality_gate.sh backend`.

## Cierre
- [ ] Documentar cobertura lograda por torneo y limitaciones reales de fuente si persisten.
- [ ] Guardar memoria del cambio cuando se implemente.