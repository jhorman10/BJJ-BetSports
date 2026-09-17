"""Shared rate limiter for all API endpoints.

Single Limiter instance so that storage/state is shared app-wide
and the exception handler registered in main.py catches violations
from every router consistently.

STORAGE SHARDING (CRITICAL): slowapi's default in-memory storage is
per-process. With gunicorn's N workers, each worker has its own counter —
effective limits are N× higher than advertised. To enforce limits across
workers, set RATE_LIMIT_STORAGE_URI to a Redis URL (e.g. redis://cache:6379/0).
"""

from __future__ import annotations

import os
from typing import Any, Optional

from slowapi import Limiter


def _get_client_ip(request: Any) -> str:
    """Get real client IP, respecting X-Forwarded-For only when explicitly trusted.

    In production behind a reverse proxy (nginx, ALB), the direct peer is the
    proxy. Without proxy trust configuration, all requests appear to come from
    the proxy IP — collapsing every user into one rate-limit bucket.

    Set TRUST_PROXY_IPS to a comma-separated list of CIDRs (e.g.
    "10.0.0.0/8,172.16.0.0/12") to accept X-Forwarded-For from those proxies.
    Defaults: empty (never trust XFF). The rightmost untrusted IP in the chain
    is used.
    """
    # If no trusted proxies configured, use socket peer directly
    trusted_proxies_raw = os.getenv("TRUST_PROXY_IPS", "").strip()
    peer: str = str(request.client.host) if request.client else "unknown"

    if not trusted_proxies_raw:
        return peer

    # X-Forwarded-For chain (comma-separated, leftmost = original client)
    xff = request.headers.get("x-forwarded-for") or ""
    if not xff:
        return peer

    # Parse chain: [client, proxy1, proxy2, ..., LB]
    chain = [ip.strip() for ip in xff.split(",") if ip.strip()]

    # Walk right-to-left: find the first IP in the chain that is NOT in our
    # trusted proxy list. That IP is the real client.
    # If peer itself is not trusted, ignore XFF entirely.
    import ipaddress

    try:
        trusted_networks = [
            ipaddress.ip_network(n.strip(), strict=False)
            for n in trusted_proxies_raw.split(",")
            if n.strip()
        ]
    except ValueError:
        # Invalid CIDR config → ignore XFF entirely (safe default)
        return peer

    def _is_trusted(ip_str: str) -> bool:
        try:
            addr = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        return any(addr in net for net in trusted_networks)

    if not _is_trusted(peer):
        # Direct connection from an untrusted host — do not trust XFF
        return peer

    # Walk chain right-to-left, skipping trusted proxies
    for ip_str in reversed(chain):
        if not _is_trusted(ip_str):
            return ip_str

    # All IPs in XFF are trusted proxies — use leftmost as client
    result: str = chain[0] if chain else peer
    return result


# Storage backend: Redis if configured, else in-memory (per-process).
# NOTE: with gunicorn multi-worker, in-memory storage means each worker has
# its own counter — effective limits are (N workers × configured limit).
# To share state across workers, set RATE_LIMIT_STORAGE_URI=redis://...
_RATE_LIMIT_STORAGE_URI: Optional[str] = os.getenv("RATE_LIMIT_STORAGE_URI") or None

limiter = Limiter(
    key_func=_get_client_ip,
    storage_uri=_RATE_LIMIT_STORAGE_URI,  # None → in-memory
    default_limits=[],  # No global default; limits are per-endpoint via decorators
)

# Predefined limit strings (tunable per endpoint category)
LIMIT_PREDICTIONS_READ = "60/minute"
LIMIT_PREDICTIONS_MATCH = "120/minute"  # cheap per-match lookup
LIMIT_MATCHES_LIVE = "60/minute"
LIMIT_MATCHES_QUERY = "30/minute"
LIMIT_SPORTS_PREDICT = "30/minute"  # expensive ML compute
LIMIT_SPORTS_READ = "60/minute"
LIMIT_PICKS_GENERATE = "20/minute"  # 90s timeout, heavy AI synthesis
LIMIT_PICKS_OTHER = "60/minute"
LIMIT_BEST_COMBINATION = "10/minute"  # combinatorial optimization
LIMIT_LEAGUES_READ = "60/minute"  # public league catalog
LIMIT_METRICS_READ = "60/minute"  # public metrics
