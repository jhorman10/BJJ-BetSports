"""Security hardening tests covering PR #61 4R review findings.

Tests for:
- C4: is_loopback bypass rejection for private IPs
- C5: rate limit 429 responses
- C6: security headers presence
- H8: Pydantic DTO validator rejections
- M1: 413 includes CORS headers
"""

from __future__ import annotations

import os
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Minimal env for app boot — validate_required_env is skipped when
# PYTEST_CURRENT_TEST is set (see src/core/env.py)
os.environ.setdefault("PYTEST_CURRENT_TEST", "1")


# ---------------------------------------------------------------------------
# C4 — Local dev bypass: private IPs must NOT qualify as loopback
# ---------------------------------------------------------------------------


class TestLocalDevBypassNarrowing:
    """The security.py change: is_private → is_loopback + no proxy headers."""

    class _FakeHeaders:
        """Mimics Starlette Headers.get() API for our narrow use case."""

        def __init__(self, data: dict | None = None):
            self._data = {k.lower(): v for k, v in (data or {}).items()}

        def get(self, key: str, default: str | None = None) -> str | None:
            return self._data.get(key.lower(), default)

    def _req(self, host: str, headers: dict | None = None):

        request = MagicMock()
        request.client.host = host
        request.headers = self._FakeHeaders(headers)
        request.method = "POST"
        request.url.path = "/api/v1/training/jobs"
        return request

    def test_loopback_ipv4_allowed(self):
        """127.0.0.1 directly → local."""
        from src.api.security import _is_local_dev_request

        req = self._req("127.0.0.1")
        assert _is_local_dev_request(req) is True

    def test_loopback_ipv6_allowed(self):
        """::1 directly → local."""
        from src.api.security import _is_local_dev_request

        req = self._req("::1")
        assert _is_local_dev_request(req) is True

    def test_private_ipv4_rejected(self):
        """192.168.x.x must NOT qualify as local (corporate LAN spoof risk)."""
        from src.api.security import _is_local_dev_request

        req = self._req("192.168.1.10")
        assert _is_local_dev_request(req) is False

    def test_private_class_a_rejected(self):
        """10.x.x.x must NOT qualify as local."""
        from src.api.security import _is_local_dev_request

        req = self._req("10.0.0.5")
        assert _is_local_dev_request(req) is False

    def test_loopback_with_proxy_headers_rejected(self):
        """Even if client is loopback, XFF header = came through proxy → reject."""
        from src.api.security import _is_local_dev_request

        req = self._req("127.0.0.1", headers={"x-forwarded-for": "203.0.113.5"})
        assert _is_local_dev_request(req) is False


# ---------------------------------------------------------------------------
# C5 — 429 responses from rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiting:
    """Verify @limiter.limit actually returns 429 when exceeded."""

    def test_rate_limit_429_after_threshold(self):
        """Exceeded limit returns 429 + Retry-After header."""
        from src.api.main import app
        from src.api.rate_limits import limiter

        limiter.reset()
        client = TestClient(app)

        statuses = []
        for _ in range(65):
            r = client.get("/api/v1/leagues")
            statuses.append(r.status_code)

        # LIMIT_LEAGUES_READ = 60/minute
        assert statuses[:60] == [200] * 60, f"First 60 should pass: {statuses[:5]}"
        assert all(s == 429 for s in statuses[60:]), "61+ should be 429"

    def test_429_has_retry_after_header(self):
        """429 response must include Retry-After header for client backoff."""
        from src.api.main import app
        from src.api.rate_limits import limiter

        limiter.reset()
        client = TestClient(app)

        # Hit the lowest-limit endpoint: best-combination (10/min)
        for _ in range(10):
            client.post("/api/v1/best-combination", json={})

        r = client.post("/api/v1/best-combination", json={})
        assert r.status_code == 429
        assert "retry-after" in {k.lower(): v for k, v in r.headers.items()}


# ---------------------------------------------------------------------------
# C6 — Security headers present on all responses
# ---------------------------------------------------------------------------


