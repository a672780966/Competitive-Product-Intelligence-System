"""
CPIS V1 — Feishu Bitable field mapping.

Maps CPIS structured product fields to Feishu column names.
Each column name corresponds to a field in the Feishu multi-dimensional table.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_feishu_record(
    structured_data: dict[str, Any],
    analysis_data: dict[str, Any],
    unique_key: str,
    version_no: int,
    source_url: str,
    collected_at: datetime | None = None,
) -> dict:
    """Build a Feishu record dict from CPIS product data.

    Keys are the Feishu column names (configured in the Bitable).
    Values are the data to write.

    Args:
        collected_at: Optional timestamp. If provided, included in the record.
    """
    sd = structured_data
    ad = analysis_data

    # Helper: join list fields into a string
    def _join(items: list | None, sep: str = "\n") -> str:
        if not items:
            return ""
        return sep.join(str(x) for x in items if x)

    return {
        "唯一标识": unique_key,
        "产品名称": sd.get("product_name") or "",
        "品牌": sd.get("brand") or "",
        "型号": sd.get("model") or "",
        "产品类别": sd.get("category") or "",
        "来源链接": source_url,
        "价格信息": _build_price_text(sd),
        "核心卖点": _join(sd.get("core_benefits")),
        # ✅ 修复 #11：主要参数使用 specs，功能列表使用 analysis data
        "主要参数": _build_specs(sd),
        "功能列表": _build_features(ad),
        "技术原理": _join(sd.get("tech_principles")),
        "工作模式": _join(sd.get("working_modes")),
        "材质": _join(sd.get("material")),
        "配件清单": _join(sd.get("accessories")),
        "包装清单": _join(sd.get("package_contents")),
        "电池": sd.get("battery") or "",
        "充电方式": sd.get("charging_method") or "",
        "认证信息": _join(sd.get("certification_name")),
        "目标市场": _join(sd.get("applicable_regions")),
        "目标人群": _join(sd.get("target_audience")),
        "适用场景": _join(sd.get("use_scenarios")),
        "痛点": _join(sd.get("pain_points")),
        "宣传口径": _join(sd.get("marketing_angle")),
        "差异化卖点": _join(ad.get("differentiators")),
        "优势": _join(ad.get("advantages")),
        "劣势": _join(ad.get("disadvantages")),
        "机会点": _join(ad.get("opportunities")),
        "风险": _join(ad.get("risks")),
        "建议动作": _join(ad.get("suggested_actions")),
        "分析摘要": ad.get("analysis_summary") or "",
        "数据版本": f"v{version_no}",
        # ✅ 修复 #10：传入正确的采集时间
        "最后采集时间": collected_at.isoformat() if isinstance(collected_at, datetime) else (collected_at or ""),
    }


def _build_price_text(sd: dict) -> str:
    """Build a readable price string."""
    parts = []
    currency = sd.get("currency", "")
    orig = sd.get("original_price", "")
    sale = sd.get("sale_price", "")

    if orig:
        parts.append(f"原价: {currency}{orig}" if currency else f"原价: {orig}")
    if sale:
        parts.append(f"促销: {currency}{sale}" if currency else f"促销: {sale}")
    pt = sd.get("price_text", "")
    if pt and pt not in parts:
        parts.append(pt)

    return " | ".join(parts)


def _build_specs(sd: dict) -> str:
    """Build a multi-line specs string."""
    specs = []
    for key, label in [
        ("power", "功率"), ("frequency", "频率"), ("intensity", "强度"),
        ("dimensions", "尺寸"), ("weight", "重量"),
    ]:
        val = sd.get(key)
        if val:
            specs.append(f"{label}: {val}")
    return "\n".join(specs)


def _build_features(ad: dict) -> str:
    """Build features string from analysis data."""
    features = ad.get("features", [])
    if isinstance(features, list):
        return "\n".join(str(f) for f in features if f)
    return str(features) if features else ""
