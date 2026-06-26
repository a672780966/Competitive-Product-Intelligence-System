"""Mock implementations of ModelProvider and SearchProvider.

These return fixture data with NO network calls. Used for testing
and when no real API keys are configured.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from app.models.enums import RecommendedCollector, RiskLevel, SourceType
from app.models.source_candidate import SourceCandidate
from app.providers.interfaces import (
    AnalysisResult,
    ClassifiedResult,
    ExtractionResult,
    LLMProvider,
    ModelProvider,
    SearchProvider,
    SearchResult,
    assess_risk_level,
    recommend_collector,
)


#
# ── Fixture Data ─────────────────────────────────────────────────
#


FIXTURE_SEARCH_RESULTS: list[dict[str, Any]] = [
    {
        "title": "小米14 Ultra 官方介绍页",
        "url": "https://www.mi.com/xiaomi-14-ultra",
        "snippet": "小米14 Ultra 搭载骁龙8 Gen3 处理器，徕卡光学镜头",
        "source": "web",
    },
    {
        "title": "小米14 Ultra 产品参数 - 小米官网",
        "url": "https://www.mi.com/xiaomi-14-ultra/specs",
        "snippet": "详细规格参数：屏幕 6.73英寸 2K AMOLED，电池 5000mAh",
        "source": "web",
    },
    {
        "title": "小米14 Ultra 评测 - 知乎",
        "url": "https://www.zhihu.com/topic/xiaomi-14-ultra/review",
        "snippet": "知乎用户热议：小米14 Ultra 影像系统全面升级",
        "source": "web",
    },
    {
        "title": "小米14 Ultra 深度评测：徕卡加持的影像旗舰",
        "url": "https://www.ithome.com/review/xiaomi-14-ultra",
        "snippet": "IT之家详细评测了小米14 Ultra 的相机性能、续航和系统体验",
        "source": "web",
    },
    {
        "title": "小米14 Ultra 讨论区 - 百度贴吧",
        "url": "https://tieba.baidu.com/xiaomi-14-ultra",
        "snippet": "百度贴吧小米14 Ultra 讨论区，用户交流使用心得",
        "source": "web",
    },
    {
        "title": "Xiaomi 14 Ultra Official Product Page",
        "url": "https://www.mi.com/global/xiaomi-14-ultra",
        "snippet": "Xiaomi 14 Ultra with Leica optics, Snapdragon 8 Gen 3",
        "source": "web",
    },
    {
        "title": "小米14 Ultra 开发文档 - MIUI 开发平台",
        "url": "https://dev.mi.com/docs/xiaomi-14-ultra",
        "snippet": "小米14 Ultra 开发者文档，API 接口说明",
        "source": "web",
    },
    {
        "title": "小红书 - 小米14 Ultra 使用体验",
        "url": "https://www.xiaohongshu.com/search/xiaomi-14-ultra",
        "snippet": "小红书用户分享小米14 Ultra 使用体验和拍照样张",
        "source": "web",
    },
]


FIXTURE_ANALYSIS_RESULTS: list[dict[str, Any]] = [
    {
        "source_type": SourceType.OFFICIAL_HOMEPAGE,
        "relevance_score": 0.95,
        "reason": "Official Xiaomi product page for Xiaomi 14 Ultra",
        "suggested_title": "小米14 Ultra 官方产品页",
    },
    {
        "source_type": SourceType.PRODUCT_DETAIL,
        "relevance_score": 0.90,
        "reason": "Official specs page with detailed product parameters",
        "suggested_title": "小米14 Ultra 规格参数",
    },
    {
        "source_type": SourceType.REVIEW,
        "relevance_score": 0.75,
        "reason": "Zhihu discussion about Xiaomi 14 Ultra review",
        "suggested_title": "小米14 Ultra 知乎评测",
    },
    {
        "source_type": SourceType.REVIEW,
        "relevance_score": 0.80,
        "reason": "IT Home in-depth review of Xiaomi 14 Ultra",
        "suggested_title": "小米14 Ultra IT之家深度评测",
    },
    {
        "source_type": SourceType.FORUM,
        "relevance_score": 0.50,
        "reason": "Baidu Tieba discussion forum for Xiaomi 14 Ultra",
        "suggested_title": "小米14 Ultra 贴吧讨论",
    },
    {
        "source_type": SourceType.OFFICIAL_HOMEPAGE,
        "relevance_score": 0.85,
        "reason": "Global official product page for Xiaomi 14 Ultra",
        "suggested_title": "Xiaomi 14 Ultra Global Product Page",
    },
    {
        "source_type": SourceType.DOCUMENTATION,
        "relevance_score": 0.70,
        "reason": "MIUI developer documentation for Xiaomi 14 Ultra",
        "suggested_title": "小米14 Ultra 开发文档",
    },
    {
        "source_type": SourceType.SOCIAL,
        "relevance_score": 0.40,
        "reason": "Xiaohongshu social posts about Xiaomi 14 Ultra",
        "suggested_title": "小红书 小米14 Ultra 分享",
    },
]


#
# ── Mock SearchProvider ──────────────────────────────────────────
#


class MockSearchProvider(SearchProvider):
    """Mock search provider that returns fixture data.

    No network calls. Useful for testing discovery flows.
    """

    def __init__(self, fixture_results: list[dict[str, Any]] | None = None):
        self._fixtures = fixture_results or FIXTURE_SEARCH_RESULTS

    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        """Return fixture search results, truncated to max_results."""
        # Yield to event loop to maintain greenlet context for aiosqlite
        await asyncio.sleep(0)
        results = []
        for item in self._fixtures[:max_results]:
            results.append(SearchResult(
                title=item["title"],
                url=item["url"],
                snippet=item.get("snippet", ""),
                source=item.get("source", "web"),
            ))
        return results


#
# ── Mock ModelProvider ───────────────────────────────────────────
#


class MockModelProvider(ModelProvider):
    """Mock model provider that returns fixture analysis results.

    No network calls. Useful for testing discovery flows.
    """

    def __init__(self, fixture_results: list[dict[str, Any]] | None = None):
        self._fixtures = fixture_results or FIXTURE_ANALYSIS_RESULTS
        self._search_fixtures = FIXTURE_SEARCH_RESULTS

    async def analyze_source(
        self,
        search_result: SearchResult,
        *,
        brand: str | None = None,
        topic: str | None = None,
    ) -> AnalysisResult:
        """Analyze a single search result.

        In mock mode, we look up by URL or return a default.
        """
        # Yield to event loop to maintain greenlet context for aiosqlite
        await asyncio.sleep(0)
        # Try to match by URL
        for i, item in enumerate(self._search_fixtures):
            if item["url"] == search_result.url and i < len(self._fixtures):
                f = self._fixtures[i]
                return AnalysisResult(
                    source_type=f["source_type"],
                    relevance_score=f["relevance_score"],
                    reason=f["reason"],
                    suggested_title=f["suggested_title"],
                )

        # Fallback: return generic result
        return AnalysisResult(
            source_type=SourceType.OTHER,
            relevance_score=0.3,
            reason="Generic fallback analysis",
            suggested_title=search_result.title,
        )

    async def discover_sources(
        self,
        query: str,
        *,
        brand: str | None = None,
        topic: str | None = None,
        max_results: int = 10,
    ) -> list[AnalysisResult]:
        """Run mock discovery (search + analyze) and return results.

        This is a convenience that pairs fixture searches with their
        corresponding analysis results.
        """
        # Yield to event loop to maintain greenlet context for aiosqlite
        await asyncio.sleep(0)
        # For simplicity, just return the fixture analysis results
        return [
            AnalysisResult(
                source_type=f["source_type"],
                relevance_score=f["relevance_score"],
                reason=f["reason"],
                suggested_title=f["suggested_title"],
            )
            for f in self._fixtures[:max_results]
        ]


#
# ── Factory Functions ────────────────────────────────────────────
#


def create_mock_search_provider() -> MockSearchProvider:
    """Create a MockSearchProvider with default fixtures."""
    return MockSearchProvider()


def create_mock_model_provider() -> MockModelProvider:
    """Create a MockModelProvider with default fixtures."""
    return MockModelProvider()


#
# ── Stub LLMProvider ─────────────────────────────────────────────
#


class StubLLMProvider(LLMProvider):
    """Stub LLM provider — returns fixture data, no real LLM calls.

    Used for testing and when no real LLM API keys are configured.
    """

    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        """Stub classification — determines source type from URL patterns."""
        await asyncio.sleep(0)
        domain = _extract_domain(url)
        domain_lower = domain.lower()

        if any(hr in domain_lower for hr in ["mi.com", "xiaomi"]):
            return ClassifiedResult(
                source_type=SourceType.OFFICIAL_HOMEPAGE,
                relevance_score=0.95,
                reason=f"Official domain detected: {domain}",
                suggested_title=title,
                confidence=0.9,
            )
        if any(kw in domain_lower for kw in ["zhihu", "tieba", "xiaohongshu"]):
            return ClassifiedResult(
                source_type=SourceType.FORUM,
                relevance_score=0.40,
                reason=f"Social/forum domain detected: {domain}",
                suggested_title=title,
                confidence=0.7,
            )
        if any(kw in domain_lower for kw in ["review", "ithome", "news"]):
            return ClassifiedResult(
                source_type=SourceType.REVIEW,
                relevance_score=0.75,
                reason=f"Review/news domain detected: {domain}",
                suggested_title=title,
                confidence=0.8,
            )

        return ClassifiedResult(
            source_type=SourceType.OTHER,
            relevance_score=0.3,
            reason=f"Unknown domain: {domain}",
            suggested_title=title,
            confidence=0.5,
        )

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        """Stub extraction — returns empty result."""
        await asyncio.sleep(0)
        return ExtractionResult(
            fields={},
            raw_text=content[:200] if content else "",
            confidence=0.0,
            metadata={"note": "Stub extraction — replace with real LLM call"},
        )


def create_stub_llm_provider() -> StubLLMProvider:
    """Create a StubLLMProvider with default behavior."""
    return StubLLMProvider()


def create_mock_candidates(
    session_id: uuid.UUID,
    *,
    brand: str | None = None,
    topic: str | None = None,
    max_results: int = 10,
) -> list[SourceCandidate]:
    """Create SourceCandidate objects from fixture data for testing.

    This applies the risk assessment and collector recommendation
    logic to produce fully-populated candidates.
    """
    candidates: list[SourceCandidate] = []
    search_results = FIXTURE_SEARCH_RESULTS[:max_results]
    analysis_results = FIXTURE_ANALYSIS_RESULTS[:max_results]

    for i, (sr, ar) in enumerate(zip(search_results, analysis_results)):
        domain = _extract_domain(sr["url"])
        source_type = ar["source_type"]
        risk_level = assess_risk_level(source_type, domain)
        collector = recommend_collector(source_type, risk_level, domain)

        candidate = SourceCandidate(
            discovery_session_id=session_id,
            title=ar.get("suggested_title", sr["title"]),
            url=sr["url"],
            domain=domain,
            snippet=sr.get("snippet", ""),
            source_type=source_type,
            recommended_collector=collector,
            risk_level=risk_level,
            reason=ar.get("reason", ""),
            selected=False,
            sort_order=i,
            raw_metadata={
                "query": "",
                "brand": brand,
                "topic": topic,
                "relevance_score": ar.get("relevance_score", 0.5),
            },
        )
        candidates.append(candidate)

    return candidates


def _extract_domain(url: str) -> str:
    """Extract domain from a URL string."""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split("/")[0]
    except Exception:
        return url
