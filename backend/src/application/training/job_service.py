from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.api.schemas.training import TrainingJobCreatePayload
from src.application.training.audit import append_audit_entry, build_training_job_event
from src.application.training.executors.base import PassiveTrainingExecutor, TrainingExecutor
from src.domain.training.models import TrainingJob, TrainingRecipe
from src.domain.training.registries import ExecutorRegistry, ModelRegistry
from src.infrastructure.training.repositories import (
    TrainingJobEventRepository,
    TrainingJobRepository,
)


class TrainingJobService:
    def __init__(
        self,
        *,
        job_repository: TrainingJobRepository,
        event_repository: TrainingJobEventRepository,
        executor: TrainingExecutor | None = None,
        model_registry: ModelRegistry | None = None,
        executor_registry: ExecutorRegistry | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.event_repository = event_repository
        self.executor = executor or PassiveTrainingExecutor()
        self.model_registry = model_registry
        self.executor_registry = executor_registry

    def _validate_payload(self, payload: TrainingJobCreatePayload) -> None:
        if payload.days_back <= 0:
            raise ValueError("days_back must be greater than 0")
        if not payload.league_ids:
            raise ValueError("league_ids must include at least one scope")

        model = self.model_registry.get_model(payload.model_key) if self.model_registry else None
        if self.model_registry and model is None:
            raise ValueError(f"model_key '{payload.model_key}' is not available")

        if model is not None:
            if (
                model.supported_dataset_profiles
                and payload.dataset_profile not in model.supported_dataset_profiles
            ):
                raise ValueError(
                    f"dataset_profile '{payload.dataset_profile}' is not supported"
                )
            if (
                model.supported_feature_profiles
                and payload.feature_profile not in model.supported_feature_profiles
            ):
                raise ValueError(
                    f"feature_profile '{payload.feature_profile}' is not supported"
                )
            if (
                model.supported_executor_targets
                and payload.executor_target not in model.supported_executor_targets
            ):
                raise ValueError(
                    f"executor_target '{payload.executor_target}' is not supported for model_key '{payload.model_key}'"
                )
            if model.supported_league_ids:
                invalid_leagues = sorted(
                    {league_id for league_id in payload.league_ids if league_id not in model.supported_league_ids}
                )
                if invalid_leagues:
                    raise ValueError(
                        "league_ids contains unsupported scopes: "
                        + ", ".join(invalid_leagues)
                    )
            if (
                model.supported_days_back
                and payload.days_back not in model.supported_days_back
            ):
                raise ValueError(
                    f"days_back '{payload.days_back}' is not supported for model_key '{payload.model_key}'"
                )

        executor_definition = (
            self.executor_registry.get_executor(payload.executor_target)
            if self.executor_registry
            else None
        )
        if self.executor_registry and executor_definition is None:
            raise ValueError(
                f"executor_target '{payload.executor_target}' is not available"
            )
        if executor_definition is not None and not executor_definition.is_available:
            reasons = ", ".join(executor_definition.unavailable_reasons) or "executor unavailable"
            raise ValueError(
                f"executor_target '{payload.executor_target}' is not available: {reasons}"
            )

    def create_job(
        self,
        payload: TrainingJobCreatePayload | dict[str, Any],
        *,
        requested_by: str | None = None,
    ) -> TrainingJob:
        create_payload = (
            payload
            if isinstance(payload, TrainingJobCreatePayload)
            else TrainingJobCreatePayload.model_validate(payload)
        )
        self._validate_payload(create_payload)

        recipe = TrainingRecipe(
            recipe_id=create_payload.recipe_id,
            name=create_payload.name,
            model_key=create_payload.model_key,
            dataset_profile=create_payload.dataset_profile,
            league_ids=create_payload.league_ids,
            days_back=create_payload.days_back,
            feature_profile=create_payload.feature_profile,
            hyperparameter_profile=create_payload.hyperparameter_profile,
            executor_target=create_payload.executor_target,
            publish_strategy=create_payload.publish_strategy,
            requested_by=requested_by,
            description=create_payload.description,
        )
        job = TrainingJob(job_id=str(uuid4()), recipe_snapshot=recipe)

        submission = self.executor.submit(job)
        submission_payload = (
            submission.__dict__ if hasattr(submission, "__dict__") else submission
        )
        job.executor_type = submission_payload.get("executor_type")
        job.executor_run_id = submission_payload.get("executor_run_id")
        job.status = submission_payload.get("status", job.status)
        job.phase = submission_payload.get("phase", job.phase)
        job.status_message = submission_payload.get("status_message", job.status_message)
        job.audit_trail = append_audit_entry(
            job.audit_trail,
            "training.job.created",
            requested_by,
            job.job_id,
            {
                "recipe_id": recipe.recipe_id,
                "model_key": recipe.model_key,
                "executor_target": recipe.executor_target,
            },
        )

        saved_job = self.job_repository.save(job)
        self.event_repository.append(
            build_training_job_event(
                saved_job.job_id,
                "training.job.created",
                saved_job.status_message or "Training job created",
                phase=saved_job.phase,
                progress_percent=saved_job.progress_percent,
                payload={
                    "executor_type": saved_job.executor_type,
                    "executor_run_id": saved_job.executor_run_id,
                },
            )
        )
        return saved_job

    def get_job(self, job_id: str) -> TrainingJob | None:
        return self.job_repository.get(job_id)

    def list_jobs(self, *, limit: int = 50) -> list[TrainingJob]:
        return self.job_repository.list_recent(limit=limit)

    def list_events(self, job_id: str):
        return self.event_repository.list_for_job(job_id)