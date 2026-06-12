"""
CPIS V1 — Product versioning service.

Orchestrates product creation and version management after AI extraction.

Pipeline:
1. Generate unique_key (domain + brand + model, or URL hash)
2. Find or create Product by unique_key
3. Compare content_hash with latest version → skip if unchanged
4. Create ProductVersion with structured + analysis data
5. Save per-field ProductEvidence records
6. Set review_status (auto_approved if confidence >= 0.7)
7. Update product.current_version_id (only if auto-approved)
"""

from __future__ import annotations

import hashlib
import uuid
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import Product, ProductEvidence, ProductVersion
from app.models.enums import ReviewStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.extraction import ExtractionResult
from app.schemas.task import TaskResponse

logger = get_logger(__name__)

_CONFIDENCE_AUTO_APPROVE = 0.7


class ProductVersioningError(Exception):
    """Raised when product versioning fails."""
    pass


class ProductVersioningService:
    """Service for product creation and version management."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ProductRepository(db)

    async def process_extraction(
        self,
        extraction: ExtractionResult,
        task: TaskResponse,
        snapshot_id: uuid.UUID | None = None,
    ) -> Product:
        """Process an extraction result into product + version + evidences.

        Args:
            extraction: The AI extraction result.
            task: The collection task that produced this extraction.
            snapshot_id: Optional source_snapshot.id for provenance.

        Returns:
            The Product record (created or updated).
        """
        # 1. Generate unique key
        domain = task.domain or _extract_domain(task.source_url)
        brand = extraction.structured_data.brand or ""
        model = extraction.structured_data.model or ""
        unique_key = _make_unique_key(domain, brand, model, task.source_url)

        # 2. Find or create product
        product = await self._repo.get_by_unique_key(unique_key)
        is_new = product is None

        if is_new:
            product = Product(
                unique_key=unique_key,
                brand=extraction.structured_data.brand,
                name=extraction.structured_data.product_name,
                model=extraction.structured_data.model,
                category=_resolve_category(
                    extraction.structured_data.category,
                    task.category_hint,
                ),
                source_url=task.normalized_url or task.source_url,
                review_status=ReviewStatus.PENDING,
            )
            product = await self._repo.create(product)
            logger.info("product_created", product_id=str(product.id), unique_key=unique_key)
        else:
            logger.info(
                "product_found",
                product_id=str(product.id),
                unique_key=unique_key,
            )

        # 3. Check content_hash to decide whether to create a new version
        latest = await self._repo.get_latest_version(product.id)

        # Use the extraction overall confidence + evidence to decide
        content_changed = _content_changed(latest, extraction, task)

        if not content_changed and latest is not None:
            logger.info(
                "version_skipped_no_change",
                product_id=str(product.id),
                latest_version=latest.version_no,
            )
            return product

        # 4. Determine version number
        version_no = (latest.version_no + 1) if latest else 1

        # 5. Create product version
        version = ProductVersion(
            product_id=product.id,
            version_no=version_no,
            source_snapshot_id=snapshot_id,
            structured_data=extraction.structured_data.model_dump(),
            analysis_data=extraction.analysis_data.model_dump(),
            ai_model=extraction.ai_model,
            prompt_version=extraction.prompt_version,
            overall_confidence=extraction.overall_confidence,
        )
        version = await self._repo.create_version(version)
        logger.info(
            "version_created",
            product_id=str(product.id),
            version_no=version_no,
            confidence=extraction.overall_confidence,
        )

        # 6. Save per-field evidences
        evidences: list[ProductEvidence] = []
        for field_name, ev in extraction.evidence.items():
            evidence = ProductEvidence(
                product_version_id=version.id,
                field_name=field_name,
                value=ev.value[:2048] if ev.value else None,
                confidence=ev.confidence,
                evidence_text=ev.evidence[:4096] if ev.evidence else None,
                evidence_source=task.source_url,
            )
            evidences.append(evidence)

        if evidences:
            await self._repo.batch_save_evidence(evidences)

        # 7. Determine review status
        if extraction.overall_confidence >= _CONFIDENCE_AUTO_APPROVE and not extraction.missing_fields:
            review_status = ReviewStatus.AUTO_APPROVED
            await self._repo.set_current_version(product.id, version.id)
        elif extraction.overall_confidence >= _CONFIDENCE_AUTO_APPROVE:
            # Has missing_fields — human must review before becoming current
            review_status = ReviewStatus.NEEDS_REVIEW
        else:
            review_status = ReviewStatus.NEEDS_REVIEW
            # Don't set current_version until reviewed

        await self._repo.update_review_status(product.id, review_status)
        logger.info(
            "product_review_status",
            product_id=str(product.id),
            status=review_status.value,
        )

        return product


# ── Internal helpers ────────────────────────────────────────────


def _make_unique_key(domain: str, brand: str, model: str, fallback_url: str) -> str:
    """Generate a deterministic unique key.

    Preferred: domain + brand + model (normalized)
    Fallback: SHA-256 of the source URL
    """
    brand_clean = brand.strip().lower().replace(" ", "-") if brand else ""
    model_clean = model.strip().lower().replace(" ", "-") if model else ""
    domain_clean = domain.strip().lower().replace("www.", "")

    if brand_clean and model_clean:
        return f"{domain_clean}/{brand_clean}/{model_clean}"

    if brand_clean:
        return f"{domain_clean}/{brand_clean}"

    # Fallback: URL hash
    url_hash = hashlib.sha256(fallback_url.encode("utf-8")).hexdigest()[:16]
    return f"{domain_clean}/url-{url_hash}"


def _extract_domain(url: str) -> str:
    """Extract domain from URL, removing www."""
    try:
        return (urlparse(url).hostname or "unknown").replace("www.", "")
    except Exception:
        return "unknown"


def _resolve_category(
    extracted_category: str | None,
    hint: str | None,
) -> str | None:
    """Resolve product category — prefer extracted, fall back to hint."""
    category = extracted_category or hint
    return category.lower() if category else None


def _content_changed(
    latest_version: ProductVersion | None,
    extraction: ExtractionResult,
    task: TaskResponse,
) -> bool:
    """Determine if the content has changed compared to the latest version.

    Returns True if there's no previous version, or if content has changed.
    """
    if latest_version is None:
        return True

    # Compare structured data hashes
    old_data = latest_version.structured_data or {}
    new_data = extraction.structured_data.model_dump() if extraction.structured_data else {}

    # Simple heuristic: compare brand + name + model from structured_data
    for key in ("brand", "product_name", "model"):
        old_val = old_data.get(key)
        new_val = new_data.get(key)
        if old_val != new_val:
            return True

    # Confidence change threshold: big drop/rise
    old_conf = latest_version.overall_confidence or 0.0
    new_conf = extraction.overall_confidence or 0.0
    if abs(new_conf - old_conf) > 0.3:
        return True

    return False
