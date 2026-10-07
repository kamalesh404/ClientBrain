"""Middleware and standardized error handlers for ClientBrain API."""
from datetime import datetime, timezone
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware


HTTP_STATUS_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    402: "PAYMENT_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}


def _get_request_id(request: Request) -> str:
    req_id = getattr(request.state, "request_id", None)
    if not req_id:
        req_id = request.headers.get("X-Request-ID")
    if not req_id:
        req_id = f"req_{uuid.uuid4().hex[:16]}"
    return req_id


def build_error_envelope(
    code: str,
    message: str,
    request_id: str,
    details: Any = None,
    detail: Any = None,
) -> dict[str, Any]:
    """Standardized error envelope matching production API contracts."""
    envelope = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "request_id": request_id,
    }
    if details is not None:
        envelope["error"]["details"] = details
    # Maintain top-level detail for backward compatibility with existing frontends/SDKs
    envelope["detail"] = detail if detail is not None else message
    return envelope


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID and tracks request latency."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = f"req_{uuid.uuid4().hex[:16]}"

        request.state.request_id = req_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time"] = f"{duration_ms}ms"
        return response


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = _get_request_id(request)
    code = HTTP_STATUS_CODE_NAMES.get(exc.status_code, f"HTTP_{exc.status_code}")
    message = str(exc.detail) if exc.detail else "Request error"
    envelope = build_error_envelope(
        code=code,
        message=message,
        request_id=req_id,
        detail=exc.detail,
    )
    headers = dict(getattr(exc, "headers", None) or {})
    headers["X-Request-ID"] = req_id
    return JSONResponse(status_code=exc.status_code, content=envelope, headers=headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = _get_request_id(request)
    envelope = build_error_envelope(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=req_id,
        details=exc.errors(),
        detail=exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope,
        headers={"X-Request-ID": req_id},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = _get_request_id(request)
    envelope = build_error_envelope(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred",
        request_id=req_id,
        detail="Internal server error",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope,
        headers={"X-Request-ID": req_id},
    )


def setup_middleware_and_exceptions(app: FastAPI):
    """Register custom middleware and exception handlers onto FastAPI app."""
    # Add tracing middleware
    app.add_middleware(RequestContextMiddleware)

    # Register standardized exception handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
