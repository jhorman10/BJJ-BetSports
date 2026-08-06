from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.domain.training.models import TrainingJobEvent, TrainingJobPhase
from src.utils.time_utils import get_current_time


def build_audit_entry(
    action: str,
    actor: str | None,
    target_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "entry_id": str(uuid4()),
        "action": action,
        "actor": actor,
        "target_id": target_id,
        "metadata": metadata or {},
        "occurred_at": get_current_time().isoformat(),
    }


def append_audit_entry(
    audit_trail: list[dict[str, Any]],
    action: str,
    actor: str | None,
    target_id: str,
    metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [*audit_trail, build_audit_entry(action, actor, target_id, metadata)]


def build_training_job_event(
    job_id: str,
    event_type: str,
    message: str,
    *,
    phase: TrainingJobPhase | None = None,
    progress_percent: int | None = None,
    payload: dict[str, Any] | None = None,
) -> TrainingJobEvent:
    return TrainingJobEvent(
        event_id=str(uuid4()),
        job_id=job_id,
        event_type=event_type,
        message=message,
        phase=phase,
        progress_percent=progress_percent,
        payload=payload or {},
    )
