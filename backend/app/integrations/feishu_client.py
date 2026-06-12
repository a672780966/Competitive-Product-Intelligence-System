"""
CPIS V1 — Feishu API Client.

Handles authentication and HTTP communication with Feishu Open APIs.
Token is cached in-memory to reduce API calls.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_FEISHU_BASE = "https://open.feishu.cn/open-apis"


class FeishuAuthError(Exception):
    """Raised when Feishu authentication fails."""
    pass


class FeishuApiError(Exception):
    """Raised when a Feishu API call returns an error."""
    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}")


@dataclass
class FeishuToken:
    """Cached tenant access token with expiry."""

    access_token: str
    expires_at: float  # unix timestamp


class FeishuClient:
    """Low-level HTTP client for Feishu Open APIs.

    Manages token lifecycle automatically.
    Use ``request()`` for authenticated API calls.
    """

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        timeout: int = 30,
    ) -> None:
        settings = get_settings()
        self._app_id = app_id or settings.FEISHU_APP_ID
        self._app_secret = app_secret or settings.FEISHU_APP_SECRET
        self._timeout = timeout
        self._token: FeishuToken | None = None

        if not self._app_id or not self._app_secret:
            logger.warning("feishu_not_configured", msg="Feishu App ID or Secret not set")

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make an authenticated request to the Feishu Open API.

        Automatically acquires or refreshes the bearer token.
        """
        token = await self._get_token()
        url = f"{_FEISHU_BASE}{path}"

        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.request(
                method, url, json=json, params=params, headers=headers,
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FeishuApiError(exc.response.status_code, exc.response.text[:500])

        data = response.json()
        code = data.get("code", -1)
        msg = data.get("msg", "")

        if code != 0:
            logger.error("feishu_api_error", path=path, code=code, msg=msg)
            raise FeishuApiError(code, msg)

        return data

    async def _get_token(self) -> FeishuToken:
        """Get a valid tenant access token (uses cache if not expired)."""
        if self._token and time.time() < self._token.expires_at - 60:
            return self._token

        if not self._app_id or not self._app_secret:
            raise FeishuAuthError("Feishu App ID and App Secret must be configured")

        url = f"{_FEISHU_BASE}/auth/v3/tenant_access_token/internal"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json={
                "app_id": self._app_id,
                "app_secret": self._app_secret,
            })
            data = response.json()

        code = data.get("code", -1)
        if code != 0:
            raise FeishuAuthError(f"Failed to get token: {data.get('msg', '')}")

        token_str = data.get("tenant_access_token", "")
        expire = data.get("expire", 7200)  # default 7200s

        self._token = FeishuToken(
            access_token=token_str,
            expires_at=time.time() + expire,
        )
        logger.info("feishu_token_acquired", expires_in=expire)
        return self._token

    def clear_token(self) -> None:
        """Force token refresh on next request."""
        self._token = None
