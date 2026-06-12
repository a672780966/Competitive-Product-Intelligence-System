"""
CPIS V1 — 内容清洗与正文抽取测试

Tests HtmlCleaner, JSON-LD extraction, candidate extraction,
noise removal, and markdown generation.
"""

from __future__ import annotations

from app.cleaners.html_cleaner import HtmlCleaner, _remove_noise, _to_markdown
from app.cleaners.jsonld_extractor import extract_jsonld
from app.cleaners.candidate_extractor import extract_candidates, _PRICE_PATTERN


# ══════════════════════════════════════════════════════════════════
# Sample HTML fragments
# ══════════════════════════════════════════════════════════════════

_PRODUCT_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>SmartPro X200 - Official Store</title>
  <meta property="og:title" content="SmartPro X200 Smartwatch" />
  <meta property="og:price:amount" content="299.99" />
  <meta property="og:availability" content="in_stock" />
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "SmartPro X200",
    "brand": {
      "@type": "Brand",
      "name": "TechCorp"
    },
    "model": "SP-X200-2025",
    "sku": "SPX200-BLK-64",
    "offers": {
      "@type": "Offer",
      "price": "299.99",
      "priceCurrency": "USD"
    }
  }
  </script>
</head>
<body>
  <nav class="navbar"><a href="/">Home</a> <a href="/products">Products</a></nav>
  <div class="cookie-banner">This site uses cookies. Accept?</div>
  <div class="sidebar">Related products...</div>
  <div class="ad">Buy now! Limited offer!</div>

  <main>
    <h1>SmartPro X200 Smartwatch</h1>
    <p class="price">$299.99</p>
    <p>The SmartPro X200 is our latest smartwatch with 24h battery life.</p>

    <h2>Specifications</h2>
    <ul>
      <li>Display: 1.4-inch AMOLED</li>
      <li>Battery: 7 days typical use</li>
      <li>Water resistant: 5 ATM</li>
      <li>Compatible with: iOS 16+, Android 12+</li>
    </ul>

    <h2>Pricing</h2>
    <p>Sale price: $249.99</p>
    <p>Regular price: <span itemprop="price">299.99</span></p>

    <div class="footer">© 2026 TechCorp. All rights reserved.</div>
  </main>
</body>
</html>
"""

_SIMPLE_HTML = "<html><body><h1>Hello</h1><p>World</p></body></html>"
_EMPTY_HTML = ""
_NOISE_HTML = """<html><body>
  <nav>Nav links here</nav>
  <script>alert('bad')</script>
  <div class="ad">Advertisement</div>
  <div class="cookie-banner">Accept cookies</div>
  <main><h1>Content</h1><p>Real content here.</p></main>
