"""Safe URL utilities -- SSRF protection guard.

Provides a single function ``check_url_safe()`` that validates:
- Scheme (http/https only)
- Port (80/443 only)
- Hostname (no localhost, no metadata endpoints)
- DNS resolution (no private/reserved IPs)
- No IPv4-mapped IPv6 tricks
- No cloud metadata hosts

All collectors MUST call ``check_url_safe()`` before making any request.
Every 30x redirect target MUST also be re-checked.
"""

from __future__ import annotations

import asyncio
import socket
import urllib.parse
from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network

# ── Safe schemes and ports ─────────────────────────────────────────
_SAFE_SCHEMES: frozenset[str] = frozenset({"http", "https"})
_SAFE_PORTS: frozenset[int] = frozenset({80, 443})

# ── Private / reserved IP ranges (SSRF protection) ─────────────────
_PRIVATE_NETWORKS: list = [
    # IPv4
    ip_network("127.0.0.0/8"),       # loopback
    ip_network("10.0.0.0/8"),        # class A private
    ip_network("172.16.0.0/12"),     # class B private
    ip_network("192.168.0.0/16"),    # class C private
    ip_network("169.254.0.0/16"),    # link-local
    ip_network("0.0.0.0/8"),         # current network
    ip_network("100.64.0.0/10"),     # carrier-grade NAT (CGNAT)
    ip_network("198.18.0.0/15"),     # benchmark testing
    # IPv6
    ip_network("::1/128"),           # loopback
    ip_network("fc00::/7"),          # unique-local (ULA)
    ip_network("fe80::/10"),         # link-local
]

# ── Cloud metadata endpoints (must never be reachable) ─────────────
_CLOUD_METADATA_HOSTS: frozenset[str] = frozenset({
    "169.254.169.254",                  # AWS / GCP / Azure metadata
    "metadata.google.internal",         # GCP
    "metadata.google.internal.",        # GCP (fully qualified)
    "metadata.internal",                # GCP internal
    "100.100.100.200",                  # Alibaba Cloud
    "100.100.100.204",                  # Alibaba Cloud (secondary)
    "168.63.129.16",                    # Azure IMDS
    "metadata.azure.internal",          # Azure internal
    "metadata.azure.internal.",         # Azure internal (fully qualified)
})

_HOSTNAME_LOCAL_BLOCKLIST: frozenset[str] = frozenset({
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
})


@dataclass
class SafeUrlResult:
    """Result of a URL safety check.

    Attributes:
        safe: Whether the URL is safe to request.
        reason: Human-readable explanation if unsafe.
        resolved_ips: List of IP addresses the hostname resolved to.
    """

    safe: bool
    reason: str = ""
    resolved_ips: list[str] = field(default_factory=list)


# ── Public API ─────────────────────────────────────────────────────


