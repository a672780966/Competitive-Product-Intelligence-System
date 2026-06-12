"""
CPIS V1 — Middleware: request_id, structured logging context, and performance tracking.

Every request gets a unique request_id injected into the structlog contextvars,
making it possible to correlate log entries across the request lifecycle.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that:
    1. Assigns a unique request_id to each request.
    2. Adds request_id + method + path to structured log context.
    3. Logs request start and completion with duration.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())

        # Inject context into structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        method = request.method
        path = request.url.path

        logger.info("request_start", method=method, path=path)

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "request_error",
                method=method, path=path,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "request_end",
            method=method, path=path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        # Add request_id to response headers for debugging
        response.headers["X-Request-ID"] = request_id
        return response