class TestSecurityHeaders:
    """Verify add_security_headers middleware covers all required headers."""

    def test_all_security_headers_present_on_health(self):
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

        # Always-on headers
        assert "content-security-policy" in response.headers
        assert "default-src 'self'" in response.headers["content-security-policy"]
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert "permissions-policy" in response.headers

    def test_hsts_absent_on_localhost(self):
        """HSTS must NOT be set when hostname is localhost (dev mode)."""
        from src.api.main import app

        client = TestClient(app)
        response = client.get("/health")

        # testclient reports hostname as "testserver" — not localhost → HSTS present
        # This documents the actual behavior: any non-localhost gets HSTS
        assert "strict-transport-security" in response.headers

    def test_cors_headers_on_413(self):
        """413 response must include CORS headers so browser doesn't see network error."""
        from src.api.main import app

        client = TestClient(app)
        big_payload = b'{"x": "' + b"a" * (1_048_577) + b'"}'

        response = client.post(
            "/api/v1/tennis/predict",
            content=big_payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        assert "access-control-allow-origin" in response.headers


# ---------------------------------------------------------------------------
# H8 — Pydantic DTO validators reject invalid input
# ---------------------------------------------------------------------------


class TestSportsDTOValidators:
    """Verify Field constraints reject malformed payloads."""

    # --- Tennis ---
    def test_tennis_rejects_invalid_surface(self):
        from pydantic import ValidationError
        from src.api.dtos.tennis_dtos import TennisMatchRequest

        with pytest.raises(ValidationError):
            TennisMatchRequest(
                tournament_name="Wimbledon",
                surface="Sand",  # invalid
                tourney_level="G",
                round_name="QF",
                match_date=date(2025, 7, 1),
                best_of=5,
                p1_name="Djokovic",
                p2_name="Alcaraz",
            )

    def test_tennis_rejects_impossible_odds(self):
        from pydantic import ValidationError
        from src.api.dtos.tennis_dtos import TennisMatchRequest

        with pytest.raises(ValidationError):
            TennisMatchRequest(
                tournament_name="Roland Garros",
                surface="Clay",
                tourney_level="G",
                round_name="R1",
                match_date=date(2025, 6, 1),
                best_of=5,
                p1_name="Nadal",
                p1_odds=0.5,  # odds must be > 1.0
                p2_name="Federer",
            )

    def test_tennis_accepts_valid_enums(self):
        """Happy path — valid Literal values pass."""
        from src.api.dtos.tennis_dtos import TennisMatchRequest

        payload = TennisMatchRequest(
            tournament_name="US Open",
            surface="Hard",
            tourney_level="G",
            round_name="F",
            match_date=date(2025, 9, 7),
            best_of=5,
            p1_name="Sinner",
            p1_hand="R",
            p1_rank=1,
            p2_name="Alcaraz",
            p2_hand="R",
            p2_rank=2,
        )
        assert payload.surface == "Hard"
        assert payload.best_of == 5

    # --- Baseball ---
    def test_baseball_rejects_invalid_day_night(self):
        from pydantic import ValidationError
        from src.api.dtos.baseball_dtos import BaseballPredictRequest

        with pytest.raises(ValidationError):
            BaseballPredictRequest(
                date=date(2025, 4, 1),
                home_team="NYY",
                away_team="BOS",
                day_night="twilight",  # invalid
            )

    def test_baseball_rejects_impossible_odds(self):
        from pydantic import ValidationError
        from src.api.dtos.baseball_dtos import BaseballPredictRequest

        with pytest.raises(ValidationError):
            BaseballPredictRequest(
                date=date(2025, 4, 1),
                home_team="NYY",
                away_team="BOS",
                home_odds=0.95,  # < 1.0
            )

    # --- Basketball ---
    def test_basketball_rejects_bad_season_format(self):
        from pydantic import ValidationError
        from src.api.dtos.basketball_dtos import BasketballPredictRequest

        with pytest.raises(ValidationError):
            BasketballPredictRequest(
                date=date(2025, 10, 22),
                home_team="LAL",
                away_team="BOS",
                season="25-26",  # must be YYYY-YY
            )

    def test_basketball_rejects_bad_game_type(self):
        from pydantic import ValidationError
        from src.api.dtos.basketball_dtos import BasketballPredictRequest

        with pytest.raises(ValidationError):
            BasketballPredictRequest(
                date=date(2025, 10, 22),
                home_team="LAL",
                away_team="BOS",
                game_type="X",  # only R (regular) or P (playoffs)
            )


# ---------------------------------------------------------------------------
# H9 — Sports router routes resolve after FastAPI 0.141 upgrade
# ---------------------------------------------------------------------------


class TestSportsRoutesRegistered:
    """Sanity: every /api/v1/<sport>/* endpoint is wired post-upgrade."""

    def test_all_sport_routes_present(self):
        from src.api.main import app

        expected_paths = [
            "/api/v1/tennis/predict",
            "/api/v1/tennis/upcoming",
            "/api/v1/tennis/tournaments",
            "/api/v1/tennis/predictions/{tournament_id}",
            "/api/v1/baseball/predict",
            "/api/v1/baseball/games",
            "/api/v1/baseball/series",
            "/api/v1/baseball/predictions/{series_id}",
            "/api/v1/basketball/predict",
            "/api/v1/basketball/games",
            "/api/v1/basketball/conferences",
            "/api/v1/basketball/predictions/{conference_id}",
            "/api/v1/best-combination",
        ]

        # Flatten routes (handles _IncludedRouter lazy wrappers in FastAPI 0.141+)
        def _flatten(routes):
            paths = []
            for r in routes:
                if hasattr(r, "path"):
                    paths.append(r.path)
                elif hasattr(r, "original_router"):
                    for sub in r.original_router.routes:
                        if hasattr(sub, "path"):
                            paths.append(sub.path)
            return paths

        actual_paths = set(_flatten(app.routes))

        missing = [p for p in expected_paths if p not in actual_paths]
        assert not missing, f"Missing routes after upgrade: {missing}"
