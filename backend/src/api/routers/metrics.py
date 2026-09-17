from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from src.api.rate_limits import LIMIT_METRICS_READ, limiter
from src.application.services.metrics_baseline import compute_baseline
from src.dependencies import get_persistence_repository

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/baseline90d")
@limiter.limit(LIMIT_METRICS_READ)
def baseline_90d(
    request: Request,
    persistence_repo: Any = Depends(get_persistence_repository),
) -> dict[str, Any]:
    result = compute_baseline(persistence_repo, days=90)
    return cast(dict[str, Any], result)
