"""Domain exceptions and FastAPI handlers.

Custom exceptions map to the standard error envelope in :mod:`app.core.responses`.
Handlers are registered in :func:`register_exception_handlers` and wired into
the FastAPI app in :mod:`app.main`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.responses import ErrorPayload, PageMeta


class ErrorCode:
    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"

    # Auth
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Resources
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"
    RESOURCE_GONE = "RESOURCE_GONE"

    # Business / domain
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"


class AppError(Exception):
    """Base class for all expected, mappable errors."""

    status_code: int = 400
    code: str = ErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    status_code = 404
    code = ErrorCode.RESOURCE_NOT_FOUND


class UnauthorizedError(AppError):
    status_code = 401
    code = ErrorCode.UNAUTHORIZED


class ForbiddenError(AppError):
    status_code = 403
    code = ErrorCode.FORBIDDEN


class ConflictError(AppError):
    status_code = 409
    code = ErrorCode.RESOURCE_CONFLICT


class BusinessRuleError(AppError):
    status_code = 422
    code = ErrorCode.BUSINESS_RULE_VIOLATION


class ValidationError(AppError):
    status_code = 422
    code = ErrorCode.VALIDATION_ERROR


class UpstreamUnavailableError(AppError):
    status_code = 503
    code = ErrorCode.UPSTREAM_UNAVAILABLE


# ---------------------------------------------------------------------------
# FastAPI handlers
# ---------------------------------------------------------------------------


def _envelope(
    *,
    request: Request,
    error: ErrorPayload,
    status_code: int,
) -> JSONResponse:
    meta = PageMeta(request_id=getattr(request.state, "request_id", None))
    body = {
        "success": False,
        "data": None,
        "meta": meta.model_dump(),
        "error": error.model_dump(),
    }
    return JSONResponse(status_code=status_code, content=body)


def _attach_request_id(request: Request) -> None:
    if not getattr(request.state, "request_id", None):
        request.state.request_id = uuid.uuid4().hex


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    _attach_request_id(request)
    return _envelope(
        request=request,
        error=ErrorPayload(code=exc.code, message=exc.message, details=exc.details),
        status_code=exc.status_code,
    )


def _serialisable_errors(exc: RequestValidationError) -> list[dict]:
    """Pydantic error list with the non-JSON bits stringified.

    When a field validator raises ValueError, pydantic puts the *exception
    object itself* in `ctx["error"]`, and `input` can hold arbitrary values.
    Handing those straight to JSONResponse blows up during serialisation, and
    the failure surfaces as a 500 with a traceback — so a plain bad-input
    request looks like a server crash. Any schema in the codebase that uses a
    custom validator hits this, not just one feature.
    """
    cleaned: list[dict] = []
    for err in exc.errors():
        e = dict(err)
        ctx = e.get("ctx")
        if isinstance(ctx, dict):
            e["ctx"] = {k: str(v) for k, v in ctx.items()}
        if "input" in e:
            try:
                json.dumps(e["input"])
            except (TypeError, ValueError):
                e["input"] = str(e["input"])
        cleaned.append(e)
    return cleaned


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    _attach_request_id(request)
    return _envelope(
        request=request,
        error=ErrorPayload(
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed.",
            details={"errors": _serialisable_errors(exc)},
        ),
        status_code=422,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    _attach_request_id(request)
    # Avoid leaking internals in non-debug mode.
    return _envelope(
        request=request,
        error=ErrorPayload(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error.",
            details={},
        ),
        status_code=500,
    )


async def http_404_handler(request: Request, exc: Exception) -> JSONResponse:
    _attach_request_id(request)
    return _envelope(
        request=request,
        error=ErrorPayload(
            code=ErrorCode.NOT_FOUND, message="Route not found.", details={}
        ),
        status_code=404,
    )


async def http_405_handler(request: Request, exc: Exception) -> JSONResponse:
    _attach_request_id(request)
    return _envelope(
        request=request,
        error=ErrorPayload(
            code=ErrorCode.METHOD_NOT_ALLOWED, message="Method not allowed.", details={}
        ),
        status_code=405,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(404, http_404_handler)  # type: ignore[arg-type]
    app.add_exception_handler(405, http_405_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)
