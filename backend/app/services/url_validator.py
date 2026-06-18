"""
CPIS V1 — URL 合规校验服务

核心职责：
1. URL 标准化（去跟踪参数、去锚点、归一化）
2. 仅允许 http/https 协议
3. SSRF 防护（内网 IP 阻断、DNS 二次校验）
4. robots.txt 合规检查
5. 登录页 / 验证码 / 访问拒绝页特征检测
6. 重定向链跟踪与逐跳校验
"""

from __future__ import annotations

import re
import urllib.parse
from ipaddress import ip_address
from urllib.robotparser import RobotFileParser

import httpx

from app.core import get_settings
from app.schemas import (
    UrlValidationInput,
    UrlValidationResult,
    ValidationErrorCode,
    ValidationStatus,
)
from app.security.safe_url import (
    _is_private_ip as _safe_is_private_ip,
)
from app.security.safe_url import (
    _resolve_to_ips as _safe_resolve_to_ips,
)
from app.security.safe_url import (
    check_url_safe,
)

# Tracking parameters to strip
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid",
    "mc_cid", "mc_eid",
    "_ga", "_gl",
}

# Login / captcha page heuristics — checked on the fetched text content
_LOGIN_KEYWORDS = re.compile(
    r"(sign\s*in|log\s*in|login|log\s*on|登\s*录|登录|sign\s*on)", re.IGNORECASE,
)
_CAPTCHA_KEYWORDS = re.compile(
    r"(captcha|recaptcha|hcaptcha|verify\s*you.*human|验证码|人机验证)", re.IGNORECASE,
)
_ACCESS_DENIED_KEYWORDS = re.compile(
    r"(access\s*denied|403\s*forbidden|blocked|拒绝访问|禁止访问|forbidden)", re.IGNORECASE,
)


# ── Public API ──────────────────────────────────────────────────


async def validate_url(input_data: UrlValidationInput) -> UrlValidationResult:
    """Run the full URL validation pipeline.

    Returns a ``UrlValidationResult`` with the validation outcome.
    """
    source_url = input_data.source_url.strip()

    # 1. Parse & validate scheme
    parsed = _parse_url(source_url)
    if parsed is None:
        return _fail(source_url, ValidationErrorCode.URL_INVALID, "Invalid URL format")

    scheme_error = _validate_scheme(parsed)
    if scheme_error:
        return _fail(source_url, scheme_error, "Only http/https schemes are allowed")

    # 2. Normalize
    normalized = _normalize_url(parsed)
    domain = parsed.hostname.lower() if parsed.hostname else None

    # 3. SSRF: check hostname / resolved IPs
    ssrf_error = await _check_ssrf(parsed)
    if ssrf_error:
        return _fail(source_url, ValidationErrorCode.URL_FORBIDDEN, ssrf_error,
                      normalized_url=normalized, domain=domain)

    # 4. HEAD / GET to check reachability and follow redirects
    redirect_count = 0
    final_url = normalized

    if input_data.follow_redirects:
        head_result = await _head_with_redirects(normalized, max_redirects=5)
        if head_result is None:
            return _fail(source_url, ValidationErrorCode.DNS_RESOLUTION_FAILED,
                          "DNS resolution or connection failed",
                          normalized_url=normalized, domain=domain)
        redirect_count = head_result["redirect_count"]
        final_url = head_result["final_url"]

        if head_result["status_code"] >= 400:
            return _fail(source_url, ValidationErrorCode.FETCH_HTTP_ERROR,
                          f"HTTP {head_result['status_code']}",
                          normalized_url=normalized, domain=domain, final_url=final_url)

    # 5. Check robots.txt
    if input_data.check_robots and domain:
        robots_error = await _check_robots_txt(normalized)
        if robots_error:
            return _fail(source_url, ValidationErrorCode.ROBOTS_BLOCKED, robots_error,
                          normalized_url=normalized, domain=domain, final_url=final_url)

    # 6. Fetch content for login / captcha detection
    fetch_result = await _fetch_for_detection(final_url)
    if fetch_result is None:
        return _fail(source_url, ValidationErrorCode.FETCH_HTTP_ERROR,
                      "Failed to fetch page content",
                      normalized_url=normalized, domain=domain, final_url=final_url)

    page_text = fetch_result["text"]
    content_warnings: list[str] = []

    if _LOGIN_KEYWORDS.search(page_text):
        content_warnings.append("Login page detected (requires authentication)")
    if _CAPTCHA_KEYWORDS.search(page_text):
        content_warnings.append("CAPTCHA detected (automated access blocked)")
    if _ACCESS_DENIED_KEYWORDS.search(page_text):
        content_warnings.append("Access denied / forbidden page detected")

    # Determine final status
    status = ValidationStatus.PASSED
    error_code = None
    error_message = None

    for keyword_warning in content_warnings:
        if "CAPTCHA" in keyword_warning:
            status = ValidationStatus.FAILED
            error_code = ValidationErrorCode.CAPTCHA_DETECTED
            error_message = keyword_warning
            break
        if "Login" in keyword_warning:
            status = ValidationStatus.BLOCKED
            error_code = ValidationErrorCode.LOGIN_REQUIRED
            error_message = keyword_warning
            break
        if "forbidden" in keyword_warning.lower():
            status = ValidationStatus.FAILED
            error_code = ValidationErrorCode.FETCH_HTTP_ERROR
            error_message = keyword_warning
            break

    return UrlValidationResult(
        source_url=source_url,
        normalized_url=normalized,
        domain=domain,
        final_url=final_url,
        status=status,
        error_code=error_code,
        error_message=error_message,
        redirect_count=redirect_count,
        warnings=content_warnings,
    )


# ── Internal helpers ────────────────────────────────────────────


