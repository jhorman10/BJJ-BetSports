from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from src.domain.training.models import TrainingJob, TrainingJobPhase, TrainingJobStatus


@dataclass(frozen=True)
class TrainingExecutorSubmission:
    executor_type: str
    executor_run_id: str
    status: TrainingJobStatus = TrainingJobStatus.QUEUED
    phase: TrainingJobPhase = TrainingJobPhase.REQUESTED
    status_message: str = "Queued for executor dispatch"


class TrainingExecutor(ABC):
    key: str

    @abstractmethod
    def submit(self, job: TrainingJob) -> TrainingExecutorSubmission | dict[str, Any]:
        """Submit a training job to the execution backend."""

    @abstractmethod
    def get_status(self, job: TrainingJob) -> dict[str, Any]:
        """Return the executor-visible status for a job."""

    @abstractmethod
    def cancel(self, job: TrainingJob) -> bool:
        """Request cooperative cancellation for a submitted job."""


class PassiveTrainingExecutor(TrainingExecutor):
    key = "passive-executor"

    def submit(self, job: TrainingJob) -> TrainingExecutorSubmission:
        return TrainingExecutorSubmission(
            executor_type=self.key,
            executor_run_id=f"run::{job.job_id}::{uuid4().hex[:8]}",
        )

    def get_status(self, job: TrainingJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "phase": job.phase.value,
        }

    def cancel(self, job: TrainingJob) -> bool:
        return False