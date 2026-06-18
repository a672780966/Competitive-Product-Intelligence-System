"""
CPIS V1 — URL 合规校验服务 测试

Covers:
- URL normalization & tracking param stripping
- Scheme validation
- SSRF / private IP protection
- robots.txt compliance
- Login / CAPTCHA page detection
- Redirect following with validation
"""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.schemas import UrlValidationInput, ValidationErrorCode, ValidationStatus
from app.security.safe_url import SafeUrlResult
from app.services.url_validator import (
    _check_ssrf,
    _is_private_ip,
    _normalize_url,
    _parse_url,
    _validate_scheme,
    validate_url,
)

# ══════════════════════════════════════════════════════════════════
# 1. URL parsing & normalization
# ══════════════════════════════════════════════════════════════════


class TestUrlParsing:
    def test_parse_valid_https(self):
        p = _parse_url("https://example.com/product")
        assert p is not None
        assert p.hostname == "example.com"
        assert p.scheme == "https"

    def test_parse_missing_scheme_adds_https(self):
        p = _parse_url("example.com/product")
        assert p is not None
        assert p.scheme == "https"
        assert p.hostname == "example.com"

    def test_parse_invalid_returns_none(self):
        assert _parse_url("") is None
        assert _parse_url("   ") is None

    def test_parse_ftp_rejected_by_scheme_check(self):
        p = _parse_url("ftp://example.com/file")
        assert p is not None
        assert _validate_scheme(p) == ValidationErrorCode.URL_INVALID

    def test_parse_file_rejected(self):
        # file:///etc/passwd has no netloc → parser returns None (rejected)
        p = _parse_url("file:///etc/passwd")
        assert p is None


class TestUrlNormalization:
    def test_lowercases_hostname(self):
        result = _normalize_url(_parse_url("https://Example.COM/Path"))
        assert "example.com" in result

    def test_removes_tracking_params(self):
        url = "https://example.com/page?utm_source=google&utm_medium=cpc&real_param=value"
        result = _normalize_url(_parse_url(url))
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "real_param=value" in result

    def test_removes_fragment(self):
        url = "https://example.com/page#section"
        result = _normalize_url(_parse_url(url))
        assert "#" not in result

    def test_removes_all_tracking(self):
        url = "https://example.com/p?fbclid=abc&gclid=def&gclsrc=ad&mc_cid=xyz"
        result = _normalize_url(_parse_url(url))
        assert result == "https://example.com/p"

    def test_removes_empty_query_string_when_all_removed(self):
        url = "https://example.com/page?utm_source=google"
        result = _normalize_url(_parse_url(url))
        assert "?" not in result

    def test_preserves_port_when_non_default(self):
        result = _normalize_url(_parse_url("https://example.com:8080/path"))
        assert ":8080" in result

    def test_strips_default_port(self):
        result = _normalize_url(_parse_url("https://example.com:443/path"))
        assert ":443" not in result


# ══════════════════════════════════════════════════════════════════
# 2. SSRF / IP validation
# ══════════════════════════════════════════════════════════════════


class TestPrivateIpDetection:
    def test_loopback_is_private(self):
        assert _is_private_ip(ip_address("127.0.0.1"))
        assert _is_private_ip(ip_address("127.255.255.255"))

    def test_class_a_private_is_private(self):
        assert _is_private_ip(ip_address("10.0.0.1"))
        assert _is_private_ip(ip_address("10.255.255.255"))

    def test_class_b_private_is_private(self):
        assert _is_private_ip(ip_address("172.16.0.1"))
        assert _is_private_ip(ip_address("172.31.255.255"))

    def test_class_c_private_is_private(self):
        assert _is_private_ip(ip_address("192.168.0.1"))
        assert _is_private_ip(ip_address("192.168.255.255"))

    def test_link_local_is_private(self):
        assert _is_private_ip(ip_address("169.254.0.1"))

    def test_public_ip_not_private(self):
        assert not _is_private_ip(ip_address("8.8.8.8"))
        assert not _is_private_ip(ip_address("93.184.216.34"))
        assert not _is_private_ip(ip_address("1.1.1.1"))

    def test_cgnat_is_private(self):
        assert _is_private_ip(ip_address("100.64.0.1"))
        assert _is_private_ip(ip_address("100.127.255.255"))


