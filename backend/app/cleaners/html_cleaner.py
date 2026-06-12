"""
CPIS V1 — HtmlCleaner: main content cleaning and body extraction.

Pipeline:
1. Parse HTML with BeautifulSoup4 (lxml)
2. Remove noise elements (script, style, nav, footer, cookie banners, ads)
3. Extract JSON-LD, Open Graph, Microdata
4. Extract price / brand / model candidates
5. Generate cleaned plain-text and markdown
6. Compute content hash
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger
from app.cleaners.jsonld_extractor import extract_jsonld
from app.cleaners.candidate_extractor import extract_candidates

logger = get_logger(__name__)

# ── Noise selectors — elements to remove ────────────────────────
_NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe", "svg",
    "nav", "header", "footer",
    ".nav", ".navbar", ".navigation", ".menu", ".header", ".footer", ".foot",
    ".cookie", ".cookie-banner", ".cookie-notice", ".cookie-consent",
    ".ad", ".ads", ".advertisement", ".ad-container",
    ".sidebar", ".aside",
    ".modal", ".popup", ".overlay",
    ".social-share", ".share-buttons",
    ".breadcrumb", ".breadcrumbs",
    ".comments", ".comment-list", ".comment-form",
    "[role=complementary]", "[role=navigation]",
    # Common CMS classes
    ".wp-block", ".widget", ".widget-area",
]

# ── Keep selectors — content-rich elements ──────────────────────
_CONTENT_SELECTORS = [
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "li", "td", "th",
    "blockquote", "pre", "code",
    "img[alt]",  # images with alt text
]

# ── Max character count for cleaned text ────────────────────────
_MAX_TEXT_CHARS = 50_000


@dataclass
class CleanResult:
    """Output of the cleaning pipeline."""

    cleaned_text: str = ""
    cleaned_markdown: str = ""
    json_ld_data: list[dict] = field(default_factory=list)
    open_graph_data: dict = field(default_factory=dict)
    price_candidates: list[dict] = field(default_factory=list)
    brand_candidates: list[str] = field(default_factory=list)
    model_candidates: list[str] = field(default_factory=list)
    content_hash: str = ""
    success: bool = False
    error_message: str = ""


class HtmlCleaner:
    """Cleans raw HTML into structured, AI-ready content."""

    def clean(self, raw_html: bytes | str, page_url: str = "") -> CleanResult:
        """Run the full cleaning pipeline on raw HTML.

        Args:
            raw_html: The raw HTML content (bytes or str).
            page_url: The page URL (for resolving relative links).

        Returns:
            A CleanResult with cleaned content and extracted candidates.
        """
        if isinstance(raw_html, bytes):
            raw_html = raw_html.decode("utf-8", errors="replace")

        if not raw_html.strip():
            return CleanResult(
                success=False, error_message="Empty HTML content",
            )

        try:
            soup = BeautifulSoup(raw_html, "lxml")
        except Exception as exc:
            logger.error("parse_error", error=str(exc))
            return CleanResult(
                success=False, error_message=f"HTML parse error: {exc}",
            )

        # 1. Extract structured data before cleaning (data may be in head)
        json_ld = extract_jsonld(soup)
        og_data = _extract_open_graph(soup)

        # 2. Remove noise elements
        _remove_noise(soup)

        # 3. Extract candidates
        candidates = extract_candidates(soup, json_ld)

        # 4. Generate cleaned text
        cleaned_text = _extract_clean_text(soup)
        cleaned_text = _truncate_text(cleaned_text, _MAX_TEXT_CHARS)

        # 5. Generate markdown
        cleaned_markdown = _to_markdown(soup, page_url=page_url)
        cleaned_markdown = _truncate_text(cleaned_markdown, _MAX_TEXT_CHARS)

        # 6. Compute hash
        content_hash = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()

        return CleanResult(
            cleaned_text=cleaned_text,
            cleaned_markdown=cleaned_markdown,
            json_ld_data=json_ld,
            open_graph_data=og_data,
            price_candidates=candidates.get("prices", []),
            brand_candidates=candidates.get("brands", []),
            model_candidates=candidates.get("models", []),
            content_hash=content_hash,
            success=True,
        )


# ── Internal helpers ────────────────────────────────────────────


def _remove_noise(soup: BeautifulSoup) -> None:
    """Remove noise elements from the DOM in-place."""
    for selector in _NOISE_SELECTORS:
        for element in soup.select(selector):
            element.decompose()

    # Remove elements with very few text nodes and lots of links (likely nav)
    for tag in soup.find_all(True):
        if isinstance(tag, Tag):
            text_len = len(tag.get_text(strip=True))
            links = tag.find_all("a")
            if links and text_len < 50 and len(links) > 3:
                tag.decompose()


def _extract_clean_text(soup: BeautifulSoup) -> str:
    """Extract clean text, preserving structure."""
    parts: list[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th", "blockquote", "pre"]):
        text = tag.get_text(strip=True)
        if text:
            parts.append(text)
    return "\n\n".join(parts)


def _to_markdown(soup: BeautifulSoup, page_url: str = "") -> str:
    """Convert cleaned HTML to a simple markdown-like format.

    If ``page_url`` is provided, relative ``src`` attributes on images
    are resolved to absolute URLs.
    """
    lines: list[str] = []

    for tag in soup.find_all(True):
        if isinstance(tag, Tag):
            text = tag.get_text(strip=True)
            if not text:
                continue

            tag_name = tag.name.lower()

            if tag_name in ("h1",):
                lines.append(f"# {text}")
                lines.append("")
            elif tag_name in ("h2",):
                lines.append(f"## {text}")
                lines.append("")
            elif tag_name in ("h3",):
                lines.append(f"### {text}")
                lines.append("")
            elif tag_name in ("h4", "h5", "h6"):
                lines.append(f"**{text}**")
                lines.append("")
            elif tag_name == "li":
                lines.append(f"- {text}")
            elif tag_name == "blockquote":
                lines.append(f"> {text}")
                lines.append("")
            elif tag_name == "pre":
                lines.append(f"```\n{text}\n```")
                lines.append("")
            elif tag_name in ("p", "td", "th"):
                lines.append(text)
                lines.append("")
            elif tag_name == "img":
                alt = tag.get("alt", "")
                src = tag.get("src", "")
                if src and page_url:
                    src = urllib.parse.urljoin(page_url, src)
                if alt:
                    lines.append(f"![{alt}]({src})" if src else alt)
                    lines.append("")

    return "\n".join(lines).strip()


def _extract_open_graph(soup: BeautifulSoup) -> dict:
    """Extract Open Graph metadata from meta tags."""
    og: dict = {}
    for meta in soup.find_all("meta"):
        if isinstance(meta, Tag):
            prop = meta.get("property", "") or meta.get("name", "")
            content = meta.get("content", "")
            if prop and content and str(prop).startswith("og:"):
                key = str(prop).replace("og:", "")
                og[key] = str(content)
    return og


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text at the last sentence boundary before max_chars."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind("。")
    last_dot = truncated.rfind(". ")
    split_at = max(last_period, last_dot)
    if split_at > max_chars // 2:
        return truncated[: split_at + 1]
    return truncated
