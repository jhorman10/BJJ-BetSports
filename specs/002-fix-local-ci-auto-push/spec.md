# Feature Specification: CI Local con Auto-Commit y Push de Cambios Corregidos

**Feature Branch**: `[002-fix-local-ci-auto-push]`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: User request: "Corre el CI local para que se suban los cambios corregidos con pruebas"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ejecutar validación completa local antes de push (Priority: P1)

Como desarrollador, quiero ejecutar un script local que aplique auto-fix (formato, lint), ejecute todas las pruebas (backend + frontend), y si todo pasa, haga commit y push automático a la rama actual, para garantizar que solo código validado llegue al repositorio remoto.

**Why this priority**: El flujo actual requiere pasos manuales: corregir formato, correr pruebas, hacer commit, push. Esto propaga errores y consume tiempo.

**Independent Test**: Ejecutar `./scripts/validate_and_fix.sh` en un repo con cambios pendientes; debe auto-formatear, pasar pruebas y subir los cambios sin intervención manual.

**Acceptance Scenarios**:

1. **Given** cambios pendientes en backend o frontend con problemas de formato, **When** se ejecuta el script, **Then** se aplican auto-fixes (black, ruff, isort, eslint) y los archivos quedan formateados.
2. **Given** código con errores de tipado (mypy) o lint no auto-fixable, **When** se ejecuta el script, **Then** el script falla y no hace commit/push, mostrando el error.
3. **Given** código válido que pasa todas las validaciones (backend + frontend tests), **When** se ejecuta el script, **Then** se crea un commit con mensaje "chore(ci): auto-format fixes and test validation" y se hace push a la rama actual.
4. **Given** que no hay cambios pendientes después de las validaciones, **When** se ejecuta el script, **Then** el script informa que no hay cambios para commitear y finaliza exitosamente.
5. **Given** que las pruebas de frontend o backend fallan, **When** se ejecuta el script, **Then** el script aborta antes de commit/push y retorna código de error no-zero.

---

### User Story 2 - Soportar entornos con o sin venv (Priority: P2)

Como desarrollador en diferentes máquinas, quiero que el script detecte automáticamente el entorno virtual del backend (backend/.venv, .venv, venv) y use las herramientas instaladas allí, o bien las globales del sistema, para que el script funcione en cualquier entorno de desarrollo.

**Why this priority**: Actualmente el script asume un entorno específico y puede fallar si no está el venv.

**Independent Test**: Ejecutar el script en un entorno sin backend/.venv pero con herramientas instaladas globalmente; debe funcionar.

**Acceptance Scenarios**:

1. **Given** backend/.venv existente con black/ruff/mypy/pytest, **When** se ejecuta el script, **Then** usa los binarios del venv.
2. **Given** backend sin venv pero con python3 y herramientas instaladas globalmente, **When** se ejecuta el script, **Then** usa `python3 -m <tool>` para cada herramienta.
3. **Given** que no hay backend, **When** se ejecuta el script, **Then** omite pasos de backend y continúa con frontend si existe.

---

### User Story 3 - Mensaje de commit convencional (Priority: P3)

Como maintainer del repo, quiero que el commit generado automáticamente por el script siga el estándar Conventional Commits, para mantener un historial limpio y compatible con herramientas de changelog.

**Why this priority**: Historial consistente es importante para release automation.

**Acceptance Scenarios**:

1. **Given** que el script realiza un commit automático, **When** crea el commit, **Then** el mensaje es `chore(ci): auto-format fixes and test validation`.
