#!/usr/bin/env bash
set -euo pipefail

TRAIN_DAYS="${TRAIN_DAYS:-550}"
N_JOBS="${N_JOBS:-2}"
PREDICT_LEAGUES="${PREDICT_LEAGUES:-E0,SP1,D1,I1,F1,P1,B1,UCL}"
TOP_PICKS_LIMIT="${TOP_PICKS_LIMIT:-50}"

echo "🚀 Iniciando pipeline MLOps local dentro de contenedor"
echo "📦 TRAIN_DAYS=${TRAIN_DAYS} | N_JOBS=${N_JOBS}"
echo "🎯 PREDICT_LEAGUES=${PREDICT_LEAGUES}"

python3 scripts/orchestrator_cli.py cleanup
python3 scripts/orchestrator_cli.py train --days "${TRAIN_DAYS}" --n-jobs "${N_JOBS}" --leagues "${PREDICT_LEAGUES}"
python3 scripts/orchestrator_cli.py predict --leagues "${PREDICT_LEAGUES}" --parallel
python3 scripts/orchestrator_cli.py top-picks --limit "${TOP_PICKS_LIMIT}" --leagues "${PREDICT_LEAGUES}"

echo "🧹 Paso final: limpiando artefactos ML (cache + disco)..."
# Non-fatal: `|| true` keeps `set -e` from aborting the pipeline when there is
# nothing to clean or cleanup raises (spec: cleanup failure is non-fatal).
PYTHONPATH="$(pwd)" python3 - <<'PY' || true
import logging

from src.core.model_artifacts import cleanup_model_artifacts
from src.infrastructure.cache import get_cache_service

logger = logging.getLogger("pipeline-cleanup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

cache = get_cache_service()
# No explicit cache.clear() here: cleanup_model_artifacts(..., cache=cache)
# already purges the disk cache internally (avoids the duplicate clear, N3).
cleanup_model_artifacts(logger, cache=cache)
print("✅ Cleanup ML completado (artifact cleanup incluye cache.clear)")
PY

echo "✅ Pipeline MLOps local completado"
