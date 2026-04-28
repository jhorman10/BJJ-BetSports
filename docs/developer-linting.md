# Guía de linting y formateo para desarrolladores

Resumen rápido
--------------
Esta guía recoge el flujo canónico para validar backend y frontend localmente y para entender cómo CI valida el código.

Política de push
----------------
- Antes de cualquier `git push`, instala el hook versionado una vez desde la raíz:

```bash
./scripts/setup-hooks.sh
```

- El hook de `pre-push` ejecuta el gate completo:

```bash
./scripts/quality_gate.sh all
```

- Si el gate falla, el push queda bloqueado y no debe subirse código hasta corregirlo.
- La validación remota se completa en Pull Requests: `setup-branch-protection.yml` está preparado para exigir los checks `Backend: Lint + Types`, `Backend: Tests`, `Frontend: Lint + Build` y `Frontend: Tests` antes de mergear a ramas protegidas.
- Para ejecutar `setup-branch-protection.yml`, configura el secreto `BRANCH_PROTECTION_TOKEN` con permisos de administración del repositorio.

Comandos principales (local)
---------------------------
- Ejecutar el gate canónico full-stack desde la raíz del repo:

```bash
./scripts/quality_gate.sh all
```

- Ejecutar solo backend:

```bash
./scripts/quality_gate.sh backend
```

- Ejecutar solo frontend:

```bash
./scripts/quality_gate.sh frontend
```

- Ejecutar una línea base completa sin detenerse en el primer fallo:

```bash
./scripts/quality_gate.sh report
```

- `scripts/local_checks.sh` sigue existiendo, pero ahora delega al gate canónico:

```bash
./scripts/local_checks.sh
```

- Activar entorno virtual del backend para checks manuales:

```bash
source backend/.venv/bin/activate
```

- Ejecutar todos los hooks de `pre-commit` desde la raíz sin depender de `PATH`:

```bash
./scripts/pre_commit.sh run --all-files
```

- Ejecutar ruff para ver todos los errores de lint:

```bash
cd backend && .venv/bin/ruff check src tests
```

- Ejecutar `black` en modo verificación (excluir venv):

```bash
cd backend && .venv/bin/black --check src tests
```

- Ejecutar `isort` en modo verificación (evitar venv/node_modules):

```bash
cd backend && .venv/bin/isort --check-only src tests
```

- Ejecutar `mypy` con la misma forma que usa CI:

```bash
cd backend && .venv/bin/mypy src/ --ignore-missing-imports --follow-imports=skip
```

- Ejecutar pruebas unitarias del backend:

```bash
cd backend && .venv/bin/pytest -v --tb=short
```

- Ejecutar validación del frontend manualmente:

```bash
cd frontend && npm run lint && npm run build && npx vitest run
```

Qué hacer si hay fallos
-----------------------
- Para problemas de formato e imports: ejecutar el check concreto afectado o `./scripts/pre_commit.sh run --all-files`, luego volver a hacer `git add` + `git commit`.
- Para reglas de `ruff` (p. ej. E402, F821): revisar los imports y las anotaciones de tipos. Las correcciones no triviales (p. ej. C901) requieren un spec y refactor controlado.

CI
--
Las acciones de GitHub relevantes están en `.github/workflows/ci.yml`, `.github/workflows/ci-pr.yml` y `.github/workflows/lint.yml`. La intención operativa local debe replicar esta matriz:
- Backend: `ruff`, `black`, `isort`, `mypy`, `pytest`
- Frontend: `eslint`, `build`, `vitest`

Notas importantes
-----------------
- No deshabilitar reglas globalmente sin criar un `spec.md` justificando la excepción.
- Para C901 (funciones demasiado complejas): crear una tarea de refactor con tests que validen comportamiento antes de cambiar la implementación.
- Si necesitas ayuda para crear tests para una función compleja, pídemelo y puedo generar el esquema de tests y un plan de refactor.

Contacto
-------
- Orquestador (esta repo) documenta el proceso en `specs/manual-lint-fixes/spec.md` y en `specs/remove-c901/spec.md` (si existe).