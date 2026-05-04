# Implementation Plan: CI Local con Auto-Commit y Push

**Based on**: `specs/002-fix-local-ci-auto-push/spec.md`  
**Scope**: Modificación del script `scripts/validate_and_fix.sh` y verificación de herramientas.  
**Non-goals**: Modificar configuraciones de linter (ruff, eslint) o agregar nuevas dependencias. El script asume que las herramientas ya están instaladas (en venv o global).

## Technical Approach

### 1. Análisis del estado actual

- El script `validate_and_fix.sh` existente solo ejecuta pruebas de backend (`pytest`) y no incluye frontend.
- Utiliza un enfoque mixto: intenta usar pre-commit si existe, si no, ejecuta herramientas individuales.
- No hace commit ni push automático.
- No detecta entorno virtual de manera robusta; intenta activarlo vía `source` pero no es efectivo en bash no-interactivo.

### 2. Decisiones de diseño

- **Eliminar dependencia de pre-commit**: El script debe ser autónomo y ejecutar las herramientas directamente para asegurar predecibilidad.
- **Detección de venv**: Buscar `backend/.venv`, `.venv`, `venv` y usar binarios de ahí si existen. Si no, usar `python3 -m <tool>`.
- **Flujo de pasos**:
  1. Auto-fix backend: `black`, `ruff check --fix`, `isort`, `mypy` (chequeo estricto).
  2. Auto-fix frontend: `npm run lint -- --fix` (eslint).
  3. Tests: backend (`pytest`) y frontend (`npx vitest run`).
  4. Si todos los pasos anteriores exitosos, verificar si hay cambios pendientes en git.
  5. Si hay cambios, hacer `git add -A`, `git commit -m "chore(ci): auto-format fixes and test validation"` y `git push origin <current-branch>`.
- **Manejo de errores**: Usar `set -euo pipefail` para abortar en cualquier fallo. Mostrar mensajes claros con colores.
- **Configuración de git**: Si no hay `user.name`/`user.email` configurados, establecer valores por defecto para el commit automático.
- **Validación de entorno**: Verificar que se está en un repositorio git antes de intentar commit/push.

### 3. Requisitos previos (asumidos)

- Backend: `backend/requirements.txt` incluye `black`, `ruff`, `isort`, `mypy`, `pytest`.
- Frontend: `frontend/package.json` incluye scripts `lint` (eslint) y `test` (vitest). Dependencias instaladas vía `npm ci`.
- El script se ejecuta desde la raíz del repositorio.

### 4. Estructura del script resultante

```bash
#!/usr/bin/env bash
set -euo pipefail

# Colores y logging
# Detección de repo git
# Detección de backend venv
# Paso 1: Auto-fix backend y frontend
# Paso 2: Tests (backend + frontend)
# Paso 3: Commit y push si hay cambios
```

### 5. Validación y pruebas

- **Prueba manual**: 
  - Introducir deliberadamente un error de formato en backend o frontend y ejecutar script; debe auto-corregir y commitear.
  - Introducir un error de tipo (mypy) que falle; el script debe abortar sin commit.
  - Dejar código limpio; el script debe commitear y push exitosamente.
- **Prueba de entornos**: Ejecutar con y sin venv.
- **Prueba frontend**: Asegurar que `npx vitest run` se ejecuta correctamente en el directorio `frontend`.

### 6. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| El script haga push a la rama equivocada | Obtiene la rama actual con `git rev-parse --abbrev-ref HEAD`. |
| Falla de herramientas no instaladas | El script falla con mensaje claro indicando instalar dependencias. |
| Conflictos de merge después del push | El script no hace pull; se asume que el usuario tiene la rama actualizada. Se puede agregar `git pull --rebase` opcional en futuras iteraciones. |
| Cambios no deseados se incluyen en el commit | El script usa `git add -A` que respeta `.gitignore`. |

### 7. Entregables

- Archivo modificado: `scripts/validate_and_fix.sh` (permisos de ejecución ya establecidos).

### 8. Checklist de calidad (code-quality)

- **Conventional Commits**: mensaje de commit usa tipo `chore`, scope `ci`.
- **Bash best practices**: `set -euo pipefail`, funciones de logging, variables locales, paths absolutos via `cd`.
- **Logs claros**: Secciones con emojis y colores para fácil seguimiento.
- **Robustez**: verifica entorno git y existencia de directorios.
- **DRY**: reusa lógica de detección de venv.
