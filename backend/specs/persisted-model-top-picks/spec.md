---
title: Modelo persistido en DB y paridad top-picks Mongo
author: GitHub Copilot
date: 2026-04-28
status: in-progress
tags: [backend, mongo, ml, predictions, bugfix]
---

Resumen ejecutivo
------------------
Esta intervención corrige dos fallas conectadas en la capa backend:
1. La ruta de predicción usa una carga local del modelo ML desde disco y puede ignorar
   el artefacto persistido en MongoDB.
2. La generación de `top-picks` falla sobre Mongo porque la API de repositorio no tiene
   paridad para consultar predicciones activas por liga y devuelve una forma de datos que
   no coincide con la esperada por el caso de uso.

Contexto y motivación
----------------------
- El entrenamiento ya persiste el modelo en `binary_artifacts`.
- `AIPicksService` ya implementa una carga DB-first del modelo.
- `GetPredictionsUseCase` mantiene una segunda ruta de carga, disk-first, lo que rompe la
  consistencia entre entrenamiento y predicción.
- `GetTopMLPicksUseCase` espera documentos con forma `{ match, prediction, ... }`, pero el
  repo Mongo actual envuelve esos documentos y además no implementa `get_league_predictions`.

Alcance (in-scope)
-------------------
- Reutilizar la carga DB-first del modelo en la ruta de predicción afectada.
- Añadir paridad mínima en Mongo para leer predicciones activas globales y por liga con la
  forma correcta esperada por `GetTopMLPicksUseCase`.
- Mantener fallback a disco solo como compatibilidad heredada.

Fuera de alcance (out-of-scope)
-------------------------------
- Reescribir la lógica de entrenamiento.
- Cambiar contratos API del frontend.
- Migrar todos los consumers async/sync de la capa de persistencia.

Requisitos y criterios de aceptación
------------------------------------
- La ruta de predicción usa el modelo cargado desde MongoDB cuando existe el artefacto.
- Si Mongo no tiene el modelo, el sistema conserva el fallback existente a disco/heurística.
- `GetTopMLPicksUseCase.execute(league_id=...)` deja de fallar por método faltante.
- `GetTopMLPicksUseCase` recibe predicciones con forma consistente para extraer `match` y
  `prediction` sin perder datos.
- La validación enfocada del slice tocado pasa sin introducir errores nuevos relevantes.

Diseño propuesto
----------------
- `GetPredictionsUseCase` dejará de cargar el modelo por cuenta propia y tomará el modelo
  ya resuelto por `AIPicksService` inicializado con `persistence_repository`.
- `MongoRepository` añadirá `get_league_predictions(league_id)` con el mismo criterio de
  expiración y mantendrá la forma de documento que ya consumen los callers existentes.
- `GetTopMLPicksUseCase` aceptará tanto el payload directo como el payload envuelto por el
  repositorio, evitando acoplamiento accidental a una sola forma.
- `AsyncMongoRepository` y `AsyncMongoAdapter` se mantendrán en paridad para evitar
  divergencia futura.

Riesgos y mitigaciones
----------------------
- Riesgo: algún caller depende del envoltorio actual `{match_id, prediction, last_updated}`.
  Mitigación: limitar el cambio a métodos usados para top-picks y preservar campos auxiliares
  cuando sea posible.
- Riesgo: el modelo no esté en DB en entornos parciales.
  Mitigación: conservar fallback a disco ya existente en `AIPicksService`.

Pruebas y validación
--------------------
- Validación sintáctica/errores del archivo tocado.
- Ejecución dirigida del flujo `top-picks` o prueba enfocada equivalente si existe.
- Comprobación dirigida del caso de carga de modelo en la ruta de predicción.