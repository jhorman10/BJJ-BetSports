# Plan — Contexto doméstico real para torneos internacionales

## Objetivo
Cerrar la brecha entre soporte parcial y soporte real para `LIB`, `SUD`, `UCL`, `UEL`,
`UECL`, `EURO` y `WC`, garantizando contexto contextualizado por equipo y paridad entre
entrenamiento e inferencia.

## Fases

1) Taxonomía y reglas base
   - Centralizar la definición de torneos internacionales.
   - Eliminar listas hardcodeadas inconsistentes (`min_matches`, `days_ahead`, separación de
     stats internacionales, etc.).

2) Resolver contexto por participante
   - Introducir un resolvedor explícito para clubes vs selecciones.
   - Determinar competencia base, competencia objetivo y cobertura de resolución.

3) Separar corpus objetivo y corpus de soporte
   - Adaptar el servicio de entrenamiento para que los partidos del torneo sigan siendo las
     etiquetas, pero el contexto se alimente desde un `support corpus` real.
   - Reutilizar el mismo enfoque en predicción.

4) Unificar el constructor de estadísticas model-facing
   - Dejar de depender de `calculate_team_statistics()` plano en rutas internacionales.
   - Construir `TeamStatistics` con `domestic_stats`, `international_stats` y
     `target_competition_stats`.

5) Restaurar paridad de features
   - Hacer que el entrenamiento del clasificador de picks use el mismo contrato de features que
     la inferencia.
   - Añadir un guard de longitud/semántica del vector.

6) Cerrar con pruebas y gates
   - Unit tests del resolvedor, del bundle contextual y del extractor.
   - Integration tests para `LIB`, `SUD`, `UCL`, `EURO/WC`.
   - Validación focalizada + gate backend canónico.

## Orden operativo
- El orden archivo por archivo quedó documentado en `backend/specs/international-tournaments-domestic-context/execution-order.md`.
- Regla práctica: cerrar Fase 0 a Fase 3 antes de tocar refinamiento ML en inferencia.
- Regla práctica: no mezclar creación del resolvedor con cambios en `picks_service.py` o
   `prediction_service.py` en el mismo primer slice.

## Criterio de cierre
- El sistema demuestra contexto doméstico real para torneos internacionales de clubes.
- `EURO` y `WC` usan contexto de selección, no de clubes.
- Entrenamiento e inferencia comparten el mismo contrato de estadísticas y features.
- Las pruebas focalizadas e integraciones del slice pasan sin regresiones relevantes.

## Cierre ejecutado
- Observabilidad añadida en `TrainingResult.context_summary` y propagada a los reportes
   lightweight persistidos por el pipeline.
- Integración validada explícitamente para `LIB`, `SUD`, `UCL`, `EURO` y regresión doméstica
   `E0`.
- Gate backend canónico ejecutado en verde con lint, formato, typing y `78` pruebas.