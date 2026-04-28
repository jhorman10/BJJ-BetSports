#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
HOOKS_PATH=".githooks"
PRE_PUSH_HOOK="$HOOKS_PATH/pre-push"

if [[ -z "$REPO_ROOT" ]]; then
    echo "❌ Error: no se encontró la raíz git del repositorio." >&2
    exit 1
fi

if [[ ! -f "$REPO_ROOT/$PRE_PUSH_HOOK" ]]; then
    echo "❌ Error: hook versionado no encontrado en $PRE_PUSH_HOOK." >&2
    exit 1
fi

echo "Installing versioned pre-push hook..."
git -C "$REPO_ROOT" config core.hooksPath "$HOOKS_PATH"
chmod +x "$REPO_ROOT/$PRE_PUSH_HOOK"

echo "✅ Pre-push hook installed successfully."
echo "Now every push will run ./scripts/quality_gate.sh all before leaving your machine."
