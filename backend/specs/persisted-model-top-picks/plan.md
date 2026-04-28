# Plan — Modelo persistido en DB y top-picks Mongo

## Objetivo
Eliminar la divergencia entre entrenamiento y predicción para el modelo ML, y restaurar
la compatibilidad de `top-picks` con Mongo usando una API de repositorio coherente.

## Fases

1) Alinear carga del modelo
   - Inicializar `AIPicksService` con `persistence_repository`.
   - Reutilizar `picks_service.ml_model` en la ruta de predicción.
   - Eliminar la carga paralela disk-only del caso de uso afectado.

2) Restaurar paridad de predicciones activas en Mongo
   - Añadir `get_league_predictions(league_id)`.
   - Mantener la forma actual de `get_all_active_predictions()` para no romper otros callers.
   - Ajustar `GetTopMLPicksUseCase` para aceptar el payload envuelto del repo.
   - Replicar la paridad mínima en `AsyncMongoRepository` y `AsyncMongoAdapter`.

3) Validación enfocada
   - Revisar errores del slice tocado.
   - Ejecutar una comprobación dirigida sobre las rutas afectadas si el entorno lo permite.

## Criterio de cierre
- Predicción usa modelo DB-first.
- `top-picks` deja de romper por método faltante y por shape inconsistente.
- No se amplía alcance fuera del slice backend afectado.