</body></html>
"""


# ══════════════════════════════════════════════════════════════════
# HtmlCleaner tests
# ══════════════════════════════════════════════════════════════════


class TestHtmlCleaner:
    def test_clean_product_page(self):
        """A full product page is cleaned with text, markdown, and candidates."""
        cleaner = HtmlCleaner()
        result = cleaner.clean(_PRODUCT_HTML)

        assert result.success is True
        assert len(result.cleaned_text) > 0
        assert len(result.cleaned_markdown) > 0
        assert result.content_hash is not None

        # Structured data
        assert len(result.json_ld_data) >= 1
        assert result.json_ld_data[0]["name"] == "SmartPro X200"

        # Open Graph
        assert result.open_graph_data.get("title") == "SmartPro X200 Smartwatch"

        # Candidates
        assert any("299.99" in p["value"] for p in result.price_candidates)
        assert "TechCorp" in result.brand_candidates
        assert "SP-X200-2025" in result.model_candidates

    def test_clean_removes_noise(self):
        """Noise elements are removed from the text output."""
        cleaner = HtmlCleaner()
        result = cleaner.clean(_NOISE_HTML)

        assert result.success is True
        assert "Nav links" not in result.cleaned_text
        assert "Accept cookies" not in result.cleaned_text
        assert "Advertisement" not in result.cleaned_text
        assert "Content" in result.cleaned_text
        assert "Real content" in result.cleaned_text

    def test_clean_empty_html(self):
        """Empty HTML returns failure."""
        cleaner = HtmlCleaner()
        result = cleaner.clean(_EMPTY_HTML)
        assert result.success is False
        assert "Empty" in result.error_message

    def test_clean_minimal_html(self):
        """Minimal valid HTML still works."""
        cleaner = HtmlCleaner()
        result = cleaner.clean(_SIMPLE_HTML)
        assert result.success is True
        assert "Hello" in result.cleaned_text
        assert "World" in result.cleaned_text

    def test_content_hash_changes_with_different_content(self):
        """Different content produces different hashes."""
        cleaner = HtmlCleaner()
        r1 = cleaner.clean(_SIMPLE_HTML)
        r2 = cleaner.clean(_PRODUCT_HTML)
        assert r1.content_hash != r2.content_hash

    def test_clean_bytes_input(self):
        """Bytes input is accepted and decoded."""
        cleaner = HtmlCleaner()
        result = cleaner.clean(_PRODUCT_HTML.encode("utf-8"))
        assert result.success is True
        assert "SmartPro" in result.cleaned_text

    def test_truncate_long_text(self):
        """Very long HTML is truncated."""
        long_body = "<html><body>" + " ".join(["<p>Sentence. </p>"] * 30000) + "</body></html>"
        cleaner = HtmlCleaner()
        result = cleaner.clean(long_body)
        assert result.success is True
        assert len(result.cleaned_text) <= 60000  # 50k max + small buffer


# ══════════════════════════════════════════════════════════════════
# Noise removal
# ══════════════════════════════════════════════════════════════════


class TestNoiseRemoval:
    def test_removes_script_and_style(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><head><script>alert(1)</script><style>.x{}</style></head><body><p>Text</p></body></html>", "lxml")
        _remove_noise(soup)
        assert soup.find("script") is None
        assert soup.find("style") is None
        assert soup.find("p") is not None

    def test_removes_nav_and_footer(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><nav>Nav</nav><footer>Footer</footer><main><p>Content</p></main></body></html>", "lxml")
        _remove_noise(soup)
        assert soup.find("nav") is None
        assert soup.find("footer") is None
        assert soup.find("main") is not None


# ══════════════════════════════════════════════════════════════════
# JSON-LD extraction
# ══════════════════════════════════════════════════════════════════


class TestJsonldExtraction:
    def test_extract_product_jsonld(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(_PRODUCT_HTML, "lxml")
        data = extract_jsonld(soup)
        assert len(data) >= 1
        assert data[0]["@type"] == "Product"
        assert data[0]["name"] == "SmartPro X200"
        assert data[0]["brand"]["name"] == "TechCorp"

    def test_no_jsonld_returns_empty(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><p>No JSON-LD</p></body></html>", "lxml")
        data = extract_jsonld(soup)
        assert data == []

    def test_invalid_jsonld_ignored(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup('<html><script type="application/ld+json">{invalid}</script></html>', "lxml")
        data = extract_jsonld(soup)
        assert data == []


# ══════════════════════════════════════════════════════════════════
# Candidate extraction
# ══════════════════════════════════════════════════════════════════


class TestCandidateExtraction:
    def test_extract_prices_from_text(self):
        text = "Price: $299.99 and €199,95"
        matches = _PRICE_PATTERN.findall(text)
        assert len(matches) >= 2

    def test_extract_candidates_from_product_page(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(_PRODUCT_HTML, "lxml")
        jsonld = extract_jsonld(soup)
        candidates = extract_candidates(soup, jsonld)

        assert len(candidates["brands"]) > 0
        assert "TechCorp" in candidates["brands"]

        assert len(candidates["models"]) > 0
        assert "SP-X200-2025" in candidates["models"]

        assert len(candidates["prices"]) > 0
        values = [p["value"] for p in candidates["prices"]]
        assert any("299.99" in v for v in values)


# ══════════════════════════════════════════════════════════════════
# Markdown output
# ══════════════════════════════════════════════════════════════════


class TestMarkdownOutput:
    def test_headings_become_markdown(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><h1>Title</h1><h2>Subtitle</h2><p>Body</p></body></html>", "lxml")
        md = _to_markdown(soup)
        assert "# Title" in md
        assert "## Subtitle" in md
        assert "Body" in md

    def test_list_items_become_dash_list(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><ul><li>Item 1</li><li>Item 2</li></ul></body></html>", "lxml")
        md = _to_markdown(soup)
        assert "- Item 1" in md
        assert "- Item 2" in md

    def test_blockquote_becomes_quote(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<html><body><blockquote>Quote text</blockquote></body></html>", "lxml")
        md = _to_markdown(soup)
        assert "> Quote text" in md
