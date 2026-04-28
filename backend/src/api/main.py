from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict

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
from src.api.security import require_admin_key
from src.api.utils.helpers import _load_training_result
from src.api.utils.serializers import _utc_now_iso
from src.core.env import load_backend_env

load_backend_env()

# Logger and runtime globals
_logger = logging.getLogger(__name__)
_BACKEND_DIR = Path(__file__).parent.parent.parent
_training_lock = threading.Lock()
_training_running = False
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiter for selective endpoint protection
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
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

app.include_router(leagues_router)
app.include_router(predictions_router)
app.include_router(matches_router)
app.include_router(picks_router)
app.include_router(metrics_router)
app.include_router(labeler_router)
app.include_router(monitor_router)


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

            # get_database_service will raise if cannot connect
            get_database_service()
            checks["database"] = "ok"
        except Exception as exc:  # pragma: no cover - runtime environment dependent
            checks["database"] = f"error: {exc}"
            ready = False

    return {"ready": ready, "checks": checks}


@app.get("/api/v1/train/status", response_model=TrainingStatusPayload)
def get_training_status() -> TrainingStatusPayload:
    if _training_running:
        return TrainingStatusPayload(
            status="IN_PROGRESS",
            message="Entrenamiento en progreso...",
            has_result=False,
            result=None,
            last_update=None,
        )
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
    request: Request, admin_key: str = Depends(require_admin_key)
) -> dict[str, str]:
    global _training_running
    with _training_lock:
        if _training_running:
            return {
                "status": "already_running",
                "message": "El entrenamiento ya está en progreso.",
            }
        _training_running = True

    n_jobs = os.getenv("N_JOBS", "2")
    train_days = os.getenv("TRAIN_DAYS", "550")
    predict_leagues = os.getenv("PREDICT_LEAGUES", "E0")

    def _run() -> None:
        global _training_running
        try:
            _logger.info(
                "Iniciando entrenamiento: days=%s leagues=%s",
                train_days,
                predict_leagues,
            )
            subprocess.run(
                ["python3", "scripts/orchestrator_cli.py", "cleanup"],
                cwd=str(_BACKEND_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                [
                    "python3",
                    "scripts/orchestrator_cli.py",
                    "train",
                    "--days",
                    train_days,
                    "--n-jobs",
                    n_jobs,
                    "--leagues",
                    predict_leagues,
                ],
                cwd=str(_BACKEND_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            _logger.info("Entrenamiento finalizado.")
        except Exception as exc:
            _logger.error("Error en entrenamiento: %s", exc)
        finally:
            with _training_lock:
                _training_running = False

    threading.Thread(target=_run, daemon=True).start()
    return {
        "status": "started",
        "message": "Entrenamiento iniciado dentro del contenedor.",
    }
