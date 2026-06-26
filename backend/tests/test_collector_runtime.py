"""Tests for Node 5 — Built-in Collector Runtime MVP.

Tests the CollectorRuntimeRegistry, DirectHttpCollector,
PlaywrightRuntimeCollector, and RunPlanExecutor.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.collectors.registry import (
    BaseCollectorProvider,
    CollectResult,
    CollectorRuntimeRegistry,
    get_collector_registry,
)
from app.core.database import get_db
from app.main import app
from app.models import Base
from app.models.enums import TaskPriority

client = TestClient(app)


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a fresh SQLite in-memory database."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        poolclass=NullPool,
    )
    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)

    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Override the get_db dependency to use our test database."""

    async def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


# ══════════════════════════════════════════════════════════════════
# CollectorRuntimeRegistry Tests
# ══════════════════════════════════════════════════════════════════


class TestCollectorRuntimeRegistry:
    """Tests for CollectorRuntimeRegistry."""

    def setup_method(self):
        self.registry = CollectorRuntimeRegistry()

    def test_registry_has_builtin_providers(self):
        """Should have direct_http and playwright registered."""
        kinds = self.registry.get_supported_kinds()
        assert "direct_http" in kinds
        assert "playwright" in kinds

    def test_get_provider_direct_http(self):
        """Should return a DirectHttpCollector instance."""
        provider = self.registry.get_provider("direct_http")
        assert provider is not None
        assert provider.kind == "direct_http"

    def test_get_provider_playwright(self):
        """Should return a PlaywrightRuntimeCollector instance."""
        provider = self.registry.get_provider("playwright")
        assert provider is not None
        assert provider.kind == "playwright"

    def test_get_provider_unknown(self):
        """Should return None for unknown collector kind."""
        provider = self.registry.get_provider("nonexistent")
        assert provider is None

    def test_get_supported_kinds(self):
        """Should list all registered kinds."""
        kinds = self.registry.get_supported_kinds()
        assert len(kinds) >= 2

    def test_register_feature_gated(self):
        """Should allow registering feature-gated providers."""
        class MockProvider(BaseCollectorProvider):
            kind = "mock_gated"

            async def fetch(self, url, **kwargs):
                return CollectResult(success=True)

        self.registry.register_feature_gated("mock_gated", MockProvider)
        assert "mock_gated" in self.registry.get_supported_kinds()

        provider = self.registry.get_provider("mock_gated")
        assert provider is not None
        assert provider.kind == "mock_gated"

    @pytest.mark.asyncio
    async def test_execute_unknown_kind_raises(self):
        """Should raise ValueError for unknown kind."""
        with pytest.raises(ValueError, match="Unknown collector kind"):
            await self.registry.execute("nonexistent", "https://example.com")

    @pytest.mark.asyncio
    async def test_execute_direct_http_success(self):
        """Should successfully execute a direct_http fetch."""
        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b"<html><title>Test</title><body>Hello</body></html>"
            mock_response.url = "https://example.com"
            mock_response.headers = {"content-type": "text/html"}

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await self.registry.execute(
                "direct_http", "https://example.com", timeout=10,
            )
            assert result.success
            assert result.final_url == "https://example.com"
            assert result.http_status == 200
            assert b"Hello" in result.raw_html
            assert result.collector_kind == "direct_http"

    @pytest.mark.asyncio
    async def test_execute_direct_http_timeout(self):
        """Should handle timeout gracefully."""
        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            from httpx import TimeoutException
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.side_effect = TimeoutException("timed out")
            mock_client.return_value = mock_instance

            result = await self.registry.execute(
                "direct_http", "https://example.com", timeout=5,
            )
            assert not result.success
            assert result.error_code == "FETCH_TIMEOUT"

    @pytest.mark.asyncio
    async def test_execute_direct_http_http_error(self):
        """Should handle HTTP errors gracefully."""
        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.url = "https://example.com/notfound"
            mock_response.headers = {}

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await self.registry.execute(
                "direct_http", "https://example.com/notfound",
            )
            assert not result.success
            assert result.http_status == 404

    @pytest.mark.asyncio
    async def test_execute_playwright_fallback_when_not_available(self):
        """Should fallback to direct_http when playwright is not installed."""
        with patch(
            "app.collectors.playwright_runtime.PlaywrightRuntimeCollector._check_playwright",
            return_value=False,
        ), patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b"<html><title>Playwright fallback</title></html>"
            mock_response.url = "https://example.com"
            mock_response.headers = {}

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await self.registry.execute(
                "playwright", "https://example.com",
            )
            assert result.success

    def test_registry_singleton(self):
        """get_collector_registry should return the same instance."""
        reg1 = get_collector_registry()
        reg2 = get_collector_registry()
        assert reg1 is reg2

    def test_collect_result_defaults(self):
        """CollectResult should have sensible defaults."""
        result = CollectResult(success=True)
        assert result.success
        assert result.final_url == ""
        assert result.http_status == 0
        assert result.raw_html == b""
        assert result.fetch_time_ms == 0
        assert result.collector_kind == "direct_http"


