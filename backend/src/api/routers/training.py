from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from src.api.schemas.training import (
    TrainingCapabilitiesPayload,
    TrainingExecutorOptionModel,
    TrainingJobCreatePayload,
    TrainingJobEventPayload,
    TrainingJobEventsPayload,
    TrainingJobListPayload,
    TrainingJobPayload,
    TrainingLatestResultPayload,
    TrainingModelOptionModel,
    TrainingModelsPayload,
    TrainingOptionModel,
    TrainingUnavailableReasonModel,
)
from src.api.security import require_training_read, require_training_write
from src.application.training.catalog import TrainingCapabilityService
from src.application.training.job_service import TrainingJobService
from src.application.training.result_reader import TrainingResultReader
from src.dependencies import (
    get_training_capability_service,
    get_training_job_service,
    get_training_result_reader,
)

router = APIRouter(prefix="/api/v1/training", tags=["training"])


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _job_payload(job) -> TrainingJobPayload:
    recipe = job.recipe_snapshot
    return TrainingJobPayload(
        job_id=job.job_id,
        recipe_snapshot={
            "recipe_id": recipe.recipe_id,
            "name": recipe.name,
            "model_key": recipe.model_key,
            "dataset_profile": recipe.dataset_profile,
            "league_ids": recipe.league_ids,
            "days_back": recipe.days_back,
            "feature_profile": recipe.feature_profile,
            "hyperparameter_profile": recipe.hyperparameter_profile,
            "executor_target": recipe.executor_target,
            "publish_strategy": recipe.publish_strategy,
            "requested_by": recipe.requested_by,
            "requested_at": _iso(recipe.requested_at),
            "description": recipe.description,
        },
        status=job.status,
        status_message=job.status_message,
        progress_percent=job.progress_percent,
        phase=job.phase,
        executor_type=job.executor_type,
        executor_run_id=job.executor_run_id,
        queued_at=_iso(job.queued_at),
        started_at=_iso(job.started_at),
        finished_at=_iso(job.finished_at),
        cancel_requested_at=_iso(job.cancel_requested_at),
        error_code=job.error_code,
        error_message=job.error_message,
        result_summary=job.result_summary,
        artifact_ids=job.artifact_ids,
        audit_trail=job.audit_trail,
    )


def _model_payload(model) -> TrainingModelOptionModel:
    return TrainingModelOptionModel(
        key=model.key,
        label=model.label,
        description=model.description,
        supported_feature_profiles=model.supported_feature_profiles,
        supported_dataset_profiles=model.supported_dataset_profiles,
        supported_executor_targets=model.supported_executor_targets,
        supported_league_ids=model.supported_league_ids,
        supported_days_back=model.supported_days_back,
        default_executor_target=model.default_executor_target,
    )


def _executor_payload(executor) -> TrainingExecutorOptionModel:
    description = executor.description
    if not executor.is_available and executor.unavailable_reasons:
        description = "; ".join(executor.unavailable_reasons)
    return TrainingExecutorOptionModel(
        key=executor.key,
        label=executor.label,
        description=description,
        available=executor.is_available,
        supports_cancel=executor.supports_cancel,
        supports_logs=executor.supports_logs,
    )


def _capabilities_payload(
    capability_service: TrainingCapabilityService,
) -> TrainingCapabilitiesPayload:
    snapshot = capability_service.snapshot()
    return TrainingCapabilitiesPayload(
        available=snapshot.available,
        models=[_model_payload(model) for model in snapshot.models],
        executors=[_executor_payload(executor) for executor in snapshot.executors],
        dataset_profiles=[
            TrainingOptionModel(
                key=profile.key,
                label=profile.label,
                description=profile.description,
            )
            for profile in snapshot.dataset_profiles
        ],
        feature_profiles=[
            TrainingOptionModel(
                key=profile.key,
                label=profile.label,
                description=profile.description,
            )
            for profile in snapshot.feature_profiles
        ],
        league_options=[
            TrainingOptionModel(
                key=league.key,
                label=league.label,
                description=league.description,
            )
            for league in snapshot.league_options
        ],
        days_back_options=snapshot.days_back_options,
        reasons=[
            TrainingUnavailableReasonModel(
                code=reason["code"], message=reason["message"]
            )
            for reason in snapshot.reasons
        ],
    )


@router.get("/capabilities", response_model=TrainingCapabilitiesPayload)
def get_training_capabilities(
    admin_key: str = Depends(require_training_read),
    capability_service: TrainingCapabilityService = Depends(
        get_training_capability_service
    ),
) -> TrainingCapabilitiesPayload:
    del admin_key
    return _capabilities_payload(capability_service)


@router.get("/models", response_model=TrainingModelsPayload)
def get_training_models(
    admin_key: str = Depends(require_training_read),
    capability_service: TrainingCapabilityService = Depends(
        get_training_capability_service
    ),
) -> TrainingModelsPayload:
    del admin_key
    snapshot = capability_service.snapshot()
    return TrainingModelsPayload(
        models=[_model_payload(model) for model in snapshot.models]
    )


@router.get("/results/latest", response_model=TrainingLatestResultPayload)
def get_latest_training_result(
    admin_key: str = Depends(require_training_read),
    training_result_reader: TrainingResultReader = Depends(get_training_result_reader),
) -> TrainingLatestResultPayload:
    del admin_key
    result, last_update = training_result_reader.get_latest_result()
    return TrainingLatestResultPayload(
        available=result is not None,
        data=result,
        last_update=last_update,
    )


@router.post(
    "/jobs", response_model=TrainingJobPayload, status_code=status.HTTP_201_CREATED
)
def create_training_job(
    payload: TrainingJobCreatePayload,
    admin_key: str = Depends(require_training_write),
    training_job_service: TrainingJobService = Depends(get_training_job_service),
) -> TrainingJobPayload:
    try:
        job = training_job_service.create_job(payload, requested_by=admin_key or None)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _job_payload(job)


@router.get("/jobs", response_model=TrainingJobListPayload)
def list_training_jobs(
    limit: int = Query(default=50, ge=1, le=200),
    admin_key: str = Depends(require_training_read),
    training_job_service: TrainingJobService = Depends(get_training_job_service),
) -> TrainingJobListPayload:
    del admin_key
    return TrainingJobListPayload(
        jobs=[_job_payload(job) for job in training_job_service.list_jobs(limit=limit)]
    )


@router.get("/jobs/{job_id}", response_model=TrainingJobPayload)
def get_training_job(
    job_id: str,
    admin_key: str = Depends(require_training_read),
    training_job_service: TrainingJobService = Depends(get_training_job_service),
) -> TrainingJobPayload:
    del admin_key
    job = training_job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Training job not found")
    return _job_payload(job)


@router.get("/jobs/{job_id}/events", response_model=TrainingJobEventsPayload)
def list_training_job_events(
    job_id: str,
    admin_key: str = Depends(require_training_read),
    training_job_service: TrainingJobService = Depends(get_training_job_service),
) -> TrainingJobEventsPayload:
    del admin_key
    job = training_job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Training job not found")
    events = training_job_service.list_events(job_id)
    return TrainingJobEventsPayload(
        job_id=job_id,
        events=[
            TrainingJobEventPayload(
                event_id=event.event_id,
                job_id=event.job_id,
                event_type=event.event_type,
                message=event.message,
                phase=event.phase,
                progress_percent=event.progress_percent,
                payload=event.payload,
                created_at=_iso(event.created_at),
            )
            for event in events
        ],
    )
