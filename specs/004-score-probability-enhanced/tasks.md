# Implementation Tasks: Marcador Tentativo Avanzado

**Feature Branch**: `004-score-probability-enhanced`  
**Created**: 2026-08-07  
**Status**: Draft  
**Plan**: `specs/004-score-probability-enhanced/plan.md`

## Task Decomposition

### Backend Tasks

- [ ] **T001** [backend] Agregar método `calculate_score_matrix()` en `PredictionService` que retorne matriz 6x6 con `{home_goals, away_goals, probability, home_xg_contribution, away_xg_contribution}`.
- [ ] **T002** [backend] Agregar método `calculate_score_xg_contribution()` que compute la proporción de xG local vs visitante para cada score.
- [ ] **T003** [backend] Agregar método `calculate_score_accuracy_history(league_id)` que consulte MongoDB y retorne `{total_predictions, exact_score_hits, accuracy_percentage}`.
- [ ] **T004** [backend] Integrar `calculate_score_matrix()` y `calculate_score_accuracy_history()` en `generate_prediction()` para poblar `score_matrix` y `score_accuracy_history`.
- [ ] **T005** [backend] Actualizar `Prediction` entity en `entities.py` con campos opcionales `score_matrix` y `score_accuracy_history`.
- [ ] **T006** [backend] Actualizar `PredictionModel` en `schemas/predictions.py` con `ScoreCell` y `ScoreAccuracyHistory`.
- [ ] **T007** [backend] Actualizar `prediction_mapper.py` para mapear los nuevos campos desde MongoDB.
- [ ] **T008** [backend] Agregar tests unitarios para `calculate_score_matrix()` en `test_prediction_service_ml_context.py`.
- [ ] **T009** [backend] Agregar tests unitarios para `calculate_score_xg_contribution()`.
- [ ] **T010** [backend] Agregar tests unitarios para `calculate_score_accuracy_history()`.
- [ ] **T011** [backend] Ejecutar suite completa de tests backend y verificar zero regression.

### Frontend Tasks

- [ ] **T012** [frontend] Actualizar interfaces TypeScript (`types/index.ts` y `domain/entities/prediction.ts`) con `ScoreCell`, `ScoreAccuracyHistory`, `score_matrix`, `score_accuracy_history`.
- [ ] **T013** [frontend] Crear componente `ScoreMatrixModal.tsx` con matriz 6x6, heatmap, tooltips con xG breakdown, y sección de accuracy history.
- [ ] **T014** [frontend] Modificar `PreMatchPrediction.tsx` para abrir `ScoreMatrixModal` al hacer clic en la sección "Marcador Tentativo".
- [ ] **T015** [frontend] Modificar `MatchCard.tsx` para abrir `ScoreMatrixModal` al hacer clic en el chip de "Marcador Tentativo".
- [ ] **T016** [frontend] Agregar estilos responsive para mobile en `ScoreMatrixModal.tsx`.
- [ ] **T017** [frontend] Ejecutar lint, build y tests frontend y verificar zero regression.

### Integration & Verification

- [ ] **T018** [fullstack] Verificar que los endpoints `/api/v1/predictions/league/{id}` y `/api/v1/predictions/match/{id}` exponen `score_matrix` y `score_accuracy_history`.
- [ ] **T019** [fullstack] Verificar end-to-end que el modal muestra la matriz completa, xG breakdown y accuracy history.
- [ ] **T020** [code-quality] Ejecutar quality gate completo (`ruff`, `black`, `isort`, `mypy`, `pytest`, `eslint`, `vitest`) y confirmar todo en verde.

## Execution Order

1. T001 → T002 → T003 (backend core methods)
2. T004 (integration en generate_prediction)
3. T005 → T006 → T007 (entity, schema, mapper)
4. T008 → T009 → T010 (tests backend)
5. T011 (verify backend)
6. T012 (frontend types)
7. T013 (frontend modal component)
8. T014 → T015 (integration en vistas)
9. T016 (responsive)
10. T017 (verify frontend)
11. T018 → T019 (integration E2E)
12. T020 (quality gate final)

## Notes

- `calculate_score_matrix()` reusa `calculate_score_probabilities()` para no duplicar lógica Poisson.
- `score_accuracy_history` se calcula on-the-fly consultando MongoDB. Para performance, se puede cachear por league_id en memoria con TTL.
- La matriz se limita a 6x6 (0-5 goles) como default. Si se requiere ampliar, basta cambiar `MAX_GOALS` en el método.
- El modal usa MUI `Dialog` estándar del proyecto, consistente con `MatchDetailsModal.tsx`.
