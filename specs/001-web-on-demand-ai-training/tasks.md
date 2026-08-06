# Tasks: Entrenamiento On-Demand desde la Web y Ejecucion Agnostica de Modelo

**Input**: Design documents from `/specs/001-web-on-demand-ai-training/`  
**Prerequisites**: plan.md, spec.md  
**Tests**: Se incluyen porque el feature cambia backend y frontend y necesita validacion de contratos, estados y permisos.  
**Organization**: Tasks grouped by user story so each slice can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo si toca archivos distintos y no depende de otro task.
- **[Story]**: US1, US2 o US3.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: preparar el arbol del feature y el punto de entrada comun para backend y frontend.

- [x] T001 Create backend training module scaffolding under `backend/src/domain/training/`, `backend/src/application/training/` and `backend/src/infrastructure/training/`
- [x] T002 [P] Create frontend training UI scaffolding under `frontend/src/application/stores/` and `frontend/src/presentation/components/Training/`
- [x] T003 [P] Document the feature entrypoints in `backend/ARCHITECTURE.md` and `frontend/ARCHITECTURE.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: contratos y seguridad que bloquean todo lo demas.

**CRITICAL**: no arrancar user stories hasta cerrar esta fase.

- [x] T004 Define canonical training entities and states in `backend/src/domain/training/models.py`
- [x] T005 [P] Define model registry and executor registry contracts in `backend/src/domain/training/registries.py`
- [x] T006 [P] Add explicit training permissions and guards in `backend/src/api/security.py`
- [x] T007 Create repositories for jobs, job events, artifacts and active model pointers in `backend/src/infrastructure/training/repositories.py`
- [x] T008 Define request/response schemas for capabilities, jobs, events and promotion in `backend/src/api/schemas/training.py`
- [x] T009 Add audit logging hooks for create, retry, cancel and promote actions in `backend/src/application/training/audit.py`

**Checkpoint**: foundation ready, user stories can start.

---

## Phase 3: User Story 1 - Lanzar y seguir un entrenamiento real (Priority: P1) 🎯 MVP

**Goal**: permitir crear un job desde la web y seguirlo por `job_id` sin ejecutar el entrenamiento dentro del proceso del API.

**Independent Test**: crear un job en `API_ONLY_MODE`, ver `job_id`, consultar detalle/eventos y confirmar que el API no lanza el pipeline local en el request.

### Tests for User Story 1

- [x] T010 [P] [US1] Add backend API tests for create/list/detail job flows in `backend/tests/test_training_jobs_api.py`
- [x] T011 [P] [US1] Add backend unit tests for orchestration state transitions in `backend/tests/unit/test_training_job_service.py`

### Implementation for User Story 1

- [x] T012 [P] [US1] Implement `TrainingJobService` in `backend/src/application/training/job_service.py`
- [x] T013 [P] [US1] Implement executor submission/status abstraction in `backend/src/application/training/executors/base.py`
- [x] T014 [US1] Add `POST /api/v1/training/jobs`, `GET /api/v1/training/jobs` and `GET /api/v1/training/jobs/{job_id}` in `backend/src/api/routers/training.py`
- [x] T015 [US1] Add `GET /api/v1/training/jobs/{job_id}/events` and event persistence wiring in `backend/src/api/routers/training.py`
- [x] T016 [US1] Bridge legacy `POST /api/v1/train/run-now` to the new control plane or return a documented deprecation path in `backend/src/api/main.py`
- [x] T017 [US1] Add training job polling and local state handling in `frontend/src/application/stores/useTrainingJobsStore.ts`
- [x] T018 [US1] Render launch and live status UI in `frontend/src/presentation/components/BotDashboard/BotDashboard.tsx`

**Checkpoint**: el operador ya puede crear y observar jobs de entrenamiento.

---

## Phase 4: User Story 2 - Elegir modelo, receta y ejecutor por capacidades (Priority: P2)

**Goal**: permitir seleccion agnostica de modelo y ejecutor desde un catalogo publicado por backend.

**Independent Test**: abrir el formulario, cargar capacidades, enviar una combinacion valida y rechazar una invalida con razon accionable.

### Tests for User Story 2

- [x] T019 [P] [US2] Add backend contract tests for `GET /api/v1/training/capabilities` and model catalog responses in `backend/tests/test_training_capabilities_api.py`
- [x] T020 [P] [US2] Add frontend tests for capability-driven selectors in `frontend/src/presentation/components/Training/TrainingControlPanel.test.tsx`

### Implementation for User Story 2

- [x] T021 [P] [US2] Implement `ModelRegistryService` and `TrainingExecutorRegistry` in `backend/src/application/training/`
- [x] T022 [US2] Add `GET /api/v1/training/capabilities` and `GET /api/v1/training/models` in `backend/src/api/routes/training.py`
- [x] T023 [US2] Validate `model_key`, `executor_target`, `league_ids`, `days_back` and profiles before job creation in `backend/src/application/training/job_service.py`
- [x] T024 [US2] Consume capabilities and model catalog in `frontend/src/application/stores/useTrainingJobsStore.ts`
- [x] T025 [US2] Build selectors for model, executor, presets and scope in `frontend/src/presentation/components/Training/TrainingControlPanel.tsx`
- [x] T026 [US2] Replace generic training-unavailable messaging with actionable reason mapping in `frontend/src/presentation/components/BotDashboard/BotDashboard.tsx`

**Checkpoint**: el mismo contrato soporta multiples modelos y ejecutores sin endpoints nuevos.

---

## Phase 5: User Story 3 - Promover artefactos y gobernar el ciclo operativo (Priority: P3)

**Goal**: separar entrenamiento de publicacion, con promotion, retry, cancel y auditoria.

**Independent Test**: completar un job, listar el artefacto candidato, promoverlo con permiso valido y verificar que un job fallido no puede promocionarse.

### Tests for User Story 3

- [ ] T027 [P] [US3] Add backend tests for retry, cancel, promote and permission enforcement in `backend/tests/test_training_artifacts_api.py`
- [ ] T028 [P] [US3] Add frontend tests for artifact promotion and blocked states in `frontend/src/presentation/components/Training/TrainingArtifactsPanel.test.tsx`

### Implementation for User Story 3

- [ ] T029 [P] [US3] Implement artifact and active-model persistence in `backend/src/infrastructure/training/repositories.py`
- [ ] T030 [US3] Add `POST /api/v1/training/jobs/{job_id}/retry`, `POST /api/v1/training/jobs/{job_id}/cancel`, `POST /api/v1/training/artifacts/{artifact_id}/promote` and `GET /api/v1/training/active-models` in `backend/src/api/routes/training.py`
- [ ] T031 [US3] Implement promotion rules and audit trail in `backend/src/application/training/promotion_service.py`
- [ ] T032 [US3] Render job history, artifact candidates and promotion actions in `frontend/src/presentation/components/Training/TrainingArtifactsPanel.tsx`
- [ ] T033 [US3] Block invalid transitions and surface explicit reasons in `frontend/src/application/stores/useTrainingJobsStore.ts`

**Checkpoint**: entrenar y promover quedan separados y auditables.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: endurecer el feature y validar integracion completa.

- [ ] T034 [P] Update operational documentation in `backend/ARCHITECTURE.md` and `docs/`
- [ ] T035 Run backend validation with `env PYTHONPATH="$PWD/backend" python -m pytest -v --tb=short`
- [ ] T036 Run frontend validation with `npm run lint`, `npm run build` and `npm run test` inside `frontend/`
- [ ] T037 Run `./scripts/quality_gate.sh` from repository root and capture rollout notes in `specs/001-web-on-demand-ai-training/plan.md`

---

## Dependencies & Execution Order

- Setup (Phase 1) starts immediately.
- Foundational (Phase 2) blocks all user stories.
- US1 is the MVP and must land before US2 or US3.
- US2 depends on the contracts and endpoints from US1.
- US3 depends on persisted job/artifact metadata from US1 and capability validation from US2.
- Polish runs after the desired user stories are complete.

## Parallel Opportunities

- T002 and T003 can run in parallel with T001.
- T005, T006, T007 and T008 can run in parallel after T004 defines the canonical domain.
- Within each user story, test tasks can run in parallel before implementation tasks.
- Backend and frontend tasks inside the same user story can split once the backend contract is stable.

## Implementation Strategy

1. Deliver US1 first as the minimum viable operational slice.
2. Add US2 to unlock model-agnostic and executor-agnostic operation.
3. Add US3 to close governance, promotion and auditability.
4. Finish with repo quality gates and operational documentation.