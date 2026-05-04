from __future__ import annotations

from typing import Any


class TrainingResultReader:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def get_latest_result(self) -> tuple[dict[str, Any] | None, str | None]:
        result, updated_at = self.repository.get_training_result_with_timestamp(
            "latest_daily"
        )
        if updated_at is None:
            return result, None
        if hasattr(updated_at, "isoformat"):
            return result, updated_at.isoformat()
        return result, str(updated_at)