from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class ImmediateThread:
    def __init__(self, target=None, daemon=None):
        self._target = target
        self._daemon = daemon

    def start(self) -> None:
        if self._target is not None:
            self._target()


def test_load_backend_env_reads_admin_key_from_dotenv(tmp_path, monkeypatch) -> None:
    from src.core.env import load_backend_env

    env_file = tmp_path / ".env"
    env_file.write_text("ADMIN_API_KEY=test-from-dotenv\n", encoding="utf-8")

    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    loaded_env = load_backend_env(env_file)

    assert loaded_env == env_file
    assert os.getenv("ADMIN_API_KEY") == "test-from-dotenv"


def test_trigger_training_allows_local_dev_browser_without_api_key(monkeypatch) -> None:
    import src.api.main as main_mod

    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("API_ONLY_MODE", "false")
    monkeypatch.setattr(main_mod, "_training_running", False)
    monkeypatch.setattr(
        main_mod.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        main_mod,
        "threading",
        SimpleNamespace(Thread=ImmediateThread),
    )

    client = TestClient(main_mod.app)
    response = client.post(
        "/api/v1/train/run-now",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "started"
