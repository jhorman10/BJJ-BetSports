# Tasks — Modelo persistido en DB y top-picks Mongo

## Implementación
- [x] Actualizar `GetPredictionsUseCase` para usar `AIPicksService` con `persistence_repository`.
- [x] Reemplazar la carga manual del modelo en `use_cases.py` por el modelo resuelto por el servicio.
- [x] Añadir `get_league_predictions()` en `mongo_repository.py`.
- [x] Ajustar `GetTopMLPicksUseCase` para aceptar el payload envuelto del repositorio.
- [x] Mantener paridad mínima en `async_mongo_repository.py`.
- [x] Mantener paridad mínima en `async_mongo_adapter.py`.

## Validación
- [x] Ejecutar validación enfocada de errores para archivos tocados.
- [x] Ejecutar una comprobación dirigida del flujo afectado si existe un comando/prueba barata.

## Cierre
- [x] Guardar memoria del bugfix y resumen de sesión.