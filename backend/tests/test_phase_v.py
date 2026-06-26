"""Phase V tests — retry policy, execution reports, selector v2, registry metadata.

Tests for:
- RetryPolicy (per-kind retry config, overrides, fallback)
- CollectorExecutionReport (model creation, schema validation)
- CollectorSelectorV2 (select method, blocked source, feature flags)
- CollectorRegistryMetadata (is_enabled, get_metadata, placeholders)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.collectors.registry import (
    BaseCollectorProvider,
    CollectResult,
    CollectorMetadata,
    CollectorRuntimeRegistry,
    get_collector_registry,
)
from app.collectors.retry_policy import RetryPolicy
from app.collectors.selector import CollectorSelector, SelectResult
from app.models.collector_execution_report import CollectorExecutionReport
from app.schemas.collector_execution_report import CollectorExecutionReportResponse


# ══════════════════════════════════════════════════════════════════
# RetryPolicy Tests
# ══════════════════════════════════════════════════════════════════


class TestRetryPolicy:
    """Tests for RetryPolicy — per-collector-kind retry configuration."""

    def test_direct_http_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("direct_http") == 3

    def test_playwright_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("playwright") == 1

    def test_blocked_has_zero_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("blocked") == 0

    def test_unknown_kind_falls_back(self):
        policy = RetryPolicy()
        retries = policy.get_max_retries("nonexistent")
        assert retries >= 1

    def test_override_overrides_default(self):
        policy = RetryPolicy(overrides={"direct_http": 5})
        assert policy.get_max_retries("direct_http") == 5

    def test_override_only_affects_specified_kind(self):
        policy = RetryPolicy(overrides={"direct_http": 5})
        assert policy.get_max_retries("playwright") == 1

    def test_scrapling_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("scrapling") == 2

    def test_crawl4ai_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("crawl4ai") == 1

    def test_rss_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("rss") == 3

    def test_pdf_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("pdf") == 2

    def test_api_default_retries(self):
        policy = RetryPolicy()
        assert policy.get_max_retries("api") == 3


# ══════════════════════════════════════════════════════════════════
# CollectorExecutionReport Tests
# ══════════════════════════════════════════════════════════════════


class TestCollectorExecutionReport:
    """Tests for CollectorExecutionReport model and schema."""

    def test_model_creation_with_minimal_fields(self):
        report = CollectorExecutionReport(
            task_id=uuid.uuid4(),
            url="https://example.com",
            collector_runtime="direct_http",
            status="started",
        )
        assert report.status == "started"
        assert report.collector_runtime == "direct_http"
        # retry_count has server_default=0, is None until DB flush
        assert report.retry_count is None or report.retry_count == 0
        assert report.duration_ms is None
        assert report.content_size is None

    def test_model_creation_with_all_fields(self):
        task_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        report = CollectorExecutionReport(
            id=uuid.uuid4(),
            task_id=task_id,
            snapshot_id=snapshot_id,
            url="https://example.com/page",
            collector_runtime="playwright",
            status="success",
            started_at=now,
            finished_at=now,
            duration_ms=1234,
            content_size=56789,
            retry_count=1,
            error_message=None,
        )
        assert report.task_id == task_id
        assert report.snapshot_id == snapshot_id
        assert report.status == "success"
        assert report.duration_ms == 1234
        assert report.content_size == 56789
        assert report.retry_count == 1

    def test_model_default_retry_count_is_zero(self):
        report = CollectorExecutionReport(
            task_id=uuid.uuid4(),
            url="https://example.com",
            collector_runtime="direct_http",
            status="started",
        )
        assert report.retry_count is None or report.retry_count == 0

    def test_schema_response_from_model(self):
        now = datetime.now(timezone.utc)
        report = CollectorExecutionReport(
            id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            url="https://example.com",
            collector_runtime="direct_http",
            status="success",
            started_at=now,
            created_at=now,
            updated_at=now,
            duration_ms=500,
            content_size=1024,
            retry_count=0,
        )
        response = CollectorExecutionReportResponse.model_validate(report)
        assert response.collector_runtime == "direct_http"
        assert response.status == "success"
        assert response.duration_ms == 500
        assert response.content_size == 1024
        assert response.retry_count == 0
        assert response.error_message is None

    def test_schema_response_with_error(self):
        now = datetime.now(timezone.utc)
        report = CollectorExecutionReport(
            id=uuid.uuid4(),
            task_id=uuid.uuid4(),
            url="https://example.com",
            collector_runtime="direct_http",
            status="failed",
            started_at=now,
            created_at=now,
            updated_at=now,
            duration_ms=200,
            content_size=0,
            retry_count=3,
            error_message="Connection refused",
        )
        response = CollectorExecutionReportResponse.model_validate(report)
        assert response.status == "failed"
        assert response.error_message == "Connection refused"
        assert response.retry_count == 3


# ══════════════════════════════════════════════════════════════════
# CollectorSelector v2 Tests (registry-backed)
# ══════════════════════════════════════════════════════════════════


class TestCollectorSelectorV2:
    """Tests for the registry-backed CollectorSelector (Phase V)."""

    def test_select_returns_direct_http_by_default(self):
        selector = CollectorSelector()
        result = selector.select("https://example.com")
        assert result.collector_kind == "direct_http"
        assert result.runtime is not None

    def test_select_blocked_returns_blocked_kind(self):
        selector = CollectorSelector()
        result = selector.select("https://example.com", risk_level="blocked")
        assert result.collector_kind == "blocked"
        assert result.runtime is None

    def test_select_blocked_returns_reason(self):
        selector = CollectorSelector()
        result = selector.select("https://example.com", risk_level="blocked")
        assert "blocked" in result.reason.lower()

    def test_select_includes_runtime_when_enabled(self):
        selector = CollectorSelector()
        result = selector.select("https://example.com")
        assert result.collector_kind == "direct_http"
        assert result.runtime is not None
        assert hasattr(result.runtime, "fetch")

    @patch("app.collectors.registry.CollectorRuntimeRegistry.is_enabled")
    def test_select_returns_none_runtime_when_disabled(self, mock_is_enabled):
        mock_is_enabled.return_value = False
        registry = CollectorRuntimeRegistry()
        selector = CollectorSelector(registry=registry)
        result = selector.select("https://example.com")
        assert result.collector_kind == "direct_http"
        assert result.runtime is None

    @patch("app.collectors.registry.CollectorRuntimeRegistry.is_enabled")
    def test_select_fallback_to_feature_gated_collector(self, mock_is_enabled):
        def side_effect(kind):
            if kind == "direct_http":
                return False
            if kind == "scrapling":
                return True
            return False
        mock_is_enabled.side_effect = side_effect

        registry = CollectorRuntimeRegistry()
        selector = CollectorSelector(registry=registry)
        result = selector.select("https://example.com")
        assert result.collector_kind == "scrapling"


# ══════════════════════════════════════════════════════════════════
# CollectorRegistryMetadata Tests
# ══════════════════════════════════════════════════════════════════


class TestCollectorRegistryMetadata:
    """Tests for CollectorRuntimeRegistry metadata and feature flags."""

    def setup_method(self):
        self.registry = CollectorRuntimeRegistry()

    def test_is_enabled_direct_http_true(self):
        assert self.registry.is_enabled("direct_http") is True

    def test_is_enabled_blocked_true(self):
        assert self.registry.is_enabled("blocked") is True

    def test_is_enabled_unknown_kind_false(self):
        assert self.registry.is_enabled("nonexistent") is False

    def test_get_metadata_returns_metadata_for_known_kind(self):
        meta = self.registry.get_metadata("direct_http")
        assert meta is not None
        assert meta.kind == "direct_http"
        assert meta.display_name == "Direct HTTP"
        assert meta.enabled is True

    def test_get_metadata_returns_none_for_unknown(self):
        meta = self.registry.get_metadata("nonexistent")
        assert meta is None

    def test_get_metadata_playwright_disabled_by_default(self):
        meta = self.registry.get_metadata("playwright")
        assert meta is not None
        assert meta.enabled is False
        assert meta.disabled_reason is not None

    def test_placeholder_kinds_have_metadata(self):
        for kind in ("scrapling", "crawl4ai", "rss", "pdf", "api"):
            meta = self.registry.get_metadata(kind)
            assert meta is not None, f"No metadata for {kind}"
            assert meta.kind == kind

    def test_placeholder_kinds_disabled_by_default(self):
        for kind in ("scrapling", "crawl4ai", "rss", "pdf", "api"):
            meta = self.registry.get_metadata(kind)
            assert meta is not None
            assert meta.enabled is False

    def test_placeholder_kinds_have_display_names(self):
        expected = {
            "scrapling": "Scrapling",
            "crawl4ai": "Crawl4AI",
            "rss": "RSS Feed",
            "pdf": "PDF Downloader",
            "api": "API Fetcher",
        }
        for kind, name in expected.items():
            meta = self.registry.get_metadata(kind)
            assert meta is not None
            assert meta.display_name == name

    def test_get_metadata_disabled_reason_for_placeholder(self):
        for kind in ("scrapling", "crawl4ai", "rss", "pdf", "api"):
            meta = self.registry.get_metadata(kind)
            assert meta is not None
            assert meta.disabled_reason is not None

    def test_supported_kinds_includes_placeholders(self):
        kinds = self.registry.get_supported_kinds()
        for kind in ("direct_http", "playwright", "scrapling", "crawl4ai", "rss", "pdf", "api"):
            assert kind in kinds

    def test_registry_singleton(self):
        reg1 = get_collector_registry()
        reg2 = get_collector_registry()
        assert reg1 is reg2
