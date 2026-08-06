from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


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
    from src.dependencies import get_training_job_service

    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.setenv("API_ONLY_MODE", "false")
    # Local dev bypass requires this flag (see security._allow_local_dev_bypass)
    monkeypatch.setenv("LOCAL_DEV_BYPASS_ENABLED", "true")
    # Disable rate limiting for this test
    monkeypatch.setattr(main_mod.limiter, "enabled", False)

    fake_job = SimpleNamespace(
        job_id="job-123",
        status="queued",
        executor_type="thread",
        executor_run_id="run-1",
    )

    class FakeTrainingJobService:
        def create_job(self, payload, *, requested_by=None):
            return fake_job

    monkeypatch.setitem(
        main_mod.app.dependency_overrides,
        get_training_job_service,
        lambda: FakeTrainingJobService(),
    )

    client = TestClient(main_mod.app)
    response = client.post(
        "/api/v1/train/run-now",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "started"
