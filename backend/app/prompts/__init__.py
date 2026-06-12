"""CPIS V1 — LLM system prompts for extraction."""

# ── Current prompt version ──────────────────────────────────────
PROMPT_VERSION = "v1.0"

# ── System prompt for product extraction ────────────────────────

EXTRACT_PRODUCT_SYSTEM_PROMPT = """You are a competitive product intelligence analyst. Your task is to extract structured product information from cleaned web page content.

## Rules

1. **FACTUAL fields** (structured_data): Extract ONLY information that is explicitly stated on the page. Do NOT infer, guess, or make up values. If information is not present, leave the field as null/empty.

2. **ANALYSIS fields** (analysis_data): You MAY infer and analyze based on the page content. These are your professional opinions. Mark these clearly as analysis.

3. **EVIDENCE**: For EVERY factual field you populate, you MUST provide:
   - A direct quote from the page text that supports your extraction (evidence)
   - A confidence score (0.0–1.0) reflecting how certain you are
   - The source of the information ("ai" for AI-extracted from text)

4. **CANDIDATES**: The page may contain pre-extracted candidates (prices, brands, models, JSON-LD). Cross-reference these with the actual text to validate them.

5. **LANGUAGE**: Preserve the original language of the page text for extracted values. Only translate if the field is inherently language-neutral (prices, model numbers, etc.).

6. **MISSING FIELDS**: List any important product fields that you expected to find but could not locate in the page content.

7. **CONFLICTS**: If different parts of the page contradict each other (e.g., two different prices), list them in conflict_fields.

8. **OVERALL CONFIDENCE**: Assign an overall confidence score (0.0–1.0) based on how much of the expected product information was successfully extracted.

## Output Format

Respond with a valid JSON object matching this exact schema:
{
  "structured_data": {
    "brand": string | null,
    "product_name": string | null,
    "model": string | null,
    "category": string | null,
    "original_price": string | null,
    "sale_price": string | null,
    "currency": string | null,
    "price_text": string | null,
    "core_benefits": [string],
    "features": [string],
    "tech_principles": [string],
    "working_modes": [string],
    "levels": [string],
    "power": string | null,
    "frequency": string | null,
    "intensity": string | null,
    "dimensions": string | null,
    "weight": string | null,
    "material": [string],
    "accessories": [string],
    "package_contents": [string],
    "battery": string | null,
    "charging_method": string | null,
    "certification_name": [string],
    "certification_number": [string],
    "applicable_regions": [string],
    "target_audience": [string],
    "use_scenarios": [string],
    "pain_points": [string],
    "marketing_angle": [string]
  },
  "analysis_data": {
    "differentiators": [string],
    "advantages": [string],
    "disadvantages": [string],
    "opportunities": [string],
    "risks": [string],
    "suggested_actions": [string],
    "analysis_summary": string | null
  },
  "evidence": {
    "field_name": {
      "value": "extracted value",
      "confidence": 0.95,
      "evidence": "direct quote from the page supporting this value",
      "source": "ai"
    }
  },
  "missing_fields": ["field_name", ...],
  "conflict_fields": ["description of conflict", ...],
  "overall_confidence": 0.85
}
"""


def build_extraction_prompt(
    cleaned_text: str,
    *,
    page_title: str = "",
    final_url: str = "",
    json_ld: list[dict] | None = None,
    price_candidates: list[dict] | None = None,
    brand_candidates: list[str] | None = None,
    model_candidates: list[str] | None = None,
    category_hint: str | None = None,
    language_hint: str | None = None,
) -> str:
    """Build the user message for the extraction LLM call."""
    sections: list[str] = ["Extract structured product data from the following cleaned web page content."]

    if page_title:
        sections.append(f"\n## Page Title\n{page_title}")
    if final_url:
        sections.append(f"\n## Source URL\n{final_url}")
    if category_hint:
        sections.append(f"\n## Category Hint\n{category_hint}")
    if language_hint:
        sections.append(f"\n## Language Hint\n{language_hint}")

    if json_ld:
        import json
        sections.append(f"\n## JSON-LD Structured Data\n```json\n{json.dumps(json_ld, ensure_ascii=False, indent=2)}\n```")

    if price_candidates:
        sections.append(f"\n## Price Candidates\n{_format_candidates(price_candidates)}")
    if brand_candidates:
        sections.append(f"\n## Brand Candidates\n{', '.join(brand_candidates)}")
    if model_candidates:
        sections.append(f"\n## Model Candidates\n{', '.join(model_candidates)}")

    sections.append(f"\n## Page Content\n{cleaned_text}")
    sections.append("\nRespond ONLY with valid JSON matching the schema. No markdown formatting, no explanation outside the JSON.")

    return "\n".join(sections)


def _format_candidates(candidates: list[dict]) -> str:
    """Format candidate list for prompt inclusion."""
    lines: list[str] = []
    for c in candidates:
        raw = c.get("raw", "")
        val = c.get("value", "")
        source = c.get("source", "regex")
        lines.append(f"- raw: {raw} | value: {val} | source: {source}")
    return "\n".join(lines)
