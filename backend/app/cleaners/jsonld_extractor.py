"""
CPIS V1 — JSON-LD structured data extractor.

Extracts JSON-LD <script type="application/ld+json"> blocks from a
BeautifulSoup-parsed document, filters for product-relevant types,
and returns parsed dictionaries.
"""

from __future__ import annotations

import json
from typing import Any

from bs4 import BeautifulSoup, Tag

# Schema.org types that may contain product information
_PRODUCT_TYPES = {
    "Product",
    "ProductGroup",
    "IndividualProduct",
    "SomeProducts",
    "Offer",
    "AggregateOffer",
    "PriceSpecification",
    "UnitPriceSpecification",
    "BusinessFunction",
    "Brand",
}


def extract_jsonld(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract all JSON-LD blocks from the page, returning product-relevant ones.

    Returns a list of parsed JSON-LD dicts that match product-related types.
    """
    results: list[dict[str, Any]] = []
    for script in soup.find_all("script", type="application/ld+json"):
        if not isinstance(script, Tag):
            continue
        try:
            raw = script.string
            if not raw:
                continue
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue

        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if _is_product_related(block):
                results.append(block)

    return results


def _is_product_related(data: dict) -> bool:
    """Check if a JSON-LD block is product-related based on @type."""
    type_val = data.get("@type", "")
    if isinstance(type_val, list):
        return any(t in _PRODUCT_TYPES for t in type_val)
    return type_val in _PRODUCT_TYPES
