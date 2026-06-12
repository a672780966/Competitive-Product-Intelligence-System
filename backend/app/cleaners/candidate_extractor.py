"""
CPIS V1 — Candidate extractor for price, brand, and model.

Uses heuristics and common HTML patterns to identify likely
values for key product fields before AI extraction.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

# ── Price patterns ──────────────────────────────────────────────
_PRICE_PATTERN = re.compile(
    r"(?:[\$€£¥₩₹₽₺₴₦₱₿])\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)"
    r"|(?:([0-9]{1,6}(?:[.,][0-9]{1,2})?)\s*(?:USD|EUR|GBP|JPY|CNY|KRW|元|円|€|£))",
    re.IGNORECASE,
)

_SALE_PRICE_PATTERN = re.compile(
    r"(?:sale|special|current|now|price|我们的价格|售价|促销价|现价)[:\s]*"
    r"[\$€£¥]?\s*([0-9]{1,6}(?:[.,][0-9]{1,2})?)",
    re.IGNORECASE,
)

# ── Brand / model patterns ──────────────────────────────────────
_BRAND_KEYWORDS = [
    "brand", "manufacturer", "品牌", "制造商", "厂家",
    "by", "from", "厂商",
]


def extract_candidates(
    soup: BeautifulSoup,
    jsonld_data: list[dict],
) -> dict[str, list[Any]]:
    """Extract price, brand, and model candidates from the page.

    Args:
        soup: BeautifulSoup-parsed page (after noise removal).
        jsonld_data: List of JSON-LD dicts already extracted.

    Returns:
        Dict with keys: prices, brands, models.
    """
    prices: list[dict] = []
    brands: list[str] = []
    models: list[str] = []

    # 1. Extract from JSON-LD
    for block in jsonld_data:
        _extract_jsonld_prices(block, prices)
        _extract_jsonld_brand(block, brands)
        _extract_jsonld_model(block, models)

    # 2. Extract from text / HTML
    page_text = soup.get_text(separator=" ", strip=True)

    # Price regex on visible text
    for match in _PRICE_PATTERN.finditer(page_text):
        raw = match.group(0)
        price_candidate = {
            "raw": raw.strip()[:60],
            "value": (match.group(1) or match.group(2) or "").replace(",", ""),
        }
        if not any(p["raw"] == price_candidate["raw"] for p in prices):
            prices.append(price_candidate)

    # Sale price patterns
    for match in _SALE_PRICE_PATTERN.finditer(page_text):
        price_candidate = {
            "raw": match.group(0).strip()[:60],
            "value": match.group(1).replace(",", ""),
        }
        if not any(p["raw"] == price_candidate["raw"] for p in prices):
            prices.append(price_candidate)

    # Brand from meta / common selectors
    for tag in soup.find_all(["meta", "link", "span", "div", "a"]):
        if not isinstance(tag, Tag):
            continue
        # Check itemprop or class for "brand" keyword (NOT the content value)
        itemprop = tag.get("itemprop", "")
        classes = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class", ""))
        if "brand" in str(itemprop).lower() or "brand" in classes.lower():
            text = (tag.get("content", "") or tag.get_text(strip=True))
            if text and text not in brands:
                brands.append(text)

    # Model from itemprop or data attributes
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue
        itemprop = tag.get("itemprop", "")
        if itemprop and "model" in str(itemprop).lower():
            text = tag.get("content", "") or tag.get_text(strip=True)
            if text and text not in models:
                models.append(text)

    return {
        "prices": prices[:10],   # at most 10 price candidates
        "brands": brands[:5],
        "models": models[:5],
    }


def _extract_jsonld_prices(block: dict, prices: list[dict]) -> None:
    """Extract price info from a JSON-LD block."""
    # Direct offers
    for field in ("offers", "hasOffers", "makesOffer"):
        offers = block.get(field)
        if isinstance(offers, dict):
            offers = [offers]
        if isinstance(offers, list):
            for offer in offers:
                raw_price = offer.get("price")
                if raw_price is None:
                    spec = offer.get("priceSpecification")
                    raw_price = spec.get("price") if isinstance(spec, dict) else None
                currency = offer.get("priceCurrency", "")
                if raw_price is not None:
                    prices.append({
                        "raw": f"{currency} {raw_price}",
                        "value": str(raw_price),
                        "currency": currency,
                        "source": "jsonld",
                    })

    # Direct price
    price = block.get("price")
    if isinstance(price, (int, float, str)):
        prices.append({
            "raw": str(price),
            "value": str(price),
            "source": "jsonld",
        })


def _extract_jsonld_brand(block: dict, brands: list[str]) -> None:
    """Extract brand from a JSON-LD block."""
    brand = block.get("brand")
    if isinstance(brand, dict):
        name = brand.get("name", "")
        if name and name not in brands:
            brands.append(name)
    elif isinstance(brand, str) and brand not in brands:
        brands.append(brand)

    manufacturer = block.get("manufacturer")
    if isinstance(manufacturer, dict):
        name = manufacturer.get("name", "")
        if name and name not in brands:
            brands.append(name)


def _extract_jsonld_model(block: dict, models: list[str]) -> None:
    """Extract model from a JSON-LD block."""
    for field in ("model", "sku", "mpn", "gtin", "gtin13", "gtin14"):
        val = block.get(field)
        if val and isinstance(val, str) and val not in models:
            models.append(val)