async def check_url_safe(url: str) -> SafeUrlResult:
    """Check if a URL is safe from SSRF perspective.

    Validates scheme, port, hostname, and resolves DNS to check
    for private/reserved IP addresses and cloud metadata endpoints.

    Args:
        url: The URL to check.

    Returns:
        SafeUrlResult with ``safe`` boolean and ``reason`` if unsafe.
    """
    # 1. Parse URL
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:
        return SafeUrlResult(safe=False, reason=f"URL parse error: {exc}")

    if not parsed.scheme or not parsed.netloc:
        return SafeUrlResult(safe=False, reason="URL missing scheme or netloc")

    # 2. Check scheme
    if parsed.scheme not in _SAFE_SCHEMES:
        return SafeUrlResult(
            safe=False,
            reason=f"Scheme '{parsed.scheme}' not allowed (only http/https)",
        )

    hostname = parsed.hostname or ""

    # 3. Check port
    if parsed.port is not None and parsed.port not in _SAFE_PORTS:
        return SafeUrlResult(
            safe=False,
            reason=f"Port {parsed.port} not allowed (only 80/443)",
        )

    # 4. Check cloud metadata hosts (exact match)
    if hostname.lower() in _CLOUD_METADATA_HOSTS:
        return SafeUrlResult(
            safe=False,
            reason=f"Cloud metadata endpoint blocked: {hostname}",
        )

    # 5. Check for "metadata" keyword in hostname
    if "metadata" in hostname.lower():
        return SafeUrlResult(
            safe=False,
            reason=f"Hostname contains 'metadata': {hostname}",
        )

    # 6. Check .local hostnames
    if hostname.lower().endswith(".local"):
        return SafeUrlResult(
            safe=False,
            reason=f"'.local' hostname blocked: {hostname}",
        )

    # 7. Check localhost variants
    if hostname.lower() in _HOSTNAME_LOCAL_BLOCKLIST:
        return SafeUrlResult(
            safe=False,
            reason=f"Localhost access forbidden: {hostname}",
        )

    # 8. Check if hostname is a bare IP address
    try:
        addr = ip_address(hostname)

        # Block all IPv4-mapped IPv6 addresses (SSRF bypass technique)
        if addr.version == 6 and addr.ipv4_mapped is not None:
            return SafeUrlResult(
                safe=False,
                reason=f"IPv4-mapped IPv6 address blocked: {hostname}",
            )

        if _is_private_ip(addr):
            return SafeUrlResult(
                safe=False,
                reason=f"Private IP address blocked: {hostname}",
            )

        # Public bare IP -- no DNS resolution needed
        resolved_ips = [str(addr)]
        return SafeUrlResult(safe=True, reason="OK", resolved_ips=resolved_ips)

    except ValueError:
        pass  # Not a bare IP, resolve below

    # 9. Resolve hostname to IP addresses (DNS lookup)
    try:
        resolved_ips = await _resolve_to_ips(hostname)
    except Exception as exc:
        return SafeUrlResult(
            safe=False,
            reason=f"DNS resolution failed: {exc}",
            resolved_ips=[],
        )

    if not resolved_ips:
        return SafeUrlResult(
            safe=False,
            reason="DNS resolution returned no addresses",
            resolved_ips=[],
        )

    # 10. Check each resolved IP against private/reserved ranges
    for ip_str in resolved_ips:
        try:
            addr = ip_address(ip_str)
        except ValueError:
            continue

        # Block all IPv4-mapped IPv6
        if addr.version == 6 and addr.ipv4_mapped is not None:
            return SafeUrlResult(
                safe=False,
                reason=f"Resolved to IPv4-mapped IPv6: {ip_str}",
                resolved_ips=resolved_ips,
            )

        # Block private/reserved IPs
        if _is_private_ip(addr):
            return SafeUrlResult(
                safe=False,
                reason=f"Resolved to private IP ({ip_str})",
                resolved_ips=resolved_ips,
            )

    return SafeUrlResult(safe=True, reason="OK", resolved_ips=resolved_ips)


# ── Internal helpers ───────────────────────────────────────────────


def _is_private_ip(addr) -> bool:
    """Check if an IP address belongs to a private/reserved range.

    Supports both IPv4 and IPv6 addresses.
    Handles IPv4-mapped IPv6 by unwrapping to the embedded IPv4 address.
    """
    # Unwrap IPv4-mapped IPv6 (::ffff:x.x.x.x) to the embedded IPv4
    if addr.version == 6 and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return any(addr in network for network in _PRIVATE_NETWORKS)


async def _resolve_to_ips(hostname: str) -> list[str]:
    """Resolve a hostname to a list of IP address strings.

    Uses a thread pool via ``run_in_executor`` to avoid blocking
    the event loop during DNS resolution.

    Returns an empty list if resolution fails.
    """
    loop = asyncio.get_running_loop()
    try:
        addrinfo = await loop.run_in_executor(
            None,
            socket.getaddrinfo,
            hostname,
            80,
        )
        seen: set[str] = set()
        result: list[str] = []
        for info in addrinfo:
            ip_str: str = info[4][0]
            if ip_str not in seen:
                seen.add(ip_str)
                result.append(ip_str)
        return result
    except OSError:
        return []
