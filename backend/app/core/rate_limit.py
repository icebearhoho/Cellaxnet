"""Sliding-window rate limiter, Redis-backed.

Key strategy: ``area303:rl:<scope>:<bucket>:<ip>`` where ``bucket``
is the current epoch minute. The middleware increments the counter
on every request and rejects when it exceeds the configured limit.

If Redis is unreachable, the process-local limiter remains active. This does
not coordinate multiple instances, but it avoids silently disabling all
protection during an outage.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.logging import get_logger
from app.core.responses import ErrorPayload, PageMeta

log = get_logger("app.core.rate_limit")

# In-process fallback when Redis is unavailable.
_LOCAL: dict[str, list[float]] = defaultdict(list)

# When Redis fails, skip it for a cooldown window so we don't pay the
# connect-timeout on *every* request while it's down (fail-open + fast).
_REDIS_DOWN_UNTIL: float = 0.0
_REDIS_DOWN_COOLDOWN = 30.0  # seconds


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if settings.TRUST_PROXY_HEADERS and fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _scope_for(request: Request) -> str:
    """Apply stricter limits on GenAI routes; fall through to global."""
    path = request.url.path
    if any(seg in path for seg in ("personal-shopper", "content-generator", "recsys", "seller-coach")):
        return "genai"
    return "global"


async def _check_redis(
    scope: str, ip: str, *, limit: int, window: int = 60
) -> tuple[bool, int] | None:
    global _REDIS_DOWN_UNTIL
    # Skip Redis entirely during the cooldown after a recent failure.
    if time.monotonic() < _REDIS_DOWN_UNTIL:
        return None

    bucket = int(time.time() // window)
    key = f"area303:rl:{scope}:{bucket}:{ip}"
    try:
        from app.db.redis import get_redis

        client = get_redis()
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        count, _ = await pipe.execute()
        return int(count) <= limit, int(count)
    except Exception as exc:
        _REDIS_DOWN_UNTIL = time.monotonic() + _REDIS_DOWN_COOLDOWN
        log.warning("rate_limit.redis_failed", error=str(exc), cooldown_s=_REDIS_DOWN_COOLDOWN)
        return None


def _check_local(scope: str, ip: str, *, limit: int, window: int = 60) -> tuple[bool, int]:
    key = f"{scope}:{ip}"
    now = time.monotonic()
    bucket = _LOCAL[key]
    cutoff = now - window
    bucket[:] = [t for t in bucket if t > cutoff]
    bucket.append(now)
    return len(bucket) <= limit, len(bucket)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limit. Off by default until GENAI routes are live."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        scope = _scope_for(request)
        ip = _client_ip(request)
        limit = (
            settings.RATE_LIMIT_PER_MINUTE
            if scope == "genai"
            else settings.GLOBAL_RATE_LIMIT_PER_MINUTE
        )

        redis_result = await _check_redis(scope, ip, limit=limit)
        if redis_result is None:
            ok, count = _check_local(scope, ip, limit=limit)
        else:
            ok, count = redis_result
        if not ok:
            return _reject(scope, ip, count, limit)

        response = await call_next(request)
        response.headers["x-ratelimit-limit"] = str(limit)
        response.headers["x-ratelimit-remaining"] = str(max(0, limit - count))
        return response


def _reject(scope: str, ip: str, count: int, limit: int) -> JSONResponse:
    log.info("rate_limit.exceeded", scope=scope, ip=ip, count=count)
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "data": None,
            "meta": PageMeta().model_dump(),
            "error": ErrorPayload(
                code="RATE_LIMITED",
                message=f"Too many requests. Limit: {limit}/min.",
                details={"scope": scope, "count": count, "limit": limit},
            ).model_dump(),
        },
        headers={
            "Retry-After": "60",
            "x-ratelimit-limit": str(limit),
            "x-ratelimit-remaining": "0",
        },
    )
