---
title: Excelencia de Validación Full-Stack
author: GitHub Copilot
date: 2026-04-27
status: completed
tags: [quality, testing, ci, frontend, backend, linting]
---

Resumen ejecutivo
------------------
Esta especificación define una intervención transversal para que la validación del
proyecto sea reproducible, confiable y estricta. El objetivo no es solo correr tests,
sino consolidar un gate canónico full-stack que replique CI localmente, permita
ejecutar backend y frontend con un solo comando y exponga con precisión la deuda de
calidad restante hasta lograr un estado completamente verde.

Contexto y motivación
----------------------
- El backend ya demuestra que `pytest` puede pasar localmente y en hooks remotos,
  pero la validación total del repositorio sigue bloqueada por deuda histórica de
  Ruff, Mypy y discrepancias entre scripts locales, hooks y workflows de GitHub.
- `scripts/local_checks.sh` no replica la matriz real de CI y mezcla instalación,
  build y testing de forma poco determinista.
- El frontend tiene Vitest configurado y tests existentes, pero no existe hoy un
  comando canónico de calidad full-stack ni un umbral explícito de coverage.
- Los hooks locales y remotos corren validaciones diferentes, lo que obliga a usar
  bypasses y destruye la confianza en el pipeline.

Alcance (in-scope)
-------------------
- Definir e implementar un comando canónico full-stack para validación local.
- Alinear scripts locales con la matriz efectiva de CI para backend y frontend.
- Ejecutar la validación canónica y capturar una línea base reproducible de fallos.
- Corregir el primer bloque de fallos de mayor retorno para acercar el proyecto a un
  estado verde real.
- Documentar el flujo operativo para que cualquier agente o desarrollador pueda usar
  el mismo gate.

Fuera de alcance (out-of-scope)
-------------------------------
- Resolver en una sola iteración toda la deuda histórica de Mypy, Ruff y complejidad.
- Rediseñar por completo la estrategia de branch protection o la topología de CI.
- Introducir cobertura global obligatoria sin antes estabilizar los gates básicos.

Requisitos y criterios de aceptación
-----------------------------------
- Existe un comando único y documentado que ejecuta la validación full-stack.
- El comando canónico cubre, como mínimo:
  - Backend: Ruff, Black, Isort, Mypy y Pytest.
  - Frontend: ESLint, Build y Vitest.
- El script deja un estado de salida inequívoco y falla ante cualquier gate roto.
- Los workflows principales de CI reutilizan o reflejan exactamente el mismo orden de
  validación que el comando local.
- Se captura una línea base real de errores tras ejecutar el gate canónico.
- Se corrige al menos una familia de fallos prioritaria, validada con el mismo gate.

Diseño propuesto
----------------
- Introducir un script canónico en `scripts/` que orqueste la validación full-stack
  sin instalar dependencias de forma oportunista ni alterar el entorno por sorpresa.
- Mantener `scripts/local_checks.sh` como wrapper o derivarlo al nuevo comando para
  no conservar dos fuentes de verdad distintas.
- Separar claramente:
  - preparación de entorno,
  - validación backend,
  - validación frontend,
  - reporte final.
- Hacer que la documentación de desarrollo apunte al mismo comando y al mismo orden
  de checks que CI.

Plan de implementación (alto nivel)
-----------------------------------
1. Crear artefactos Spec Kit para el cambio.
2. Implementar el comando canónico full-stack.
3. Alinear scripts y documentación con ese comando.
4. Ejecutar el gate canónico para obtener la línea base real.
5. Corregir la primera familia crítica de errores con mayor retorno.
6. Revalidar y dejar el estado exacto de deuda restante.

Riesgos y mitigaciones
----------------------
- Riesgo: el gate full-stack falle en demasiados puntos a la vez.
  - Mitigación: atacar primero familias de errores mecánicas o de alto apalancamiento.
- Riesgo: hooks locales y CI sigan divergiendo.
  - Mitigación: centralizar el flujo en un único script reutilizable.
- Riesgo: cambios en linting rompan paths ya estables.
  - Mitigación: validar tras cada edición con el slice más estrecho posible.

Pruebas y validación
--------------------
- Ejecutar el nuevo comando canónico completo.
- Ejecutar validaciones focalizadas tras cada edición relevante.
- Confirmar que backend y frontend siguen cubiertos por los mismos checks que CI.

Entregables
-----------
- `backend/specs/testing-excellence/spec.md`
- `backend/specs/testing-excellence/plan.md`
- `backend/specs/testing-excellence/tasks.md`
- Script canónico de validación full-stack en `scripts/`
- Documentación local actualizada

Siguientes pasos inmediatos
---------------------------
1. Crear el comando canónico full-stack.
2. Reapuntar `scripts/local_checks.sh` a la fuente de verdad nueva.
3. Ejecutar el gate y capturar fallos prioritarios.

Estado de cierre verificado
---------------------------
- `scripts/quality_gate.sh all` ejecuta backend y frontend con un único comando y quedó verde.
- El backend valida `ruff`, `black`, `isort`, `mypy` y `pytest` en el mismo orden documentado.
- El frontend valida `eslint`, `build` y `vitest` con el mismo orden usado por el gate local.
- `.github/workflows/ci.yml` y `.github/workflows/ci-pr.yml` quedaron alineados con la matriz canónica.
- `.github/workflows/lint.yml` dejó de usar shortcuts por archivos cambiados y ahora refleja los mismos checks de lint/tipado/build que el gate.
- `docs/developer-linting.md` ya documenta el gate como fuente de verdad local y remota.

Deuda restante no bloqueante
----------------------------
- Coverage global obligatorio sigue fuera de alcance para este spec.
- La siguiente iteración natural queda separada como endurecimiento de coverage, tipado más estricto y refactors de complejidad, no como bloqueo del gate canónico.