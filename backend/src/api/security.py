"""Seguridad de la API: autenticación por API key.

Provee dependencia para endpoints administrativos.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from src.core.env import load_backend_env

load_backend_env()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_LOCAL_DEV_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


class TrainingPermission(str, Enum):
    READ = "training:read"
    WRITE = "training:write"
    PROMOTE = "training:promote"


def _get_admin_api_key() -> str:
    return os.getenv("ADMIN_API_KEY", "").strip()


def _is_api_only_mode() -> bool:
    return os.getenv("API_ONLY_MODE", "false").strip().lower() == "true"


def _get_request_host(request: Request) -> str:
    if request.client and request.client.host:
        return str(request.client.host).strip().lower()
    return ""


def _is_local_dev_request(request: Request) -> bool:
    host = _get_request_host(request)
    if host in _LOCAL_DEV_HOSTS:
        return True

    # Allow Docker and private network IPs (172.16.x.x - 172.31.x.x,
    # 192.168.x.x, 10.x.x.x)
    if host.startswith("172.") or host.startswith("192.168.") or host.startswith("10."):
        return True

    return False


def _allow_local_dev_bypass(request: Request) -> bool:
    return not _is_api_only_mode() and _is_local_dev_request(request)


def _get_training_permissions() -> set[TrainingPermission]:
    raw_permissions = os.getenv(
        "TRAINING_ADMIN_PERMISSIONS",
        ",".join(
            [
                TrainingPermission.READ.value,
                TrainingPermission.WRITE.value,
                TrainingPermission.PROMOTE.value,
            ]
        ),
    )
    permissions: set[TrainingPermission] = set()
    for raw_permission in raw_permissions.split(","):
        normalized = raw_permission.strip()
        if not normalized:
            continue
        try:
            permissions.add(TrainingPermission(normalized))
        except ValueError:
            continue
    return permissions


async def require_admin_key(
    request: Request,
    api_key: Optional[str] = Security(API_KEY_HEADER),
) -> str:
    """Dependency que exige API key válida para endpoints administrativos.

    En desarrollo local permite bypass para peticiones desde loopback si ML está
    habilitado. Lanza HTTPException 503 si la key no está configurada en el
    servidor y la petición no califica para bypass local.
    Lanza HTTPException 403 si la key es inválida.
    """
    admin_api_key = _get_admin_api_key()

    if admin_api_key and api_key == admin_api_key:
        return api_key

    if _allow_local_dev_bypass(request):
        return api_key or ""

    if not admin_api_key:
        raise HTTPException(
            status_code=503,
            detail="Admin API key not configured on server",
        )

    if api_key != admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    return api_key


def require_training_permission(permission: TrainingPermission):
    async def _dependency(
        request: Request,
        api_key: Optional[str] = Security(API_KEY_HEADER),
    ) -> str:
        resolved_api_key = await require_admin_key(request, api_key)
        if permission not in _get_training_permissions():
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {permission.value}",
            )
        return resolved_api_key

    return _dependency


require_training_read = require_training_permission(TrainingPermission.READ)
require_training_write = require_training_permission(TrainingPermission.WRITE)
require_training_promote = require_training_permission(TrainingPermission.PROMOTE)
