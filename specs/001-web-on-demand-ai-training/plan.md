# Implementation Plan: Entrenamiento On-Demand desde la Web y Ejecucion Agnostica de Modelo

**Branch**: `[001-web-on-demand-ai-training]` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-web-on-demand-ai-training/spec.md`

## Summary

Introducir un training control plane que permita lanzar jobs desde la web, observarlos por `job_id`, ejecutar el trabajo fuera del request lifecycle del API y desacoplar tanto el catalogo de modelos como los backends de ejecucion. El baseline debe reutilizar el pipeline actual como primer adaptador sin perpetuar el antipatron de `thread + subprocess` dentro del servidor web.

## Technical Context

**Language/Version**: Python 3.11 en backend, TypeScript 5.8 en frontend  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy, PyMongo/Motor, pytest; React 19, Vite 7, Zustand, MUI, Vitest  
**Storage**: Persistencia backend existente para metadata operativa, mas almacenamiento de artefactos/versiones de modelo separado del payload binario pesado  
**Testing**: pytest, pytest-asyncio, Vitest, React Testing Library, `scripts/quality_gate.sh`  
**Target Platform**: API Python sobre Linux/macOS, ejecutores externos o locales controlados, navegador moderno para la consola web  
**Project Type**: Aplicacion web full-stack con backend Python y frontend React/Vite  
**Performance Goals**: creacion de job en menos de 2 segundos; cambios de estado visibles en el siguiente ciclo de polling; promocion idempotente y auditable  
**Constraints**: `API_ONLY_MODE` no puede lanzar entrenamiento pesado localmente; la autorizacion debe ser explicita; la UI debe guiarse por capacidades reales del backend; el flujo legacy debe tener compatibilidad temporal  
**Scale/Scope**: Capacidad operativa para administradores, multiple modelos, multiples ejecutores y trazabilidad completa de jobs y artefactos

## Constitution Check

- El backend define primero contratos de dominio, capacidades y seguridad antes de reescribir la UI.
- Ningun request web puede depender de `thread + subprocess` local para considerar el entrenamiento soportado.
- Las acciones `create`, `retry`, `cancel` y `promote` requieren autenticacion, autorizacion y auditoria explicita.
- La implementacion debe cerrar con pruebas backend/frontend y quality gates del repo para el slice tocado.

## Project Structure

### Documentation (this feature)

```text
specs/001-web-on-demand-ai-training/
├── checklists/
│   └── requirements.md
├── plan.md
├── spec.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/
│   ├── application/
│   ├── domain/
│   └── infrastructure/
└── tests/

frontend/
└── src/
    ├── application/
    └── presentation/
```

**Structure Decision**: Feature full-stack con backend como control plane, frontera explicita contra ejecutores externos y UI React que consume un catalogo de capacidades en lugar de asumir entrenamiento local.

## Phase Outline

### Phase 0 - Contract Baseline

- Definir entidades `TrainingRecipe`, `TrainingJob`, `ModelAdapterDefinition`, `ExecutorDefinition`, `ModelArtifact` y `ActiveModelPointer`.
- Fijar estados canonicos, eventos, contrato de capacidades y estrategia de compatibilidad legacy.

### Phase 1 - Backend Control Plane

- Crear servicios de orquestacion de jobs, registro de modelos, registro de ejecutores y promocion de artefactos.
- Exponer endpoints para `capabilities`, creacion de jobs, historial, detalle, eventos, `retry`, `cancel`, `promote` y modelos activos.

### Phase 2 - First Formal Executor

- Encapsular el baseline actual como adaptador formal.
- Integrar un ejecutor real desacoplado del API (`launchagent-local` o `github-actions`) con mapping estable `job_id` <-> `executor_run_id`.

### Phase 3 - Capability-Driven UI

- Evolucionar el dashboard actual hacia una consola de training con formulario, historial, progreso, errores accionables y promotion flow.
- Reemplazar mensajes genericos de indisponibilidad por razones concretas derivadas del backend.

### Phase 4 - Security and Rollout

- Endurecer permisos, eliminar dependencia del bypass local para el nuevo flujo, agregar auditoria y validar el rollout con quality gates y smoke operativo.

## Delivery Strategy

1. Cerrar primero el slice P1: crear y seguir jobs con compatibilidad `API_ONLY_MODE`.
2. Extender luego el catalogo de capacidades para desbloquear seleccion agnostica de modelos y ejecutores.
3. Agregar al final la promocion explicita y los controles de gobierno operativo.

## Risks and Mitigations

- **Riesgo**: Reutilizar `POST /api/v1/train/run-now` como punto de crecimiento perpetua el acoplamiento actual.  
  **Mitigacion**: convertirlo en fachada temporal hacia el nuevo control plane o deprecarlo de forma visible.
- **Riesgo**: El primer ejecutor no expone progreso suficientemente fino.  
  **Mitigacion**: normalizar un contrato minimo de fase, porcentaje y resumen de logs.
- **Riesgo**: Se mezcle entrenamiento con publicacion.  
  **Mitigacion**: modelar `ModelArtifact` y `ActiveModelPointer` como entidades separadas con permisos distintos.
- **Riesgo**: La seguridad actual del trigger administrativo no alcance para una capacidad sensible.  
  **Mitigacion**: introducir permisos dedicados y eliminar cualquier dependencia del bypass loopback en el nuevo flujo.

## Validation Plan

- Ejecutar pruebas backend del slice de entrenamiento con `env PYTHONPATH="$PWD/backend" python -m pytest -v --tb=short` desde la raiz.
- Ejecutar lint, type-check y tests frontend con `npm run lint`, `npm run build` y `npm run test` dentro de `frontend/` cuando la UI cambie.
- Ejecutar `./scripts/quality_gate.sh` para validar la integracion final del slice.
- Hacer smoke manual: crear job, observar progreso, completar o fallar, listar artefacto candidato y promoverlo.