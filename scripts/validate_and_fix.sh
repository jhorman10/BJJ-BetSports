#!/usr/bin/env bash
# scripts/validate_and_fix.sh
# CI local: auto-formatea, lintea, ejecuta pruebas y sube cambios corregidos.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()   { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success(){ echo -e "${GREEN}✅ $1${NC}"; }
log_warn()   { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error()  { echo -e "${RED}❌ $1${NC}" >&2; }

# --- Verificar que estamos en un repo git ---
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  log_error "No estás en un repositorio git."
  exit 1
fi
# -----------------------------------------

# --- Detectar entorno virtual del backend ---
BACKEND_VENV_BIN=""
if [[ -f "$BACKEND_DIR/.venv/bin/python" ]]; then
  BACKEND_VENV_BIN="$BACKEND_DIR/.venv/bin"
elif [[ -f ".venv/bin/python" ]]; then
  BACKEND_VENV_BIN=".venv/bin"
elif [[ -f "venv/bin/python" ]]; then
  BACKEND_VENV_BIN="venv/bin"
fi

if [[ -n "$BACKEND_VENV_BIN" ]]; then
  log_info "Usando venv de backend: $BACKEND_VENV_BIN"
else
  log_warn "No se encontró venv de backend. Usando python3 del sistema."
fi
# -----------------------------------------

echo "============================================="
echo "🛠️  Paso 1: Auto-formateo y linting (fixed)..."
echo "============================================="

# --- Backend: Black, Ruff, Isort, Mypy ---
if [[ -d "$BACKEND_DIR" ]]; then
  log_info "Backend: Black (formato)..."
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    (cd "$BACKEND_DIR" && "$BACKEND_VENV_BIN/black" src tests)
  else
    (cd "$BACKEND_DIR" && python3 -m black src tests)
  fi

  log_info "Backend: Ruff (lint + auto-fix)..."
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    (cd "$BACKEND_DIR" && "$BACKEND_VENV_BIN/ruff" check --fix src tests)
  else
    (cd "$BACKEND_DIR" && python3 -m ruff check --fix src tests)
  fi

  log_info "Backend: Isort (imports)..."
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    (cd "$BACKEND_DIR" && "$BACKEND_VENV_BIN/isort" src tests)
  else
    (cd "$BACKEND_DIR" && python3 -m isort src tests)
  fi

  log_info "Backend: Mypy (tipado)..."
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    (cd "$BACKEND_DIR" && "$BACKEND_VENV_BIN/mypy" src --ignore-missing-imports --follow-imports=skip)
  else
    (cd "$BACKEND_DIR" && python3 -m mypy src --ignore-missing-imports --follow-imports=skip)
  fi
fi

# --- Frontend: ESLint (auto-fix) ---
if [[ -d "$FRONTEND_DIR" ]]; then
  log_info "Frontend: ESLint (auto-fix)..."
  (cd "$FRONTEND_DIR" && npm run lint -- --fix)
fi

echo ""
echo "============================================="
echo "🧪 Paso 2: Ejecutando tests (Backend + Frontend)..."
echo "============================================="

# --- Backend tests ---
if [[ -d "$BACKEND_DIR" ]]; then
  log_info "Backend: pytest..."
  cd "$BACKEND_DIR"
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    env PYTHONPATH="$BACKEND_DIR" "$BACKEND_VENV_BIN/python" -m pytest -v --tb=short
  else
    env PYTHONPATH="$BACKEND_DIR" python3 -m pytest -v --tb=short
  fi
  cd "$REPO_ROOT"
fi

# --- Frontend tests ---
if [[ -d "$FRONTEND_DIR" ]]; then
  log_info "Frontend: vitest..."
  (cd "$FRONTEND_DIR" && npx vitest run)
fi

echo ""
echo "============================================="
echo "📊 Resumen: todas las validaciones pasaron ✅"
echo "============================================="

# --- Commit y push si hay cambios ---
if git status --porcelain | grep -q '^'; then
  echo ""
  echo "============================================="
  echo "📦 Paso 3: Commit y push de cambios corregidos"
  echo "============================================="

  # Configurar git user si no existe (entorno CI local)
  git config user.name "CI Local Bot" 2>/dev/null || true
  git config user.email "ci-local@bjj-betsports.local" 2>/dev/null || true

  git add -A
  git commit -m "chore(ci): auto-format fixes and test validation"

  CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  log_info "Pushing a '$CURRENT_BRANCH'..."
  git push origin "$CURRENT_BRANCH"

  log_success "✅ Cambios subidos exitosamente."
else
  log_info "No hay cambios pendientes para commitear."
fi

echo ""
log_success "🎉 Pipeline local completado con éxito."
echo "============================================="
exit 0
echo "🛠️  Paso 1: Detectando y corrigiendo formato y linting (Auto-fix)..."
echo "============================================="

# Si existe el wrapper repo-local, lo usamos como fuente de verdad.
AUTO_FIX_MODE=0
if [[ "$1" == "--auto-fix" ]]; then
  AUTO_FIX_MODE=1
fi

if [[ -x "$PRE_COMMIT_WRAPPER" && $AUTO_FIX_MODE -eq 1 ]]; then
  log_info "Ejecutando pre-commit (auto-fix) vía wrapper local..."
  if ! "$PRE_COMMIT_WRAPPER" run --all-files; then
    log_warn "pre-commit modificó archivos. Se procederá a commit automático si todo pasa."
  fi
elif command -v pre-commit &> /dev/null && [[ $AUTO_FIX_MODE -eq 1 ]]; then
  log_info "Ejecutando pre-commit (auto-fix)..."
  if ! pre-commit run --all-files; then
    log_warn "pre-commit modificó archivos. Se procederá a commit automático si todo pasa."
  fi
else
  log_info "Ejecutando herramientas de formato individuales..."

  # Backend: Black, Ruff (auto-fix), Isort
  if [[ -d "$BACKEND_DIR" ]]; then
    log_info "Backend: Corriendo Black (formateo)..."
    if [[ -n "$BACKEND_VENV_BIN" ]]; then
      "$BACKEND_VENV_BIN/black" src tests || log_error "Falló Black en backend."
    else
      python3 -m black src tests || log_error "Falló Black en backend."
    fi

    log_info "Backend: Corriendo Ruff (auto-fix)..."
    if [[ -n "$BACKEND_VENV_BIN" ]]; then
      "$BACKEND_VENV_BIN/ruff" check --fix src tests || log_warn "Ruff encontró problemas no auto-fixables."
    else
      python3 -m ruff check --fix src tests || log_warn "Ruff encontró problemas no auto-fixables."
    fi

    log_info "Backend: Corriendo Isort (auto-fix)..."
    if [[ -n "$BACKEND_VENV_BIN" ]]; then
      "$BACKEND_VENV_BIN/isort" src tests || log_warn "Isort encontró problemas."
    else
      python3 -m isort src tests || log_warn "Isort encontró problemas."
    fi
  fi

  # Frontend: ESLint (auto-fix), Prettier si está configurado
  if [[ -d "$FRONTEND_DIR" ]]; then
    log_info "Frontend: Corriendo ESLint (auto-fix)..."
    cd "$FRONTEND_DIR"
    if command -v npm &> /dev/null; then
      npm run lint -- --fix || log_warn "ESLint falló en frontend (puede requerir atención manual)."
    else
      log_error "npm no encontrado para frontend."
    fi
    cd "$REPO_ROOT"
  fi
fi

echo ""
echo "============================================="
echo "🧪 Paso 2: Ejecutando suite de tests (Backend + Frontend)..."
echo "============================================="

BACKEND_STATUS=0
FRONTEND_STATUS=0

# Backend tests
if [[ -d "$BACKEND_DIR" ]]; then
  log_info "Backend: Ejecutando pytest..."
  cd "$BACKEND_DIR"
  if [[ -n "$BACKEND_VENV_BIN" ]]; then
    if ! env PYTHONPATH="$BACKEND_DIR" "$BACKEND_VENV_BIN/python" -m pytest -v --tb=short; then
      BACKEND_STATUS=1
      log_error "Fallaron pruebas de backend."
    else
      log_success "Pruebas de backend pasaron."
    fi
  else
    if ! env PYTHONPATH="$BACKEND_DIR" python3 -m pytest -v --tb=short; then
      BACKEND_STATUS=1
      log_error "Fallaron pruebas de backend."
    else
      log_success "Pruebas de backend pasaron."
    fi
  fi
  cd "$REPO_ROOT"
else
  log_warn "Carpeta backend no encontrada, omitiendo tests de Python."
fi

# Frontend tests
if [[ -d "$FRONTEND_DIR" ]]; then
  log_info "Frontend: Ejecutando vitest..."
  cd "$FRONTEND_DIR"
  if command -v npm &> /dev/null; then
    if ! npx vitest run; then
      FRONTEND_STATUS=1
      log_error "Fallaron pruebas de frontend."
    else
      log_success "Pruebas de frontend pasaron."
    fi
  else
    log_error "npm no disponible para ejecutar tests de frontend."
    FRONTEND_STATUS=1
  fi
  cd "$REPO_ROOT"
else
  log_warn "Carpeta frontend no encontrada, omitiendo tests de frontend."
fi

echo ""
echo "============================================="
echo "📊 Paso 3: Resumen de resultado"
echo "============================================="

if [[ $BACKEND_STATUS -eq 0 && $FRONTEND_STATUS -eq 0 ]]; then
  log_success "✅ Todas las validaciones pasaron. El código está listo."

  # Verificar si hay cambios pendientes en git
  if git status --porcelain | grep -q '^'; then
    echo ""
    echo "============================================="
    echo "📦 Paso 4: Commit y push automático de cambios corregidos"
    echo "============================================="

    # Configurar git user si no está (para CI local)
    if ! git config user.name &> /dev/null; then
      git config user.name "CI Local Bot"
    fi
    if ! git config user.email &> /dev/null; then
      git config user.email "ci-local@bjj-betsports.local"
    fi

    # Stage todos los cambios
    git add -A

    # Crear commit con mensaje convencional
    COMMIT_MSG="chore(ci): auto-format, lint fixes and test validation"
    git commit -m "$COMMIT_MSG"
    log_success "Commit creado: $COMMIT_MSG"

    # Push a la rama actual
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    log_info "Haciendo push a rama '$CURRENT_BRANCH'..."
    if git push origin "$CURRENT_BRANCH"; then
      log_success "✅ Cambios subidos exitosamente a '$CURRENT_BRANCH'."
    else
      log_error "Falló el push. Verifica tu conexión y permisos."
      exit 1
    fi
  else
    log_info "No hay cambios pendientes para commitear."
  fi

  echo "============================================="
  log_success "🎉 Pipeline local completado con éxito."
  echo "============================================="
  exit 0
else
  echo "============================================="
  log_error "❌ El pipeline falló. Corrige los errores antes de subir."
  echo "============================================="
  exit 1
fi
