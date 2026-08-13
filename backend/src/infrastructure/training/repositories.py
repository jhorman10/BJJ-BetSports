from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from src.domain.training.models import (
    ActiveModelPointer,
    ArtifactStatus,
    ModelArtifact,
    PublishStrategy,
    TrainingJob,
    TrainingJobEvent,
    TrainingJobPhase,
    TrainingJobStatus,
    TrainingRecipe,
)
from src.infrastructure.repositories.mongo_repository import (
    MongoRepository,
    get_mongo_repository,
)
from src.utils.time_utils import get_current_time


def _mongo_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _mongo_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _mongo_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_mongo_value(item) for item in value]
    return value


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


class _TrainingCollections:
    def __init__(self, persistence_repo: MongoRepository):
        self.training_jobs = persistence_repo.db["training_jobs"]
        self.training_job_events = persistence_repo.db["training_job_events"]
        self.model_artifacts = persistence_repo.db["model_artifacts"]
        self.active_model_pointers = persistence_repo.db["active_model_pointers"]

        self.training_jobs.create_index("job_id", unique=True)
        self.training_jobs.create_index("status")
        self.training_jobs.create_index("queued_at")
        self.training_jobs.create_index("model_key")

        self.training_job_events.create_index("event_id", unique=True)
        self.training_job_events.create_index("job_id")
        self.training_job_events.create_index("created_at")

        self.model_artifacts.create_index("artifact_id", unique=True)
        self.model_artifacts.create_index("job_id")
        self.model_artifacts.create_index("model_key")

        self.active_model_pointers.create_index("scope_key", unique=True)
        self.active_model_pointers.create_index("artifact_id")


class TrainingJobRepository:
    def __init__(self, persistence_repo: MongoRepository | None = None) -> None:
        self.persistence_repo = persistence_repo or get_mongo_repository()
        self.collections = _TrainingCollections(self.persistence_repo)

    def save(self, job: TrainingJob) -> TrainingJob:
        payload = {
            "job_id": job.job_id,
            "recipe_snapshot": _mongo_value(job.recipe_snapshot),
            "status": job.status.value,
            "status_message": job.status_message,
            "progress_percent": job.progress_percent,
            "phase": job.phase.value,
            "executor_type": job.executor_type,
            "executor_run_id": job.executor_run_id,
            "queued_at": job.queued_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "cancel_requested_at": job.cancel_requested_at,
            "error_code": job.error_code,
            "error_message": job.error_message,
            "result_summary": _mongo_value(job.result_summary),
            "artifact_ids": _mongo_value(job.artifact_ids),
            "audit_trail": _mongo_value(job.audit_trail),
            "requested_by": job.recipe_snapshot.requested_by,
            "model_key": job.recipe_snapshot.model_key,
            "updated_at": get_current_time(),
        }
        self.collections.training_jobs.update_one(
            {"job_id": job.job_id},
            {"$set": payload},
            upsert=True,
        )
        return self.get(job.job_id) or job

    def get(self, job_id: str) -> TrainingJob | None:
        doc = self.collections.training_jobs.find_one({"job_id": job_id})
        if doc is None:
            return None
        return self._to_domain(doc)

    def list_recent(
        self,
        *,
        limit: int = 50,
        status: TrainingJobStatus | None = None,
    ) -> list[TrainingJob]:
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value
        docs = (
            self.collections.training_jobs.find(query)
            .sort("queued_at", -1)
            .limit(limit)
        )
        return [self._to_domain(doc) for doc in docs]

    def delete_completed(self, logger: Any = None) -> int:
        terminal_statuses = [
            TrainingJobStatus.COMPLETED.value,
            TrainingJobStatus.FAILED.value,
            TrainingJobStatus.CANCELED.value,
        ]
        result = self.collections.training_jobs.delete_many(
            {"status": {"$in": terminal_statuses}}
        )
        if logger:
            logger.info(
                "Deleted %d terminal training jobs from MongoDB.", result.deleted_count
            )
        deleted_count: int = int(result.deleted_count)
        return deleted_count

    def _to_domain(self, doc: dict[str, Any]) -> TrainingJob:
        recipe_snapshot = doc.get("recipe_snapshot", {})
        recipe = TrainingRecipe(
            recipe_id=recipe_snapshot["recipe_id"],
            name=recipe_snapshot["name"],
            model_key=recipe_snapshot["model_key"],
            dataset_profile=recipe_snapshot["dataset_profile"],
            league_ids=recipe_snapshot.get("league_ids", []),
            days_back=recipe_snapshot.get("days_back", 0),
            feature_profile=recipe_snapshot.get("feature_profile", "default"),
            hyperparameter_profile=recipe_snapshot.get(
                "hyperparameter_profile", "default"
            ),
            executor_target=recipe_snapshot.get("executor_target", "default"),
            publish_strategy=PublishStrategy(
                recipe_snapshot.get("publish_strategy", PublishStrategy.MANUAL.value)
            ),
            requested_by=recipe_snapshot.get("requested_by"),
            requested_at=_parse_datetime(recipe_snapshot.get("requested_at"))
            or doc.get("queued_at")
            or get_current_time(),
            description=recipe_snapshot.get("description"),
        )
        return TrainingJob(
            job_id=doc["job_id"],
            recipe_snapshot=recipe,
            status=TrainingJobStatus(doc.get("status", TrainingJobStatus.QUEUED.value)),
            status_message=doc.get("status_message", ""),
            progress_percent=int(doc.get("progress_percent", 0)),
            phase=TrainingJobPhase(doc.get("phase", TrainingJobPhase.REQUESTED.value)),
            executor_type=doc.get("executor_type"),
            executor_run_id=doc.get("executor_run_id"),
            queued_at=doc.get("queued_at") or get_current_time(),
            started_at=doc.get("started_at"),
            finished_at=doc.get("finished_at"),
            cancel_requested_at=doc.get("cancel_requested_at"),
            error_code=doc.get("error_code"),
            error_message=doc.get("error_message"),
            result_summary=doc.get("result_summary", {}),
            artifact_ids=list(doc.get("artifact_ids", [])),
            audit_trail=list(doc.get("audit_trail", [])),
        )


