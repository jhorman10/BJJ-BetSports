"""Seguridad de la API: autenticación por API key.

Provee dependencia para endpoints administrativos.
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from src.core.env import load_backend_env

load_backend_env()

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_LOCAL_DEV_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _get_admin_api_key() -> str:
    return os.getenv("ADMIN_API_KEY", "").strip()


def _is_api_only_mode() -> bool:
    return os.getenv("API_ONLY_MODE", "false").strip().lower() == "true"


def _get_request_host(request: Request) -> str:
    if request.client and request.client.host:
        return str(request.client.host).strip().lower()
    return ""


def _is_local_dev_request(request: Request) -> bool:
    return _get_request_host(request) in _LOCAL_DEV_HOSTS


def _allow_local_dev_bypass(request: Request) -> bool:
    return not _is_api_only_mode() and _is_local_dev_request(request)


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
