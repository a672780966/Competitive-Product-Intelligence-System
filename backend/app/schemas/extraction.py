"""CPIS V1 — Extraction schemas: structured output from AI extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Factual fields (extracted from page content) ────────────────


class ProductFactFields(BaseModel):
    """Factual fields directly extracted from page content.

    AI must NOT infer or guess these — they must come from the page.
    """

    brand: str | None = None
    product_name: str | None = None
    model: str | None = None
    category: str | None = None
    original_price: str | None = None
    sale_price: str | None = None
    currency: str | None = None
    price_text: str | None = None
    core_benefits: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    tech_principles: list[str] = Field(default_factory=list)
    working_modes: list[str] = Field(default_factory=list)
    levels: list[str] = Field(default_factory=list)
    power: str | None = None
    frequency: str | None = None
    intensity: str | None = None
    dimensions: str | None = None
    weight: str | None = None
    material: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    package_contents: list[str] = Field(default_factory=list)
    battery: str | None = None
    charging_method: str | None = None
    certification_name: list[str] = Field(default_factory=list)
    certification_number: list[str] = Field(default_factory=list)
    applicable_regions: list[str] = Field(default_factory=list)
    target_audience: list[str] = Field(default_factory=list)
    use_scenarios: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    marketing_angle: list[str] = Field(default_factory=list)


# ── Analysis fields (AI-inferred) ───────────────────────────────


class ProductAnalysisFields(BaseModel):
    """Inferred/analytic fields — AI judgement, not direct page facts."""

    differentiators: list[str] = Field(default_factory=list)
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    analysis_summary: str | None = None


# ── Per-field evidence & confidence ─────────────────────────────


class FieldEvidence(BaseModel):
    """Evidence and confidence for one extracted field."""

    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str = ""
    source: str = "ai"  # "ai" | "jsonld" | "candidate" | "heuristic"


# ── Full extraction output ──────────────────────────────────────


class ExtractionResult(BaseModel):
    """Complete output of the AI extraction pipeline."""

    structured_data: ProductFactFields = Field(default_factory=ProductFactFields)
    analysis_data: ProductAnalysisFields = Field(default_factory=ProductAnalysisFields)
    evidence: dict[str, FieldEvidence] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    conflict_fields: list[str] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ai_model: str = ""
    prompt_version: str = ""


# ── Input for the extraction pipeline ───────────────────────────


class ExtractionInput(BaseModel):
    """All data fed into the AI extraction."""

    page_title: str = ""
    final_url: str = ""
    cleaned_text: str = ""
    cleaned_markdown: str = ""
    json_ld_data: list[dict] = Field(default_factory=list)
    open_graph_data: dict = Field(default_factory=dict)
    price_candidates: list[dict] = Field(default_factory=list)
    brand_candidates: list[str] = Field(default_factory=list)
    model_candidates: list[str] = Field(default_factory=list)
    category_hint: str | None = None
    language_hint: str | None = None
