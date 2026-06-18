"""
CPIS V1 — Safe URL tests (SSRF protection).

Covers:
- Regular public URLs pass
- 127.0.0.1 blocked
- 10.0.0.1 blocked
- 169.254.169.254 blocked
- ::1 blocked
- fc00::1 blocked
- IPv4-mapped IPv6 private blocked
- Public domain that resolves to private IP blocked
- metadata.google.internal blocked
- 100.100.100.200 (Alibaba Cloud) blocked
- Non-standard port (>1024) blocked
- FTP scheme blocked
- No DNS resolution triggers failure
- .local hostname blocked

All DNS resolution is mocked — no actual DNS lookups.
"""

from __future__ import annotations

import socket
from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

from app.security.safe_url import (
    _CLOUD_METADATA_HOSTS,
    _HOSTNAME_LOCAL_BLOCKLIST,
    _SAFE_PORTS,
    _SAFE_SCHEMES,
    SafeUrlResult,
    _is_private_ip,
    _resolve_to_ips,
    check_url_safe,
)

# ══════════════════════════════════════════════════════════════════
# 1. Constants validation
# ══════════════════════════════════════════════════════════════════


class TestConstants:
    def test_safe_schemes(self):
        assert "http" in _SAFE_SCHEMES
        assert "https" in _SAFE_SCHEMES
        assert len(_SAFE_SCHEMES) == 2

    def test_safe_ports(self):
        assert 80 in _SAFE_PORTS
        assert 443 in _SAFE_PORTS
        assert len(_SAFE_PORTS) == 2

    def test_cloud_metadata_hosts(self):
        assert "169.254.169.254" in _CLOUD_METADATA_HOSTS
        assert "metadata.google.internal" in _CLOUD_METADATA_HOSTS
        assert "100.100.100.200" in _CLOUD_METADATA_HOSTS
        assert "168.63.129.16" in _CLOUD_METADATA_HOSTS

    def test_local_blocklist(self):
        assert "localhost" in _HOSTNAME_LOCAL_BLOCKLIST
        assert "127.0.0.1" in _HOSTNAME_LOCAL_BLOCKLIST
        assert "::1" in _HOSTNAME_LOCAL_BLOCKLIST
        assert "0.0.0.0" in _HOSTNAME_LOCAL_BLOCKLIST


# ══════════════════════════════════════════════════════════════════
# 2. _is_private_ip tests
# ══════════════════════════════════════════════════════════════════


class TestIsPrivateIp:
    def test_loopback_ipv4(self):
        assert _is_private_ip(ip_address("127.0.0.1"))
        assert _is_private_ip(ip_address("127.0.0.0"))
        assert _is_private_ip(ip_address("127.255.255.255"))

    def test_class_a_private(self):
        assert _is_private_ip(ip_address("10.0.0.1"))
        assert _is_private_ip(ip_address("10.255.255.255"))

    def test_class_b_private(self):
        assert _is_private_ip(ip_address("172.16.0.1"))
        assert _is_private_ip(ip_address("172.31.255.255"))

    def test_class_c_private(self):
        assert _is_private_ip(ip_address("192.168.0.1"))
        assert _is_private_ip(ip_address("192.168.255.255"))

    def test_link_local(self):
        assert _is_private_ip(ip_address("169.254.0.1"))
        assert _is_private_ip(ip_address("169.254.169.254"))

    def test_cgnat(self):
        assert _is_private_ip(ip_address("100.64.0.1"))
        assert _is_private_ip(ip_address("100.127.255.255"))

    def test_benchmark(self):
        assert _is_private_ip(ip_address("198.18.0.1"))
        assert _is_private_ip(ip_address("198.19.255.255"))

    def test_current_network(self):
        assert _is_private_ip(ip_address("0.0.0.0"))

    def test_ipv6_loopback(self):
        assert _is_private_ip(ip_address("::1"))

    def test_ipv6_unique_local(self):
        assert _is_private_ip(ip_address("fc00::"))
        assert _is_private_ip(ip_address("fd00::1"))

    def test_ipv6_link_local(self):
        assert _is_private_ip(ip_address("fe80::1"))
        assert _is_private_ip(ip_address("fe80::"))

    def test_public_ip_not_private(self):
        assert not _is_private_ip(ip_address("8.8.8.8"))
        assert not _is_private_ip(ip_address("93.184.216.34"))
        assert not _is_private_ip(ip_address("1.1.1.1"))
        assert not _is_private_ip(ip_address("2001:4860:4860::8888"))

    def test_ipv4_mapped_ipv6_private(self):
        """IPv4-mapped IPv6 that wraps a private IPv4 is private."""
        # ::ffff:10.0.0.1 wraps 10.0.0.1 (class A private)
        addr = ip_address("::ffff:10.0.0.1")
        assert addr.ipv4_mapped == ip_address("10.0.0.1")
        assert _is_private_ip(addr)

    def test_ipv4_mapped_ipv6_public(self):
        """IPv4-mapped IPv6 that wraps a public IPv4 is NOT private
        (the mapped address itself is still flagged by check_url_safe)."""
        addr = ip_address("::ffff:8.8.8.8")
        assert addr.ipv4_mapped == ip_address("8.8.8.8")
        # For _is_private_ip, the unwrapped address is public
        # (but check_url_safe will still block it as IPv4-mapped IPv6)
        assert not _is_private_ip(addr)


