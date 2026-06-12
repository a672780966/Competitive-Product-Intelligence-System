"""
CPIS V1 — ProductExtractor: AI-powered structured product extraction.

Pipeline:
1. Build extraction input from cleaned page data + candidates
2. Call LLM with system prompt + user message
3. Parse and validate the JSON response against Pydantic schemas
4. On parse failure, attempt one fix-up re-prompt
5. Return ExtractionResult with structured_data, analysis_data, evidence
"""

from __future__ import annotations

import json
from typing import Any

from app.core import get_settings
from app.core.logging import get_logger
from app.extractors.ai_provider import AIProvider, AIProviderError, create_provider
from app.prompts import (
    EXTRACT_PRODUCT_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_extraction_prompt,
)
from app.schemas.extraction import (
    ExtractionInput,
    ExtractionResult,
    FieldEvidence,
    ProductAnalysisFields,
    ProductFactFields,
)

logger = get_logger(__name__)

_CONFIDENCE_THRESHOLD = 0.7


class ExtractionParseError(Exception):
    """Raised when the LLM output cannot be parsed."""
    pass


class ProductExtractor:
    """Orchestrates AI-powered product data extraction."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or create_provider()

    async def extract(self, inp: ExtractionInput) -> ExtractionResult:
        """Run the full extraction pipeline.

        Args:
            inp: All extracted page data (cleaned text, candidates, etc.).

        Returns:
            An ExtractionResult with structured data and analysis.
        """
        settings = get_settings()

        # 1. Build prompt
        user_prompt = build_extraction_prompt(
            cleaned_text=inp.cleaned_text,
            page_title=inp.page_title,
            final_url=inp.final_url,
            json_ld=inp.json_ld_data,
            price_candidates=inp.price_candidates,
            brand_candidates=inp.brand_candidates,
            model_candidates=inp.model_candidates,
            category_hint=inp.category_hint,
            language_hint=inp.language_hint,
        )

        # 2. Call LLM
        try:
            raw = await self._provider.chat(
                system_prompt=EXTRACT_PRODUCT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except AIProviderError as exc:
            logger.error("extraction_llm_error", error=str(exc))
            return ExtractionResult(
                overall_confidence=0.0,
                ai_model=self._provider.model,
                prompt_version=PROMPT_VERSION,
                missing_fields=["All — LLM call failed"],
            )

        # 3. Parse JSON
        parsed = await self._parse_llm_response(raw)
        if parsed is None:
            # Fallback: return what we can
            return ExtractionResult(
                overall_confidence=0.0,
                ai_model=self._provider.model,
                prompt_version=PROMPT_VERSION,
                missing_fields=["All — LLM response unparseable"],
            )

        # 4. Build result from parsed data
        structured = ProductFactFields(**parsed.get("structured_data", {}))
        analysis = ProductAnalysisFields(**parsed.get("analysis_data", {}))

        evidence_raw = parsed.get("evidence", {})
        evidence: dict[str, FieldEvidence] = {}
        for field_name, ev in evidence_raw.items():
            if isinstance(ev, dict):
                evidence[field_name] = FieldEvidence(
                    value=str(ev.get("value", "")),
                    confidence=float(ev.get("confidence", 0.0)),
                    evidence=str(ev.get("evidence", "")),
                    source=str(ev.get("source", "ai")),
                )

        overall_confidence = float(parsed.get("overall_confidence", 0.0))
        missing = parsed.get("missing_fields", [])
        conflicts = parsed.get("conflict_fields", [])

        # 5. Determine if human review is needed
        low_conf_fields = [
            name for name, ev in evidence.items()
            if ev.confidence < _CONFIDENCE_THRESHOLD
        ]

        result = ExtractionResult(
            structured_data=structured,
            analysis_data=analysis,
            evidence=evidence,
            missing_fields=missing + low_conf_fields,
            conflict_fields=conflicts,
            overall_confidence=overall_confidence,
            ai_model=self._provider.model,
            prompt_version=PROMPT_VERSION,
        )

        logger.info(
            "extraction_complete",
            overall_confidence=overall_confidence,
            missing_count=len(result.missing_fields),
            conflict_count=len(result.conflict_fields),
            evidence_count=len(result.evidence),
        )

        return result

    async def _parse_llm_response(self, raw: str) -> dict[str, Any] | None:
        """Parse JSON from the LLM response, with one retry on failure.

        Handles common formatting issues: markdown code fences, leading/trailing text.
        """
        cleaned = raw.strip()

        # Strip markdown code fences if present
        if cleaned.startswith("```"):
            # Remove first and last ```
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            end_idx = cleaned.rfind("```")
            if end_idx >= 0:
                cleaned = cleaned[:end_idx]
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in the response
            try:
                start = cleaned.index("{")
                end = cleaned.rindex("}") + 1
                cleaned = cleaned[start:end]
                data = json.loads(cleaned)
            except (ValueError, json.JSONDecodeError):
                logger.error("json_parse_failed", snippet=cleaned[:200])
                return None

        # Validate structural presence
        if not isinstance(data, dict):
            return None

        return data
