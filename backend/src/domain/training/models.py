from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.utils.time_utils import get_current_time


class TrainingJobStatus(str, Enum):
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    PREPARING_DATA = "PREPARING_DATA"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TrainingJobPhase(str, Enum):
    REQUESTED = "REQUESTED"
    VALIDATION = "VALIDATION"
    DATA_PREPARATION = "DATA_PREPARATION"
    TRAINING = "TRAINING"
    EVALUATION = "EVALUATION"
    PUBLISHING = "PUBLISHING"
    FINISHED = "FINISHED"


class PublishStrategy(str, Enum):
    MANUAL = "manual"
    SHADOW = "shadow"
    REPLACE_ACTIVE = "replace-active"


class ArtifactStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class TrainingRecipe:
    recipe_id: str
    name: str
    model_key: str
    dataset_profile: str
    league_ids: list[str] = field(default_factory=list)
    days_back: int = 0
    feature_profile: str = "default"
    hyperparameter_profile: str = "default"
    executor_target: str = "default"
    publish_strategy: PublishStrategy = PublishStrategy.MANUAL
    requested_by: str | None = None
    requested_at: datetime = field(default_factory=get_current_time)
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.recipe_id.strip():
            raise ValueError("recipe_id is required")
        if not self.name.strip():
            raise ValueError("recipe name is required")
        if not self.model_key.strip():
            raise ValueError("model_key is required")
        if self.days_back < 0:
            raise ValueError("days_back cannot be negative")


@dataclass(frozen=True)
class TrainingJobEvent:
    event_id: str
    job_id: str
    event_type: str
    message: str
    phase: TrainingJobPhase | None = None
    progress_percent: int | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=get_current_time)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id is required")
        if not self.job_id.strip():
            raise ValueError("job_id is required")
        if not self.event_type.strip():
            raise ValueError("event_type is required")
        if not self.message.strip():
            raise ValueError("message is required")
        if self.progress_percent is not None and not 0 <= self.progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")


@dataclass
class TrainingJob:
    job_id: str
    recipe_snapshot: TrainingRecipe
    status: TrainingJobStatus = TrainingJobStatus.QUEUED
    status_message: str = ""
    progress_percent: int = 0
    phase: TrainingJobPhase = TrainingJobPhase.REQUESTED
    executor_type: str | None = None
    executor_run_id: str | None = None
    queued_at: datetime = field(default_factory=get_current_time)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    cancel_requested_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    result_summary: dict[str, Any] = field(default_factory=dict)
    artifact_ids: list[str] = field(default_factory=list)
    audit_trail: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id is required")
        if not 0 <= self.progress_percent <= 100:
            raise ValueError("progress_percent must be between 0 and 100")


@dataclass(frozen=True)
class ModelAdapterDefinition:
    key: str
    label: str
    description: str | None = None
    supported_feature_profiles: list[str] = field(default_factory=list)
    supported_dataset_profiles: list[str] = field(default_factory=list)
    supported_executor_targets: list[str] = field(default_factory=list)
    supported_league_ids: list[str] = field(default_factory=list)
    supported_days_back: list[int] = field(default_factory=list)
    default_executor_target: str | None = None
    artifact_format: str = "unknown"
    metrics_schema_version: str = "v1"
    feature_contract_version: str = "v1"

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("model adapter key is required")
        if not self.label.strip():
            raise ValueError("model adapter label is required")


@dataclass(frozen=True)
class ExecutorDefinition:
    key: str
    label: str
    description: str | None = None
    is_available: bool = True
    unavailable_reasons: list[str] = field(default_factory=list)
    supports_cancel: bool = False
    supports_logs: bool = False

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("executor key is required")
        if not self.label.strip():
            raise ValueError("executor label is required")


@dataclass
class ModelArtifact:
    artifact_id: str
    job_id: str
    model_key: str
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    metrics: dict[str, Any] = field(default_factory=dict)
    feature_contract_version: str = "v1"
    training_data_fingerprint: str | None = None
    context_summary: dict[str, Any] = field(default_factory=dict)
    storage_location: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=get_current_time)
    published_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.artifact_id.strip():
            raise ValueError("artifact_id is required")
        if not self.job_id.strip():
            raise ValueError("job_id is required")
        if not self.model_key.strip():
            raise ValueError("model_key is required")


@dataclass(frozen=True)
class ActiveModelPointer:
    scope_key: str
    artifact_id: str
    model_key: str
    promoted_by: str | None = None
    promoted_at: datetime = field(default_factory=get_current_time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scope_key.strip():
            raise ValueError("scope_key is required")
        if not self.artifact_id.strip():
            raise ValueError("artifact_id is required")
        if not self.model_key.strip():
            raise ValueError("model_key is required")