class TestSsrfCheck:
    @patch("app.services.url_validator._resolve_hostname")
    async def test_blocks_localhost_hostname(self, mock_resolve):
        parsed = _parse_url("http://localhost/admin")
        result = await _check_ssrf(parsed)
        assert result is not None
        assert "localhost" in result.lower()
        mock_resolve.assert_not_called()

    @patch("app.services.url_validator._resolve_hostname")
    async def test_blocks_localhost_ip(self, mock_resolve):
        parsed = _parse_url("http://127.0.0.1/admin")
        result = await _check_ssrf(parsed)
        assert result is not None
        mock_resolve.assert_not_called()

    @patch("app.services.url_validator._resolve_hostname")
    async def test_blocks_private_ip_bare(self, mock_resolve):
        parsed = _parse_url("http://10.0.0.5/admin")
        result = await _check_ssrf(parsed)
        assert result is not None

    @patch("app.services.url_validator._resolve_hostname")
    async def test_blocks_cloud_metadata(self, mock_resolve):
        parsed = _parse_url("http://169.254.169.254/latest/meta-data")
        result = await _check_ssrf(parsed)
        assert result is not None

    @patch("app.services.url_validator._resolve_hostname")
    async def test_blocks_metadata_hostname(self, mock_resolve):
        parsed = _parse_url("http://metadata.google.internal/computeMetadata/v1/")
        result = await _check_ssrf(parsed)
        assert result is not None

    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_blocks_resolved_private_ip(self, mock_check):
        """Domain resolving to private IP is blocked."""
        mock_check.return_value = SafeUrlResult(
            safe=False,
            reason="Resolved to private IP (10.0.0.99)",
            resolved_ips=["10.0.0.99"],
        )
        parsed = _parse_url("http://evil-internal.com/page")
        result = await _check_ssrf(parsed)
        assert result is not None
        assert "private" in result.lower()

    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_allows_public_ip(self, mock_check):
        """Domain resolving to public IP is allowed."""
        mock_check.return_value = SafeUrlResult(
            safe=True,
            reason="OK",
            resolved_ips=["93.184.216.34"],
        )
        parsed = _parse_url("http://example.com/page")
        result = await _check_ssrf(parsed)
        assert result is None


# ══════════════════════════════════════════════════════════════════
# 3. Full validation pipeline (mocked HTTP)
# ══════════════════════════════════════════════════════════════════


class MockAsyncClient:
    """Helper to build mock httpx responses."""

    def __init__(self, head_response=None, get_response=None):
        self.head_response = head_response or self._default_response()
        self.get_response = get_response or self._default_response()

    @staticmethod
    def _default_response(status_code=200, text="", headers=None):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status_code
        mock.text = text
        mock.headers = headers or {}
        mock.url = httpx.URL("https://example.com/page")
        return mock

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def head(self, url, **kwargs):
        return self.head_response

    async def get(self, url, **kwargs):
        return self.get_response


