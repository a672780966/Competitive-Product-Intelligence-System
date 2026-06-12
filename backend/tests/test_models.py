"""CPIS V1 — 数据库模型 & 迁移 测试

Tests the database models, enums, relationships, constraint enforcement,
and the initial Alembic migration.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models import (
    AuditLog,
    Base,
    CollectionTask,
    FeishuSyncRecord,
    Product,
    ProductEvidence,
    ProductVersion,
    PromptTemplate,
    ReviewRecord,
    SourceSnapshot,
    TaskEvent,
    TaskPriority,
    TaskStatus,
    ProductCategory,
    ReviewStatus,
    SyncStatus,
)


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create a fresh in-memory SQLite database for each test.

    Uses a single connection throughout to keep the in-memory DB alive.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        poolclass=NullPool,
    )

    connection = await engine.connect()
    await connection.run_sync(Base.metadata.create_all)

    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
    )

    yield session

    await session.close()
    await connection.rollback()
    await connection.close()
    await engine.dispose()


# ── CollectionTask ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_collection_task(db_session: AsyncSession) -> None:
    """A CollectionTask can be created and persisted."""
    task = CollectionTask(
        source_url="https://example.com/product",
        normalized_url="https://example.com/product",
        domain="example.com",
        status=TaskStatus.PENDING,
        priority=TaskPriority.NORMAL,
    )
    db_session.add(task)
    await db_session.commit()

    assert task.id is not None
    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.NORMAL
    assert task.created_at is not None
    assert task.updated_at is not None


@pytest.mark.asyncio
async def test_collection_task_status_transitions(db_session: AsyncSession) -> None:
    """Task status can be updated through the pipeline."""
    task = CollectionTask(source_url="https://example.com/page")
    db_session.add(task)
    await db_session.commit()

    task.status = TaskStatus.FETCHING
    await db_session.commit()

    assert task.status == TaskStatus.FETCHING


# ── TaskEvent ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_task_event(db_session: AsyncSession) -> None:
    """TaskEvent links to a CollectionTask."""
    task = CollectionTask(source_url="https://example.com/page")
    db_session.add(task)
    await db_session.flush()

    event = TaskEvent(
        task_id=task.id,
        stage="validation",
        status=TaskStatus.VALIDATING,
        message="Starting URL validation",
    )
    db_session.add(event)
    await db_session.commit()

    assert event.id is not None
    assert event.task_id == task.id
    await db_session.refresh(task, ["events"])
    assert len(task.events) == 1


# ── SourceSnapshot ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_source_snapshot(db_session: AsyncSession) -> None:
    """SourceSnapshot has a 1:1 relationship with CollectionTask."""
    task = CollectionTask(source_url="https://example.com/page")
    db_session.add(task)
    await db_session.flush()

    snapshot = SourceSnapshot(
        task_id=task.id,
        final_url="https://example.com/page",
        cleaned_text="Product description text cleaned.",
        cleaned_markdown="# Product\n\nDescription",
    )
    db_session.add(snapshot)
    await db_session.commit()

    assert snapshot.id is not None
    assert snapshot.task_id == task.id


# ── Product ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_product(db_session: AsyncSession) -> None:
    """Product with unique_key is persisted."""
    product = Product(
        unique_key="apple-iphone-15-pro",
        brand="Apple",
        name="iPhone 15 Pro",
        model="A3104",
        category=ProductCategory.SMARTPHONE,
    )
    db_session.add(product)
    await db_session.commit()

    assert product.id is not None
    assert product.unique_key == "apple-iphone-15-pro"


@pytest.mark.asyncio
async def test_product_unique_key_constraint(db_session: AsyncSession) -> None:
    """Duplicate unique_key raises an integrity error."""
    p1 = Product(unique_key="same-key")
    db_session.add(p1)
    await db_session.commit()

    p2 = Product(unique_key="same-key")
    db_session.add(p2)
    with pytest.raises(Exception):
        await db_session.commit()
    await db_session.rollback()


# ── ProductVersion ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_product_version(db_session: AsyncSession) -> None:
    """ProductVersion links to Product and stores structured_data as JSON."""
    product = Product(unique_key="test-product")
    db_session.add(product)
    await db_session.flush()

    version = ProductVersion(
        product_id=product.id,
        version_no=1,
        structured_data={"price": "$999", "display": "6.1-inch OLED"},
        overall_confidence=0.95,
        ai_model="gpt-4o",
        prompt_version="v1.0",
    )
    db_session.add(version)
    await db_session.commit()

    assert version.id is not None
    assert version.version_no == 1
    assert version.structured_data["price"] == "$999"
    assert version.overall_confidence == 0.95


# ── ProductEvidence ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_product_evidence(db_session: AsyncSession) -> None:
    """ProductEvidence holds per-field extraction evidence."""
    product = Product(unique_key="ev-product")
    db_session.add(product)
    await db_session.flush()

    v = ProductVersion(product_id=product.id, version_no=1)
    db_session.add(v)
    await db_session.flush()

    evidence = ProductEvidence(
        product_version_id=v.id,
        field_name="price",
        value="$999",
        confidence=0.97,
        evidence_text="From product page: Starting at $999",
        evidence_source="https://example.com/product",
    )
    db_session.add(evidence)
    await db_session.commit()

    assert evidence.id is not None
    assert evidence.confidence == 0.97


# ── ReviewRecord ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_review_record(db_session: AsyncSession) -> None:
    """ReviewRecord links to a ProductVersion."""
    product = Product(unique_key="review-product")
    db_session.add(product)
    await db_session.flush()

    v = ProductVersion(product_id=product.id, version_no=1)
    db_session.add(v)
    await db_session.flush()

    review = ReviewRecord(
        product_version_id=v.id,
        reviewer="admin",
        decision=ReviewStatus.APPROVED,
        comments="Looks correct.",
    )
    db_session.add(review)
    await db_session.commit()

    assert review.id is not None
    assert review.decision == ReviewStatus.APPROVED


# ── FeishuSyncRecord ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_feishu_sync_record(db_session: AsyncSession) -> None:
    """FeishuSyncRecord tracks sync state."""
    product = Product(unique_key="sync-product")
    db_session.add(product)
    await db_session.flush()

    sync = FeishuSyncRecord(
        product_id=product.id,
        sync_status=SyncStatus.PENDING,
        sync_type="bitable",
    )
    db_session.add(sync)
    await db_session.commit()

    assert sync.id is not None
    assert sync.sync_status == SyncStatus.PENDING


# ── PromptTemplate ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_prompt_template(db_session: AsyncSession) -> None:
    """PromptTemplate stores versioned prompts."""
    pt = PromptTemplate(
        name="extract-product-v1",
        version="1.0",
        content="Extract structured product data from the following text...",
    )
    db_session.add(pt)
    await db_session.commit()

    assert pt.id is not None
    assert pt.name == "extract-product-v1"


# ── AuditLog ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_audit_log(db_session: AsyncSession) -> None:
    """AuditLog records an immutable operation trail."""
    log = AuditLog(
        actor="admin@company.com",
        action="product.create",
        resource_type="product",
        resource_id="abc-123",
        detail='{"unique_key": "new-product"}',
        ip_address="192.168.1.1",
    )
    db_session.add(log)
    await db_session.commit()

    assert log.id is not None
    assert log.action == "product.create"


# ── Relationships & Cascade ─────────────────────────────────────


@pytest.mark.asyncio
async def test_cascade_delete_task_events(db_session: AsyncSession) -> None:
    """Deleting a CollectionTask cascades to its TaskEvents."""
    task = CollectionTask(source_url="https://example.com/page")
    db_session.add(task)
    await db_session.flush()

    event = TaskEvent(
        task_id=task.id,
        stage="validation",
        status=TaskStatus.COMPLETED,
    )
    db_session.add(event)
    await db_session.commit()

    await db_session.delete(task)
    await db_session.commit()

    # Verify no events remain
    from sqlalchemy import select, func
    result = await db_session.execute(select(func.count()).select_from(TaskEvent))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_product_versions_ordered(db_session: AsyncSession) -> None:
    """Product versions maintain sequential version_no."""
    product = Product(unique_key="versioned-product")
    db_session.add(product)
    await db_session.flush()

    for vno in range(1, 4):
        v = ProductVersion(product_id=product.id, version_no=vno)
        db_session.add(v)
    await db_session.commit()

    # Refresh to eagerly load the relationship
    await db_session.refresh(product, ["versions"])
    assert len(product.versions) == 3
    assert [v.version_no for v in product.versions] == [1, 2, 3]
