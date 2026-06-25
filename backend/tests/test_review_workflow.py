"""
Additional review workflow tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.models import Base, Product, ProductVersion, ReviewRecord
from app.models.enums import ReviewStatus
from app.repositories.product_repository import ProductRepository
from app.schemas.review import SaveDraftRequest, UpdateReviewRequest
from app.services.review_service import ReviewService


@pytest.fixture
async def db_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=NullPool)
    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)
    session = AsyncSession(bind=connection, expire_on_commit=False)
    yield session
    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


@pytest.fixture
async def seeded_db(db_session: AsyncSession) -> tuple[Product, ProductVersion]:
    repo = ProductRepository(db_session)
    product = await repo.create(
        Product(
            unique_key="example.com/workflow-brand/workflow-model",
            brand="WorkflowBrand",
            name="Workflow Product",
            model="WF-100",
            review_status=ReviewStatus.NEEDS_REVIEW,
        ),
    )
    version = await repo.create_version(
        ProductVersion(
            product_id=product.id,
            version_no=1,
            structured_data={"brand": "WorkflowBrand", "product_name": "Workflow Product"},
            analysis_data={"analysis_summary": "Workflow"},
            overall_confidence=0.4,
            ai_model="gpt-4o",
            prompt_version="v1.0",
        ),
    )
    return product, version


class TestReviewWorkflow:
    @pytest.mark.asyncio
    async def test_update_review_keeps_existing_comments_when_only_corrections_change(
        self, db_session: AsyncSession, seeded_db,
    ):
        product, version = seeded_db
        service = ReviewService(db_session)

        await service.save_draft(
            version.id,
            SaveDraftRequest(corrections={"brand": "DraftBrand"}, comments="Initial"),
            reviewer="tester",
        )
        detail = await service.update_review(
            version.id,
            UpdateReviewRequest(corrections={"brand": "FinalBrand"}),
        )

        assert detail is not None
        assert detail.current_review["comments"] == "Initial"
        assert detail.current_review["corrections"] == {"brand": "FinalBrand"}

        result = await db_session.execute(
            select(ReviewRecord).where(ReviewRecord.product_version_id == version.id),
        )
        review = result.scalar_one()
        assert review.changed_fields == ["brand"]
