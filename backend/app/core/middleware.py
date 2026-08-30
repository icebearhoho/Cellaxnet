"""FastAPI middleware: request-id, access log."""

from __future__ import annotations

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class CanonicalApiPathMiddleware:
    """Route slashless requests to canonical slash endpoints internally.

    FastAPI normally answers a slash mismatch with a 307 response.  When the
    frontend follows that response across origins, browsers can omit the
    ``Authorization`` header and turn a successful login into a 401.  Rewriting
    only paths that are known canonical routes keeps the request, method and
    headers intact without changing the public OpenAPI contract.
    """

    def __init__(self, app: ASGIApp, *, slash_paths: frozenset[str]) -> None:
        self.app = app
        self.slash_paths = slash_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        path = scope.get("path", "")
        canonical = f"{path}/"
        if scope["type"] == "http" and not path.endswith("/") and canonical in self.slash_paths:
            scope = dict(scope)
            scope["path"] = canonical
            scope["raw_path"] = canonical.encode("utf-8")
        await self.app(scope, receive, send)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["permissions-policy"] = "camera=(), geolocation=(), microphone=()"
        if settings.APP_ENV == "production":
            response.headers["strict-transport-security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        log.info(
            "request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            elapsed_ms=round(elapsed_ms, 2),
        )
        return response
