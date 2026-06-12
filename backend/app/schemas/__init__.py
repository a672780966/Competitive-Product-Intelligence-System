"""CPIS V1 — Pydantic schemas for URL validation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ValidationErrorCode(str, Enum):
    """Standardized error codes for URL validation."""

    URL_INVALID = "URL_INVALID"
    URL_FORBIDDEN = "URL_FORBIDDEN"
    ROBOTS_BLOCKED = "ROBOTS_BLOCKED"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    CAPTCHA_DETECTED = "CAPTCHA_DETECTED"
    FETCH_HTTP_ERROR = "FETCH_HTTP_ERROR"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"
    REDIRECT_LIMIT = "REDIRECT_LIMIT"
    EMPTY_CONTENT = "EMPTY_CONTENT"


class ValidationStatus(str, Enum):
    """URL validation result status."""

    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"
    WARNING = "warning"


class UrlValidationInput(BaseModel):
    """Input for URL validation."""

    source_url: str = Field(..., description="The raw URL to validate")
    category_hint: str | None = Field(None, description="Optional product category hint")
    language_hint: str | None = Field(None, description="Optional language hint (e.g. 'zh-CN')")
    check_robots: bool = Field(True, description="Whether to check robots.txt")
    follow_redirects: bool = Field(True, description="Whether to follow redirects during validation")


class UrlValidationResult(BaseModel):
    """Result of URL validation."""

    source_url: str
    normalized_url: str | None = None
    domain: str | None = None
    final_url: str | None = None
    status: ValidationStatus
    error_code: ValidationErrorCode | None = None
    error_message: str | None = None
    redirect_count: int = 0
    warnings: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}
