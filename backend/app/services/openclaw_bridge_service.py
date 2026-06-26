"""
CPIS V1 — OpenClaw bridge service.

Ingests evidence_batch JSON from OpenClaw collector agent and persists as
CollectionTask + SourceSnapshot + Product/ProductVersion records.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import CollectionTask, SourceSnapshot, Product, ProductVersion
from app.models.enums import TaskStatus, TaskPriority, ReviewStatus
from app.repositories.task_repository import TaskRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.openclaw import (
    EvidenceBatch,
    EvidenceItem,
    IngestedItem,
    OpenClawEvidenceRequest,
    OpenClawEvidenceResponse,
)

logger = get_logger(__name__)


class OpenClawBridgeService:
    """Service to ingest OpenClaw evidence into CPIS data model."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._task_repo = TaskRepository(db)
        self._product_repo = ProductRepository(db)

    async def ingest_evidence(
        self,
        request: OpenClawEvidenceRequest,
    ) -> OpenClawEvidenceResponse:
        """Ingest an evidence_batch from OpenClaw.

        For each item in the batch:
        1. Create a CollectionTask (COMPLETED, since OpenClaw already collected)
        2. Create SourceSnapshot with evidence data
        3. Find or create Product + ProductVersion
        4. Record TaskEvent at each stage
        """
        batch: EvidenceBatch = request.payload
        run_id = request.run_id
        ingested_items: list[IngestedItem] = []
        errors: list[str] = []

        for item in batch.items:
            try:
                result = await self._ingest_item(item, run_id, batch.sources)
                ingested_items.append(result)
            except Exception as exc:
                logger.error(
                    "openclaw_ingest_item_failed",
                    item_id=item.item_id,
                    error=str(exc),
                )
                ingested_items.append(IngestedItem(
                    item_id=item.item_id,
                    task_id=uuid.uuid4(),
                    status="failed",
                    error=str(exc),
                ))
                errors.append(f"item {item.item_id}: {exc}")

        status = "partial" if errors else "success"
        if ingested_items and all(i.status == "failed" for i in ingested_items):
            status = "failed"

        return OpenClawEvidenceResponse(
            run_id=run_id,
            status=status,
            ingested=sum(1 for i in ingested_items if i.status == "success"),
            items=ingested_items,
            errors=errors,
        )

    async def _ingest_item(
        self,
        item: EvidenceItem,
        run_id: str,
        sources: list | None = None,
    ) -> IngestedItem:
        """Ingest a single evidence item."""
        source_url = item.product_url
        domain = self._extract_domain(source_url)

        # 1. Create CollectionTask (COMPLETED - data already collected)
        task = CollectionTask(
            source_url=source_url,
            normalized_url=source_url,
            domain=domain,
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.NORMAL,
            category_hint=item.category,
            auto_sync_feishu=False,
            created_by="openclaw-bridge",
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
        )
        task = await self._task_repo.create(task)
        logger.info("openclaw_task_created", task_id=str(task.id), url=source_url)

        # Record creation event
        await self._task_repo.create_event(
            task_id=task.id,
            stage="openclaw_ingest",
            status=TaskStatus.COMPLETED,
            message=f"Ingested from OpenClaw evidence batch {run_id}",
        )

        # 2. Build structured data from evidence item
        pricing = item.pricing or {}
        ratings = item.ratings or {}

        structured_data = {
            "product_name": item.product_name,
            "brand": item.brand,
            "asin": item.asin,
            "model": None,
            "category": item.category,
            "pricing": pricing,
            "ratings": ratings,
            "ranking_type": item.ranking_type,
            "ranking_position": item.ranking_position,
            "image_url": item.image_url,
            "description": item.description,
            "source": domain,
        }

        # Determine confidence (0.7 if complete, lower if missing fields)
        missing = []
        if not item.product_name:
            missing.append("product_name")
        if not item.brand:
            missing.append("brand")
        if not item.asin:
            missing.append("asin")
        confidence = 0.7 if not missing else 0.4

        # 3. Find or create Product
        unique_key = self._make_unique_key(domain, item.brand or "", item.product_name or "", source_url)
        product = await self._product_repo.get_by_unique_key(unique_key)

        if product is None:
            product = Product(
                unique_key=unique_key,
                brand=item.brand,
                name=item.product_name,
                category=item.category,
                source_url=source_url,
                review_status=ReviewStatus.AUTO_APPROVED if confidence >= 0.7 else ReviewStatus.PENDING,
            )
            product = await self._product_repo.create(product)
            logger.info("openclaw_product_created", product_id=str(product.id), unique_key=unique_key)
        else:
            logger.info("openclaw_product_found", product_id=str(product.id), unique_key=unique_key)

        # 4. Create ProductVersion
        latest = await self._product_repo.get_latest_version(product.id)
        version_no = (latest.version_no + 1) if latest else 1

        version = ProductVersion(
            product_id=product.id,
            version_no=version_no,
            structured_data=structured_data,
            overall_confidence=confidence,
        )
        version = await self._product_repo.create_version(version)
        logger.info(
            "openclaw_version_created",
            product_id=str(product.id),
            version_no=version_no,
            confidence=confidence,
        )

        # 5. If auto-approved, set current version
        if confidence >= 0.7:
            await self._product_repo.set_current_version(product.id, version.id)

        return IngestedItem(
            item_id=item.item_id,
            task_id=task.id,
            status="success",
        )

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            return (urlparse(url).hostname or "unknown").replace("www.", "")
        except Exception:
            return "unknown"

    @staticmethod
    def _make_unique_key(domain: str, brand: str, name: str, fallback_url: str) -> str:
        import hashlib
        brand_clean = brand.strip().lower().replace(" ", "-") if brand else ""
        name_clean = name.strip().lower().replace(" ", "-") if name else ""
        domain_clean = domain.strip().lower().replace("www.", "")
        if brand_clean and name_clean:
            return f"{domain_clean}/{brand_clean}/{name_clean}"
        if brand_clean:
            return f"{domain_clean}/{brand_clean}"
        url_hash = hashlib.sha256(fallback_url.encode("utf-8")).hexdigest()[:16]
        return f"{domain_clean}/url-{url_hash}"
