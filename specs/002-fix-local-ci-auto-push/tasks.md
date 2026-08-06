# Tasks: CI Local con Auto-Commit y Push de Cambios Corregidos

**Input**: `specs/002-fix-local-ci-auto-push/spec.md` y `plan.md`  
**Prerequisites**: Herramientas de backend (black, ruff, isort, mypy, pytest) instaladas en venv o global; frontend con npm ci ejecutado.  
**Tests**: El script mismo es la prueba: debe ejecutarse sin errores y cumplir acceptance criteria.  
**Organization**: 4 fases sequential (fix, test, commit, push). No paralelizable.

---

## Phase 1: Mejora de detección de entorno virtual y utilidades de logging

**Objetivo**: Hacer el script robusto y legible.

- [ ] T001 Añadir colores y funciones `log_info`, `log_success`, `log_warn`, `log_error`.
- [ ] T002 Verificar que el script se ejecuta dentro de un repositorio git (`git rev-parse --is-inside-work-tree`).
- [ ] T003 Detectar backend venv buscando `backend/.venv/bin/python`, luego `.venv/bin/python`, `venv/bin/python`. Guardar ruta de binarios en `BACKEND_VENV_BIN`.
- [ ] T004 Cambiar `set -e` a `set -euo pipefail` para manejo robusto de errores.

---

## Phase 2: Auto-fix Backend

**Objetivo**: Asegurar formato y lint de código Python.

- [ ] T005 Si `BACKEND_VENV_BIN` está definido, ejecutar `"$BACKEND_VENV_BIN/black" src tests`, sino `python3 -m black src tests`.
- [ ] T006 Si `BACKEND_VENV_BIN` está definido, ejecutar `"$BACKEND_VENV_BIN/ruff" check --fix src tests`, sino `python3 -m ruff check --fix src tests`.
- [ ] T007 Si `BACKEND_VENV_BIN` está definido, ejecutar `"$BACKEND_VENV_BIN/isort" src tests`, sino `python3 -m isort src tests`.
- [ ] T008 Si `BACKEND_VENV_BIN` está definido, ejecutar `"$BACKEND_VENV_BIN/mypy" src --ignore-missing-imports --follow-imports=skip`, sino `python3 -m mypy src --ignore-missing-imports --follow-imports=skip`. Si falla, abortar.

---

## Phase 3: Auto-fix Frontend

**Objetivo**: Asegurar formato y lint de código TypeScript/React.

- [ ] T009 Si existe directorio `frontend`, ejecutar `(cd frontend && npm run lint -- --fix)`.

---

## Phase 4: Ejecución de Tests

**Objetivo**: Validar que los cambios no rompen funcionalidad.

- [ ] T010 Backend:Ejecutar `pytest -v --tb=short` en `backend/` usando venv si existe.
- [ ] T011 Frontend:Ejecutar `npx vitest run` en `frontend/`.

---

## Phase 5: Commit y Push automático

**Objetivo**: Subir cambios validados al repositorio remoto.

- [ ] T012 Verificar si hay cambios pendientes (`git status --porcelain`). Si no hay, informar y terminar.
- [ ] T013 Configurar `git user.name` y `user.email` si no están definidos (valores por defecto "CI Local Bot" <ci-local@bjj-betsports.local>).
- [ ] T014 Hacer `git add -A`.
- [ ] T015 Crear commit con mensaje `chore(ci): auto-format fixes and test validation`.
- [ ] T016 Obtener rama actual con `git rev-parse --abbrev-ref HEAD` y hacer `git push origin <branch>`.
- [ ] T017 Si el push falla, mostrar error y salir con código no-zero.

---

## Validation

- [ ] V001 El script pasa `bash -n` (sintaxis correcta).
- [ ] V002 Ejecutar manualmente en un entorno de prueba con cambios pendientes; verificar que se auto-formatea, pasan pruebas y se crea commit + push.
- [ ] V003 Ejecutar con código que tiene error de mypy; verificar que el script aborta antes de commit.
- [ ] V004 Ejecutar sin cambios pendientes; verificar mensaje "no hay cambios" y salida 0.
