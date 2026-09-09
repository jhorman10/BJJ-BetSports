"""
Best Combination Router

Exposes ``POST /api/v1/best-combination`` — the single 4-leg cross-sport
combination endpoint.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from src.api.dtos.best_combination_dtos import (
    BestCombinationRequest,
    BestCombinationResponse,
)
from src.dependencies import get_best_combination_use_case
from src.domain.services.combination_optimizer import CombinationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["best-combination"])


@router.post("/best-combination", response_model=BestCombinationResponse)
async def create_best_combination(
    request: BestCombinationRequest,
) -> BestCombinationResponse:
    """Build the best 4-leg combination (one pick per sport)."""
    use_case = get_best_combination_use_case()
    try:
        return await use_case.execute(request)
    except CombinationError as exc:
        logger.info(
            "best-combination rejected (%s): %s",
            exc.code,
            exc.detail,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": exc.code,
                "detail": exc.detail,
                "missing_sports": exc.missing_sports or [],
            },
        ) from exc
