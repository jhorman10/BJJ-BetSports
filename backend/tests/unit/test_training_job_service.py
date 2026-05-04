from __future__ import annotations

import pytest

from src.domain.training.models import TrainingJobEvent, TrainingJobPhase, TrainingJobStatus


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


class StubModelRegistry:
    def list_models(self):
        from src.domain.training.models import ModelAdapterDefinition

        return [
            ModelAdapterDefinition(
                key="baseline-model",
                label="Baseline Model",
                supported_feature_profiles=["default", "aggressive"],
                supported_executor_targets=["default", "local-worker"],
                default_executor_target="default",
            )
        ]

    def get_model(self, model_key: str):
        for model in self.list_models():
            if model.key == model_key:
                return model
        return None


class StubExecutorRegistry:
    def list_executors(self):
        from src.domain.training.models import ExecutorDefinition

        return [
            ExecutorDefinition(
                key="default",
                label="Default Executor",
                is_available=True,
            )
        ]

    def get_executor(self, executor_key: str):
        for executor in self.list_executors():
            if executor.key == executor_key:
                return executor
        return None

    def get_default_executor(self):
        return self.list_executors()[0]


def test_training_job_service_creates_queued_job_with_audit_and_event() -> None:
    from src.application.training.job_service import TrainingJobService
    from src.api.schemas.training import TrainingJobCreatePayload

    service = TrainingJobService(
        job_repository=InMemoryJobRepository(),
        event_repository=InMemoryEventRepository(),
        executor=StubExecutor(),
    )

    job = service.create_job(
        TrainingJobCreatePayload(
            recipe_id="recipe-001",
            name="Manual training",
            model_key="baseline-model",
            dataset_profile="default",
            league_ids=["E0"],
            days_back=30,
        ),
        requested_by="tester",
    )

    assert job.job_id
    assert job.status == TrainingJobStatus.QUEUED
    assert job.executor_type == "stub-executor"
    assert job.executor_run_id == f"run::{job.job_id}"
    assert job.audit_trail[-1]["action"] == "training.job.created"

    events = service.list_events(job.job_id)

    assert len(events) == 1
    assert events[0].event_type == "training.job.created"
    assert events[0].phase == TrainingJobPhase.REQUESTED


def test_training_job_service_rejects_unknown_model_key() -> None:
    from src.application.training.job_service import TrainingJobService
    from src.api.schemas.training import TrainingJobCreatePayload

    service = TrainingJobService(
        job_repository=InMemoryJobRepository(),
        event_repository=InMemoryEventRepository(),
        executor=StubExecutor(),
        model_registry=StubModelRegistry(),
        executor_registry=StubExecutorRegistry(),
    )

    with pytest.raises(ValueError, match="model_key"):
        service.create_job(
            TrainingJobCreatePayload(
                recipe_id="recipe-001",
                name="Manual training",
                model_key="missing-model",
                dataset_profile="default",
                league_ids=["E0"],
                days_back=30,
            ),
            requested_by="tester",
        )


def test_training_job_service_rejects_unavailable_executor_target() -> None:
    from src.application.training.job_service import TrainingJobService
    from src.api.schemas.training import TrainingJobCreatePayload

    service = TrainingJobService(
        job_repository=InMemoryJobRepository(),
        event_repository=InMemoryEventRepository(),
        executor=StubExecutor(),
        model_registry=StubModelRegistry(),
        executor_registry=StubExecutorRegistry(),
    )

    with pytest.raises(ValueError, match="executor_target"):
        service.create_job(
            TrainingJobCreatePayload(
                recipe_id="recipe-001",
                name="Manual training",
                model_key="baseline-model",
                dataset_profile="default",
                league_ids=["E0"],
                days_back=30,
                executor_target="missing-executor",
            ),
            requested_by="tester",
        )