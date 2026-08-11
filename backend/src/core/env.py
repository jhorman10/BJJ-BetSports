from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from src.core.paths import BACKEND_ROOT

_logger = logging.getLogger(__name__)


def load_backend_env(env_path: Path | None = None) -> Path | None:
    candidate = env_path if env_path is not None else BACKEND_ROOT / ".env"
    if not candidate.exists():
        return None

    load_dotenv(candidate, override=False)
    return candidate


_REQUIRED_ENV_VARS = [
    "ADMIN_API_KEY",
    "MONGO_URI",
    "MONGO_DB_NAME",
]


def validate_required_env() -> None:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    missing = [key for key in _REQUIRED_ENV_VARS if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )


def load_backend_env_and_validate(env_path: Path | None = None) -> Path | None:
    candidate = load_backend_env(env_path)
    validate_required_env()
    return candidate
