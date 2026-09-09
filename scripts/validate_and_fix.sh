#!/usr/bin/env bash
# scripts/validate_and_fix.sh
# CI local: auto-formatea, lintea, ejecuta pruebas y commitea cambios corregidos.
# NOTA: No hace push — eso lo maneja git push original (pre-push hook).

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

echo "============================================="
echo "🛠️  Paso 1: Auto-formateo y linting..."
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
    (cd "$BACKEND_DIR" && "$BACKEND_VENV_BIN/ruff" check --fix src tests) || log_warn "Ruff: style warnings (non-fatal)."
  else
    (cd "$BACKEND_DIR" && python3 -m ruff check --fix src tests) || log_warn "Ruff: style warnings (non-fatal)."
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
echo "🧪 Paso 2: Ejecutando tests..."
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

# --- Commit si hay cambios (sin push — push lo hace git) ---
if git status --porcelain | grep -q '^'; then
  echo ""
  echo "============================================="
  echo "📦 Paso 3: Commit de cambios corregidos"
  echo "============================================="

  git config user.name "CI Local Bot" 2>/dev/null || true
  git config user.email "ci-local@bjj-betsports.local" 2>/dev/null || true

  git add -A
  git commit -m "chore(ci): auto-format fixes and test validation"

  log_success "✅ Cambios commiteados. El push original continuará."
else
  log_info "No hay cambios pendientes para commitear."
fi

echo ""
log_success "🎉 Pipeline local completado con éxito."
echo "============================================="
exit 0
