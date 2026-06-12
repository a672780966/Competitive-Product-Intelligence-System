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
import socket
import urllib.parse
from ipaddress import ip_address, ip_network
from urllib.robotparser import RobotFileParser

import httpx

from app.core import get_settings
from app.schemas import (
    UrlValidationInput,
    UrlValidationResult,
    ValidationErrorCode,
    ValidationStatus,
)

# ── Private / reserved IP ranges (SSRF protection) ──────────────
_PRIVATE_NETWORKS = [
    ip_network("127.0.0.0/8"),       # loopback
    ip_network("10.0.0.0/8"),        # class A private
    ip_network("172.16.0.0/12"),     # class B private
    ip_network("192.168.0.0/16"),    # class C private
    ip_network("169.254.0.0/16"),    # link-local
    ip_network("0.0.0.0/8"),         # current network
    ip_network("100.64.0.0/10"),     # carrier-grade NAT
    ip_network("198.18.0.0/15"),     # benchmark testing
]

# Cloud metadata endpoints (must never be reachable)
_CLOUD_METADATA_HOSTS = {
    "169.254.169.254",   # AWS/GCP/Azure
    "metadata.google.internal",
    "100.100.100.200",   # Alibaba Cloud
}

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

    Returns an error message string if blocked, or None if allowed.
    """
    hostname = parsed.hostname or ""

    # Check cloud metadata endpoints by hostname
    if hostname.lower() in _CLOUD_METADATA_HOSTS:
        return f"Access to cloud metadata endpoint is forbidden: {hostname}"

    # Check if hostname is localhost
    if hostname.lower() in ("localhost", "localhost.localdomain", "127.0.0.1", "::1", "0.0.0.0"):
        return "Access to localhost is forbidden"

    # Check if hostname is a bare IP
    try:
        addr = ip_address(hostname)
        if _is_private_ip(addr):
            return f"Access to private IP is forbidden: {hostname}"
        return None  # It's a public IP — no DNS resolution needed
    except ValueError:
        pass  # Not a bare IP, resolve below

    # Resolve hostname to IP addresses
    try:
        addrinfo = await _resolve_hostname(hostname)
    except Exception as e:
        return f"DNS resolution failed: {e}"

    for addr in addrinfo:
        if _is_private_ip(addr):
            return f"Resolved to private IP ({addr}) — access forbidden: {hostname}"

    return None


def _is_private_ip(addr) -> bool:
    """Check if an IP address belongs to a private/reserved range."""
    return any(addr in network for network in _PRIVATE_NETWORKS)


async def _resolve_hostname(hostname: str) -> list:
    """Resolve a hostname to a list of IP addresses."""
    # Use a thread pool to avoid blocking the event loop
    import asyncio
    loop = asyncio.get_running_loop()
    try:
        addrinfo = await loop.run_in_executor(
            None, socket.getaddrinfo, hostname, 80,
        )
        seen = set()
        result = []
        for info in addrinfo:
            ip = ip_address(info[4][0])
            if ip not in seen:
                seen.add(ip)
                result.append(ip)
        return result
    except socket.gaierror as e:
        raise Exception(f"Cannot resolve hostname: {e}") from e


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

                # Validate the redirect target
                target_parsed = _parse_url(current_url)
                if target_parsed is None:
                    return None
                if _validate_scheme(target_parsed):
                    return None  # Redirect to non-http scheme — block
                ssrf_error = await _check_ssrf(target_parsed)
                if ssrf_error:
                    return None  # Redirect to private IP — block

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