# ══════════════════════════════════════════════════════════════════
# DirectHttpCollector Tests
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestDirectHttpCollector:
    """Tests for DirectHttpCollector."""

    async def test_fetch_success(self):
        """Should fetch a URL and return HTML."""
        from app.collectors.direct_http import DirectHttpCollector

        collector = DirectHttpCollector()
        assert collector.kind == "direct_http"

        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b"<html><title>Direct Test</title><body>Content</body></html>"
            mock_response.url = "https://test.com/page"
            mock_response.headers = {"content-type": "text/html"}

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await collector.fetch("https://test.com/page", timeout=10)
            assert result.success
            assert result.page_title == "Direct Test"
            assert result.content_hash
            assert result.collector_kind == "direct_http"

    async def test_fetch_empty_content(self):
        """Should handle empty content."""
        from app.collectors.direct_http import DirectHttpCollector

        collector = DirectHttpCollector()

        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.content = b""
            mock_response.url = "https://test.com/empty"
            mock_response.headers = {}

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.return_value = mock_response
            mock_client.return_value = mock_instance

            result = await collector.fetch("https://test.com/empty")
            assert result.success
            assert result.raw_html == b""

    async def test_fetch_dns_failure(self):
        """Should handle DNS failures."""
        from app.collectors.direct_http import DirectHttpCollector
        from httpx import ConnectError

        collector = DirectHttpCollector()

        with patch("app.collectors.direct_http.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get.side_effect = ConnectError(
                "[Errno -2] Name or service not known",
            )
            mock_client.return_value = mock_instance

            result = await collector.fetch("https://nonexistent.example.com")
            assert not result.success
            assert result.error_code == "DNS_FAILURE"


# ══════════════════════════════════════════════════════════════════
# RunPlanExecutor Tests
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestRunPlanExecutor:
    """Tests for RunPlanExecutor."""

    async def test_execute_simple_plan(self, db_session: AsyncSession):
        """Should execute a simple url_list plan and create tasks."""
        from app.services.collection_runner_service import RunPlanExecutor

        plan = {
            "version": "1.0",
            "name": "Test Plan",
            "sources": [
                {
                    "type": "url_list",
                    "urls": [
                        "https://example.com/product1",
                        "https://example.com/product2",
                    ],
                    "category_hint": "smartphone",
                },
            ],
        }

        executor = RunPlanExecutor(db_session)

        with patch.object(executor._task_service, "_run_validation", new_callable=AsyncMock):
            tasks = await executor.execute_plan(
                plan,
                created_by="test_user",
            )
            assert len(tasks) == 2
            assert tasks[0].source_url == "https://example.com/product1"
            assert tasks[1].source_url == "https://example.com/product2"

    async def test_execute_plan_with_url_pattern(self, db_session: AsyncSession):
        """Should resolve URL patterns into multiple tasks."""
        from app.services.collection_runner_service import RunPlanExecutor

        plan = {
            "version": "1.0",
            "name": "Paginated Plan",
            "sources": [
                {
                    "type": "url_pattern",
                    "url_template": "https://example.com/products?page={page}",
                    "url_params": {
                        "page": [1, 2, 3],
                    },
                    "category_hint": "electronics",
                },
            ],
        }

        executor = RunPlanExecutor(db_session)

        with patch.object(executor._task_service, "_run_validation", new_callable=AsyncMock):
            tasks = await executor.execute_plan(
                plan,
                created_by="test_user",
            )
            assert len(tasks) == 3

    async def test_execute_plan_with_collector_override(self, db_session: AsyncSession):
        """Should respect collector override per source."""
        from app.services.collection_runner_service import RunPlanExecutor

        plan = {
            "version": "1.0",
            "name": "Collector Override",
            "collector": {"kind": "direct_http", "params": {"timeout": 30}},
            "sources": [
                {
                    "type": "url_list",
                    "urls": ["https://example.com"],
                    "collector": {"kind": "playwright", "params": {"timeout": 45}},
                },
            ],
        }

        executor = RunPlanExecutor(db_session)

        with patch.object(executor._task_service, "_run_validation", new_callable=AsyncMock):
            tasks = await executor.execute_plan(plan)
            assert len(tasks) == 1

    async def test_execute_plan_invalid_schema(self, db_session: AsyncSession):
        """Should reject plans with invalid schema."""
        from app.services.collection_runner_service import RunPlanExecutor

        executor = RunPlanExecutor(db_session)

        with pytest.raises(Exception):
            await executor.execute_plan({"version": "invalid"})

    async def test_execute_empty_plan(self, db_session: AsyncSession):
        """Should handle plans with search/sitemap sources gracefully."""
        from app.services.collection_runner_service import RunPlanExecutor

        plan = {
            "version": "1.0",
            "name": "Search Only",
            "sources": [
                {
                    "type": "search",
                    "search_query": "test query",
                    "max_results": 5,
                },
            ],
        }

        executor = RunPlanExecutor(db_session)

        tasks = await executor.execute_plan(plan)
        assert len(tasks) == 0  # Search not supported in MVP


