from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, cast

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Rate limiting (admin endpoints)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from src.api.schemas.auxiliary import TrainingCachedPayload, TrainingStatusPayload
from src.api.schemas.health import HealthResponse
from src.api.schemas.training import TrainingJobCreatePayload
from src.api.security import require_admin_key
from src.api.utils.helpers import _load_training_result
from src.api.utils.serializers import _utc_now_iso
from src.application.training.job_service import TrainingJobService
from src.core.env import load_backend_env
from src.dependencies import get_training_job_service

load_backend_env()

# Logger and runtime globals
_logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).parent.parent.parent
app = FastAPI(
    title="BJJ-BetSports API",
    version="1.0.0",
    description="API ligera para el stack portable local.",
)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

if not cors_origins:
    cors_origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Configure rate limiter for selective endpoint protection
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# slowapi's handler is typed with the narrower RateLimitExceeded exception;
# Starlette requires a generic Exception handler, so cast the variance away.
app.add_exception_handler(
    RateLimitExceeded,
    cast(
        Callable[[Request, Exception], JSONResponse],
        _rate_limit_exceeded_handler,
    ),
)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    _logger.exception(
        "Unhandled exception on %s %s: %s", request.method, request.url, exc
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", version=app.version, timestamp=_utc_now_iso())


from src.api.routers.labeler import router as labeler_router  # noqa: E402

# Register routers
from src.api.routers.leagues import router as leagues_router  # noqa: E402
from src.api.routers.matches import router as matches_router  # noqa: E402
from src.api.routers.metrics import router as metrics_router  # noqa: E402
from src.api.routers.monitor import router as monitor_router  # noqa: E402
from src.api.routers.picks import router as picks_router  # noqa: E402
from src.api.routers.predictions import router as predictions_router  # noqa: E402
from src.api.routers.training import router as training_router  # noqa: E402

app.include_router(leagues_router)
app.include_router(predictions_router)
app.include_router(matches_router)
app.include_router(picks_router)
app.include_router(metrics_router)
app.include_router(labeler_router)
app.include_router(monitor_router)
app.include_router(training_router)


@app.on_event("startup")
async def _validate_env_on_startup() -> None:
    from src.core.env import validate_required_env

    validate_required_env()


@app.get("/_ready")
def readiness_check() -> Dict[str, Any]:
    """Readiness check that attempts to validate critical dependencies.

    This endpoint is permissive: if the database is not configured it returns
    a structured response indicating the missing piece instead of failing the
    whole app startup.
    """
    import os

    checks = {"app": "ok"}
    ready = True
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        checks["database"] = "not_configured"
        ready = False
    else:
        try:
            from src.infrastructure.database.database_service import (
                get_database_service,
            )

            get_database_service()
            checks["database"] = "ok"
        except Exception:  # pragma: no cover - runtime environment dependent
            _logger.exception("Readiness check failed for database")
            checks["database"] = "error"
            ready = False

    return {"ready": ready, "checks": checks}


@app.get("/api/v1/train/status", response_model=TrainingStatusPayload)
def get_training_status() -> TrainingStatusPayload:
    result, last_update = _load_training_result()
    if result is None:
        return TrainingStatusPayload(
            status="IDLE",
            message="No hay resultado de entrenamiento disponible todavia.",
            has_result=False,
            result=None,
            last_update=None,
        )
    return TrainingStatusPayload(
        status="COMPLETED",
        message="Resultado de entrenamiento disponible.",
        has_result=True,
        result=result,
        last_update=last_update,
    )


@app.get("/api/v1/train/cached", response_model=TrainingCachedPayload)
def get_training_cached() -> TrainingCachedPayload:
    result, last_update = _load_training_result()
    return TrainingCachedPayload(
        cached=result is not None, data=result, last_update=last_update
    )


@app.post("/api/v1/train/run-now")
@limiter.limit("1/hour")
def trigger_training(
    request: Request,
    admin_key: str = Depends(require_admin_key),
    training_job_service: TrainingJobService = Depends(get_training_job_service),
) -> dict[str, str]:
    del request

    train_days = os.getenv("TRAIN_DAYS", "550")
    predict_leagues = os.getenv("PREDICT_LEAGUES", "E0")
    n_jobs = os.getenv("N_JOBS", "2")
    league_ids = [
        league.strip() for league in predict_leagues.split(",") if league.strip()
    ]

    job = training_job_service.create_job(
        TrainingJobCreatePayload(
            recipe_id="legacy-run-now",
            name="Legacy manual training",
            model_key=os.getenv("TRAIN_MODEL_KEY", "baseline-model"),
            dataset_profile="legacy-manual",
            league_ids=league_ids,
            days_back=int(train_days),
            feature_profile="default",
            hyperparameter_profile=f"n-jobs:{n_jobs}",
            executor_target=os.getenv("TRAIN_EXECUTOR_TARGET", "default"),
            description=(
                "Bridge from /api/v1/train/run-now to the training control plane."
            ),
        ),
        requested_by=admin_key or None,
    )

    _logger.info(
        "Legacy run-now bridged to training job %s: days=%s leagues=%s",
        job.job_id,
        train_days,
        predict_leagues,
    )

    return {
        "status": "started",
        "message": "Entrenamiento derivado al training control plane.",
        "job_id": job.job_id,
    }
