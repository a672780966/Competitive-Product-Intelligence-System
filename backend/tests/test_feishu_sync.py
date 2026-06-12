"""
CPIS V1 — 飞书同步测试

Tests field mapping, Feishu client auth, bitable operations,
and the sync service orchestration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import get_db
from app.integrations.feishu_client import FeishuClient, FeishuApiError
from app.integrations.feishu_bitable import FeishuBitable
from app.integrations.field_mapping import build_feishu_record
from app.models import Base, FeishuSyncRecord, Product, ProductVersion
from app.models.enums import SyncStatus


# ══════════════════════════════════════════════════════════════════
# Field mapping
# ══════════════════════════════════════════════════════════════════


class TestFieldMapping:
    def test_build_record_with_full_data(self):
        sd = {
            "product_name": "SmartPro X200",
            "brand": "TechCorp",
            "model": "SP-X200",
            "category": "smartwatch",
            "core_benefits": ["24h battery", "Water resistant"],
            "features": ["AMOLED", "GPS"],
            "currency": "USD",
            "original_price": "349.99",
            "sale_price": "299.99",
        }
        ad = {
            "advantages": ["Better display"],
            "risks": ["Market saturation"],
            "analysis_summary": "Good product",
        }
        record = build_feishu_record(sd, ad, "test-key", 1, "https://example.com/p")

        assert record["产品名称"] == "SmartPro X200"
        assert record["品牌"] == "TechCorp"
        assert record["唯一标识"] == "test-key"
        assert "24h battery" in record["核心卖点"]
        assert "349.99" in record["价格信息"]
        assert "Better display" in record["优势"]
        assert "Market saturation" in record["风险"]
        assert "Good product" in record["分析摘要"]

    def test_build_record_with_empty_data(self):
        record = build_feishu_record({}, {}, "empty-key", 1, "")
        assert record["产品名称"] == ""
        assert record["品牌"] == ""
        assert record["数据版本"] == "v1"

    def test_price_building(self):
        sd = {
            "currency": "USD",
            "original_price": "499",
            "sale_price": "399",
        }
        record = build_feishu_record(sd, {}, "k", 1, "")
        assert "USD" in record["价格信息"]
        assert "499" in record["价格信息"]
        assert "399" in record["价格信息"]

    def test_join_list_fields(self):
        sd = {"features": ["A", "B", "C"]}
        record = build_feishu_record(sd, {}, "k", 1, "")
        assert "A" in record["主要参数"]
        assert "B" in record["主要参数"]


# ══════════════════════════════════════════════════════════════════
# Feishu Client
# ══════════════════════════════════════════════════════════════════


class TestFeishuClient:
    @patch("app.integrations.feishu_client.httpx.AsyncClient")
    async def test_get_token_success(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "test-token-123",
            "expire": 7200,
        }
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = FeishuClient(app_id="test-id", app_secret="test-secret")
        token = await client._get_token()
        assert token.access_token == "test-token-123"
        assert token.expires_at > 0

    @patch("app.integrations.feishu_client.httpx.AsyncClient")
    async def test_request_success(self, mock_client_cls):
        # Mock token acquisition
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {
            "code": 0,
            "tenant_access_token": "token",
            "expire": 7200,
        }
        # Mock API call
        mock_api_resp = MagicMock()
        mock_api_resp.json.return_value = {"code": 0, "data": {"result": "ok"}}
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_token_resp
        mock_client.request.return_value = mock_api_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = FeishuClient(app_id="id", app_secret="secret")
        result = await client.request("GET", "/test")
        assert result["code"] == 0

    @patch("app.integrations.feishu_client.httpx.AsyncClient")
    async def test_request_api_error(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"code": 190001, "msg": "Record not found"}
        mock_client = AsyncMock()
        mock_client.post.return_value = MagicMock()  # token
        mock_client.post.return_value.json.return_value = {
            "code": 0, "tenant_access_token": "t", "expire": 7200,
        }
        mock_client.request.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = FeishuClient(app_id="id", app_secret="secret")
        with pytest.raises(FeishuApiError):
            await client.request("GET", "/test")

    def test_token_cache(self):
        """Token is cached and reused."""
        client = FeishuClient(app_id="id", app_secret="secret")
        assert client._token is None

    @patch("app.integrations.feishu_client.httpx.AsyncClient")
    async def test_clear_token_forces_refresh(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "code": 0, "tenant_access_token": "t1", "expire": 7200,
        }
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        client = FeishuClient(app_id="id", app_secret="secret")
        await client._get_token()
        assert client._token is not None
        client.clear_token()
        assert client._token is None


# ══════════════════════════════════════════════════════════════════
# FeishuBitable
# ══════════════════════════════════════════════════════════════════


class TestFeishuBitable:
    @patch.object(FeishuClient, "request")
    async def test_upsert_creates_new(self, mock_request):
        """When no existing record, creates a new one."""
        # Search returns no results (190001 error)
        mock_request.side_effect = [
            FeishuApiError(190001, "No records"),  # search
            {"data": {"record": {"id": "rec_new_123"}}},  # create
        ]

        bitable = FeishuBitable(client=FeishuClient(app_id="id", app_secret="secret"))
        with patch.object(bitable, "_app_token", "test_token"):
            result = await bitable.upsert_product(
                {"product_name": "Test"}, {}, "unique-1", 1, "https://example.com/p",
            )
        assert result["action"] == "created"
        assert result["record_id"] == "rec_new_123"

    @patch.object(FeishuClient, "request")
    async def test_upsert_updates_existing(self, mock_request):
        """When existing record found, updates it."""
        mock_request.side_effect = [
            {  # search result
                "data": {
                    "items": [{"record_id": "rec_existing_1"}],
                },
            },
            {"data": {"record": {"id": "rec_existing_1"}}},  # update
        ]

        bitable = FeishuBitable(client=FeishuClient(app_id="id", app_secret="secret"))
        with patch.object(bitable, "_app_token", "test_token"):
            result = await bitable.upsert_product(
                {"product_name": "Test"}, {}, "unique-1", 2, "https://example.com/p",
            )
        assert result["action"] == "updated"
        assert result["record_id"] == "rec_existing_1"


# ══════════════════════════════════════════════════════════════════
# Sync service
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


class TestFeishuSyncService:
    @pytest.mark.asyncio
    async def test_sync_product_success(self, db_session: AsyncSession):
        from app.services.feishu_sync_service import FeishuSyncService

        # Create product + version
        product = Product(
            unique_key="example.com/test-brand/test",
            brand="TestBrand",
            name="Test",
            review_status="auto_approved",
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(
            product_id=product.id, version_no=1,
            structured_data={"brand": "TestBrand", "product_name": "Test Product"},
            overall_confidence=0.95,
        )
        db_session.add(version)
        await db_session.flush()

        # Mock bitable
        mock_bitable = AsyncMock()
        mock_bitable.upsert_product.return_value = {"record_id": "rec_test_1", "action": "created"}

        service = FeishuSyncService(db_session, bitable=mock_bitable)
        sync = await service.sync_product(product.id)

        assert sync.sync_status == SyncStatus.SUCCESS.value
        assert sync.feishu_record_id == "rec_test_1"
        mock_bitable.upsert_product.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_product_fails_gracefully(self, db_session: AsyncSession):
        from app.services.feishu_sync_service import FeishuSyncService

        product = Product(
            unique_key="example.com/fail",
            brand="FailBrand",
            review_status="auto_approved",
        )
        db_session.add(product)
        await db_session.flush()

        version = ProductVersion(product_id=product.id, version_no=1)
        db_session.add(version)
        await db_session.flush()

        mock_bitable = AsyncMock()
        mock_bitable.upsert_product.side_effect = FeishuApiError(99999, "API timeout")

        service = FeishuSyncService(db_session, bitable=mock_bitable)
        sync = await service.sync_product(product.id)

        assert sync.sync_status == SyncStatus.FAILED.value
        assert sync.error_message is not None

    @pytest.mark.asyncio
    async def test_sync_all_pending(self, db_session: AsyncSession):
        from app.services.feishu_sync_service import FeishuSyncService

        # Create two products needing sync
        for i in range(2):
            p = Product(
                unique_key=f"example.com/product-{i}",
                brand=f"Brand{i}",
                review_status="auto_approved",
            )
            db_session.add(p)
            await db_session.flush()
            v = ProductVersion(product_id=p.id, version_no=1)
            db_session.add(v)
        await db_session.flush()

        mock_bitable = AsyncMock()
        mock_bitable.upsert_product.return_value = {"record_id": "rec_test", "action": "created"}

        service = FeishuSyncService(db_session, bitable=mock_bitable)
        records = await service.sync_all_pending()

        assert len(records) == 2
        assert all(r.sync_status == SyncStatus.SUCCESS.value for r in records)
