"""Rate limiter security and fallback behavior."""

from __future__ import annotations

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.core import rate_limit
from app.core.config import settings


def _request(*, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for:
        headers.append((b"x-forwarded-for", forwarded_for.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/content-generator/generate",
            "raw_path": b"/api/v1/content-generator/generate",
            "query_string": b"",
            "headers": headers,
            "client": ("10.0.0.8", 1234),
            "server": ("test", 80),
        }
    )


def test_forwarded_ip_is_ignored_unless_proxy_is_trusted(monkeypatch):
    request = _request(forwarded_for="203.0.113.9, 10.0.0.2")
    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", False)
    assert rate_limit._client_ip(request) == "10.0.0.8"

    monkeypatch.setattr(settings, "TRUST_PROXY_HEADERS", True)
    assert rate_limit._client_ip(request) == "203.0.113.9"


@pytest.mark.asyncio
async def test_redis_outage_uses_local_limiter(monkeypatch):
    async def redis_unavailable(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return None

    monkeypatch.setattr(rate_limit, "_check_redis", redis_unavailable)
    monkeypatch.setattr(rate_limit, "_check_local", lambda *_a, **_k: (False, 31))
    middleware = rate_limit.RateLimitMiddleware(lambda *_a, **_k: None)

    response = await middleware.dispatch(_request(), lambda _request: Response())

    assert response.status_code == 429
    assert response.headers["x-ratelimit-remaining"] == "0"


@pytest.mark.asyncio
async def test_redis_rejection_does_not_double_capacity_with_local_fallback(monkeypatch):
    async def redis_rejected(*_args, **_kwargs):  # noqa: ANN002, ANN003
        return False, 31

    def local_must_not_run(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("local limiter must only run when Redis is unavailable")

    monkeypatch.setattr(rate_limit, "_check_redis", redis_rejected)
    monkeypatch.setattr(rate_limit, "_check_local", local_must_not_run)
    middleware = rate_limit.RateLimitMiddleware(lambda *_a, **_k: None)

    response = await middleware.dispatch(_request(), lambda _request: Response())

    assert response.status_code == 429
