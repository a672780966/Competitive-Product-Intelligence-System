"""
CPIS V1 — Feishu Bitable operations.

High-level operations for Feishu多维表格 (Bitable):
- Upsert records by unique_key
- Search existing records
- Map CPIS structured fields to Feishu columns
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from app.core import get_settings
from app.core.logging import get_logger
from app.integrations.feishu_client import FeishuApiError, FeishuClient
from app.integrations.field_mapping import build_feishu_record

logger = get_logger(__name__)


class FeishuBitable:
    """Operations on a specific Feishu Bitable table.

    Requires ``FEISHU_BITABLE_TOKEN`` configured in settings.
    """

    def __init__(self, client: FeishuClient | None = None) -> None:
        self._client = client or FeishuClient()
        settings = get_settings()
        self._app_token = settings.FEISHU_BITABLE_TOKEN

        if not self._app_token:
            logger.warning("feishu_bitable_not_configured", msg="FEISHU_BITABLE_TOKEN not set")

    async def upsert_product(
        self,
        structured_data: dict[str, Any],
        analysis_data: dict[str, Any],
        unique_key: str,
        version_no: int,
        source_url: str,
    ) -> dict:
        """Create or update a product record in the Bitable.

        Uses ``unique_key`` as the idempotency key.
        Returns the Feishu record_id and sync result.
        """
        if not self._app_token:
            raise FeishuApiError(400, "FEISHU_BITABLE_TOKEN not configured")

        # 1. Search for existing record by unique_key
        existing = await self._search_by_unique_key(unique_key)

        # 2. Build the Feishu record fields
        from datetime import datetime
        collected_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        fields = build_feishu_record(
            structured_data, analysis_data, unique_key,
            version_no, source_url, collected_at=collected_at,
        )

        # 3. Create or update
        if existing:
            record_id = existing["record_id"]
            await self._update_record(record_id, fields)
            logger.info("feishu_record_updated", record_id=record_id, unique_key=unique_key)
            return {"record_id": record_id, "action": "updated"}
        else:
            result = await self._create_record(fields)
            record_id = result["id"]
            logger.info("feishu_record_created", record_id=record_id, unique_key=unique_key)
            return {"record_id": record_id, "action": "created"}

    async def _search_by_unique_key(self, unique_key: str) -> dict | None:
        """Search the bitable for a record with the given unique_key.

        Uses Feishu's record search API with a filter formula.
        """
        try:
            data = await self._client.request(
                "POST",
                f"/bitable/v1/apps/{self._app_token}/records/search",
                json={
                    "field_names": ["record_id", "唯一标识"],
                    "filter": {
                        "conjunction": "and",
                        "conditions": [
                            {
                                "field_name": "唯一标识",
                                "operator": "is",
                                "value": unique_key,
                            },
                        ],
                    },
                    "page_size": 1,
                },
            )
        except FeishuApiError as exc:
            # 190001 means no records match — treat as not found
            if exc.code == 190001:
                return None
            raise

        items = data.get("data", {}).get("items", [])
        return items[0] if items else None

    async def _create_record(self, fields: dict) -> dict:
        """Create a new record in the bitable."""
        data = await self._client.request(
            "POST",
            f"/bitable/v1/apps/{self._app_token}/records",
            json={"fields": fields},
        )
        return data.get("data", {}).get("record", {})

    async def _update_record(self, record_id: str, fields: dict) -> dict:
        """Update an existing record in the bitable."""
        data = await self._client.request(
            "PUT",
            f"/bitable/v1/apps/{self._app_token}/records/{record_id}",
            json={"fields": fields},
        )
        return data.get("data", {}).get("record", {})
