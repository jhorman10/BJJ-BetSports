# Plan — Contrato LearningWeights en entrenamiento ML

## Objetivo
Eliminar la divergencia entre la capa de dominio y la serialización para que el pipeline
de entrenamiento pase un objeto `LearningWeights` válido a `PicksService`.

## Fases

1) Reproducir el bug con una prueba barata
   - Añadir un test enfocado al constructor/factory usado por `prepare_datasets()`.
   - Verificar que el valor pasado al servicio de picks implementa el contrato esperado.

2) Corregir la raíz
   - Hacer que `LearningService.get_learning_weights()` devuelva la entidad de dominio.
   - Dejar la serialización solo para persistencia interna.

3) Cerrar el slice
   - Ajustar dobles de prueba inconsistentes.
   - Ejecutar pytest focalizado del archivo tocado.

## Criterio de cierre
- El entrenamiento deja de pasar `dict` a `PicksService`.
- El test dirigido protege el contrato.
- No se amplía alcance fuera del backend ML afectado.