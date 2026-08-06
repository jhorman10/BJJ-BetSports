from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from src.domain.training.models import (
    ArtifactStatus,
    PublishStrategy,
    TrainingJobPhase,
    TrainingJobStatus,
)


class TrainingOptionModel(BaseModel):
    key: str
    label: str
    description: str | None = None


class TrainingModelOptionModel(TrainingOptionModel):
    supported_feature_profiles: list[str] = Field(default_factory=list)
    supported_dataset_profiles: list[str] = Field(default_factory=list)
    supported_executor_targets: list[str] = Field(default_factory=list)
    supported_league_ids: list[str] = Field(default_factory=list)
    supported_days_back: list[int] = Field(default_factory=list)
    default_executor_target: str | None = None


class TrainingExecutorOptionModel(TrainingOptionModel):
    available: bool = True
    supports_cancel: bool = False
    supports_logs: bool = False


class TrainingUnavailableReasonModel(BaseModel):
    code: str
    message: str


class TrainingCapabilitiesPayload(BaseModel):
    available: bool
    models: list[TrainingModelOptionModel] = Field(default_factory=list)
    executors: list[TrainingExecutorOptionModel] = Field(default_factory=list)
    dataset_profiles: list[TrainingOptionModel] = Field(default_factory=list)
    feature_profiles: list[TrainingOptionModel] = Field(default_factory=list)
    league_options: list[TrainingOptionModel] = Field(default_factory=list)
    days_back_options: list[int] = Field(default_factory=list)
    reasons: list[TrainingUnavailableReasonModel] = Field(default_factory=list)


class TrainingModelsPayload(BaseModel):
    models: list[TrainingModelOptionModel] = Field(default_factory=list)


class TrainingLatestResultPayload(BaseModel):
    available: bool
    data: dict[str, Any] | None = None
    last_update: str | None = None


class TrainingJobCreatePayload(BaseModel):
    recipe_id: str
    name: str
    model_key: str
    dataset_profile: str
    league_ids: list[str] = Field(default_factory=list)
    days_back: int = 0
    feature_profile: str = "default"
    hyperparameter_profile: str = "default"
    executor_target: str = "default"
    publish_strategy: PublishStrategy = PublishStrategy.MANUAL
    description: str | None = None


class TrainingJobPayload(BaseModel):
    job_id: str
    recipe_snapshot: dict[str, Any]
    status: TrainingJobStatus
    status_message: str
    progress_percent: int = 0
    phase: TrainingJobPhase
    executor_type: str | None = None
    executor_run_id: str | None = None
    queued_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    cancel_requested_at: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    artifact_ids: list[str] = Field(default_factory=list)
    audit_trail: list[dict[str, Any]] = Field(default_factory=list)


class TrainingJobListPayload(BaseModel):
    jobs: list[TrainingJobPayload] = Field(default_factory=list)


class TrainingJobEventPayload(BaseModel):
    event_id: str
    job_id: str
    event_type: str
    message: str
    phase: TrainingJobPhase | None = None
    progress_percent: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class TrainingJobEventsPayload(BaseModel):
    job_id: str
    events: list[TrainingJobEventPayload] = Field(default_factory=list)


class ModelArtifactPayload(BaseModel):
    artifact_id: str
    job_id: str
    model_key: str
    status: ArtifactStatus
    metrics: dict[str, Any] = Field(default_factory=dict)
    feature_contract_version: str
    training_data_fingerprint: str | None = None
    context_summary: dict[str, Any] = Field(default_factory=dict)
    storage_location: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    published_at: str | None = None


class ActiveModelPointerPayload(BaseModel):
    scope_key: str
    artifact_id: str
    model_key: str
    promoted_by: str | None = None
    promoted_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromotionPayload(BaseModel):
    artifact_id: str
    scope_key: str
    promoted_by: str | None = None