# ══════════════════════════════════════════════════════════════════
# PlaywrightRuntimeCollector Tests
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestPlaywrightRuntimeCollector:
    """Tests for PlaywrightRuntimeCollector."""

    async def test_fallback_when_playwright_not_installed(self):
        """Should fallback cleanly when playwright is not installed."""
        from app.collectors.playwright_runtime import PlaywrightRuntimeCollector

        collector = PlaywrightRuntimeCollector()

        with patch.object(collector, "_check_playwright", return_value=False), \
             patch.object(collector._fallback, "fetch", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = CollectResult(success=True, collector_kind="direct_http")

            result = await collector.fetch("https://example.com")
            assert result.success
            assert result.collector_kind == "direct_http"

    async def test_delegates_to_real_collector_when_available(self):
        """Should use real PlaywrightCollector when available."""
        from app.collectors.playwright_runtime import PlaywrightRuntimeCollector

        collector = PlaywrightRuntimeCollector()

        with patch.object(collector, "_check_playwright", return_value=True), \
             patch.object(collector, "_do_playwright_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = CollectResult(
                success=True,
                raw_html=b"<html>Playwright content</html>",
                collector_kind="playwright",
            )

            result = await collector.fetch("https://example.com")
            assert result.success
            assert result.collector_kind == "playwright"

    async def test_fallback_on_playwright_error(self):
        """Should fallback when playwright fetch raises exception."""
        from app.collectors.playwright_runtime import PlaywrightRuntimeCollector

        collector = PlaywrightRuntimeCollector()

        with patch.object(collector, "_check_playwright", return_value=True), \
             patch.object(collector, "_do_playwright_fetch", side_effect=Exception("Playwright error")), \
             patch.object(collector._fallback, "fetch", new_callable=AsyncMock) as mock_fallback:
            mock_fallback.return_value = CollectResult(success=True, collector_kind="direct_http")

            result = await collector.fetch("https://example.com")
            assert result.success


# ══════════════════════════════════════════════════════════════════
# RunPlan URL Resolution Tests
# ══════════════════════════════════════════════════════════════════


class TestRunPlanUrlResolution:
    """Tests for URL resolution logic in RunPlanExecutor."""

    def test_resolve_url_pattern(self):
        """Should resolve URL templates with multiple parameters."""
        from app.services.collection_runner_service import RunPlanExecutor

        urls = RunPlanExecutor._resolve_url_pattern(
            "https://example.com/products?page={page}&size={size}",
            {"page": [1, 2], "size": [10, 20]},
        )
        assert len(urls) == 4
        assert "https://example.com/products?page=1&size=10" in urls
        assert "https://example.com/products?page=2&size=20" in urls

    def test_resolve_url_pattern_single_param(self):
        """Should resolve with a single parameter."""
        from app.services.collection_runner_service import RunPlanExecutor

        urls = RunPlanExecutor._resolve_url_pattern(
            "https://example.com/page/{id}",
            {"id": [1, 2, 3]},
        )
        assert len(urls) == 3
        assert "https://example.com/page/1" in urls
        assert "https://example.com/page/3" in urls

    def test_resolve_url_pattern_rejects_dollar_braces(self):
        """Should reject ${} syntax (security rule S005)."""
        from app.services.collection_runner_service import RunPlanExecutor

        with pytest.raises(ValueError, match="Security violation S005"):
            RunPlanExecutor._resolve_url_pattern(
                "https://example.com/${path}",
                {"path": ["test"]},
            )

    def test_resolve_url_pattern_missing_param(self):
        """Should reject if template param is missing from url_params."""
        from app.services.collection_runner_service import RunPlanExecutor

        with pytest.raises(ValueError, match="not found in url_params"):
            RunPlanExecutor._resolve_url_pattern(
                "https://example.com/{page}/{missing}",
                {"page": [1]},
            )


# ══════════════════════════════════════════════════════════════════
# RunPlan Schema Validation Tests
# ══════════════════════════════════════════════════════════════════


class TestRunPlanValidation:
    """Tests for RunPlan schema validation (from run_plan.py)."""

    def test_valid_run_plan(self):
        """Should validate a correct RunPlan."""
        from app.schemas.run_plan import validate_run_plan

        plan = {
            "version": "1.0",
            "name": "Test",
            "sources": [
                {
                    "type": "url_list",
                    "urls": ["https://example.com"],
                },
            ],
        }
        result = validate_run_plan(plan)
        assert result.version == "1.0"
        assert result.name == "Test"

    def test_invalid_version(self):
        """Should reject plans with invalid version."""
        from app.schemas.run_plan import validate_run_plan

        with pytest.raises(Exception):
            validate_run_plan({
                "version": "2.0",
                "sources": [{"type": "url_list", "urls": ["https://example.com"]}],
            })

    def test_empty_sources(self):
        """Should reject plans with no sources."""
        from app.schemas.run_plan import validate_run_plan

        with pytest.raises(Exception):
            validate_run_plan({
                "version": "1.0",
                "sources": [],
            })

    def test_url_list_missing_urls(self):
        """Should reject url_list without urls field."""
        from app.schemas.run_plan import validate_run_plan

        with pytest.raises(Exception):
            validate_run_plan({
                "version": "1.0",
                "sources": [{"type": "url_list"}],
            })

    def test_invalid_url_scheme(self):
        """Should reject non-http/https URLs."""
        from app.schemas.run_plan import SourceDef

        with pytest.raises(ValueError, match="must start with http"):
            SourceDef.model_validate({
                "type": "url_list",
                "urls": ["ftp://example.com"],
            })

    def test_url_pattern_requires_template(self):
        """Should reject url_pattern without template."""
        from app.schemas.run_plan import SourceDef

        with pytest.raises(ValueError, match="requires 'url_template'"):
            SourceDef.model_validate({
                "type": "url_pattern",
                "url_params": {"page": [1]},
            })

    def test_search_requires_query(self):
        """Should reject search without query."""
        from app.schemas.run_plan import SourceDef

        with pytest.raises(ValueError, match="requires 'search_query'"):
            SourceDef.model_validate({
                "type": "search",
            })

    def test_security_no_dangerous_keys(self):
        """Should reject plans with dangerous keys."""
        from app.schemas.run_plan import validate_run_plan

        with pytest.raises(ValueError, match="Security violation"):
            validate_run_plan({
                "version": "1.0",
                "sources": [{
                    "type": "url_list",
                    "urls": ["https://example.com"],
                    "script": "alert('xss')",
                }],
            })

    def test_security_no_dangerous_patterns(self):
        """Should reject plans with dangerous string patterns."""
        from app.schemas.run_plan import validate_run_plan

        with pytest.raises(ValueError, match="Security violation"):
            validate_run_plan({
                "version": "1.0",
                "sources": [{
                    "type": "url_list",
                    "urls": ["https://example.com/exec?cmd=ls"],
                }],
            })

    def test_collector_params_timeout_range(self):
        """Should enforce timeout min/max."""
        from app.schemas.run_plan import CollectorParams

        with pytest.raises(Exception):
            CollectorParams(timeout=200)  # > 120

        with pytest.raises(Exception):
            CollectorParams(timeout=2)  # < 5

        # Valid
        params = CollectorParams(timeout=30)
        assert params.timeout == 30

    def test_collector_spec_valid_kinds(self):
        """Should accept valid collector kinds."""
        from app.schemas.run_plan import CollectorSpec

        for kind in ["direct_http", "playwright", "scrapling", "crawl4ai"]:
            spec = CollectorSpec(kind=kind)  # type: ignore[arg-type]
            assert spec.kind == kind

    def test_scope_defaults(self):
        """CollectionScope should have sensible defaults."""
        from app.schemas.run_plan import CollectionScope

        scope = CollectionScope()
        assert scope.max_pages == 50
        assert scope.max_pages_per_domain == 25
        assert scope.respect_robots_txt is True
        assert scope.delay_between_requests_ms == 500


# ══════════════════════════════════════════════════════════════════
# Integration: API endpoint implicit loading
# ══════════════════════════════════════════════════════════════════


class TestRegistryEndpointPresence:
    """Verify the registry module loads without errors."""

    def test_registry_module_importable(self):
        """Should import registry module without errors."""
        from app.collectors import registry
        assert registry.CollectorRuntimeRegistry is not None
        assert registry.get_collector_registry is not None

    def test_direct_http_module_importable(self):
        """Should import direct_http module without errors."""
        from app.collectors import direct_http
        assert direct_http.DirectHttpCollector is not None
