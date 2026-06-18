"""
CPIS V1 — AI 结构化抽取测试

Tests:
- Extraction schema validation
- Prompt building
- LLM response parsing
- Full extraction pipeline (mocked LLM)
- Confidence / evidence tracking
"""

from __future__ import annotations

import json

import pytest

from app.extractors.product_extractor import ProductExtractor
from app.prompts import EXTRACT_PRODUCT_SYSTEM_PROMPT, build_extraction_prompt
from app.schemas.extraction import (
    ExtractionInput,
    ExtractionResult,
    FieldEvidence,
    ProductAnalysisFields,
    ProductFactFields,
)

# ══════════════════════════════════════════════════════════════════
# Schema tests
# ══════════════════════════════════════════════════════════════════


class TestExtractionSchemas:
    def test_fact_fields_defaults(self):
        f = ProductFactFields()
        assert f.brand is None
        assert f.features == []
        assert f.core_benefits == []

    def test_analysis_fields_defaults(self):
        a = ProductAnalysisFields()
        assert a.advantages == []
        assert a.analysis_summary is None

    def test_field_evidence_validation(self):
        ev = FieldEvidence(value="Apple", confidence=0.95, evidence="From title tag")
        assert ev.confidence == 0.95
        assert ev.source == "ai"

    def test_field_evidence_clamps_confidence(self):
        with pytest.raises(ValueError):
            FieldEvidence(value="x", confidence=1.5, evidence="")

    def test_extraction_input_defaults(self):
        inp = ExtractionInput(cleaned_text="Some text")
        assert inp.cleaned_text == "Some text"
        assert inp.json_ld_data == []
        assert inp.price_candidates == []

    def test_extraction_result_defaults(self):
        r = ExtractionResult()
        assert r.overall_confidence == 0.0
        assert r.missing_fields == []
        assert r.evidence == {}


# ══════════════════════════════════════════════════════════════════
# Prompt building
# ══════════════════════════════════════════════════════════════════


class TestPromptBuilding:
    def test_basic_prompt_contains_content(self):
        prompt = build_extraction_prompt("Product description here")
        assert "Product description here" in prompt
        assert "Page Content" in prompt

    def test_prompt_includes_title_and_url(self):
        prompt = build_extraction_prompt(
            "text",
            page_title="SmartWatch Pro",
            final_url="https://example.com/product",
        )
        assert "SmartWatch Pro" in prompt
        assert "example.com" in prompt

    def test_prompt_includes_candidates(self):
        prompt = build_extraction_prompt(
            "text",
            price_candidates=[{"raw": "$299", "value": "299", "source": "regex"}],
            brand_candidates=["TechCorp"],
            model_candidates=["X200"],
        )
        assert "$299" in prompt
        assert "TechCorp" in prompt
        assert "X200" in prompt

    def test_prompt_includes_jsonld(self):
        prompt = build_extraction_prompt(
            "text",
            json_ld=[{"@type": "Product", "name": "Test"}],
        )
        assert '"Product"' in prompt
        assert '"Test"' in prompt

    def test_prompt_includes_hints(self):
        prompt = build_extraction_prompt(
            "text",
            category_hint="smartwatch",
            language_hint="en",
        )
        assert "smartwatch" in prompt
        assert "en" in prompt

    def test_system_prompt_has_instructions(self):
        assert "structured_data" in EXTRACT_PRODUCT_SYSTEM_PROMPT
        assert "analysis_data" in EXTRACT_PRODUCT_SYSTEM_PROMPT
        assert "overall_confidence" in EXTRACT_PRODUCT_SYSTEM_PROMPT


# ══════════════════════════════════════════════════════════════════
# LLM response parsing
# ══════════════════════════════════════════════════════════════════