# ══════════════════════════════════════════════════════════════════
# 3. check_url_safe — scheme & port validation
# ══════════════════════════════════════════════════════════════════


class TestSchemeAndPort:
    """Tests that don't need DNS resolution."""

    async def test_http_scheme_allowed(self):
        """http scheme is allowed for public IPs."""
        result = await check_url_safe("http://8.8.8.8")
        assert result.safe

    async def test_https_scheme_allowed(self):
        """https scheme is allowed."""
        result = await check_url_safe("https://8.8.8.8")
        assert result.safe

    async def test_ftp_scheme_blocked(self):
        """FTP scheme must be blocked."""
        result = await check_url_safe("ftp://example.com/file")
        assert not result.safe
        assert "scheme" in result.reason.lower()

    async def test_file_scheme_no_netloc_blocked(self):
        """file:// URLs (no netloc) are blocked."""
        result = await check_url_safe("file:///etc/passwd")
        assert not result.safe
        assert "scheme" in result.reason.lower() or "missing" in result.reason.lower()

    async def test_gopher_scheme_blocked(self):
        """Non-http/s schemes are blocked."""
        result = await check_url_safe("gopher://internal:8080/")
        assert not result.safe
        assert "scheme" in result.reason.lower()

    async def test_port_80_allowed(self):
        """Port 80 is allowed."""
        result = await check_url_safe("http://8.8.8.8:80")
        assert result.safe

    async def test_port_443_allowed(self):
        """Port 443 is allowed."""
        result = await check_url_safe("https://8.8.8.8:443")
        assert result.safe

    async def test_non_standard_port_blocked(self):
        """Port > 1024 (e.g. 8080, 3000) must be blocked."""
        result = await check_url_safe("http://8.8.8.8:8080")
        assert not result.safe
        assert "port" in result.reason.lower()

    async def test_port_21_blocked(self):
        """Port 21 (FTP) must be blocked."""
        result = await check_url_safe("http://8.8.8.8:21")
        assert not result.safe
        assert "port" in result.reason.lower()

    async def test_url_missing_netloc(self):
        """URL without netloc is rejected."""
        result = await check_url_safe("http:///path")
        assert not result.safe

    async def test_empty_url(self):
        """Empty string is rejected."""
        result = await check_url_safe("")
        assert not result.safe


# ══════════════════════════════════════════════════════════════════
# 4. check_url_safe — private / blocked bare IP addresses
# ══════════════════════════════════════════════════════════════════