def _parse_url(raw: str) -> urllib.parse.ParseResult | None:
    """Parse a raw URL string."""
    try:
        parsed = urllib.parse.urlparse(raw.strip())
        if parsed.scheme and parsed.netloc:
            return parsed
        # Try adding https:// if missing
        if not parsed.scheme and "://" not in raw:
            parsed = urllib.parse.urlparse("https://" + raw.strip())
            if parsed.netloc:
                return parsed
        return None
    except Exception:
        return None


def _validate_scheme(parsed: urllib.parse.ParseResult) -> ValidationErrorCode | None:
    """Check that the scheme is http or https."""
    if parsed.scheme not in ("http", "https"):
        return ValidationErrorCode.URL_INVALID
    return None


def _normalize_url(parsed: urllib.parse.ParseResult) -> str:
    """Normalize a URL: lowercase hostname, strip tracking params and fragment."""
    scheme = parsed.scheme.lower()
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    port = ""
    if parsed.port and (
        (scheme == "http" and parsed.port != 80) or
        (scheme == "https" and parsed.port != 443)
    ):
        port = f":{parsed.port}"

    path = _clean_path(parsed.path)
    params = _clean_query(parsed.query)
    # Strip fragment (#)
    fragment = ""

    result = urllib.parse.ParseResult(scheme, f"{hostname}{port}", path, parsed.params, params, fragment)
    return urllib.parse.urlunparse(result)


def _clean_path(path: str) -> str:
    """Normalize path: ensure it's not empty."""
    if not path or path == "":
        return "/"
    return path


def _clean_query(query: str) -> str:
    """Remove tracking parameters from query string."""
    if not query:
        return ""
    params = urllib.parse.parse_qs(query, keep_blank_values=True)
    cleaned = {k: v for k, v in params.items() if k not in _TRACKING_PARAMS}
    if not cleaned:
        return ""
    return urllib.parse.urlencode(cleaned, doseq=True)


async def _check_ssrf(parsed: urllib.parse.ParseResult) -> str | None:
    """Check for SSRF / private IP access.

    Delegates to ``check_url_safe()`` from ``app.security.safe_url``.

    Returns an error message string if blocked, or None if allowed.
    """
    url = urllib.parse.urlunparse(parsed)
    result = await check_url_safe(url)
    if not result.safe:
        return result.reason
    return None


def _is_private_ip(addr) -> bool:
    """Check if an IP address belongs to a private/reserved range.

    Delegates to ``app.security.safe_url._is_private_ip``.
    """
    return _safe_is_private_ip(addr)


async def _resolve_hostname(hostname: str) -> list:
    """Resolve a hostname to a list of IP addresses.

    Delegates to ``app.security.safe_url._resolve_to_ips``.
    """
    ips = await _safe_resolve_to_ips(hostname)
    result = []
    for ip_str in ips:
        try:
            result.append(ip_address(ip_str))
        except ValueError:
            continue
    return result


async def _head_with_redirects(
    url: str,
    max_redirects: int = 5,
    timeout: int = 15,
) -> dict | None:
    """Follow redirects with HEAD requests, validate each hop.

    Returns dict with final_url, status_code, redirect_count or None on failure.
    """
    settings = get_settings()
    user_agent = settings.COLLECTION_USER_AGENT

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=False,
        headers={"User-Agent": user_agent},
    ) as client:
        current_url = url
        redirect_count = 0

        for _ in range(max_redirects + 1):
            try:
                response = await client.head(current_url)
            except (httpx.RequestError, httpx.TimeoutException):
                # Fallback to GET if HEAD not supported
                try:
                    response = await client.get(current_url)
                except (httpx.RequestError, httpx.TimeoutException):
                    return None

            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location")
                if not location:
                    break
                current_url = urllib.parse.urljoin(current_url, location)

                # Validate the redirect target via safe_url
                safe_result = await check_url_safe(current_url)
                if not safe_result.safe:
                    return None  # Redirect to unsafe target — block

                redirect_count += 1
            else:
                return {
                    "final_url": str(response.url),
                    "status_code": response.status_code,
                    "redirect_count": redirect_count,
                }

    return None  # Too many redirects


async def _check_robots_txt(url: str) -> str | None:
    """Check robots.txt for the given URL.

    Returns an error message if blocked, or None if allowed.
    """
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.hostname}/robots.txt"

    settings = get_settings()
    user_agent = settings.COLLECTION_USER_AGENT

    rp = RobotFileParser(robots_url)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(robots_url, headers={"User-Agent": user_agent})
            if response.status_code == 200:
                rp.parse(response.text.splitlines())
            else:
                return None  # No robots.txt or inaccessible — allow by default
    except Exception:
        return None  # Fail open if robots.txt unreachable

    if not rp.can_fetch(user_agent, url):
        return f"Blocked by robots.txt: {robots_url}"

    return None


async def _fetch_for_detection(url: str, timeout: int = 20) -> dict | None:
    """Fetch page content for login / captcha detection.

    Returns dict with 'text' containing the page body text,
    or None if the fetch fails.
    """
    settings = get_settings()
    user_agent = settings.COLLECTION_USER_AGENT

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": user_agent})
            if response.status_code == 200:
                return {"text": response.text}
            return None
    except (httpx.RequestError, httpx.TimeoutException):
        return None


def _fail(
    source_url: str,
    error_code: ValidationErrorCode,
    error_message: str,
    *,
    normalized_url: str | None = None,
    domain: str | None = None,
    final_url: str | None = None,
) -> UrlValidationResult:
    """Build a failed validation result."""
    return UrlValidationResult(
        source_url=source_url,
        normalized_url=normalized_url,
        domain=domain,
        final_url=final_url,
        status=ValidationStatus.FAILED,
        error_code=error_code,
        error_message=error_message,
    )
