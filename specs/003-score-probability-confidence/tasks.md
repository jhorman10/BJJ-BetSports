# Implementation Tasks: Marcador Tentativo con Distribución de Poisson y Nivel de Confianza

**Feature Branch**: `003-score-probability-confidence`  
**Created**: 2026-08-07  
**Status**: Draft  
**Plan**: `specs/003-score-probability-confidence/plan.md`

## Task Decomposition

### Backend Tasks

- [ ] **T001** [backend] Agregar método `calculate_score_probabilities()` en `PredictionService` que calcule la distribución de Poisson para scores exactos y retorne top-N.
- [ ] **T002** [backend] Agregar método `calculate_score_confidence_tier()` en `PredictionService` que mapee entropía + confianza existente a "Alta"/"Media"/"Baja"/"N/A".
- [ ] **T003** [backend] Integrar ambos métodos en el flujo de generación de predicciones (`generate_prediction` o equivalente) para poblar `score_probabilities` y `score_confidence_tier`.
- [ ] **T004** [backend] Actualizar `PredictionModel` en `backend/src/api/schemas/predictions.py` con campos opcionales `score_probabilities` y `score_confidence_tier`.
- [ ] **T005** [backend] Actualizar `prediction_mapper.py` para mapear los nuevos campos desde el documento MongoDB.
- [ ] **T006** [backend] Agregar tests unitarios para `calculate_score_probabilities()` en `tests/unit/test_prediction_service_ml_context.py`.
- [ ] **T007** [backend] Agregar tests unitarios para `calculate_score_confidence_tier()` en `tests/unit/test_prediction_service_ml_context.py`.
- [ ] **T008** [backend] Ejecutar suite completa de tests backend y verificar zero regression.

### Frontend Tasks

- [ ] **T009** [frontend] Actualizar interfaz `Prediction` en `frontend/src/types/index.ts` con `score_probabilities?` y `score_confidence_tier?`.
- [ ] **T010** [frontend] Actualizar `frontend/src/domain/entities/prediction.ts` con los nuevos campos opcionales.
- [ ] **T011** [frontend] Modificar `PreMatchPrediction.tsx` para mostrar sección "Marcador Tentativo" con top 3-5 scores.
- [ ] **T012** [frontend] Agregar badge de confianza (Alta/Media/Baja) con color en `MatchCard.tsx` o `PreMatchPrediction.tsx`.
- [ ] **T013** [frontend] Ejecutar lint, build y tests frontend y verificar zero regression.

### Integration & Verification

- [ ] **T014** [backend] Verificar que los endpoints `/api/v1/predictions/league/{id}` y `/api/v1/predictions/match/{id}` exponen los nuevos campos.
- [ ] **T015** [fullstack] Verificar end-to-end que el frontend muestra "Marcador Tentativo" correctamente con datos reales.
- [ ] **T016** [code-quality] Ejecutar quality gate completo (`ruff`, `black`, `isort`, `mypy`, `pytest`, `eslint`, `vitest`) y confirmar todo en verde.

## Execution Order

1. T001 → T002 (backend core methods)
2. T003 (integration en flujo de predicciones)
3. T004 → T005 (schema + mapper)
4. T006 → T007 (tests backend)
5. T008 (verify backend)
6. T009 → T010 (frontend types)
7. T011 → T012 (frontend UI)
8. T013 (verify frontend)
9. T014 → T015 (integration)
10. T016 (quality gate final)

## Notes

- Los métodos nuevos se agregan en `PredictionService` porque ahí ya existe la lógica de Poisson y xG.
- Los campos son opcionales en backend y frontend para mantener retrocompatibilidad.
- No se requiere migración de base de datos.
- MAX_GOALS se define como constante en `PredictionService` (valor sugerido: 8) para limitar el cálculo a 81 combinaciones máximo.
