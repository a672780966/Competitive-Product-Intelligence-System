"""CollectorRuntimeRegistry — maps collector kind strings to executor wrappers.

This registry is the safe, declarative entry point for the collector runtime.
Each "collector kind" (direct_http, playwright, etc.) maps to a callable
that returns a CollectResult-compatible dict.

No dynamic code execution. No eval. No exec.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.collectors.failure_intelligence import FailureAnalysis
from app.core import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Data types ───────────────────────────────────────────────────


@dataclass
class CollectResult:
    """Normalised result from any collector in the runtime registry."""

    success: bool
    final_url: str = ""
    http_status: int = 0
    page_title: str = ""
    raw_html: bytes = b""
    response_headers: dict[str, str] = field(default_factory=dict)
    content_hash: str = ""
    error_code: str | None = None
    error_message: str = ""
    fetch_time_ms: int = 0
    collector_kind: str = "direct_http"
    failure_intelligence: Optional[FailureAnalysis] = None


@dataclass
class CollectorMetadata:
    """Static metadata describing a collector kind."""

    kind: str
    display_name: str
    description: str
    enabled: bool
    has_dependencies: bool
    missing_dependencies: list[str] = field(default_factory=list)
    default_retry_count: int = 1
    supported_source_types: list[str] = field(default_factory=list)
    supported_risk_levels: list[str] = field(default_factory=list)
    disabled_reason: str | None = None


# ── Feature flag mapping ─────────────────────────────────────────

_FEATURE_FLAG_MAP: dict[str, str | None] = {
    "direct_http": None,
    "playwright": "COLLECTOR_PLAYWRIGHT_ENABLED",
    "blocked": None,
    "scrapling": "COLLECTOR_SCRAPLING_ENABLED",
    "crawl4ai": "COLLECTOR_CRAWL4AI_ENABLED",
    "rss": "COLLECTOR_RSS_ENABLED",
    "pdf": "COLLECTOR_PDF_ENABLED",
    "api": "COLLECTOR_API_ENABLED",
}

_ALL_SOURCE_TYPES = [
    "official_homepage", "product_detail", "documentation",
    "news", "review", "forum", "social", "other",
]
_ALL_RISK_LEVELS = ["low", "medium", "high"]


# ── Abstract Provider ────────────────────────────────────────────


class BaseCollectorProvider(ABC):
    """Interface for a named collector in the registry."""

    kind: str

    @abstractmethod
    async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
        """Fetch a URL and return a normalised CollectResult."""
        ...


# ── Registry ─────────────────────────────────────────────────────


class CollectorRuntimeRegistry:
    """Maps collector kind strings to executor providers.

    The registry is the single entry point for executing collectors
    in the RunPlan / Collection Runner context.
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseCollectorProvider] = {}
        self._feature_gated: dict[str, type[BaseCollectorProvider]] = {}
        self._metadata: dict[str, CollectorMetadata] = {}

        # Register built-in providers
        self._register_builtins()

    # ── Metadata definitions ─────────────────────────────────────

    def _build_metadata_definitions(self) -> dict[str, dict]:
        """Return static metadata definitions for all known collector kinds."""
        return {
            "direct_http": {
                "kind": "direct_http",
                "display_name": "Direct HTTP",
                "description": "Static HTTP fetcher using httpx",
                "enabled": True,
                "has_dependencies": False,
                "default_retry_count": 3,
                "supported_source_types": _ALL_SOURCE_TYPES,
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "playwright": {
                "kind": "playwright",
                "display_name": "Playwright",
                "description": "JS-rendered page fetcher using Playwright",
                "enabled": False,
                "has_dependencies": True,
                "missing_dependencies": self._check_playwright_deps(),
                "default_retry_count": 1,
                "supported_source_types": _ALL_SOURCE_TYPES,
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "blocked": {
                "kind": "blocked",
                "display_name": "Blocked",
                "description": "No collector — source is blocked",
                "enabled": True,
                "has_dependencies": False,
                "default_retry_count": 0,
                "supported_source_types": [],
                "supported_risk_levels": ["blocked"],
            },
            "scrapling": {
                "kind": "scrapling",
                "display_name": "Scrapling",
                "description": "Scrapling-powered smart collector (feature-gated)",
                "enabled": False,
                "has_dependencies": True,
                "missing_dependencies": ["scrapling"],
                "default_retry_count": 2,
                "supported_source_types": _ALL_SOURCE_TYPES,
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "crawl4ai": {
                "kind": "crawl4ai",
                "display_name": "Crawl4AI",
                "description": "Crawl4AI-powered deep collector (feature-gated)",
                "enabled": False,
                "has_dependencies": True,
                "missing_dependencies": ["crawl4ai"],
                "default_retry_count": 1,
                "supported_source_types": _ALL_SOURCE_TYPES,
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "rss": {
                "kind": "rss",
                "display_name": "RSS Feed",
                "description": "RSS feed collector (feature-gated)",
                "enabled": False,
                "has_dependencies": False,
                "default_retry_count": 3,
                "supported_source_types": ["news", "other"],
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "pdf": {
                "kind": "pdf",
                "display_name": "PDF Downloader",
                "description": "PDF document collector (feature-gated)",
                "enabled": False,
                "has_dependencies": False,
                "default_retry_count": 2,
                "supported_source_types": ["documentation", "other"],
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
            "api": {
                "kind": "api",
                "display_name": "API Fetcher",
                "description": "API-based data collector (feature-gated)",
                "enabled": False,
                "has_dependencies": False,
                "default_retry_count": 3,
                "supported_source_types": ["other"],
                "supported_risk_levels": _ALL_RISK_LEVELS,
            },
        }

    @staticmethod
    def _check_playwright_deps() -> list[str]:
        """Check if playwright package is available."""
        try:
            import playwright  # noqa: F401
            return []
        except ImportError:
            return ["playwright"]

    def _register_builtins(self) -> None:
        """Register always-available built-in providers and populate metadata."""
        from app.collectors.direct_http import DirectHttpCollector

        self._register("direct_http", DirectHttpCollector())

        # Playwright wrapper — deferred import to allow graceful degradation
        from app.collectors.playwright_runtime import PlaywrightRuntimeCollector

        self._register("playwright", PlaywrightRuntimeCollector())

        # Populate metadata for all known kinds
        definitions = self._build_metadata_definitions()
        for kind, meta in definitions.items():
            self._metadata[kind] = CollectorMetadata(**meta)

        # Register feature-gated placeholder providers so they appear in
        # get_supported_kinds() and can be resolved via get_provider().
        _PLACEHOLDER_CLASSES: dict[str, type[BaseCollectorProvider]] = {}
        try:
            from app.collectors.scrapling_runtime import ScraplingRuntimeCollector
            _PLACEHOLDER_CLASSES["scrapling"] = ScraplingRuntimeCollector
        except ImportError:
            pass
        try:
            from app.collectors.crawl4ai_runtime import Crawl4AIRuntimeCollector
            _PLACEHOLDER_CLASSES["crawl4ai"] = Crawl4AIRuntimeCollector
        except ImportError:
            pass
        try:
            from app.collectors.rss_runtime import RssRuntimeCollector
            _PLACEHOLDER_CLASSES["rss"] = RssRuntimeCollector
        except ImportError:
            pass
        try:
            from app.collectors.pdf_runtime import PdfRuntimeCollector
            _PLACEHOLDER_CLASSES["pdf"] = PdfRuntimeCollector
        except ImportError:
            pass
        try:
            from app.collectors.api_runtime import ApiRuntimeCollector
            _PLACEHOLDER_CLASSES["api"] = ApiRuntimeCollector
        except ImportError:
            pass
        for kind, cls in _PLACEHOLDER_CLASSES.items():
            self.register_feature_gated(kind, cls)

    def _register(self, kind: str, provider: BaseCollectorProvider) -> None:
        self._providers[kind] = provider

    def register_feature_gated(
        self, kind: str, provider_cls: type[BaseCollectorProvider],
    ) -> None:
        """Register a feature-gated provider class (e.g. scrapling, crawl4ai)."""
        self._feature_gated[kind] = provider_cls

    def get_provider(self, kind: str) -> BaseCollectorProvider | None:
        """Get a provider by kind string. Returns None if not registered."""
        if kind in self._providers:
            return self._providers[kind]

        # Try feature-gated
        if kind in self._feature_gated:
            provider = self._feature_gated[kind]()
            self._providers[kind] = provider
            return provider

        return None

    def get_supported_kinds(self) -> list[str]:
        """Return list of all registered collector kind strings.

        Includes providers, feature-gated classes, and metadata-only entries
        (placeholder collectors that are registered as metadata but not as
        executable providers).
        """
        kinds = list(self._providers.keys())
        kinds.extend(self._feature_gated.keys())
        # Also include metadata-only kinds (placeholder collectors)
        for kind in self._metadata:
            if kind not in kinds:
                kinds.append(kind)
        return kinds

    # ── Metadata & feature flag helpers ──────────────────────────

    def _get_metadata(self) -> dict[str, CollectorMetadata]:
        """Return metadata for all registered kinds."""
        return dict(self._metadata)

    def is_enabled(self, kind: str) -> bool:
        """Check whether a collector kind is currently enabled at runtime.

        Checks:
        1. Is the kind registered (has metadata)?
        2. Is the feature flag enabled in Settings?
        3. Does it have dependencies satisfied?
        """
        meta = self._metadata.get(kind)
        if meta is None:
            return False

        # Check feature flag
        flag_name = _FEATURE_FLAG_MAP.get(kind)
        if flag_name is not None:
            settings = get_settings()
            if not getattr(settings, flag_name, False):
                return False

        # Check dependencies
        if meta.has_dependencies and meta.missing_dependencies:
            return False

        return True

    def get_metadata(self, kind: str) -> CollectorMetadata | None:
        """Return dynamic metadata for a collector kind, with runtime state."""
        meta = self._metadata.get(kind)
        if meta is None:
            return None

        enabled = self.is_enabled(kind)
        disabled_reason: str | None = None

        if not enabled:
            flag_name = _FEATURE_FLAG_MAP.get(kind)
            if flag_name is not None:
                settings = get_settings()
                if not getattr(settings, flag_name, False):
                    disabled_reason = f"Feature flag {flag_name} is disabled"
            if disabled_reason is None and meta.has_dependencies and meta.missing_dependencies:
                disabled_reason = f"Missing dependencies: {', '.join(meta.missing_dependencies)}"
            if disabled_reason is None:
                disabled_reason = "Collector is not available"

        return CollectorMetadata(
            kind=meta.kind,
            display_name=meta.display_name,
            description=meta.description,
            enabled=enabled,
            has_dependencies=meta.has_dependencies,
            missing_dependencies=list(meta.missing_dependencies),
            default_retry_count=meta.default_retry_count,
            supported_source_types=list(meta.supported_source_types),
            supported_risk_levels=list(meta.supported_risk_levels),
            disabled_reason=disabled_reason,
        )

    async def execute(
        self,
        kind: str,
        url: str,
        **kwargs: Any,
    ) -> CollectResult:
        """Execute a collector by kind string.

        Args:
            kind: Collector kind (direct_http, playwright, etc.)
            url: URL to fetch
            **kwargs: Additional parameters passed to the collector

        Returns:
            CollectResult

        Raises:
            ValueError: If the collector kind is not registered
        """
        provider = self.get_provider(kind)
        if provider is None:
            raise ValueError(
                f"Unknown collector kind: '{kind}'. "
                f"Supported kinds: {self.get_supported_kinds()}",
            )
        return await provider.fetch(url, **kwargs)


# Singleton
_registry: CollectorRuntimeRegistry | None = None


def get_collector_registry() -> CollectorRuntimeRegistry:
    """Return the singleton CollectorRuntimeRegistry instance."""
    global _registry
    if _registry is None:
        _registry = CollectorRuntimeRegistry()
    return _registry
