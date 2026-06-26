# RunPlan Declarative JSON Specification

## 1. Purpose

The `RunPlan` is a **declarative JSON document** that tells the `WhitelistExecutor`
what content to collect and how. It is NOT a script — it contains zero executable
code. No `eval()`, no `exec()`, no inline Python/JS, no template expressions,
no dynamic imports.

This ensures that collection templates and scheduled collections are safe to
store, share, and execute without sandboxing.

## 2. JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RunPlan",
  "description": "Declarative collection plan for CPIS WhitelistExecutor. Contains zero executable code.",
  "type": "object",
  "required": ["version", "sources"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["1.0"],
      "description": "RunPlan schema version. Currently only '1.0' is valid."
    },
    "name": {
      "type": "string",
      "maxLength": 255,
      "description": "Optional human-readable name for this plan."
    },
    "sources": {
      "type": "array",
      "minItems": 1,
      "maxItems": 100,
      "description": "List of source definitions to collect from.",
      "items": {
        "$ref": "#/$defs/SourceDef"
      }
    },
    "collector": {
      "$ref": "#/$defs/CollectorSpec",
      "description": "Default collector for all sources. Can be overridden per-source."
    },
    "scope": {
      "$ref": "#/$defs/CollectionScope",
      "description": "Optional scope configuration."
    }
  },
  "$defs": {
    "SourceDef": {
      "type": "object",
      "required": ["type"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["url_list", "url_pattern", "search", "sitemap"],
          "description": "Source type determines how URLs are resolved: url_list = explicit URLs, url_pattern = templated URL, search = perform web search, sitemap = parse XML sitemap."
        },
        "urls": {
          "type": "array",
          "items": {
            "type": "string",
            "format": "uri",
            "maxLength": 2048
          },
          "minItems": 1,
          "maxItems": 500,
          "description": "Explicit list of URLs to collect. Used when type='url_list'."
        },
        "url_template": {
          "type": "string",
          "maxLength": 2048,
          "description": "URL template with {replaceable} parameters. Used when type='url_pattern'. Example: 'https://example.com/products?page={page}'"
        },
        "url_params": {
          "type": "object",
          "description": "Parameters to substitute into url_template. Keys are parameter names, values are arrays of values. Example: {\"page\": [1, 2, 3]}"
        },
        "search_query": {
          "type": "string",
          "maxLength": 500,
          "description": "Search query string. Used when type='search'."
        },
        "search_provider": {
          "type": "string",
          "enum": ["duckduckgo", "bing", "serpapi", "default"],
          "default": "default",
          "description": "Search engine to use. 'default' uses the system-configured provider."
        },
        "max_results": {
          "type": "integer",
          "minimum": 1,
          "maximum": 50,
          "default": 10,
          "description": "Maximum search results (only for type='search')."
        },
        "sitemap_url": {
          "type": "string",
          "format": "uri",
          "maxLength": 2048,
          "description": "URL of the XML sitemap to parse. Used when type='sitemap'."
        },
        "sitemap_filter": {
          "type": "string",
          "maxLength": 500,
          "description": "Regex pattern to filter sitemap URLs (e.g., '/product/' to only collect product pages)."
        },
        "collector": {
          "$ref": "#/$defs/CollectorSpec",
          "description": "Overrides the default collector for this source."
        },
        "category_hint": {
          "type": "string",
          "maxLength": 64,
          "description": "Optional product category hint for all URLs in this source."
        },
        "language_hint": {
          "type": "string",
          "maxLength": 16,
          "description": "Optional language hint (e.g., 'zh-CN', 'en-US')."
        },
        "extract_options": {
          "$ref": "#/$defs/ExtractOptions",
          "description": "Optional extraction overrides."
        }
      },
      "oneOf": [
        {"required": ["urls"], "properties": {"type": {"const": "url_list"}}},
        {"required": ["url_template", "url_params"], "properties": {"type": {"const": "url_pattern"}}},
        {"required": ["search_query"], "properties": {"type": {"const": "search"}}},
        {"required": ["sitemap_url"], "properties": {"type": {"const": "sitemap"}}}
      ]
    },
    "CollectorSpec": {
      "type": "object",
      "required": ["kind"],
      "properties": {
        "kind": {
          "type": "string",
          "enum": ["direct_http", "playwright", "scrapling", "crawl4ai"],
          "description": "collector kind: direct_http (always available), playwright (always available), scrapling (feature-gated), crawl4ai (feature-gated)"
        },
        "params": {
          "type": "object",
          "properties": {
            "timeout": {
              "type": "integer",
              "minimum": 5,
              "maximum": 120,
              "default": 20,
              "description": "Per-request timeout in seconds."
            },
            "wait_for_selector": {
              "type": "string",
              "maxLength": 200,
              "description": "CSS selector to wait for (playwright only)."
            },
            "viewport_width": {
              "type": "integer",
              "minimum": 320,
              "maximum": 3840,
              "default": 1280,
              "description": "Viewport width in pixels (playwright only)."
            },
            "viewport_height": {
              "type": "integer",
              "minimum": 240,
              "maximum": 2160,
              "default": 800,
              "description": "Viewport height in pixels (playwright only)."
            },
            "headers": {
              "type": "object",
              "maxProperties": 20,
              "description": "Additional HTTP headers to send with the request."
            },
            "cookies": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "name": {"type": "string"},
                  "value": {"type": "string"},
                  "domain": {"type": "string"}
                },
                "required": ["name", "value"]
              },
              "maxItems": 20,
              "description": "Cookies to include with the request."
            }
          }
        }
      }
    },
    "CollectionScope": {
      "type": "object",
      "properties": {
        "max_pages": {
          "type": "integer",
          "minimum": 1,
          "maximum": 500,
          "default": 50,
          "description": "Maximum number of pages to collect across all sources."
        },
        "max_pages_per_domain": {
          "type": "integer",
          "minimum": 1,
          "maximum": 100,
          "default": 25,
          "description": "Maximum pages per domain."
        },
        "respect_robots_txt": {
          "type": "boolean",
          "default": true,
          "description": "Whether to check robots.txt before collection."
        },
        "delay_between_requests_ms": {
          "type": "integer",
          "minimum": 0,
          "maximum": 60000,
          "default": 500,
          "description": "Delay between consecutive requests in milliseconds."
        }
      }
    },
    "ExtractOptions": {
      "type": "object",
      "properties": {
        "extraction_prompt": {
          "type": "string",
          "maxLength": 2000,
          "description": "Custom prompt suffix for AI extraction. Must not contain executable code."
        },
        "skip_extraction": {
          "type": "boolean",
          "default": false,
          "description": "If true, collect and clean content but skip AI extraction."
        },
        "confidence_threshold": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "default": 0.7,
          "description": "Override the default auto-approve confidence threshold."
        }
      }
    }
  }
}
```

## 3. Validation Rules

### 3.1 Structural Rules (enforced by Pydantic schema)

| Rule | Description |
|------|-------------|
| R001 | `version` must be exactly `"1.0"` |
| R002 | `sources` array must contain 1–100 items |
| R003 | Each source must have exactly one type: `url_list`, `url_pattern`, `search`, or `sitemap` |
| R004 | `url_list` sources must have a `urls` array with 1–500 items |
| R005 | `url_pattern` sources must have both `url_template` and `url_params` |
| R006 | `search` sources must have a non-empty `search_query` |
| R007 | `sitemap` sources must have a valid `sitemap_url` |
| R008 | All URLs must be valid http/https URIs (max 2048 chars) |
| R009 | Collector `kind` must be one of the whitelist values |

### 3.2 Security Rules (enforced by `WhitelistExecutor.validate()`)

| Rule | Description |
|------|-------------|
| S001 | RunPlan must be valid JSON (parseable by `json.loads`) or Pydantic model |
| S002 | RunPlan must NOT contain any key named `"script"`, `"code"`, `"eval"`, `"exec"`, `"fn"`, `"function"`, `"command"`, `"executable"` — validation scans the JSON tree recursively |
| S003 | RunPlan must NOT contain any string value matching pattern `r'\\b(exec|eval|__builtins__|__import__|os\\.|subprocess|spawn|fork)\\b'` |
| S004 | Collector `kind` must be in whitelist: `["direct_http", "playwright"]` for baseline; `["scrapling", "crawl4ai"]` only if feature flag is enabled |
| S005 | `url_template` must NOT contain `${..}` — only `{param}` syntax is allowed (Python `.format()` style) |
| S006 | `url_template` parameters must match keys in `url_params` exactly |
| S007 | `max_pages` must not exceed `settings.SCHEDULER_MAX_PER_SCHEDULE` |
| S008 | `url_params` values must be primitive types (strings, numbers, booleans) only — no arrays of objects |

### 3.3 Business Rules (enforced by `TemplateService`)

| Rule | Description |
|------|-------------|
| B001 | A template name must be unique (case-insensitive) |
| B002 | `search` type sources require a configured `SearchProvider` (settings.SEARCH_PROVIDER) |
| B003 | `sitemap` type sources require network access to the sitemap URL |
| B004 | Combined URLs from all sources must not exceed 500 unique URLs |

## 4. Collector Whitelist

| Collector Kind | Always Available | Requires Feature Flag | Description |
|---------------|:----------------:|:---------------------:|-------------|
| `direct_http` | ✅ | — | Static HTTP fetch via httpx. Fast, low overhead. |
| `playwright` | ✅ | — | JS-rendered page fetch via Playwright. Fallback for JS-heavy sites. |
| `scrapling` | ❌ | `SCRAPLING_ENABLED=true` | Advanced scraping with automatic anti-bot detection. |
| `crawl4ai` | ❌ | `CRAWL4AI_ENABLED=true` | AI-powered crawling with smart extraction. |

Each collector kind corresponds to a `BaseCollectorProvider` subclass that
wraps the actual fetch library. The `WhitelistExecutor` instantiates providers
lazily and caches them for the lifetime of the executor.

## 5. RunPlan Examples

### Example 1: Simple URL list

```json
{
  "version": "1.0",
  "name": "iPhone 16 competitor check",
  "collector": {
    "kind": "direct_http",
    "params": {
      "timeout": 30
    }
  },
  "sources": [
    {
      "type": "url_list",
      "urls": [
        "https://www.apple.com/iphone-16/",
        "https://www.samsung.com/galaxy-s25/",
        "https://store.google.com/product/pixel_10"
      ],
      "category_hint": "smartphone",
      "language_hint": "en-US"
    }
  ]
}
```

### Example 2: URL pattern with parameters

```json
{
  "version": "1.0",
  "name": "Amazon best sellers — multiple pages",
  "collector": {
    "kind": "playwright",
    "params": {
      "timeout": 45,
      "wait_for_selector": "#search-result"
    }
  },
  "scope": {
    "max_pages": 10,
    "delay_between_requests_ms": 2000
  },
  "sources": [
    {
      "type": "url_pattern",
      "url_template": "https://www.amazon.com/best-sellers-electronics?pg={page}",
      "url_params": {
        "page": [1, 2, 3, 4, 5]
      },
      "category_hint": "electronics",
      "collector": {
        "kind": "playwright",
        "params": {
          "timeout": 60
        }
      }
    }
  ]
}
```

### Example 3: Web search then collect

```json
{
  "version": "1.0",
  "name": "Discover Chinese smartphone competitors",
  "collector": {
    "kind": "direct_http"
  },
  "sources": [
    {
      "type": "search",
      "search_query": "2025 flagship smartphone review site:zhihu.com",
      "search_provider": "default",
      "max_results": 5,
      "category_hint": "smartphone",
      "language_hint": "zh-CN"
    },
    {
      "type": "search",
      "search_query": "小米15 评测",
      "search_provider": "default",
      "max_results": 5,
      "category_hint": "smartphone",
      "language_hint": "zh-CN"
    }
  ]
}
```

### Example 4: Sitemap-based crawl

```json
{
  "version": "1.0",
  "name": "Daily competitor product crawl",
  "collector": {
    "kind": "direct_http"
  },
  "scope": {
    "max_pages": 20,
    "max_pages_per_domain": 10,
    "respect_robots_txt": true
  },
  "sources": [
    {
      "type": "sitemap",
      "sitemap_url": "https://example.com/sitemap-products.xml",
      "sitemap_filter": "/product/",
      "category_hint": "smart_home"
    }
  ]
}
```

## 6. Python Validation Implementation

```python
# app/schemas/run_plan.py (NEW)

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

