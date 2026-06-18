"""
CPIS V1 — Feishu API Client.

Handles authentication and HTTP communication with Feishu Open APIs.
Token is cached in-memory to reduce API calls.
"""

from __future__ import annotations

import json
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

        # ✅ 修复 1：总是先检查 HTTP 状态
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "feishu_http_error",
                path=path,
                status=exc.response.status_code,
                response_text=exc.response.text[:500],
            )
            raise FeishuApiError(
                exc.response.status_code,
                f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
            )

        # ✅ 修复 2：检查 Content-Type，确保是 JSON
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            logger.error(
                "feishu_invalid_content_type",
                path=path,
                content_type=content_type,
                response_text=response.text[:500],
            )
            raise FeishuApiError(
                -1,
                f"Expected JSON response, got {content_type}",
            )

        # ✅ 修复 3：添加 JSON 解析异常处理
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            logger.error(
                "feishu_json_parse_error",
                path=path,
                error=str(exc),
                response_text=response.text[:500],
            )
            raise FeishuApiError(
                -1,
                f"Failed to parse JSON response: {str(exc)[:100]}",
            )

        # ✅ 修复 4：检查 Feishu API 返回的业务错误码
        code = data.get("code", -1)
        msg = data.get("msg", "")

        if code != 0:
            logger.error(
                "feishu_api_error",
                path=path,
                code=code,
                msg=msg,
                response=data,
            )
            raise FeishuApiError(code, msg)

        logger.debug("feishu_request_success", path=path)
        return data

    async def _get_token(self) -> FeishuToken:
        """Get a valid tenant access token (uses cache if not expired)."""
        if self._token and time.time() < self._token.expires_at - 60:
            return self._token

        if not self._app_id or not self._app_secret:
            raise FeishuAuthError("Feishu App ID and App Secret must be configured")

        url = f"{_FEISHU_BASE}/auth/v3/tenant_access_token/internal"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json={
                    "app_id": self._app_id,
                    "app_secret": self._app_secret,
                })

                # ✅ 修复：同样检查 HTTP 状态
                response.raise_for_status()

                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "feishu_auth_http_error",
                status=exc.response.status_code,
                response_text=exc.response.text[:500],
            )
            raise FeishuAuthError(f"HTTP {exc.response.status_code} from auth endpoint")
        except json.JSONDecodeError as exc:
            logger.error("feishu_auth_json_error", error=str(exc))
            raise FeishuAuthError(f"Failed to parse auth response: {str(exc)}")

        code = data.get("code", -1)
        if code != 0:
            error_msg = data.get("msg", "Unknown error")
            logger.error("feishu_auth_api_error", code=code, msg=error_msg)
            raise FeishuAuthError(f"Failed to get token: {error_msg}")

        token_str = data.get("tenant_access_token", "")
        expire = data.get("expire", 7200)  # default 7200s

        if not token_str:
            logger.error("feishu_no_token_in_response", response=data)
            raise FeishuAuthError("No tenant_access_token in response")

        self._token = FeishuToken(
            access_token=token_str,
            expires_at=time.time() + expire,
        )
        logger.info("feishu_token_acquired", expires_in=expire)
        return self._token

    def clear_token(self) -> None:
        """Force token refresh on next request."""
        self._token = None