class TestBareIpBlocking:
    """Tests for bare IP addresses (no DNS resolution needed)."""

    async def test_loopback_ipv4_blocked(self):
        """127.0.0.1 must be blocked."""
        result = await check_url_safe("http://127.0.0.1/")
        assert not result.safe
        assert "private" in result.reason.lower() or "localhost" in result.reason.lower()

    async def test_private_10_blocked(self):
        """10.0.0.1 must be blocked."""
        result = await check_url_safe("http://10.0.0.1/admin")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_private_172_16_blocked(self):
        """172.16.0.1 must be blocked."""
        result = await check_url_safe("http://172.16.0.1/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_private_192_168_blocked(self):
        """192.168.1.1 must be blocked."""
        result = await check_url_safe("http://192.168.1.1/admin")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_cloud_metadata_169_254_blocked(self):
        """169.254.169.254 (AWS/GCP/Azure metadata) must be blocked."""
        result = await check_url_safe("http://169.254.169.254/latest/meta-data")
        assert not result.safe
        assert "metadata" in result.reason.lower() or "private" in result.reason.lower()

    async def test_ipv6_loopback_blocked(self):
        """::1 (IPv6 loopback) must be blocked."""
        result = await check_url_safe("http://[::1]/")
        assert not result.safe

    async def test_ipv6_unique_local_blocked(self):
        """fc00::1 (IPv6 unique-local) must be blocked."""
        result = await check_url_safe("http://[fc00::1]/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_ipv6_unique_local_fd_blocked(self):
        """fd00::1 (IPv6 unique-local) must be blocked."""
        result = await check_url_safe("http://[fd00::1]/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_ipv6_link_local_blocked(self):
        """fe80::1 (IPv6 link-local) must be blocked."""
        result = await check_url_safe("http://[fe80::1]/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_public_ipv4_allowed(self):
        """Public IPv4 address (8.8.8.8) must be allowed."""
        result = await check_url_safe("http://8.8.8.8/")
        assert result.safe

    async def test_public_ipv6_allowed(self):
        """Public IPv6 address must be allowed."""
        result = await check_url_safe("http://[2001:4860:4860::8888]/")
        assert result.safe

    async def test_ipv4_mapped_ipv6_blocked(self):
        """IPv4-mapped IPv6 (::ffff:10.0.0.1) must be blocked."""
        result = await check_url_safe("http://[::ffff:10.0.0.1]/")
        assert not result.safe
        assert "ipv4-mapped" in result.reason.lower()

    async def test_ipv4_mapped_ipv6_public_blocked(self):
        """IPv4-mapped IPv6 even with public IP must be blocked."""
        result = await check_url_safe("http://[::ffff:8.8.8.8]/")
        assert not result.safe
        assert "ipv4-mapped" in result.reason.lower()

    async def test_cgnat_blocked(self):
        """100.64.0.1 (CGNAT) must be blocked."""
        result = await check_url_safe("http://100.64.0.1/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_benchmark_blocked(self):
        """198.18.0.1 (benchmark) must be blocked."""
        result = await check_url_safe("http://198.18.0.1/")
        assert not result.safe
        assert "private" in result.reason.lower()

    async def test_zero_dot_zero_blocked(self):
        """0.0.0.0 must be blocked."""
        result = await check_url_safe("http://0.0.0.0/")
        assert not result.safe


# ══════════════════════════════════════════════════════════════════
# 5. check_url_safe — hostname / metadata blocking
# ══════════════════════════════════════════════════════════════════


class TestHostnameBlocking:
    """Tests for hostname-based blocking (no DNS resolution needed)."""

    async def test_localhost_hostname_blocked(self):
        """Hostname 'localhost' must be blocked."""
        result = await check_url_safe("http://localhost/admin")
        assert not result.safe
        assert "localhost" in result.reason.lower()

    async def test_localhost_localdomain_blocked(self):
        """Hostname 'localhost.localdomain' must be blocked."""
        result = await check_url_safe("http://localhost.localdomain/")
        assert not result.safe
        assert "localhost" in result.reason.lower()

    async def test_metadata_google_internal_blocked(self):
        """metadata.google.internal must be blocked."""
        result = await check_url_safe("http://metadata.google.internal/computeMetadata/v1/")
        assert not result.safe
        assert "metadata" in result.reason.lower()

    async def test_alibaba_cloud_metadata_blocked(self):
        """100.100.100.200 (Alibaba Cloud) must be blocked."""
        result = await check_url_safe("http://100.100.100.200/latest/meta-data")
        assert not result.safe

    async def test_azure_imds_blocked(self):
        """168.63.129.16 (Azure IMDS) must be blocked."""
        result = await check_url_safe("http://168.63.129.16/")
        assert not result.safe
        assert "private" in result.reason.lower() or "metadata" in result.reason.lower()

    async def test_metadata_internal_blocked(self):
        """metadata.internal (GCP) must be blocked."""
        result = await check_url_safe("http://metadata.internal/")
        assert not result.safe
        assert "metadata" in result.reason.lower()

    async def test_metadata_azure_internal_blocked(self):
        """metadata.azure.internal must be blocked."""
        result = await check_url_safe("http://metadata.azure.internal/")
        assert not result.safe
        assert "metadata" in result.reason.lower()

    async def test_metadata_keyword_in_hostname_blocked(self):
        """Any hostname containing 'metadata' must be blocked."""
        result = await check_url_safe("http://metadata.something.internal/")
        assert not result.safe
        assert "metadata" in result.reason.lower()

    async def test_dot_local_hostname_blocked(self):
        """.local hostname must be blocked."""
        result = await check_url_safe("http://myhost.local/")
        assert not result.safe
        assert ".local" in result.reason.lower()

    async def test_anything_dot_local_blocked(self):
        """Hostname ending in .local must be blocked."""
        result = await check_url_safe("http://router.local/admin")
        assert not result.safe
        assert ".local" in result.reason.lower()


# ══════════════════════════════════════════════════════════════════
# 6. check_url_safe — DNS resolution tests (all mocked)
# ══════════════════════════════════════════════════════════════════


class TestDnsResolution:
    """Tests requiring mocked DNS resolution."""

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_public_domain_passes(self, mock_resolve):
        """A public domain resolving to a public IP passes."""
        mock_resolve.return_value = ["93.184.216.34"]
        result = await check_url_safe("https://example.com/product")
        assert result.safe
        assert "93.184.216.34" in result.resolved_ips

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_public_domain_multiple_ips(self, mock_resolve):
        """Domain with multiple public IPs passes."""
        mock_resolve.return_value = ["93.184.216.34", "93.184.216.35"]
        result = await check_url_safe("https://example.com")
        assert result.safe
        assert len(result.resolved_ips) == 2

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_domain_resolves_to_private_ip_blocked(self, mock_resolve):
        """Domain that resolves to a private IP (10.x.x.x) is blocked."""
        mock_resolve.return_value = ["10.0.0.99"]
        result = await check_url_safe("http://evil-internal.com/page")
        assert not result.safe
        assert "private" in result.reason.lower()
        assert "10.0.0.99" in result.reason

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_domain_resolves_to_loopback_blocked(self, mock_resolve):
        """Domain that resolves to 127.0.0.1 is blocked."""
        mock_resolve.return_value = ["127.0.0.1"]
        result = await check_url_safe("http://internal-redirect.com/")
        assert not result.safe
        assert "private" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_domain_resolves_to_mixed_private_and_public(self, mock_resolve):
        """Domain with mixed private+public IPs is blocked."""
        mock_resolve.return_value = ["8.8.8.8", "10.0.0.5"]
        result = await check_url_safe("http://mixed-domain.com/")
        assert not result.safe
        assert "private" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_domain_resolves_to_ipv6_link_local_blocked(self, mock_resolve):
        """Domain that resolves to IPv6 link-local is blocked."""
        mock_resolve.return_value = ["fe80::1"]
        result = await check_url_safe("http://ipv6-local.example.com/")
        assert not result.safe
        assert "private" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_domain_resolves_to_ipv4_mapped_ipv6_blocked(self, mock_resolve):
        """Domain that resolves to IPv4-mapped IPv6 is blocked."""
        mock_resolve.return_value = ["::ffff:10.0.0.1"]
        result = await check_url_safe("http://mapped-ipv6.example.com/")
        assert not result.safe
        assert "ipv4-mapped" in result.reason.lower() or "private" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_dns_resolution_failure_blocked(self, mock_resolve):
        """Failed DNS resolution blocks the URL."""
        mock_resolve.side_effect = Exception("DNS server timeout")
        result = await check_url_safe("http://nonexistent-domain-xyz123.com/")
        assert not result.safe
        assert "dns" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_dns_returns_empty_list_blocked(self, mock_resolve):
        """DNS returning no addresses blocks the URL."""
        mock_resolve.return_value = []
        result = await check_url_safe("http://empty-resolution.com/")
        assert not result.safe
        assert "no addresses" in result.reason.lower()

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_non_standard_port_with_public_domain_blocked(self, mock_resolve):
        """Domain with non-standard port is blocked regardless of DNS."""
        mock_resolve.return_value = ["93.184.216.34"]
        result = await check_url_safe("https://example.com:8080/path")
        assert not result.safe
        assert "port" in result.reason.lower()
        # DNS should not have been called since port check happens before DNS
        # But the current implementation checks port before DNS, so:
        # This test should pass because port is checked before resolve
        # but the mock is in place just in case

    @patch("app.security.safe_url._resolve_to_ips", new_callable=AsyncMock)
    async def test_subdomain_of_public_domain_passes(self, mock_resolve):
        """Subdomain resolving to public IP passes."""
        mock_resolve.return_value = ["93.184.216.34"]
        result = await check_url_safe("https://sub.example.com/path?q=1")
        assert result.safe


# ══════════════════════════════════════════════════════════════════
# 7. _resolve_to_ips tests (integration-light, mock socket)
# ══════════════════════════════════════════════════════════════════


class TestResolveToIps:
    """Tests for _resolve_to_ips with mocked socket.getaddrinfo."""

    @patch("app.security.safe_url.socket.getaddrinfo")
    async def test_resolve_single_ip(self, mock_getaddrinfo):
        """Resolving a hostname with one IP returns that IP."""
        mock_getaddrinfo.return_value = [
            (socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
        ]
        ips = await _resolve_to_ips("example.com")
        assert ips == ["93.184.216.34"]

    @patch("app.security.safe_url.socket.getaddrinfo")
    async def test_resolve_multiple_ips_dedup(self, mock_getaddrinfo):
        """Duplicate IPs are deduplicated."""
        mock_getaddrinfo.return_value = [
            (socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
            (socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
            (socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM, 0, "", ("93.184.216.35", 80)),
        ]
        ips = await _resolve_to_ips("example.com")
        assert len(ips) == 2
        assert "93.184.216.34" in ips
        assert "93.184.216.35" in ips

    @patch("app.security.safe_url.socket.getaddrinfo")
    async def test_resolve_ipv6(self, mock_getaddrinfo):
        """IPv6 addresses are returned correctly."""
        mock_getaddrinfo.return_value = [
            (socket.AddressFamily.AF_INET6, socket.SocketKind.SOCK_STREAM, 0, "", ("2001:db8::1", 80, 0, 0)),
        ]
        ips = await _resolve_to_ips("ipv6.example.com")
        assert ips == ["2001:db8::1"]

    @patch("app.security.safe_url.socket.getaddrinfo")
    async def test_resolve_failure_oserror(self, mock_getaddrinfo):
        """OSError during resolution returns empty list."""
        mock_getaddrinfo.side_effect = OSError("Name or service not known")
        ips = await _resolve_to_ips("nonexistent.example.com")
        assert ips == []

    @patch("app.security.safe_url.socket.getaddrinfo")
    async def test_resolve_mixed_ipv4_ipv6(self, mock_getaddrinfo):
        """Mixed IPv4 and IPv6 results are both returned."""
        mock_getaddrinfo.return_value = [
            (socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM, 0, "", ("93.184.216.34", 80)),
            (socket.AddressFamily.AF_INET6, socket.SocketKind.SOCK_STREAM, 0, "", ("2606:2800:220:1:248:1893:25c8:1946", 80, 0, 0)),
        ]
        ips = await _resolve_to_ips("example.com")
        assert len(ips) == 2
        assert "93.184.216.34" in ips
        assert "2606:2800:220:1:248:1893:25c8:1946" in ips


# ══════════════════════════════════════════════════════════════════
# 8. SafeUrlResult dataclass
# ══════════════════════════════════════════════════════════════════


class TestSafeUrlResult:
    def test_safe_result(self):
        result = SafeUrlResult(safe=True, reason="OK", resolved_ips=["8.8.8.8"])
        assert result.safe
        assert result.reason == "OK"
        assert result.resolved_ips == ["8.8.8.8"]

    def test_unsafe_result(self):
        result = SafeUrlResult(safe=False, reason="Blocked", resolved_ips=[])
        assert not result.safe
        assert result.reason == "Blocked"

    def test_default_reason(self):
        result = SafeUrlResult(safe=True)
        assert result.safe
        assert result.reason == ""

    def test_default_resolved_ips(self):
        result = SafeUrlResult(safe=False)
        assert result.resolved_ips == []


# ══════════════════════════════════════════════════════════════════
# 9. Edge cases
# ══════════════════════════════════════════════════════════════════


class TestEdgeCases:
    async def test_url_with_query_string(self):
        """URL with query string on public IP passes."""
        result = await check_url_safe("https://8.8.8.8/path?q=search&page=1")
        assert result.safe

    async def test_url_with_fragment(self):
        """URL with fragment on public IP passes."""
        result = await check_url_safe("https://8.8.8.8/page#section")
        assert result.safe

    async def test_url_with_auth(self):
        """URL with embedded credentials."""
        result = await check_url_safe("http://user:pass@8.8.8.8/")
        assert result.safe

    async def test_malformed_url_scheme_only(self):
        """Scheme-only URL is rejected."""
        result = await check_url_safe("http://")
        assert not result.safe

    async def test_almost_private_ip(self):
        """172.32.0.1 is just outside class B private range and is allowed."""
        result = await check_url_safe("http://172.32.0.1/")
        assert result.safe

    async def test_just_above_cgnat(self):
        """100.128.0.1 is just above CGNAT range and is allowed."""
        result = await check_url_safe("http://100.128.0.1/")
        assert result.safe

    async def test_https_with_default_port_443(self):
        """Explicit port 443 with https is fine."""
        result = await check_url_safe("https://8.8.8.8:443/api")
        assert result.safe

    async def test_http_with_default_port_80(self):
        """Explicit port 80 with http is fine."""
        result = await check_url_safe("http://8.8.8.8:80/")
        assert result.safe