class TrainingJobEventRepository:
    def __init__(self, persistence_repo: MongoRepository | None = None) -> None:
        self.persistence_repo = persistence_repo or get_mongo_repository()
        self.collections = _TrainingCollections(self.persistence_repo)

    def append(self, event: TrainingJobEvent) -> TrainingJobEvent:
        self.collections.training_job_events.update_one(
            {"event_id": event.event_id},
            {
                "$set": {
                    "event_id": event.event_id,
                    "job_id": event.job_id,
                    "event_type": event.event_type,
                    "message": event.message,
                    "phase": event.phase.value if event.phase else None,
                    "progress_percent": event.progress_percent,
                    "payload": _mongo_value(event.payload),
                    "created_at": event.created_at,
                }
            },
            upsert=True,
        )
        return event

    def list_for_job(self, job_id: str) -> list[TrainingJobEvent]:
        docs = self.collections.training_job_events.find({"job_id": job_id}).sort(
            "created_at", 1
        )
        return [
            TrainingJobEvent(
                event_id=doc["event_id"],
                job_id=doc["job_id"],
                event_type=doc["event_type"],
                message=doc["message"],
                phase=TrainingJobPhase(doc["phase"]) if doc.get("phase") else None,
                progress_percent=doc.get("progress_percent"),
                payload=doc.get("payload", {}),
                created_at=doc.get("created_at") or get_current_time(),
            )
            for doc in docs
        ]

    def delete_for_removed_jobs(self, logger: Any = None) -> int:
        remaining_job_ids = list(
            self.collections.training_job_events.distinct("job_id")
        )
        jobs_collection = self.collections.training_jobs
        existing_job_ids = [
            doc["job_id"]
            for doc in jobs_collection.find(
                {"job_id": {"$in": remaining_job_ids}}, {"job_id": 1}
            )
        ]
        result = self.collections.training_job_events.delete_many(
            {"job_id": {"$nin": existing_job_ids}}
        )
        if logger:
            logger.info(
                "Deleted %d orphaned training job events from MongoDB.",
                result.deleted_count,
            )
        deleted_count: int = int(result.deleted_count)
        return deleted_count