class TestFullValidation:
    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_valid_public_url_passes(self, mock_check, mock_client_cls):
        """A valid public URL should pass all checks."""
        mock_check.return_value = SafeUrlResult(
            safe=True, reason="OK", resolved_ips=["93.184.216.34"],
        )
        head_resp = MagicMock(spec=httpx.Response)
        head_resp.status_code = 200
        head_resp.text = ""
        head_resp.headers = {}
        head_resp.url = httpx.URL("https://example.com/product")
        mock_client = MockAsyncClient(head_response=head_resp,
                                       get_response=head_resp)
        mock_client_cls.return_value = mock_client

        result = await validate_url(UrlValidationInput(source_url="https://example.com/product"))
        assert result.status == ValidationStatus.PASSED
        assert result.normalized_url is not None
        assert "example.com" in result.domain

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_rejects_localhost(self, mock_check, mock_client_cls):
        """localhost URLs should be rejected."""
        mock_check.return_value = SafeUrlResult(
            safe=False, reason="Access to localhost is forbidden", resolved_ips=[],
        )
        result = await validate_url(UrlValidationInput(source_url="http://localhost/admin"))
        assert result.status == ValidationStatus.FAILED
        assert result.error_code == ValidationErrorCode.URL_FORBIDDEN

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_rejects_private_ip(self, mock_check, mock_client_cls):
        """Private IP URLs should be rejected."""
        mock_check.return_value = SafeUrlResult(
            safe=False, reason="Private IP blocked", resolved_ips=[],
        )
        result = await validate_url(UrlValidationInput(source_url="http://192.168.1.1/admin"))
        assert result.status == ValidationStatus.FAILED
        assert result.error_code == ValidationErrorCode.URL_FORBIDDEN

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_rejects_file_scheme(self, mock_check, mock_client_cls):
        """file:// URLs should be rejected."""
        result = await validate_url(UrlValidationInput(source_url="file:///etc/passwd"))
        assert result.status == ValidationStatus.FAILED
        assert result.error_code == ValidationErrorCode.URL_INVALID

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_detects_login_page(self, mock_check, mock_client_cls):
        """Pages with login forms should be blocked."""
        mock_check.return_value = SafeUrlResult(
            safe=True, reason="OK", resolved_ips=["93.184.216.34"],
        )
        head_resp = MagicMock(spec=httpx.Response)
        head_resp.status_code = 200
        head_resp.headers = {}
        head_resp.url = httpx.URL("https://example.com/login")

        get_resp = MagicMock(spec=httpx.Response)
        get_resp.status_code = 200
        get_resp.text = "<html><body><form>Email: <input type='text'/>Password: <input type='password'/><button>Sign In</button></form></body></html>"
        get_resp.url = httpx.URL("https://example.com/login")

        mock_client = MockAsyncClient(head_response=head_resp, get_response=get_resp)
        mock_client_cls.return_value = mock_client

        result = await validate_url(UrlValidationInput(source_url="https://example.com/login"))
        assert result.status == ValidationStatus.BLOCKED
        assert result.error_code == ValidationErrorCode.LOGIN_REQUIRED

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_detects_captcha(self, mock_check, mock_client_cls):
        """Pages with captcha should be failed."""
        mock_check.return_value = SafeUrlResult(
            safe=True, reason="OK", resolved_ips=["93.184.216.34"],
        )
        head_resp = MagicMock(spec=httpx.Response)
        head_resp.status_code = 200
        head_resp.headers = {}
        head_resp.url = httpx.URL("https://example.com/captcha-page")

        get_resp = MagicMock(spec=httpx.Response)
        get_resp.status_code = 200
        get_resp.text = "<html><body><div class='g-recaptcha'></div><p>Please verify you are human</p></body></html>"
        get_resp.url = httpx.URL("https://example.com/captcha-page")

        mock_client = MockAsyncClient(head_response=head_resp, get_response=get_resp)
        mock_client_cls.return_value = mock_client

        result = await validate_url(UrlValidationInput(source_url="https://example.com/captcha-page"))
        assert result.status == ValidationStatus.FAILED
        assert result.error_code == ValidationErrorCode.CAPTCHA_DETECTED

    @patch("app.services.url_validator.httpx.AsyncClient")
    @patch("app.services.url_validator.check_url_safe", new_callable=AsyncMock)
    async def test_http_error_fails(self, mock_check, mock_client_cls):
        """HTTP 403/404 should fail validation."""
        mock_check.return_value = SafeUrlResult(
            safe=True, reason="OK", resolved_ips=["93.184.216.34"],
        )
        head_resp = MagicMock(spec=httpx.Response)
        head_resp.status_code = 404
        head_resp.headers = {}
        head_resp.url = httpx.URL("https://example.com/not-found")

        mock_client = MockAsyncClient(head_response=head_resp)
        mock_client_cls.return_value = mock_client

        result = await validate_url(UrlValidationInput(source_url="https://example.com/not-found"))
        assert result.status == ValidationStatus.FAILED
        assert result.error_code == ValidationErrorCode.FETCH_HTTP_ERROR