_DANGEROUS_PATTERNS = re.compile(
    r'\b(exec|eval|__builtins__|__import__|os\.|subprocess|spawn|fork|compile|globals|locals)\b'
)


class CollectorParams(BaseModel):
    timeout: int = Field(default=20, ge=5, le=120)
    wait_for_selector: str | None = Field(None, max_length=200)
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=800, ge=240, le=2160)
    headers: dict[str, str] | None = Field(None, max_length=20)
    cookies: list[dict[str, str]] | None = Field(None, max_length=20)


class CollectorSpec(BaseModel):
    kind: Literal["direct_http", "playwright", "scrapling", "crawl4ai"]
    params: CollectorParams = Field(default_factory=CollectorParams)


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
    def validate_source_type_requirements(self) -> "SourceDef":
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


class RunPlan(BaseModel):
    """Declarative collection plan — zero executable code allowed."""

    version: Literal["1.0"]
    name: str | None = Field(None, max_length=255)
    sources: list[SourceDef] = Field(..., min_length=1, max_length=100)
    collector: CollectorSpec | None = None
    scope: CollectionScope = Field(default_factory=CollectionScope)

    @field_validator("sources")
    @classmethod
    def validate_no_dynamic_code(cls, v: list[SourceDef]) -> list[SourceDef]:
        """Recursively validate that no field contains executable code patterns."""
        raw = [s.model_dump() for s in v]
        _check_no_dangerous_patterns(raw)
        return v


