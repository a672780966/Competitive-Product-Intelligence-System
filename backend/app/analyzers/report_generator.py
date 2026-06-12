"""
CPIS V1 — Markdown report templates and generators.

Produces beautiful, readable competitive intelligence reports
from structured product data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def generate_single_product_report(
    product_name: str,
    brand: str,
    model: str,
    category: str,
    source_url: str,
    structured_data: dict[str, Any],
    analysis_data: dict[str, Any],
    version_no: int,
    collected_at: datetime | None = None,
) -> str:
    """Generate a single-product Markdown brief."""
    sd = structured_data
    ad = analysis_data
    collected = (collected_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# 产品竞品简报：{product_name or '未知'}",
        "",
        "## 来源信息",
        "",
        f"- **来源链接**：{source_url}",
        f"- **采集时间**：{collected}",
        f"- **品牌**：{brand or '—'}",
        f"- **型号**：{model or '—'}",
        f"- **品类**：{category or '—'}",
        f"- **数据版本**：v{version_no}",
        "",
    ]

    # ── Page facts section ──────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## 页面事实")
    lines.append("")
    lines.append("> 以下信息直接从原始页面提取。")
    lines.append("")

    # Price
    price_text = _build_price_text(sd)
    if price_text:
        lines.append("### 价格信息")
        lines.append("")
        lines.append(price_text)
        lines.append("")

    # Core benefits
    benefits = sd.get("core_benefits", [])
    if benefits:
        lines.append("### 核心卖点")
        lines.append("")
        for b in benefits:
            lines.append(f"- {b}")
        lines.append("")

    # Features
    features = sd.get("features", [])
    if features:
        lines.append("### 主要参数 / 功能列表")
        lines.append("")
        for f in features:
            lines.append(f"- {f}")
        lines.append("")

    # Tech principles
    tech = sd.get("tech_principles", [])
    if tech:
        lines.append("### 技术原理")
        lines.append("")
        for t in tech:
            lines.append(f"- {t}")
        lines.append("")

    # Working modes
    modes = sd.get("working_modes", [])
    if modes:
        lines.append("### 工作模式")
        lines.append("")
        for m in modes:
            lines.append(f"- {m}")
        lines.append("")

    # Specs
    specs = _build_specs(sd)
    if specs:
        lines.append("### 规格参数")
        lines.append("")
        for s in specs:
            lines.append(f"- {s}")
        lines.append("")

    # Material
    material = sd.get("material", [])
    if material:
        lines.append("### 材质")
        lines.append("")
        lines.append(", ".join(material))
        lines.append("")

    # Accessories
    accessories = sd.get("accessories", [])
    if accessories:
        lines.append("### 配件")
        lines.append("")
        for a in accessories:
            lines.append(f"- {a}")
        lines.append("")

    # Package contents
    package = sd.get("package_contents", [])
    if package:
        lines.append("### 包装清单")
        lines.append("")
        for p in package:
            lines.append(f"- {p}")
        lines.append("")

    # Certifications
    certs = sd.get("certification_name", [])
    if certs:
        lines.append("### 认证信息")
        lines.append("")
        for c in certs:
            lines.append(f"- {c}")
        lines.append("")

    # Target audience
    audience = sd.get("target_audience", [])
    if audience:
        lines.append("### 目标人群")
        lines.append("")
        lines.append(", ".join(audience))
        lines.append("")

    # Use scenarios
    scenarios = sd.get("use_scenarios", [])
    if scenarios:
        lines.append("### 适用场景")
        lines.append("")
        for s in scenarios:
            lines.append(f"- {s}")
        lines.append("")

    # Pain points
    pain = sd.get("pain_points", [])
    if pain:
        lines.append("### 痛点")
        lines.append("")
        for p in pain:
            lines.append(f"- {p}")
        lines.append("")

    # Marketing angle
    marketing = sd.get("marketing_angle", [])
    if marketing:
        lines.append("### 宣传口径")
        lines.append("")
        for m in marketing:
            lines.append(f"- {m}")
        lines.append("")

    # ── AI Analysis section ─────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## AI 分析")
    lines.append("")
    lines.append("> 以下分析为 AI 基于页面内容的推断，仅供参考。")
    lines.append("")

    # Differentiators
    diff = ad.get("differentiators", [])
    if diff:
        lines.append("### 差异化卖点")
        lines.append("")
        for d in diff:
            lines.append(f"- {d}")
        lines.append("")

    # Advantages
    advantages = ad.get("advantages", [])
    if advantages:
        lines.append("### 优势")
        lines.append("")
        for a in advantages:
            lines.append(f"- {a}")
        lines.append("")

    # Disadvantages
    disadvantages = ad.get("disadvantages", [])
    if disadvantages:
        lines.append("### 劣势")
        lines.append("")
        for d in disadvantages:
            lines.append(f"- {d}")
        lines.append("")

    # Opportunities
    opportunities = ad.get("opportunities", [])
    if opportunities:
        lines.append("### 机会点")
        lines.append("")
        for o in opportunities:
            lines.append(f"- {o}")
        lines.append("")

    # Risks
    risks = ad.get("risks", [])
    if risks:
        lines.append("### 潜在风险")
        lines.append("")
        for r in risks:
            lines.append(f"- {r}")
        lines.append("")

    # Suggested actions
    actions = ad.get("suggested_actions", [])
    if actions:
        lines.append("### 建议动作")
        lines.append("")
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

    # Analysis summary
    summary = ad.get("analysis_summary")
    if summary:
        lines.append("### 分析摘要")
        lines.append("")
        lines.append(summary)
        lines.append("")

    lines.append("---")
    lines.append(f"*简报由 CPIS V1 自动生成 | {collected}*")
    lines.append("")

    return "\n".join(lines)


def generate_comparison_report(
    products: list[dict[str, Any]],
) -> str:
    """Generate a multi-product comparison Markdown report.

    Args:
        products: List of product dicts with keys:
            name, brand, model, category, price_text, source_url,
            analysis_data (dict), version_no, collected_at.
    """
    lines = [
        "# 竞品对比简报",
        "",
        f"生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"对比产品数：{len(products)}",
        "",
    ]

    if not products:
        lines.append("*暂无产品数据*")
        lines.append("")
        return "\n".join(lines)

    # Comparison table
    lines.append("## 对比产品")
    lines.append("")
    lines.append("| 产品 | 品牌 | 品类 | 价格 | 来源 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for p in products:
        lines.append(
            f"| {p.get('name', '—')} "
            f"| {p.get('brand', '—')} "
            f"| {p.get('category', '—')} "
            f"| {p.get('price_text', '—')} "
            f"| [链接]({p.get('source_url', '')}) |",
        )
    lines.append("")

    # Summary of differences
    lines.append("## 差异总结")
    lines.append("")
    categories = set()
    for p in products:
        cat = p.get("category")
        if cat:
            categories.add(cat)
    if categories:
        lines.append(f"覆盖品类：{', '.join(sorted(categories))}")

    all_advantages: list[str] = []
    all_risks: list[str] = []
    all_actions: list[str] = []

    for p in products:
        ad = p.get("analysis_data", {})
        all_advantages.extend(ad.get("advantages", []))
        all_risks.extend(ad.get("risks", []))
        all_actions.extend(ad.get("suggested_actions", []))

    if all_advantages:
        lines.append("")
        lines.append("### 综合优势")
        lines.append("")
        for a in _dedup(all_advantages):
            lines.append(f"- {a}")

    lines.append("")

    # Opportunities across products
    all_opportunities: list[str] = []
    for p in products:
        all_opportunities.extend(p.get("analysis_data", {}).get("opportunities", []))
    if all_opportunities:
        lines.append("## 机会点")
        lines.append("")
        for o in _dedup(all_opportunities):
            lines.append(f"- {o}")
        lines.append("")

    # Risks
    if all_risks:
        lines.append("## 风险提示")
        lines.append("")
        for r in _dedup(all_risks):
            lines.append(f"- ⚠️ {r}")
        lines.append("")

    # Suggested actions
    if all_actions:
        lines.append("## 建议动作")
        lines.append("")
        for a in _dedup(all_actions):
            lines.append(f"- **{a}**")
        lines.append("")

    lines.append("---")
    lines.append("*对比简报由 CPIS V1 自动生成*")
    lines.append("")

    return "\n".join(lines)


# ── Helpers ─────────────────────────────────────────────────────


def _build_price_text(sd: dict) -> str:
    parts = []
    currency = sd.get("currency", "")
    orig = sd.get("original_price", "")
    sale = sd.get("sale_price", "")
    if orig:
        parts.append(f"原价：{currency}{orig}" if currency else f"原价：{orig}")
    if sale:
        parts.append(f"促销价：{currency}{sale}" if currency else f"促销价：{sale}")
    pt = sd.get("price_text", "")
    if pt and pt not in parts:
        parts.append(pt)
    return " | ".join(parts)


def _build_specs(sd: dict) -> list[str]:
    specs = []
    for key, label in [
        ("power", "功率"), ("frequency", "频率"), ("intensity", "强度"),
        ("dimensions", "尺寸"), ("weight", "重量"),
        ("battery", "电池"), ("charging_method", "充电方式"),
        ("levels", "档位"),
    ]:
        val = sd.get(key)
        if val:
            specs.append(f"{label}: {val}")
    return specs


def _dedup(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result
