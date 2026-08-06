from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from src.core.constants import ML_MODEL_FILENAME
from src.core.paths import BACKEND_ROOT, DATA_DIR

if TYPE_CHECKING:
    from src.infrastructure.cache.cache_service import CacheService


def get_model_artifact_paths() -> list[Path]:
    """Return the local ML artifact paths that must not survive a run."""
    model_paths = [
        BACKEND_ROOT / ML_MODEL_FILENAME,
        BACKEND_ROOT / "learning_weights.json",
    ]
    # Include all joblib files in roots and subdirs
    model_paths.extend(sorted(BACKEND_ROOT.glob("*.joblib")))
    model_paths.extend(sorted(BACKEND_ROOT.glob("*.csv")))
    model_paths.extend(sorted((BACKEND_ROOT / "ml_models").glob("*.joblib")))
    # Expanded coverage: baseline JSON in output/, benchmark artifacts in
    # tmp/ (files only). Runtime JSON assets (data/team_logos.json,
    # data/team_short_names.json) are intentionally NOT matched (they are not
    # *.joblib).
    # data/*.joblib: safety net only — the trained model is currently
    # persisted to MongoDB (binary_artifacts), NOT to data/, but keep the glob
    # in case a local joblib ever appears (older runs, manual fallbacks).
    model_paths.extend(sorted(DATA_DIR.glob("*.joblib")))
    model_paths.extend(sorted((BACKEND_ROOT / "output").glob("*.json")))
    model_paths.extend(
        p for p in sorted((BACKEND_ROOT / "tmp").glob("*")) if p.is_file()
    )

    # Deduplicate paths
    return list(set(model_paths))


def cleanup_model_artifacts(
    logger: logging.Logger, cache: "CacheService | None" = None
) -> None:
    """Remove persisted ML artifacts without interrupting the caller.

    When a cache provider is passed, its ``clear()`` is invoked to purge the
    disk cache (``.cache_data``). Failures are logged, never raised.
    """
    removed_count = 0
    failed_count = 0

    if cache is not None:
        try:
            cache.clear()
            logger.info("Cache cleared via cleanup_model_artifacts.")
        except Exception as exc:
            failed_count += 1
            logger.warning("Failed to clear cache during cleanup: %s", exc)

    for artifact_path in get_model_artifact_paths():
        if not artifact_path.exists():
            continue

        try:
            artifact_path.unlink()
            removed_count += 1
            logger.info("Removed local ML artifact: %s", artifact_path)
        except OSError as exc:
            failed_count += 1
            logger.warning(
                "Failed to remove local ML artifact %s: %s",
                artifact_path,
                exc,
            )

    if removed_count == 0 and failed_count == 0:
        logger.info("No local ML artifacts found to remove.")
        return

    logger.info(
        "Local ML artifact cleanup finished. removed=%s failed=%s",
        removed_count,
        failed_count,
    )