def _check_no_dangerous_patterns(data: Any, path: str = "$") -> None:
    """
    Recursively scan the RunPlan JSON for dangerous patterns.
    Raises ValueError if any are found.
    """
    if isinstance(data, str):
        if _DANGEROUS_PATTERNS.search(data):
            raise ValueError(
                f"RunPlan contains a potentially dangerous pattern at {path}. "
                "Dynamic code execution is not allowed in RunPlans."
            )
    elif isinstance(data, dict):
        for key in data:
            # Check for forbidden top-level keys
            if key.lower() in {"script", "code", "eval", "exec", "fn", "function", "command", "executable"}:
                raise ValueError(
                    f"Forbidden key '{key}' at {path}. "
                    "RunPlans must be declarative only — no executable keys."
                )
            _check_no_dangerous_patterns(data[key], f"{path}.{key}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_no_dangerous_patterns(item, f"{path}[{i}]")


def validate_run_plan(data: dict) -> RunPlan:
    """
    Validate a raw dict as a RunPlan.
    
    Args:
        data: Raw JSON dict (from user input or database).
        
    Returns:
        Validated RunPlan Pydantic model.
        
    Raises:
        ValueError: If validation fails with a user-readable message.
    """
    # Step 1: Structural validation via Pydantic
    plan = RunPlan.model_validate(data)
    
    # Step 2: Security scan (redundant with Pydantic validator, but explicit)
    _check_no_dangerous_patterns(data)
    
    return plan
```

## 7. Execution Flow

```
Raw JSON (from API or DB)
    │
    ▼
json.loads() or Pydantic model_validate()
    │
    ▼
RunPlan.model_validate(raw)         ← Structural + Security validation
    │
    ▼
validate_run_plan(raw)              ← Explicit security scan (belt + suspenders)
    │
    ▼
WhitelistExecutor.execute(plan)     ← Only whitelisted collectors are created
    │
    ├─ For each source:
    │   ├─ Resolve URLs (from urls, pattern, search, or sitemap)
    │   ├─ Resolve collector (source override or default)
    │   ├─ Fetch content (with scope limits)
    │   └─ Collect CollectResult
    │
    ▼
List[CollectResult]                 ← Returned to caller (service or task)
```

## 8. FAQ

**Q: Can I include a Python lambda or JS arrow function in url_params?**
A: No. `url_params` values must be primitive types only (string, number, boolean).

**Q: Can I use `{today}` or `{random}` in url_template?**
A: No. The only allowed template parameters are those explicitly listed in
`url_params`. Dynamic values (dates, random numbers) must be resolved before
submitting the RunPlan.

**Q: What if I need custom extraction logic that differs per URL?**
A: Create separate sources with different `extract_options.extraction_prompt`
values. The prompt is plain text — not executable code.

**Q: Can I use `sitemap_filter` as regex to extract data from the URL?**
A: No. The filter selects which sitemap entries to collect. It cannot capture
or transform URL segments.

**Q: What happens if someone adds a key named `"exec"` inside an innocent field?**
A: The security scanner recursively checks both keys and string values.
Any occurrence of forbidden keys or patterns anywhere in the RunPlan causes
validation failure.
