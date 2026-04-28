#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_VENV_BIN="$BACKEND_DIR/.venv/bin"
REPORT_MODE=0

print_section() {
  printf '\n=== %s ===\n' "$1"
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  return 1
}

require_file() {
  local file_path="$1"
  local message="$2"

  if [[ ! -e "$file_path" ]]; then
    fail "$message"
  fi
}

require_command() {
  local command_name="$1"
  local message="$2"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "$message"
  fi
}

run_gate_command() {
  local status=0

  if [[ "$REPORT_MODE" -eq 1 ]]; then
    set +e
    "$@"
    status=$?
    set -e
    return "$status"
  fi

  "$@"
}

run_backend() {
  local status=0

  print_section "Backend quality gate"

  require_file "$BACKEND_VENV_BIN/python" "Backend virtualenv missing. Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  require_file "$BACKEND_VENV_BIN/ruff" "Backend tooling missing. Run: cd backend && .venv/bin/pip install -r requirements.txt"
  require_file "$BACKEND_VENV_BIN/black" "Black missing in backend virtualenv. Run: cd backend && .venv/bin/pip install -r requirements.txt"
  require_file "$BACKEND_VENV_BIN/isort" "Isort missing in backend virtualenv. Run: cd backend && .venv/bin/pip install -r requirements.txt"
  require_file "$BACKEND_VENV_BIN/mypy" "Mypy missing in backend virtualenv. Run: cd backend && .venv/bin/pip install -r requirements.txt"
  require_file "$BACKEND_VENV_BIN/pytest" "Pytest missing in backend virtualenv. Run: cd backend && .venv/bin/pip install -r requirements.txt"

  (
    cd "$BACKEND_DIR"
    run_gate_command "$BACKEND_VENV_BIN/ruff" check src tests || status=$?
    run_gate_command "$BACKEND_VENV_BIN/black" --check src tests || status=$?
    run_gate_command "$BACKEND_VENV_BIN/isort" --check-only src tests || status=$?
    run_gate_command "$BACKEND_VENV_BIN/mypy" src --ignore-missing-imports --follow-imports=skip || status=$?
    run_gate_command env PYTHONPATH="$BACKEND_DIR" "$BACKEND_VENV_BIN/python" -m pytest -v --tb=short || status=$?
    exit "$status"
  )
}

run_frontend() {
  local status=0

  print_section "Frontend quality gate"

  require_command "npm" "npm is required for frontend validation"
  require_file "$FRONTEND_DIR/package-lock.json" "frontend/package-lock.json is required before running the quality gate"
  require_file "$FRONTEND_DIR/node_modules/.package-lock.json" "Frontend dependencies missing. Run: cd frontend && npm ci"

  (
    cd "$FRONTEND_DIR"
    run_gate_command npm run lint || status=$?
    run_gate_command npm run build || status=$?
    run_gate_command npx vitest run || status=$?
    exit "$status"
  )
}

print_summary() {
  local backend_status="$1"
  local frontend_status="$2"

  print_section "Quality gate summary"
  printf 'backend: %s\n' "$([[ "$backend_status" -eq 0 ]] && printf 'passed' || printf 'failed')"
  printf 'frontend: %s\n' "$([[ "$frontend_status" -eq 0 ]] && printf 'passed' || printf 'failed')"
}

case "$MODE" in
  all)
    run_backend
    run_frontend
    ;;
  backend)
    run_backend
    ;;
  frontend)
    run_frontend
    ;;
  report)
    REPORT_MODE=1
    set +e
    run_backend
    backend_status=$?
    run_frontend
    frontend_status=$?
    set -e

    print_summary "$backend_status" "$frontend_status"

    if [[ "$backend_status" -ne 0 || "$frontend_status" -ne 0 ]]; then
      exit 1
    fi
    ;;
  *)
    fail "Unsupported mode '$MODE'. Use: all | backend | frontend | report"
    ;;
esac

print_section "Quality gate passed"