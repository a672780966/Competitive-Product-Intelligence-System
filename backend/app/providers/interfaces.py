"""Abstract base classes for ModelProvider and SearchProvider.

These interfaces define the contract for provider implementations.
No real network calls happen here — only abstract method signatures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.models.enums import RecommendedCollector, RiskLevel, SourceType
from app.models.source_candidate import SourceCandidate


#
# ── Risk Assessment ─────────────────────────────────────────────
#

# High-risk platforms that should be blocked
HIGH_RISK_DOMAINS: set[str] = {
    "weibo.com", "zhihu.com", "tieba.baidu.com",
    "douyin.com", "xiaohongshu.com", "bilibili.com",
}

# Forum/Social domains
SOCIAL_DOMAIN_KEYWORDS: set[str] = {
    "forum", "bbs", "community", "discuss", "reddit",
    "quora", "stackexchange",
}

# News/Review domains
REVIEW_DOMAIN_KEYWORDS: set[str] = {
    "review", "news", "blog", "medium", "techcrunch",
    "theverge", "cnet", "zdnet", "gizmodo",
}

# Source type desirability scores (higher = more valuable for discovery)
SOURCE_TYPE_SCORE: dict[str, float] = {
    "official_homepage": 1.0,
    "product_detail": 0.95,
    "documentation": 0.85,
    "review": 0.70,
    "news": 0.65,
    "forum": 0.40,
    "social": 0.20,
    "other": 0.10,
}


def assess_risk_level(source_type: SourceType, domain: str) -> RiskLevel:
    """Determine the risk level for a source candidate.

    Based on source_type classification and domain analysis:
    - Official homepage / Product detail / Documentation → LOW
    - News / Review → MEDIUM
    - Forum / Social → HIGH
    - High-risk platforms (weibo, zhihu, etc.) → BLOCKED
    """
    # Check high-risk domains first
    domain_lower = domain.lower().strip()
    for hr_domain in HIGH_RISK_DOMAINS:
        if hr_domain in domain_lower:
            return RiskLevel.BLOCKED

    # Check by source type
    if source_type in (SourceType.OFFICIAL_HOMEPAGE,
                       SourceType.PRODUCT_DETAIL,
                       SourceType.DOCUMENTATION):
        return RiskLevel.LOW

    if source_type in (SourceType.NEWS, SourceType.REVIEW):
        return RiskLevel.MEDIUM

    if source_type in (SourceType.FORUM, SourceType.SOCIAL):
        return RiskLevel.HIGH

    # Default
    return RiskLevel.LOW


def recommend_collector(source_type: SourceType,
                        risk_level: RiskLevel,
                        domain: str) -> RecommendedCollector:
    """Recommend a collector kind based on source type and risk level.

    - BLOCKED risk → disabled collector
    - HIGH risk → requires_confirmation
    - LOW risk official/doc pages → direct_http
    - NEWS/Review → direct_http (with playwright fallback)
    """
    if risk_level == RiskLevel.BLOCKED:
        return RecommendedCollector.REQUIRES_CONFIRMATION

    if risk_level == RiskLevel.HIGH:
        return RecommendedCollector.REQUIRES_CONFIRMATION

    if risk_level == RiskLevel.MEDIUM:
        return RecommendedCollector.DIRECT_HTTP

    # LOW risk
    if source_type == SourceType.OFFICIAL_HOMEPAGE:
        return RecommendedCollector.DIRECT_HTTP
    if source_type == SourceType.PRODUCT_DETAIL:
        return RecommendedCollector.DIRECT_HTTP
    if source_type == SourceType.DOCUMENTATION:
        return RecommendedCollector.DIRECT_HTTP

    # Fallback for other types
    domain_lower = domain.lower()
    if any(kw in domain_lower for kw in REVIEW_DOMAIN_KEYWORDS):
        return RecommendedCollector.DIRECT_HTTP

    return RecommendedCollector.DIRECT_HTTP


def rank_candidates(
    candidates: list[Any],
    *,
    source_type_attr: str = "source_type",
    score_attr: str | None = None,
    boost_brand: str | None = None,
    boost_topic: str | None = None,
) -> list[Any]:
    """Rank source candidates by desirability score (highest first).

    Uses SOURCE_TYPE_SCORE as the primary sort key. Optionally
    boosts candidates whose metadata matches brand/topic.

    Args:
        candidates: List of objects with source_type attribute.
        source_type_attr: Attribute name for source type on each candidate.
        score_attr: Optional attribute name for an existing relevance score.
        boost_brand: If set, candidates with matching brand get +0.1 boost.
        boost_topic: If set, candidates with matching topic get +0.1 boost.

    Returns:
        New list sorted by score descending.
    """
    scored: list[tuple[float, int, Any]] = []

    for i, candidate in enumerate(candidates):
        raw_type = getattr(candidate, source_type_attr)
        type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)
        base = SOURCE_TYPE_SCORE.get(type_str, 0.1)

        # Boost from existing relevance score (if available)
        if score_attr is not None:
            existing = getattr(candidate, score_attr, None) or 0.0
            base = max(base, existing)

        # Brand/topic boost
        meta = getattr(candidate, "raw_metadata", {}) or {}
        if boost_brand and meta.get("brand") == boost_brand:
            base += 0.1
        if boost_topic and meta.get("topic") == boost_topic:
            base += 0.1

        # Clamp to [0, 1]
        base = max(0.0, min(1.0, base))
        scored.append((base, i, candidate))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [item for _, _, item in scored]


#
# ── SearchResult Data Class ──────────────────────────────────────
#


@dataclass
class SearchResult:
    """A single search result from a SearchProvider."""
    title: str
    url: str
    snippet: str = ""
    source: str = "web"
    metadata: dict[str, Any] = field(default_factory=dict)


#
# ── AnalysisResult Data Class ────────────────────────────────────
#


@dataclass
class AnalysisResult:
    """Output from a ModelProvider after analyzing a search result."""
    source_type: SourceType
    relevance_score: float = 0.5
    reason: str = ""
    suggested_title: str = ""
    extracted_metadata: dict[str, Any] = field(default_factory=dict)


#
# ── Provider Interfaces ──────────────────────────────────────────
#


class SearchProvider(ABC):
    """Abstract search provider — used during source discovery.

    Implementations must not make network calls in test mode.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
        brand: str | None = None,
        topic: str | None = None,
    ) -> list[SearchResult]:
        """Execute a search and return raw results."""
        ...