class _MockProvider:
    """Mock AI provider returning a canned JSON response."""

    def __init__(self, response_json: dict | str, model: str = "mock-model"):
        self._response = json.dumps(response_json) if isinstance(response_json, dict) else response_json
        self.model = model

    async def chat(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        return self._response


class TestLlmResponseParsing:
    @pytest.mark.asyncio
    async def test_parse_valid_json(self):
        """Valid JSON response produces a successful ExtractionResult."""
        provider = _MockProvider({
            "structured_data": {"brand": "Apple", "product_name": "iPhone 15 Pro"},
            "analysis_data": {"analysis_summary": "Premium smartphone"},
            "evidence": {
                "brand": {"value": "Apple", "confidence": 0.98, "evidence": "From page title"},
            },
            "missing_fields": ["model"],
            "conflict_fields": [],
            "overall_confidence": 0.85,
        })
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="iPhone 15 Pro details")
        result = await extractor.extract(inp)

        assert result.structured_data.brand == "Apple"
        assert result.structured_data.product_name == "iPhone 15 Pro"
        assert result.analysis_data.analysis_summary == "Premium smartphone"
        assert result.overall_confidence == 0.85
        assert "model" in result.missing_fields
        assert result.ai_model == "mock-model"

    @pytest.mark.asyncio
    async def test_parse_with_markdown_code_fence(self):
        """LLM response wrapped in ```json is handled correctly."""
        provider = _MockProvider("""```json
{
  "structured_data": {"brand": "Samsung"},
  "analysis_data": {},
  "evidence": {},
  "missing_fields": [],
  "conflict_fields": [],
  "overall_confidence": 0.9
}
```""")
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="Samsung TV")
        result = await extractor.extract(inp)
        assert result.structured_data.brand == "Samsung"
        assert result.overall_confidence == 0.9

    @pytest.mark.asyncio
    async def test_parse_with_extra_text(self):
        """LLM response with text before/after JSON is handled."""
        provider = _MockProvider("""Here's my analysis:
```json
{"structured_data": {"brand": "LG"}, "analysis_data": {}, "evidence": {}, "missing_fields": [], "conflict_fields": [], "overall_confidence": 0.8}
```
Hope this helps!""")
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="LG TV")
        result = await extractor.extract(inp)
        assert result.structured_data.brand == "LG"

    @pytest.mark.asyncio
    async def test_parse_invalid_json_falls_back(self):
        """Unparseable LLM response returns empty result with zero confidence."""
        provider = _MockProvider("This is not JSON at all")
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="whatever")
        result = await extractor.extract(inp)
        assert result.overall_confidence == 0.0
        assert "unparseable" in str(result.missing_fields[0])

    @pytest.mark.asyncio
    async def test_parse_empty_response(self):
        """Empty LLM response returns empty result."""
        provider = _MockProvider("")
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="whatever")
        result = await extractor.extract(inp)
        assert result.overall_confidence == 0.0

    @pytest.mark.asyncio
    async def test_low_confidence_added_to_missing(self):
        """Fields below 0.7 confidence are added to missing_fields."""
        provider = _MockProvider({
            "structured_data": {"brand": "Unknown"},
            "analysis_data": {},
            "evidence": {
                "brand": {"value": "Unknown", "confidence": 0.3, "evidence": "Weak signal"},
            },
            "missing_fields": [],
            "conflict_fields": [],
            "overall_confidence": 0.5,
        })
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="product page")
        result = await extractor.extract(inp)

        # brand was extracted but with low confidence → should be in missing_fields
        # Actually the field IS in evidence but with low confidence.
        # The logic adds ev field names with <0.7 to missing
        assert "brand" in result.missing_fields  # low confidence

    @pytest.mark.asyncio
    async def test_all_fields_populated(self):
        """Full extraction with all field types works."""
        provider = _MockProvider({
            "structured_data": {
                "brand": "TechCorp",
                "product_name": "SmartPro X200",
                "model": "SP-X200",
                "category": "smartwatch",
                "original_price": "349.99",
                "sale_price": "299.99",
                "currency": "USD",
                "core_benefits": ["24h battery", "Water resistant"],
                "features": ["AMOLED display", "GPS", "Heart rate monitor"],
                "tech_principles": ["Optical heart sensing"],
                "working_modes": ["Sport mode", "Sleep tracking"],
                "power": "5V 1A",
                "weight": "45g",
                "material": ["Titanium", "Silicone"],
                "battery": "300mAh",
                "charging_method": "Wireless charging",
                "certification_name": ["CE", "FCC"],
            },
            "analysis_data": {
                "differentiators": ["Longer battery life than competitors"],
                "advantages": ["Better display", "More accurate GPS"],
                "disadvantages": ["No cellular version"],
                "analysis_summary": "Competitive mid-range smartwatch.",
            },
            "evidence": {
                "brand": {"value": "TechCorp", "confidence": 0.99, "evidence": "Header logo text"},
                "product_name": {"value": "SmartPro X200", "confidence": 0.95, "evidence": "H1 title"},
            },
            "missing_fields": ["intensity"],
            "conflict_fields": [],
            "overall_confidence": 0.88,
        })
        extractor = ProductExtractor(provider=provider)
        inp = ExtractionInput(cleaned_text="SmartPro X200 page content")
        result = await extractor.extract(inp)

        assert result.structured_data.brand == "TechCorp"
        assert result.structured_data.model == "SP-X200"
        assert result.structured_data.original_price == "349.99"
        assert len(result.structured_data.features) == 3
        assert result.structured_data.charging_method == "Wireless charging"
        assert result.analysis_data.analysis_summary is not None
        assert len(result.analysis_data.differentiators) == 1
        assert len(result.evidence) == 2
        assert result.overall_confidence == 0.88
