"""RunPlan Pydantic validation schemas.

Validates the declarative RunPlan JSON as defined in RUNPLAN_DECLARATIVE_SPEC.md.
No executable code allowed — pure data validation only.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_DANGEROUS_PATTERNS = re.compile(
    r"\b(exec|eval|__builtins__|__import__|os\.|subprocess|spawn|fork|compile|globals|locals)\b",
)


class CollectorParams(BaseModel):
    timeout: int = Field(default=20, ge=5, le=120)
    wait_for_selector: str | None = Field(None, max_length=200)
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=800, ge=240, le=2160)
    headers: dict[str, str] | None = Field(None)
    cookies: list[dict[str, str]] | None = Field(None, max_length=20)


class CollectorSpec(BaseModel):
    kind: Literal["direct_http", "playwright", "scrapling", "crawl4ai"]
    params: CollectorParams = Field(default_factory=lambda: CollectorParams())


class ExtractOptions(BaseModel):
    extraction_prompt: str | None = Field(None, max_length=2000)
    skip_extraction: bool = False
    confidence_threshold: float | None = Field(None, ge=0.0, le=1.0)


class CollectionScope(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=500)
    max_pages_per_domain: int = Field(default=25, ge=1, le=100)
    respect_robots_txt: bool = True
    delay_between_requests_ms: int = Field(default=500, ge=0, le=60000)


class SourceDef(BaseModel):
    type: Literal["url_list", "url_pattern", "search", "sitemap"]
    urls: list[str] | None = Field(None, min_length=1, max_length=500)
    url_template: str | None = Field(None, max_length=2048)
    url_params: dict[str, list[str | int | float]] | None = None
    search_query: str | None = Field(None, max_length=500)
    search_provider: Literal["duckduckgo", "bing", "serpapi", "default"] = "default"
    max_results: int = Field(default=10, ge=1, le=50)
    sitemap_url: str | None = Field(None, max_length=2048)
    sitemap_filter: str | None = Field(None, max_length=500)
    collector: CollectorSpec | None = None
    category_hint: str | None = Field(None, max_length=64)
    language_hint: str | None = Field(None, max_length=16)
    extract_options: ExtractOptions | None = None

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str] | None) -> list[str] | None:
        if v:
            for url in v:
                if not url.startswith(("http://", "https://")):
                    raise ValueError(f"URL must start with http:// or https://: {url[:100]}")
        return v

    @model_validator(mode="after")
    def validate_source_type_requirements(self) -> SourceDef:
        """Validate that required fields are present based on type."""
        if self.type == "url_list" and not self.urls:
            raise ValueError("type='url_list' requires 'urls' field")
        if self.type == "url_pattern":
            if not self.url_template:
                raise ValueError("type='url_pattern' requires 'url_template'")
            if not self.url_params:
                raise ValueError("type='url_pattern' requires 'url_params'")
        if self.type == "search" and not self.search_query:
            raise ValueError("type='search' requires 'search_query'")
        if self.type == "sitemap" and not self.sitemap_url:
            raise ValueError("type='sitemap' requires 'sitemap_url'")
        return self


class RunPlanSchema(BaseModel):
    """Top-level declarative RunPlan document."""

    version: Literal["1.0"]
    name: str | None = Field(None, max_length=255)
    sources: list[SourceDef] = Field(..., min_length=1, max_length=100)
    collector: CollectorSpec | None = None
    scope: CollectionScope | None = None

    @field_validator("sources")
    @classmethod
    def validate_no_dangerous_keys(cls, v: list[SourceDef]) -> list[SourceDef]:
        """Security rule S002: scan for dangerous keys/patterns."""
        for source in v:
            _check_dangerous_patterns(source.model_dump())
        return v


def _check_dangerous_patterns(obj: Any, path: str = "") -> None:
    """Recursively check for dangerous keys and string patterns.

    Raises ValueError if any dangerous pattern is found.
    """
    dangerous_keys = {"script", "code", "eval", "exec", "fn", "function", "command", "executable"}

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in dangerous_keys:
                raise ValueError(
                    f"Security violation S002: dangerous key '{key}' found at {path}",
                )
            if isinstance(key, str) and _DANGEROUS_PATTERNS.search(key):
                raise ValueError(
                    f"Security violation S003: dangerous pattern in key '{key}' at {path}",
                )
            _check_dangerous_patterns(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_dangerous_patterns(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        if _DANGEROUS_PATTERNS.search(obj):
            raise ValueError(
                f"Security violation S003: dangerous pattern found at {path}: '{obj[:100]}'",
            )


def validate_run_plan(data: dict) -> RunPlanSchema:
    """Validate a RunPlan dict and return the parsed model.

    Raises ValueError if validation fails.
    """
    # Security check on raw data BEFORE Pydantic parsing (extra fields are dropped)
    _check_dangerous_patterns(data, "$")
    return RunPlanSchema.model_validate(data)
