"""Tests for Failure Intelligence."""
from __future__ import annotations

import pytest

from app.collectors.failure_intelligence import FailureAnalysis, analyze_failure


class TestFailureIntelligence:
    """Comprehensive tests for analyze_failure and FailureAnalysis."""

    def test_dns_failure_by_name(self):
        """Detect DNS failure from 'Name or service not known' error."""
        result = analyze_failure("Name or service not known")
        assert result.failure_type == "dns_failure"
        assert not result.retryable
        assert result.suggested_next == "search_alternative"

    def test_dns_failure_by_nodename(self):
        """Detect DNS failure from 'nodename nor servname' error."""
        result = analyze_failure("nodename nor servname provided")
        assert result.failure_type == "dns_failure"

    def test_dns_failure_by_getaddrinfo(self):
        """Detect DNS failure from 'getaddrinfo' error."""
        result = analyze_failure("getaddrinfo failed for example.com")
        assert result.failure_type == "dns_failure"

    def test_dns_failure_by_resolution(self):
        """Detect DNS failure from 'temporary failure in name resolution'."""
        result = analyze_failure("Temporary failure in name resolution")
        assert result.failure_type == "dns_failure"

    def test_http_403_detection(self):
        """HTTP 403 → http_error, retryable, retry_ua_rotate."""
        result = analyze_failure("Forbidden", http_status=403)
        assert result.failure_type == "http_error"
        assert result.retryable
        assert result.suggested_next == "retry_ua_rotate"

    def test_http_404_detection(self):
        """HTTP 404 → http_error, not retryable, skip_permanent."""
        result = analyze_failure("Not found", http_status=404)
        assert result.failure_type == "http_error"
        assert not result.retryable
        assert result.suggested_next == "skip_permanent"

    def test_http_429_detection(self):
        """HTTP 429 → http_error, retryable, retry_same."""
        result = analyze_failure("Too many requests", http_status=429)
        assert result.failure_type == "http_error"
        assert result.retryable
        assert result.suggested_next == "retry_same"

    def test_http_503_detection(self):
        """HTTP 503 → http_error, retryable, retry_same."""
        result = analyze_failure("Service unavailable", http_status=503)
        assert result.failure_type == "http_error"
        assert result.retryable
        assert result.suggested_next == "retry_same"

    def test_timeout_detection_lowercase(self):
        """Detect timeout from 'timeout' in error message."""
        result = analyze_failure("Connection timed out")
        assert result.failure_type == "timeout"
        assert result.retryable
        assert result.suggested_next == "retry_same"

    def test_timeout_detection_timed_out(self):
        """Detect timeout from 'timed out' in error message."""
        result = analyze_failure("The request timed out after 30s")
        assert result.failure_type == "timeout"
        assert result.retryable

    def test_empty_response_detection(self):
        """Detect empty content from 'empty' in error message."""
        result = analyze_failure("Response contained no content", http_status=200)
        assert result.failure_type == "empty_content"
        assert result.retryable
        assert result.suggested_next == "retry_playwright"

    def test_empty_blank_detection(self):
        """Detect empty content from 'blank' in error message."""
        result = analyze_failure("Blank response received")
        assert result.failure_type == "empty_content"

    def test_empty_no_content_detection(self):
        """Detect empty content from 'no content' in error message."""
        result = analyze_failure("No content returned from server")
        assert result.failure_type == "empty_content"

    def test_blocked_source_detection(self):
        """Detect blocked source from 'blocked' in error message."""
        result = analyze_failure("The request was blocked by firewall")
        assert result.failure_type == "blocked_source"
        assert not result.retryable

    def test_forbidden_blocked_detection(self):
        """Detect blocked source from 'forbidden' in error message."""
        result = analyze_failure("Forbidden access")
        assert result.failure_type == "blocked_source"

    def test_connection_refused_detection(self):
        """Detect connection refused from 'connection refused' in error."""
        result = analyze_failure("Connection refused by remote server")
        assert result.failure_type == "connection_refused"
        assert result.retryable
        assert result.suggested_next == "retry_same"

    def test_connect_error_detection(self):
        """Detect connection error from 'connect' in error message."""
        result = analyze_failure("Failed to connect to host")
        assert result.failure_type == "connection_refused"

    def test_unknown_failure(self):
        """Unrecognized errors → unknown, not retryable, check_manually."""
        result = analyze_failure("Some weird unexpected error occurred")
        assert result.failure_type == "unknown"
        assert not result.retryable
        assert result.suggested_next == "check_manually"

    def test_empty_error_message_unknown(self):
        """Empty error message → unknown."""
        result = analyze_failure("")
        assert result.failure_type == "unknown"

    def test_content_type_preserved(self):
        """Content-Type is preserved in the FailureAnalysis."""
        result = analyze_failure(
            "Forbidden",
            http_status=403,
            content_type="text/html",
        )
        assert result.content_type == "text/html"

    def test_http_status_preserved(self):
        """HTTP status is preserved in the FailureAnalysis."""
        result = analyze_failure("Not found", http_status=404)
        assert result.http_status == 404

    def test_blocked_reason_truncation(self):
        """Blocked reason is truncated to 500 chars."""
        long_msg = "x" * 1000
        result = analyze_failure(long_msg)
        assert len(result.blocked_reason) <= 500

    def test_http_status_overrides_error_message(self):
        """HTTP status code takes precedence over error message keywords."""
        result = analyze_failure("Connection timed out", http_status=403)
        # 403 should take precedence
        assert result.failure_type == "http_error"
        assert result.http_status == 403
        assert result.suggested_next == "retry_ua_rotate"

    def test_failure_analysis_dataclass_defaults(self):
        """FailureAnalysis has sensible defaults."""
        fa = FailureAnalysis()
        assert fa.failure_type == ""
        assert not fa.retryable
        assert fa.suggested_next == ""
        assert fa.blocked_reason == ""
        assert fa.user_visible_message == ""
        assert fa.http_status == 0
        assert fa.content_type == ""
        assert fa.retry_after_seconds is None
