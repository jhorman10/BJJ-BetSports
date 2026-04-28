---
title: Contrato LearningWeights en entrenamiento ML
author: GitHub Copilot
date: 2026-04-27
status: completed
tags: [backend, ml, bugfix, learning-weights]
---

Resumen ejecutivo
------------------
Esta intervención corrige un bug en el pipeline de entrenamiento ML donde los pesos de
aprendizaje se pasan serializados como `dict` a `PicksService`, aunque el servicio espera
un objeto `LearningWeights` con métodos de dominio como `get_market_adjustment()`.

Contexto y motivación
----------------------
- El error observado en producción es: `'dict' object has no attribute 'get_market_adjustment'`.
- `prepare_datasets()` instancia `PicksService` usando `learning_service.get_learning_weights()`.
- `LearningService.get_learning_weights()` hoy devuelve un payload serializado, no la entidad
  de dominio viva.

Alcance (in-scope)
-------------------
- Restablecer el contrato para que `PicksService` reciba `LearningWeights`.
- Añadir una prueba dirigida que cubra el contrato usado por `prepare_datasets()`.
- Endurecer el slice sin cambiar algoritmos de picks ni del entrenamiento.

Fuera de alcance (out-of-scope)
-------------------------------
- Cambios en heurísticas de picks.
- Refactors amplios del pipeline ML.
- Cambios de API frontend o persistencia externa.

Requisitos y criterios de aceptación
------------------------------------
- `prepare_datasets()` puede construir `PicksService` sin romper cuando hay pesos cargados.
- `PicksService.learning_weights` expone `get_market_adjustment()` durante el entrenamiento.
- El test dirigido falla antes del fix y pasa después.
- La validación focalizada del backend afectado pasa sin errores nuevos relevantes.

Diseño propuesto
----------------
- Cambiar `LearningService.get_learning_weights()` para devolver la entidad `LearningWeights`.
- Mantener `_serialize_weights()` como frontera explícita para persistencia/export.
- Ajustar tests unitarios del orquestador para verificar el contrato correcto.

Riesgos y mitigaciones
----------------------
- Riesgo: algún caller espere un `dict` desde `get_learning_weights()`.
  Mitigación: buscar usos reales y mantener serialización solo donde se persiste/exporta.
- Riesgo: tests existentes mockean `{}` y esconden el bug.
  Mitigación: reemplazar ese patrón por un doble que modele el contrato real.

Pruebas y validación
--------------------
- `pytest backend/tests/unit/test_ml_training_orchestrator.py -k learning_weights`
- `pytest backend/tests/unit/test_ml_training_orchestrator.py`