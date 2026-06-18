"""
CPIS V1 — 产品入库与版本管理测试

Tests the ProductVersioningService and ProductRepository.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Base
from app.models.enums import ReviewStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.extraction import (
    ExtractionResult,
    FieldEvidence,
    ProductAnalysisFields,
    ProductFactFields,
)
from app.schemas.task import TaskResponse
from app.services.product_service import (
    ProductVersioningService,
    _extract_domain,
    _make_unique_key,
)

# ══════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a fresh SQLite in-memory database."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=NullPool)
    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


def _make_extraction(
    brand: str | None = "TechCorp",
    product_name: str | None = "SmartPro X200",
    model: str | None = "SP-X200",
    confidence: float = 0.85,
    category: str | None = "smartwatch",
) -> ExtractionResult:
    """Helper: create an ExtractionResult with specified values."""
    return ExtractionResult(
        structured_data=ProductFactFields(
            brand=brand,
            product_name=product_name,
            model=model,
            category=category,
            core_benefits=["24h battery", "Water resistant"],
        ),
        analysis_data=ProductAnalysisFields(
            analysis_summary="A good smartwatch",
        ),
        evidence={
            "brand": FieldEvidence(value=brand or "", confidence=0.99, evidence="From H1"),
            "product_name": FieldEvidence(value=product_name or "", confidence=0.95, evidence="From title"),
        },
        overall_confidence=confidence,
        ai_model="gpt-4o",
        prompt_version="v1.0",
    )


def _make_task(source_url: str = "https://example.com/product") -> TaskResponse:
    """Helper: create a TaskResponse."""
    return TaskResponse(
        id=uuid.uuid4(),
        source_url=source_url,
        normalized_url=source_url,
        domain="example.com",
        status="completed",
        priority=50,
        auto_sync_feishu=False,
        retry_count=0,
        max_retries=3,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


# ══════════════════════════════════════════════════════════════════
# Unique key generation
# ══════════════════════════════════════════════════════════════════


class TestUniqueKey:
    def test_with_brand_and_model(self):
        key = _make_unique_key("example.com", "TechCorp", "X200", "https://example.com/p")
        assert "example.com" in key
        assert "techcorp" in key
        assert "x200" in key

    def test_with_brand_only(self):
        key = _make_unique_key("example.com", "Apple", "", "https://example.com/iphone")
        assert "example.com" in key
        assert "apple" in key
        assert "url-" not in key

    def test_fallback_to_url_hash(self):
        key = _make_unique_key("example.com", "", "", "https://example.com/unique-product")
        assert "example.com" in key
        assert "url-" in key

    def test_differentiate_brands(self):
        k1 = _make_unique_key("example.com", "Apple", "iPhone15", "https://example.com/a")
        k2 = _make_unique_key("example.com", "Samsung", "GalaxyS24", "https://example.com/b")
        assert k1 != k2

    def test_strips_www(self):
        key = _make_unique_key("www.example.com", "Brand", "Model", "url")
        assert "www." not in key

    def test_normalizes_case(self):
        key = _make_unique_key("Example.COM", "TECH CORP", "Model-123", "url")
        assert key == "example.com/tech-corp/model-123"


# ══════════════════════════════════════════════════════════════════
# Domain extraction
# ══════════════════════════════════════════════════════════════════


class TestDomainExtraction:
    def test_normal_url(self):
        assert _extract_domain("https://example.com/page") == "example.com"

    def test_strips_www(self):
        assert _extract_domain("https://www.example.com/page") == "example.com"

    def test_handles_invalid(self):
        # urlparse("not-a-url") has no hostname → falls back to "unknown"
        assert _extract_domain("not-a-url") == "unknown"


# ══════════════════════════════════════════════════════════════════
# ProductVersioningService
# ══════════════════════════════════════════════════════════════════


class TestProductVersioningService:
    @pytest.mark.asyncio
    async def test_create_product_from_extraction(self, db_session: AsyncSession):
        """First extraction creates a new product and version."""
        service = ProductVersioningService(db_session)
        extraction = _make_extraction()
        task = _make_task()

        product = await service.process_extraction(extraction, task)

        assert product.id is not None
        assert product.unique_key is not None
        assert product.brand == "TechCorp"
        assert product.name == "SmartPro X200"
        assert product.review_status == ReviewStatus.AUTO_APPROVED.value  # high confidence

        # Check version was created
        repo = ProductRepository(db_session)
        versions = await repo.get_versions(product.id)
        assert len(versions) == 1
        assert versions[0].version_no == 1
        assert versions[0].overall_confidence == 0.85

        # Check current_version was set (auto-approved)
        product2 = await repo.get_by_id(product.id)
        assert product2.current_version_id == versions[0].id

    @pytest.mark.asyncio
    async def test_duplicate_url_no_duplicate_product(self, db_session: AsyncSession):
        """Same URL twice should not duplicate the product."""
        service = ProductVersioningService(db_session)
        extraction = _make_extraction()
        task = _make_task()

        # First time — create
        p1 = await service.process_extraction(extraction, task)

        # Second time — same unique_key, content unchanged → no new version
        p2 = await service.process_extraction(extraction, task)

        assert p1.id == p2.id
        repo = ProductRepository(db_session)
        versions = await repo.get_versions(p1.id)
        assert len(versions) == 1  # unchanged → no new version

    @pytest.mark.asyncio
    async def test_content_change_creates_new_version(self, db_session: AsyncSession):
        """When content changes, a new version is created."""
        service = ProductVersioningService(db_session)
        task = _make_task()

        # Version 1
        extraction1 = _make_extraction(brand="TechCorp", model="SP-X200")
        p1 = await service.process_extraction(extraction1, task)

        # Version 2 — same brand/model (same unique_key) but different product_name
        extraction2 = _make_extraction(brand="TechCorp", model="SP-X200")
        extraction2.structured_data.product_name = "SmartPro X200 v2"

        p2 = await service.process_extraction(extraction2, task)

        assert p1.id == p2.id
        repo = ProductRepository(db_session)
        versions = await repo.get_versions(p1.id)
        assert len(versions) == 2
        assert versions[0].version_no == 1
        assert versions[1].version_no == 2

    @pytest.mark.asyncio
    async def test_low_confidence_sets_needs_review(self, db_session: AsyncSession):
        """Low confidence extraction sets NEEDS_REVIEW status."""
        service = ProductVersioningService(db_session)
        extraction = _make_extraction(confidence=0.45)
        task = _make_task()

        product = await service.process_extraction(extraction, task)
        assert product.review_status == ReviewStatus.NEEDS_REVIEW.value

        # current_version should NOT be set for needs_review
        repo = ProductRepository(db_session)
        product2 = await repo.get_by_id(product.id)
        # Actually our implementation DOES set current_version if confidence >= 0.7
        # For < 0.7, it does NOT set current_version
        # Let's check the version exists but current_version_id is not set
        assert product2.current_version_id is None

    @pytest.mark.asyncio
    async def test_saves_evidences(self, db_session: AsyncSession):
        """Extraction evidences are saved as ProductEvidence records."""
        service = ProductVersioningService(db_session)
        extraction = _make_extraction()
        task = _make_task()

        product = await service.process_extraction(extraction, task)

        # Check evidences exist
        repo = ProductRepository(db_session)
        versions = await repo.get_versions(product.id)
        assert len(versions) == 1

        evidences = await repo.get_evidences(versions[0].id)
        assert len(evidences) >= 2  # brand + product_name

        field_names = {ev.field_name for ev in evidences}
        assert "brand" in field_names
        assert "product_name" in field_names

    @pytest.mark.asyncio
    async def test_different_brands_different_products(self, db_session: AsyncSession):
        """Different brands produce different unique keys and products."""
        service = ProductVersioningService(db_session)
        task = _make_task()

        extraction1 = _make_extraction(brand="Apple", model="iPhone15")
        await service.process_extraction(extraction1, task)

        extraction2 = _make_extraction(brand="Samsung", model="Galaxy24")
        await service.process_extraction(extraction2, task)

        repo = ProductRepository(db_session)
        products, total = await repo.list()
        assert total == 2

    @pytest.mark.asyncio
    async def test_auto_approved_sets_current_version(self, db_session: AsyncSession):
        """High confidence + no missing fields → auto approved + current_version set."""
        service = ProductVersioningService(db_session)
        extraction = _make_extraction(confidence=0.92)
        task = _make_task()

        product = await service.process_extraction(extraction, task)
        repo = ProductRepository(db_session)
        product2 = await repo.get_by_id(product.id)
        assert product2.current_version_id is not None
        assert product2.review_status == ReviewStatus.AUTO_APPROVED.value
