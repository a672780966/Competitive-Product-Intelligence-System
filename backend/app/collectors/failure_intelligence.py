"""Failure Intelligence — classify and analyze collection failures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FailureAnalysis:
    """Structured analysis of a collection failure.

    Provides actionable information about why a fetch failed,
    whether it's retryable, and what the next step should be.
    """

    failure_type: str = ""  # dns_failure | http_error | timeout | empty_content | content_too_large | ...
    retryable: bool = False
    suggested_next: str = ""  # retry_same | retry_ua_rotate | retry_playwright | ...
    blocked_reason: str = ""
    user_visible_message: str = ""
    http_status: int = 0
    content_type: str = ""
    retry_after_seconds: Optional[int] = None


FAILURE_CLASSIFICATION: dict[str, dict[str, object]] = {
    "DNS_FAILURE": {
        "failure_type": "dns_failure",
        "retryable": False,
        "suggested_next": "search_alternative",
        "user_visible_message": "域名解析失败，网站可能已关闭或域名已过期",
    },
    "HTTP_403": {
        "failure_type": "http_error",
        "retryable": True,
        "suggested_next": "retry_ua_rotate",
        "user_visible_message": "服务器返回403禁止访问，尝试更换User-Agent或使用浏览器渲染",
    },
    "HTTP_404": {
        "failure_type": "http_error",
        "retryable": False,
        "suggested_next": "skip_permanent",
        "user_visible_message": "页面不存在(404)，该URL可能已失效",
    },
    "HTTP_429": {
        "failure_type": "http_error",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "请求频率过高，请稍后重试",
    },
    "HTTP_503": {
        "failure_type": "http_error",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "服务暂不可用，请稍后重试",
    },
    "TIMEOUT": {
        "failure_type": "timeout",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "请求超时，网站响应较慢",
    },
    "EMPTY_RESPONSE": {
        "failure_type": "empty_content",
        "retryable": True,
        "suggested_next": "retry_playwright",
        "user_visible_message": "获取到空内容，可能需要JavaScript渲染",
    },
    "CONTENT_TOO_LARGE": {
        "failure_type": "content_too_large",
        "retryable": False,
        "suggested_next": "skip_permanent",
        "user_visible_message": "内容过大，已跳过",
    },
    "BLOCKED_SOURCE": {
        "failure_type": "blocked_source",
        "retryable": False,
        "suggested_next": "skip_permanent",
        "user_visible_message": "该来源已被安全策略拦截",
    },
    "CONNECT_ERROR": {
        "failure_type": "connection_refused",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "无法连接目标服务器",
    },
    "UNKNOWN": {
        "failure_type": "unknown",
        "retryable": False,
        "suggested_next": "check_manually",
        "user_visible_message": "未知错误，请手动检查",
    },
}


def analyze_failure(
    error_message: str = "",
    http_status: int = 0,
    content_type: str = "",
) -> FailureAnalysis:
    """Analyze a failure reason and return a structured FailureAnalysis.

    Args:
        error_message: The error message from the fetch attempt.
        http_status: HTTP status code (0 if not applicable).
        content_type: Content-Type of the response (if available).

    Returns:
        A FailureAnalysis with classification, retryability, and suggested action.
    """
    error_lower = error_message.lower()

    if http_status == 403:
        cls = FAILURE_CLASSIFICATION["HTTP_403"]
    elif http_status == 404:
        cls = FAILURE_CLASSIFICATION["HTTP_404"]
    elif http_status == 429:
        cls = FAILURE_CLASSIFICATION["HTTP_429"]
    elif http_status == 503:
        cls = FAILURE_CLASSIFICATION["HTTP_503"]
    elif (
        "name or service not known" in error_lower
        or "nodename nor servname" in error_lower
        or "getaddrinfo" in error_lower
        or "temporary failure in name resolution" in error_lower
    ):
        cls = FAILURE_CLASSIFICATION["DNS_FAILURE"]
    elif "timeout" in error_lower or "timed out" in error_lower:
        cls = FAILURE_CLASSIFICATION["TIMEOUT"]
    elif "empty" in error_lower or "blank" in error_lower or "no content" in error_lower:
        cls = FAILURE_CLASSIFICATION["EMPTY_RESPONSE"]
    elif "blocked" in error_lower or "forbidden" in error_lower:
        cls = FAILURE_CLASSIFICATION["BLOCKED_SOURCE"]
    elif "connect" in error_lower or "connection refused" in error_lower:
        cls = FAILURE_CLASSIFICATION["CONNECT_ERROR"]
    else:
        cls = FAILURE_CLASSIFICATION["UNKNOWN"]

    return FailureAnalysis(
        failure_type=str(cls["failure_type"]),
        retryable=bool(cls["retryable"]),
        suggested_next=str(cls["suggested_next"]),
        user_visible_message=str(cls["user_visible_message"]),
        http_status=http_status,
        content_type=content_type,
        blocked_reason=error_message[:500] if error_message else "",
    )
