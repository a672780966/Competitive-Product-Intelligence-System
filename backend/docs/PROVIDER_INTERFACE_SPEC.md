# Provider Interface Specification

## Overview

This document defines the abstract interfaces for all provider types in the CPIS Discovery Provider Layer. Each interface follows the **Abstract Base Class (ABC)** pattern with `@abstractmethod` decorators.

---

## SearchProvider

```python
class SearchProvider(ABC):
    """Abstract search provider — used during source discovery."""

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
```

### SearchResult Dataclass

```python
@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "web"
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Contract
- Must not make network calls in test mode
- Should respect `max_results` parameter
- Should return empty list on error (not raise)
- `brand` and `topic` are hints for search refinement (optional)

---

## LLMProvider

```python
class LLMProvider(ABC):
    """Abstract LLM provider — used for AI-powered classification & extraction."""

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

    async def extract(
        self,
        *,
        content: str,
        url: str = "",
        brand: str | None = None,
        topic: str | None = None,
    ) -> ExtractionResult:
        """Extract structured fields from raw page content."""
```

### ClassifiedResult Dataclass

```python
@dataclass
class ClassifiedResult:
    source_type: SourceType
    relevance_score: float = 0.5
    reason: str = ""
    suggested_title: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### ExtractionResult Dataclass

```python
@dataclass
class ExtractionResult:
    fields: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Contract
- `classify()` must always return a valid `ClassifiedResult`
- `extract()` must always return a valid `ExtractionResult`
- Errors should be logged, not raised (return degraded result)
- `confidence` in [0.0, 1.0] range

---

## ModelProvider (Legacy — Deprecated)

```python
class ModelProvider(ABC):
    """Abstract model provider — used for AI-powered analysis."""

    async def analyze_source(
        self,
        search_result: SearchResult,
        *,
        brand: str | None = None,
        topic: str | None = None,
    ) -> AnalysisResult:
        """Analyze a search result and return classification + metadata."""

    async def discover_sources(
        self,
        query: str,
        *,
        brand: str | None = None,
        topic: str | None = None,
        max_results: int = 10,
    ) -> list[AnalysisResult]:
        """Discover and analyze sources for a given query."""
```

> **Note:** `ModelProvider` is kept for backward compatibility. New code should use `LLMProvider` instead.

---

## Risk Assessment & Collector Recommendation

### assess_risk_level(source_type, domain) → RiskLevel

| Source Type | Domain | Risk Level |
|---|---|---|
| OFFICIAL_HOMEPAGE | Any | LOW |
| PRODUCT_DETAIL | Any | LOW |
| DOCUMENTATION | Any | LOW |
| NEWS | Any | MEDIUM |
| REVIEW | Any | MEDIUM |
| FORUM | Any | HIGH |
| SOCIAL | Any | HIGH |
| Any | weibo.com / zhihu.com / tieba.baidu.com / etc. | BLOCKED |

### recommend_collector(source_type, risk_level, domain) → RecommendedCollector

| Risk Level | Recommended Collector |
|---|---|
| BLOCKED | REQUIRES_CONFIRMATION |
| HIGH | REQUIRES_CONFIRMATION |
| MEDIUM | DIRECT_HTTP |
| LOW | DIRECT_HTTP |

---

## Candidate Ranking

The `rank_candidates()` function sorts source candidates by desirability:

```python
def rank_candidates(
    candidates: list[Any],
    *,
    source_type_attr: str = "source_type",
    score_attr: str | None = None,
    boost_brand: str | None = None,
    boost_topic: str | None = None,
) -> list[Any]:
```

### Ranking Scores

| Source Type | Base Score |
|---|---|
| official_homepage | 1.0 |
| product_detail | 0.95 |
| documentation | 0.85 |
| review | 0.70 |
| news | 0.65 |
| forum | 0.40 |
| social | 0.20 |
| other | 0.10 |

**Boosts:** +0.1 for matching brand, +0.1 for matching topic.
