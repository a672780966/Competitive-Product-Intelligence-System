"""
CPIS V1 — Candidate extractor for price, brand, and model.

Uses heuristics and common HTML patterns to identify likely
values for key product fields before AI extraction.
"""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.core.logging import get_logger

logger = get_logger(__name__)

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

    # Brand from meta / common selectors — 扩大搜索范围，使用更灵活的模式
    for tag in soup.find_all(True):  # ✅ 搜索所有标签，而不仅仅是特定几个
        if not isinstance(tag, Tag):
            continue

        # ✅ 检查多种属性模式
        itemprop = tag.get("itemprop", "")
        data_brand = tag.get("data-brand", "")
        data_product_brand = tag.get("data-product-brand", "")
        classes = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class", ""))

        # ✅ 检查属性名是否包含 "brand"（小写比较）
        attr_has_brand = (
            "brand" in str(itemprop).lower()
            or "brand" in classes.lower()
            or (data_brand and data_brand.strip() != "")
            or (data_product_brand and data_product_brand.strip() != "")
        )

        if attr_has_brand:
            # ✅ 尝试多个位置获取品牌名称
            text = (
                tag.get("content", "")
                or data_brand
                or data_product_brand
                or tag.get("title", "")
                or tag.get("alt", "")
                or tag.get_text(strip=True)
            )

            # ✅ 正确的验证逻辑
            if text and isinstance(text, str) and text.strip():
                text = text.strip()
                if text not in brands and len(text) > 1:  # 过滤单个字符
                    brands.append(text)
                    logger.debug("brand_extracted", value=text, source="html_itemprop")

    # ✅ 从页面文本中额外提取品牌（弥补结构化标记缺失）
    _extract_brands_from_text(page_text, brands)

    # Model from itemprop or data attributes — 扩展属性支持
    for tag in soup.find_all(True):
        if not isinstance(tag, Tag):
            continue

        itemprop = tag.get("itemprop", "")
        data_model = tag.get("data-model", "")
        data_product_model = tag.get("data-product-model", "")
        data_sku = tag.get("data-sku", "")

        attr_has_model = (
            "model" in str(itemprop).lower()
            or (data_model and data_model.strip() != "")
            or (data_product_model and data_product_model.strip() != "")
            or (data_sku and data_sku.strip() != "")
        )

        if attr_has_model:
            text = (
                tag.get("content", "")
                or data_model
                or data_product_model
                or data_sku
                or tag.get_text(strip=True)
            )

            if text and isinstance(text, str) and text.strip():
                text = text.strip()
                if text not in models and len(text) > 1:
                    models.append(text)
                    logger.debug("model_extracted", value=text, source="html_itemprop")

    return {
        "prices": prices[:10],   # at most 10 price candidates
        "brands": brands[:5],
        "models": models[:5],
    }


def _extract_jsonld_prices(block: dict, prices: list[dict]) -> None:
    """Extract price info from a JSON-LD block.

    正确处理价格为 0 的情况（使用 is not None 而非 truthy 检查）。
    """
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

                # ✅ 使用 is not None，允许价格为 0
                if raw_price is not None:
                    currency = offer.get("priceCurrency", "")
                    try:
                        price_value = float(raw_price) if isinstance(raw_price, str) else float(raw_price)
                        # ✅ 允许 0 及以上的价格，拒绝负价格
                        if price_value >= 0:
                            prices.append({
                                "raw": f"{currency} {raw_price}".strip(),
                                "value": str(price_value),
                                "currency": currency,
                                "source": "jsonld",
                            })
                            logger.debug(
                                "jsonld_price_extracted",
                                value=price_value,
                                currency=currency,
                                source="offer",
                            )
                    except (ValueError, TypeError) as exc:
                        logger.warning(
                            "jsonld_price_conversion_failed",
                            raw_price=raw_price,
                            error=str(exc),
                        )
                        continue

    # Direct price — ✅ 允许 0
    price = block.get("price")
    if price is not None and isinstance(price, (int, float, str)):
        try:
            price_value = float(price) if isinstance(price, str) else float(price)
            if price_value >= 0:
                prices.append({
                    "raw": str(price),
                    "value": str(price_value),
                    "source": "jsonld",
                })
                logger.debug("direct_price_extracted", value=price_value, source="direct")
        except (ValueError, TypeError) as exc:
            logger.warning("direct_price_conversion_failed", raw_price=price, error=str(exc))


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


def _extract_brands_from_text(page_text: str, brands: list[str]) -> None:
    """从页面文本中提取常见品牌名称（启发式方法）。

    弥补结构化标记缺失时的空白。
    """
    # 常见品牌列表（可根据业务扩展）
    common_brands = {
        "apple", "microsoft", "google", "amazon", "meta", "tesla",
        "samsung", "lg", "sony", "panasonic", "pioneer",
        "nike", "adidas", "puma", "reebok", "jordan",
        "coca-cola", "pepsi", "red-bull",
        "dell", "hp", "lenovo", "asus", "acer",
        # 中文品牌
        "华为", "小米", "oppo", "vivo", "荣耀",
        "阿里巴巴", "腾讯", "百度", "美团", "滴滴",
    }

    # 在页面文本中查找品牌提及
    page_lower = page_text.lower()
    for brand in common_brands:
        if brand in page_lower and brand not in brands:
            brands.append(brand)
            logger.debug("brand_extracted_from_text", value=brand, source="heuristic")