class ModelArtifactRepository:
    def __init__(self, persistence_repo: MongoRepository | None = None) -> None:
        self.persistence_repo = persistence_repo or get_mongo_repository()
        self.collections = _TrainingCollections(self.persistence_repo)

    def save(self, artifact: ModelArtifact) -> ModelArtifact:
        self.collections.model_artifacts.update_one(
            {"artifact_id": artifact.artifact_id},
            {
                "$set": {
                    "artifact_id": artifact.artifact_id,
                    "job_id": artifact.job_id,
                    "model_key": artifact.model_key,
                    "status": artifact.status.value,
                    "metrics": _mongo_value(artifact.metrics),
                    "feature_contract_version": artifact.feature_contract_version,
                    "training_data_fingerprint": artifact.training_data_fingerprint,
                    "context_summary": _mongo_value(artifact.context_summary),
                    "storage_location": artifact.storage_location,
                    "metadata": _mongo_value(artifact.metadata),
                    "created_at": artifact.created_at,
                    "published_at": artifact.published_at,
                }
            },
            upsert=True,
        )
        return self.get(artifact.artifact_id) or artifact

    def get(self, artifact_id: str) -> ModelArtifact | None:
        doc = self.collections.model_artifacts.find_one({"artifact_id": artifact_id})
        if doc is None:
            return None
        return ModelArtifact(
            artifact_id=doc["artifact_id"],
            job_id=doc["job_id"],
            model_key=doc["model_key"],
            status=ArtifactStatus(doc.get("status", ArtifactStatus.CANDIDATE.value)),
            metrics=doc.get("metrics", {}),
            feature_contract_version=doc.get("feature_contract_version", "v1"),
            training_data_fingerprint=doc.get("training_data_fingerprint"),
            context_summary=doc.get("context_summary", {}),
            storage_location=doc.get("storage_location"),
            metadata=doc.get("metadata", {}),
            created_at=doc.get("created_at") or get_current_time(),
            published_at=doc.get("published_at"),
        )

    def list_for_job(self, job_id: str) -> list[ModelArtifact]:
        docs = self.collections.model_artifacts.find({"job_id": job_id}).sort(
            "created_at", -1
        )
        return [
            ModelArtifact(
                artifact_id=doc["artifact_id"],
                job_id=doc["job_id"],
                model_key=doc["model_key"],
                status=ArtifactStatus(
                    doc.get("status", ArtifactStatus.CANDIDATE.value)
                ),
                metrics=doc.get("metrics", {}),
                feature_contract_version=doc.get("feature_contract_version", "v1"),
                training_data_fingerprint=doc.get("training_data_fingerprint"),
                context_summary=doc.get("context_summary", {}),
                storage_location=doc.get("storage_location"),
                metadata=doc.get("metadata", {}),
                created_at=doc.get("created_at") or get_current_time(),
                published_at=doc.get("published_at"),
            )
            for doc in docs
        ]


class ActiveModelPointerRepository:
    def __init__(self, persistence_repo: MongoRepository | None = None) -> None:
        self.persistence_repo = persistence_repo or get_mongo_repository()
        self.collections = _TrainingCollections(self.persistence_repo)

    def save(self, pointer: ActiveModelPointer) -> ActiveModelPointer:
        self.collections.active_model_pointers.update_one(
            {"scope_key": pointer.scope_key},
            {
                "$set": {
                    "scope_key": pointer.scope_key,
                    "artifact_id": pointer.artifact_id,
                    "model_key": pointer.model_key,
                    "promoted_by": pointer.promoted_by,
                    "promoted_at": pointer.promoted_at,
                    "metadata": _mongo_value(pointer.metadata),
                }
            },
            upsert=True,
        )
        return self.get(pointer.scope_key) or pointer

    def get(self, scope_key: str) -> ActiveModelPointer | None:
        doc = self.collections.active_model_pointers.find_one({"scope_key": scope_key})
        if doc is None:
            return None
        return ActiveModelPointer(
            scope_key=doc["scope_key"],
            artifact_id=doc["artifact_id"],
            model_key=doc["model_key"],
            promoted_by=doc.get("promoted_by"),
            promoted_at=doc.get("promoted_at") or get_current_time(),
            metadata=doc.get("metadata", {}),
        )