class ModelProvider(ABC):
    """Abstract model provider — used for AI-powered analysis.

    Implementations wrap LLM calls for source type classification,
    relevance scoring, and metadata extraction.
    """

    @abstractmethod
    async def analyze_source(
        self,
        search_result: SearchResult,
        *,
        brand: str | None = None,
        topic: str | None = None,
    ) -> AnalysisResult:
        """Analyze a search result and return classification + metadata."""
        ...

    @abstractmethod
    async def discover_sources(
        self,
        query: str,
        *,
        brand: str | None = None,
        topic: str | None = None,
        max_results: int = 10,
    ) -> list[AnalysisResult]:
        """Discover and analyze sources for a given query.

        This is a convenience method that combines search + analysis.
        Implementations may delegate to a SearchProvider internally.
        """
        ...


#
# ── LLM Data Classes ──────────────────────────────────────────
#


@dataclass
class ClassifiedResult:
    """Output from LLMProvider.classify() — source type classification."""
    source_type: SourceType
    relevance_score: float = 0.5
    reason: str = ""
    suggested_title: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Output from LLMProvider.extract() — structured field extraction."""
    fields: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


#
# ── LLM Provider Interface ────────────────────────────────────
#


class LLMProvider(ABC):
    """Abstract LLM provider — used for AI-powered classification & extraction.

    Separates concerns from the older ModelProvider:
    - classify: determine source type and relevance from a search result
    - extract: pull structured fields from raw page content
    """

    @abstractmethod
    async def classify(
        self,
        *,
        title: str,
        snippet: str = "",
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ClassifiedResult:
        """Classify a search result into a source type with relevance score."""
        ...

    @abstractmethod
    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        """Extract structured fields from raw page content."""
        ...
