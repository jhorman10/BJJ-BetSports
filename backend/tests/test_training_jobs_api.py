from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ruff: noqa: E402
from fastapi.testclient import TestClient
from src.api.main import app  # noqa: E402
from src.api.schemas.training import TrainingJobCreatePayload  # noqa: E402
from src.api.security import (  # noqa: E402
    require_admin_key,
    require_training_read,
    require_training_write,
)
from src.application.training.job_service import TrainingJobService  # noqa: E402
from src.dependencies import get_training_job_service  # noqa: E402
from src.domain.training.models import (  # noqa: E402
    TrainingJobEvent,
    TrainingJobPhase,
    TrainingJobStatus,
)


class InMemoryJobRepository:
    def __init__(self) -> None:
        self.jobs = {}

    def save(self, job):
        self.jobs[job.job_id] = job
        return job

    def get(self, job_id: str):
        return self.jobs.get(job_id)

    def list_recent(self, *, limit: int = 50, status=None):
        jobs = list(self.jobs.values())
        if status is not None:
            jobs = [job for job in jobs if job.status == status]
        return jobs[:limit]


class InMemoryEventRepository:
    def __init__(self) -> None:
        self.events: dict[str, list[TrainingJobEvent]] = {}

    def append(self, event: TrainingJobEvent) -> TrainingJobEvent:
        self.events.setdefault(event.job_id, []).append(event)
        return event

    def list_for_job(self, job_id: str):
        return list(self.events.get(job_id, []))


class StubExecutor:
    key = "stub-executor"

    def submit(self, job):
        return {
            "executor_type": self.key,
            "executor_run_id": f"run::{job.job_id}",
            "status_message": "Queued for executor dispatch",
            "phase": TrainingJobPhase.REQUESTED,
            "status": TrainingJobStatus.QUEUED,
        }


def _build_service() -> TrainingJobService:
    return TrainingJobService(
        job_repository=InMemoryJobRepository(),
        event_repository=InMemoryEventRepository(),
        executor=StubExecutor(),
    )


def test_create_training_job_returns_job_identifier() -> None:
    service = _build_service()
    app.dependency_overrides[get_training_job_service] = lambda: service
    app.dependency_overrides[require_training_write] = lambda: "test-key"
    client = TestClient(app)

    response = client.post(
        "/api/v1/training/jobs",
        json={
            "recipe_id": "recipe-001",
            "name": "Manual training",
            "model_key": "baseline-model",
            "dataset_profile": "default",
            "league_ids": ["E0"],
            "days_back": 30,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"]
    assert body["status"] == "QUEUED"
    assert body["executor_type"] == "stub-executor"

    app.dependency_overrides.clear()


def test_get_training_job_events_returns_timeline() -> None:
    service = _build_service()
    created_job = service.create_job(
        TrainingJobCreatePayload(
            recipe_id="recipe-001",
            name="Manual training",
            model_key="baseline-model",
            dataset_profile="default",
            league_ids=["E0"],
            days_back=30,
        ),
        requested_by="test-key",
    )

    app.dependency_overrides[get_training_job_service] = lambda: service
    app.dependency_overrides[require_training_read] = lambda: "test-key"
    client = TestClient(app)

    response = client.get(f"/api/v1/training/jobs/{created_job.job_id}/events")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == created_job.job_id
    assert len(body["events"]) == 1
    assert body["events"][0]["event_type"] == "training.job.created"

    app.dependency_overrides.clear()


def test_legacy_run_now_creates_training_job_through_control_plane() -> None:
    service = _build_service()
    app.dependency_overrides[get_training_job_service] = lambda: service
    app.dependency_overrides[require_admin_key] = lambda: "test-key"
    client = TestClient(app)

    response = client.post("/api/v1/train/run-now")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "started"
    assert body["job_id"]
    assert service.get_job(body["job_id"]) is not None

    app.dependency_overrides.clear()
