"""
CPIS V1 — 竞品简报生成测试

Tests the Markdown report generator and report service.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.analyzers.report_generator import (
    generate_comparison_report,
    generate_single_product_report,
)
from app.models import Base, Product, ProductVersion

# ══════════════════════════════════════════════════════════════════
# Single product report
# ══════════════════════════════════════════════════════════════════

_FULL_STRUCTURED = {
    "product_name": "SmartPro X200",
    "brand": "TechCorp",
    "model": "SP-X200",
    "category": "smartwatch",
    "currency": "USD",
    "original_price": "349.99",
    "sale_price": "299.99",
    "core_benefits": ["24h battery life", "Water resistant to 50m"],
    "features": ["1.4-inch AMOLED display", "GPS tracking", "Heart rate monitor"],
    "tech_principles": ["Optical heart rate sensing"],
    "working_modes": ["Sport mode", "Sleep tracking", "Stress monitoring"],
    "power": "5V 1A",
    "weight": "45g",
    "material": ["Titanium", "Silicone strap"],
    "accessories": ["Charging cable", "Extra strap"],
    "package_contents": ["Watch", "Charger", "Manual"],
    "battery": "300mAh Li-ion",
    "charging_method": "Wireless charging",
    "certification_name": ["CE", "FCC", "RoHS"],
    "target_audience": ["Fitness enthusiasts", "Tech early adopters"],
    "use_scenarios": ["Daily fitness tracking", "Outdoor running"],
    "pain_points": ["Short battery life in competitors"],
    "marketing_angle": ["Premium design", "Longest battery in class"],
}

_FULL_ANALYSIS = {
    "differentiators": ["Longer battery than Apple Watch"],
    "advantages": ["Better display", "More accurate GPS"],
    "disadvantages": ["No cellular version", "Limited app ecosystem"],
    "opportunities": ["Corporate wellness programs"],
    "risks": ["Strong competition from Apple", "Price sensitivity"],
    "suggested_actions": ["Target fitness segment", "Bundle with health apps"],
    "analysis_summary": "A strong mid-range smartwatch competitor.",
}

_EMPTY_STRUCTURED = {}
_EMPTY_ANALYSIS = {}


class TestSingleProductReport:
    def test_generates_full_report(self):
        report = generate_single_product_report(
            product_name="SmartPro X200",
            brand="TechCorp",
            model="SP-X200",
            category="smartwatch",
            source_url="https://example.com/product",
            structured_data=_FULL_STRUCTURED,
            analysis_data=_FULL_ANALYSIS,
            version_no=1,
        )

        # Structure checks
        assert report.startswith("#")
        assert "SmartPro X200" in report
        assert "TechCorp" in report
        assert "SP-X200" in report

        # Page facts section
        assert "## 页面事实" in report
        assert "24h battery life" in report
        assert "GPS tracking" in report
        assert "Wireless charging" in report
        assert "CE" in report

        # Price
        assert "349.99" in report
        assert "299.99" in report

        # AI analysis section
        assert "## AI 分析" in report
        assert "差异化卖点" in report
        assert "Better display" in report
        assert "Strong competition" in report
        assert "Target fitness" in report

        # Source link
        assert "example.com" in report

        # Auto-generated footer
        assert "CPIS V1" in report

    def test_empty_data_does_not_crash(self):
        report = generate_single_product_report(
            product_name="",
            brand="",
            model="",
            category="",
            source_url="https://example.com/p",
            structured_data=_EMPTY_STRUCTURED,
            analysis_data=_EMPTY_ANALYSIS,
            version_no=0,
        )
        assert report.startswith("#")
        assert "未知" in report or "产品竞品简报" in report

    def test_markdown_formatting(self):
        """Checks key Markdown formatting patterns."""
        report = generate_single_product_report(
            product_name="Test", brand="B", model="M", category="C",
            source_url="https://example.com/p",
            structured_data={"core_benefits": ["Benefit 1"]},
            analysis_data={"advantages": ["Advantage 1"]},
            version_no=1,
        )
        assert "###" in report  # subheadings
        assert "- " in report  # bullet points
        assert "---" in report  # horizontal rules


# ══════════════════════════════════════════════════════════════════
# Comparison report
# ══════════════════════════════════════════════════════════════════


class TestComparisonReport:
    def test_generates_comparison_table(self):
        products = [
            {
                "name": "Product A",
                "brand": "Brand A",
                "category": "smartwatch",
                "price_text": "$299",
                "source_url": "https://a.com",
                "analysis_data": {
                    "advantages": ["Lightweight"],
                    "risks": ["No GPS"],
                    "suggested_actions": ["Add GPS"],
                },
            },
            {
                "name": "Product B",
                "brand": "Brand B",
                "category": "smartwatch",
                "price_text": "$399",
                "source_url": "https://b.com",
                "analysis_data": {
                    "advantages": ["GPS included"],
                    "risks": ["Heavy"],
                    "suggested_actions": ["Reduce weight"],
                },
            },
        ]
        report = generate_comparison_report(products)
        assert "# 竞品对比简报" in report
        assert "| Product A" in report
        assert "| Product B" in report
        assert "Lightweight" in report
        assert "No GPS" in report
        assert "Add GPS" in report

    def test_empty_products(self):
        report = generate_comparison_report([])
        assert "# 竞品对比简报" in report
        assert "暂无产品数据" in report


# ══════════════════════════════════════════════════════════════════
# Report service (with DB)
# ══════════════════════════════════════════════════════════════════


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


class TestReportService:
    @pytest.mark.asyncio
    async def test_single_product_report_from_db(self, db_session: AsyncSession):
        from app.services.report_service import ReportService

        # Seed data
        product = Product(
            unique_key="test-key", brand="TestBrand", name="Test Product",
            source_url="https://example.com/p",
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(
            product_id=product.id, version_no=1,
            structured_data={"product_name": "Test Product", "brand": "TestBrand"},
            analysis_data={"analysis_summary": "Good product"},
        )
        db_session.add(version)
        await db_session.flush()

        product.current_version_id = version.id
        await db_session.flush()

        service = ReportService(db_session)
        report = await service.single_product_report(product.id)
        assert report is not None
        assert "Test Product" in report
        assert "Good product" in report

    @pytest.mark.asyncio
    async def test_single_report_not_found(self, db_session: AsyncSession):
        from app.services.report_service import ReportService
        service = ReportService(db_session)
        report = await service.single_product_report(uuid.uuid4())
        assert report is None

    @pytest.mark.asyncio
    async def test_comparison_report_from_db(self, db_session: AsyncSession):
        from app.services.report_service import ReportService

        product_ids = []
        for i in range(2):
            p = Product(
                unique_key=f"comp-key-{i}", brand=f"Brand{i}",
                name=f"Product{i}",
            )
            db_session.add(p)
            await db_session.flush()
            v = ProductVersion(
                product_id=p.id, version_no=1,
                structured_data={"product_name": f"Product{i}"},
            )
            db_session.add(v)
            await db_session.flush()
            p.current_version_id = v.id
            product_ids.append(p.id)
        await db_session.flush()

        service = ReportService(db_session)
        report = await service.comparison_report(product_ids)
        assert "# 竞品对比简报" in report
        assert "Product0" in report
        assert "Product1" in report
