"""
CPIS V1 — Unified exception handlers.

Catches common exceptions and returns structured error responses.
Also provides a utility to log errors with full context without leaking secrets.
"""

from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)

# Patterns to redact from log messages
_SECRET_PATTERNS = [
    (r'(api_key|apikey|secret|token|password|authorization)=["\']?[^&\s"\']+', r'\1=***'),
    (r'Bearer\s+\S+', 'Bearer ***'),
    (r'(sk-[a-zA-Z0-9]{10,})', 'sk-***'),
]


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(400)
    async def bad_request(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": "Bad request", "error": str(exc)},
        )

    @app.exception_handler(404)
    async def not_found(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    @app.exception_handler(422)
    async def unprocessable(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(500)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        _log_safe("internal_error", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        _log_safe("unhandled_exception", exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


def _log_safe(event: str, exc: Exception) -> None:
    """Log an exception with redacted sensitive information."""
    msg = str(exc)
    for pattern, replacement in _SECRET_PATTERNS:
        msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
    logger.error(event, error=msg, error_type=type(exc).__name__)
