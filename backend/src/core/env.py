from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from src.core.paths import BACKEND_ROOT


def load_backend_env(env_path: Path | None = None) -> Path | None:
    candidate = env_path if env_path is not None else BACKEND_ROOT / ".env"
    if not candidate.exists():
        return None

    load_dotenv(candidate, override=False)
    return candidate
