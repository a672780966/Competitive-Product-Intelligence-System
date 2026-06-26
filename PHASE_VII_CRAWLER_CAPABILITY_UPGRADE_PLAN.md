# Phase VII: Crawler Capability Upgrade — 完整实施计划

**版本:** v1.0
**日期:** 2026-06-26
**工作目录:** `/home/ctyun/Competitive-Product-Intelligence-System`
**前置依赖:** Phase III-B (马登工装补测)、Phase V (Collector Runtime 架构)

---

## 目录

1. [当前 DirectHttpCollector 代码审计](#1-当前-directhttpcollector-代码审计)
2. [马登工装 3 个 URL 失败根因分析](#2-马登工装-3-个-url-失败根因分析)
3. [DirectHttpCollector 增强方案](#3-directhttpcollector-增强方案)
4. [Failure Intelligence 数据模型](#4-failure-intelligence-数据模型)
5. [Sitemap/RSS/Robots Discovery 实现方案](#5-sitemaprssrobots-discovery-实现方案)
6. [Playwright/Scrapling/Crawl4AI 集成方案](#6-playwrightscraplingcrawl4ai-集成方案)
7. [测试方案](#7-测试方案)
8. [文件清单](#8-文件清单)
9. [验证标准](#9-验证标准)
10. [实施顺序与不接受清单](#10-实施顺序与不接受清单)

---

## 1. 当前 DirectHttpCollector 代码审计

### 1.1 源文件

```
backend/app/collectors/direct_http.py  (141 行)
backend/app/collectors/base.py         (51 行)
backend/app/collectors/registry.py     (393 行)
backend/app/collectors/httpx_collector.py (150 行 — 旧版, 与 direct_http 几乎重复)
```

### 1.2 当前能力矩阵

| 能力 | 当前状态 | 问题 |
|------|---------|------|
| **httpx fetch** | ✅ 有 | `httpx.AsyncClient` GET |
| **User-Agent** | ⚠️ 单一 | 仅 `settings.COLLECTION_USER_AGENT`，无轮换/UA 池 |
| **Timeout** | ⚠️ 硬编码默认 20s | 参数可传 `timeout=`, 但无连接/读取分别超时 |
| **Follow Redirects** | ✅ 有 | `follow_redirects=True, max_redirects=5` |
| **HTTP 状态码检查** | ✅ 有 | `>= 400` 判定失败 |
| **内容大小检查** | ✅ 有 | `MAX_HTML_BYTES = 10MB` |
| **DNS 错误检测** | ✅ 有 | 通过 `ConnectError` 字串匹配 |
| **超时错误** | ✅ 有 | `TimeoutException` 捕获 |
| **SHA-256 哈希** | ✅ 有 | `_hash_content()` |
| **Title 提取** | ✅ 有 | 通过字符串搜索 `<title>` |
| **Charset 检测/解码** | ❌ 无 | 硬编码 `utf-8` decode, 未读 `Content-Type` charset |
| **gzip/brotli 自动解压** | ❌ 无 | httpx 默认解压，但未显式处理 `Accept-Encoding` |
| **Content-Type 判断** | ❌ 无 | 不检查是否为 HTML/JSON/PDF |
| **Retry 延时** | ❌ 无 | RetryPolicy 只返回最大次数，无退避逻辑 |
| **Cookies** | ❌ 无 | 不支持 session/cookies |
| **自定义 Headers** | ❌ 无 | 仅 User-Agent，不支持从 kwargs 传入额外 headers |
| **robots.txt 检查** | ❌ 无 | collector 自身不检查（url_validator 做此检查） |
| **连接复用** | ❌ 每调用新建 client | `async with httpx.AsyncClient()` 每次新建 |
| **Referer / Origin** | ❌ 无 | 无反爬伪装 header |

### 1.3 与旧版 HttpxCollector 的关系

`HttpxCollector` (base.py 的 BaseCollector 子类) 与 `DirectHttpCollector` (registry.py 的 BaseCollectorProvider 子类) 功能几乎完全相同。DirectHttpCollector 是 "新版" — 用于 registry 体系。HttpxCollector 保留给旧版 selector 的 `fetch()` 方法。Phase VII 只需增强 `DirectHttpCollector`，旧版保持不动。

### 1.4 执行报告集成

当前 `CollectorExecutionReport` 模型有 13 个字段，缺 Failure Intelligence 专用字段：

| 现有字段 | 类型 |
|---------|------|
| id, task_id, snapshot_id | UUID |
| collector_runtime | str(64) |
| url | str(2048) |
| status | str(16) |
| started_at, finished_at | datetime |
| duration_ms | int |
| content_size | int |
| retry_count | int |
| error_message | Text |

---

## 2. 马登工装 3 个 URL 失败根因分析

来自 Phase III-B 真实采集结果 (`P0_IIIB_FINAL_EVIDENCE.md`):

### 2.1 madenwear.com — DNS 解析失败

| 维度 | 值 |
|------|-----|
| **URL** | `https://madenwear.com` |
| **错误** | `httpx.ConnectError("[Errno -2] Name or service not known")` |
| **技术原因** | 域名 A/AAAA 记录不存在，DNS NXDOMAIN |
| **业务原因** | 域名可能已停用/过期/未注册 |
| **失败分类** | `DNS_FAILURE` |
| **是否可重试** | 否 — 域名不存在则短期不会恢复 |
| **替代策略** | 搜索 `madenwear.com` 的 Wayback Machine / 域名 whois 查询 |
| **robots.txt** | 不可达（DNS 不可达） |
| **collector** | direct_http |

### 2.2 baike.baidu.com — HTTP 403 Forbidden

| 维度 | 值 |
|------|-----|
| **URL** | `https://baike.baidu.com/item/马登/9266132` |
| **错误** | `HTTP 403` |
| **技术原因** | 百度百科 WAF/反爬拦截，检测到非浏览器 User-Agent |
| **业务原因** | 百度百科有严格的反爬策略，需要合适的 UA + Cookie + Referer |
| **失败分类** | `HTTP_FORBIDDEN` (403) |
| **是否可重试** | 是 — 更换 UA + 加 Referer/headers 后可能成功 |
| **替代策略** | (1) 增强 DirectHttpCollector UA 轮换 + Referer<br>(2) Playwright JS 渲染<br>(3) 设置 `Accept-Language: zh-CN,zh;q=0.9` |
| **robots.txt** | `https://baike.baidu.com/robots.txt` — 可能有 `/item/*` 限制 |
| **collector** | direct_http |

### 2.3 post.smzdm.com — 获取内容失败

| 维度 | 值 |
|------|-----|
| **URL** | `https://post.smzdm.com/p/akxw4nx4/` |
| **错误** | 获取内容失败（可能是 HTTP 非 200 或内容为空） |
| **技术原因** | 什么值得买有 Cloudflare/WAF 防护，需要 JS 渲染或特殊 headers |
| **业务原因** | 公开内容但 CDN/WAF 拦截非浏览器请求 |
| **失败分类** | `FETCH_FAILED` / `EMPTY_RESPONSE` |
| **是否可重试** | 是 — 使用 Playwright JS 渲染后可成功 |
| **替代策略** | (1) Playwright 渲染<br>(2) 设置完整的浏览器 headers 包 |
| **robots.txt** | `https://post.smzdm.com/robots.txt` — 可能允许 |
| **collector** | direct_http → fallback **playwright** (feature flag 关闭) |

### 2.4 站点失败分类总表

| 站点 | URL | 失败类型 | 原因分类 | Retryable | 建议方案 |
|------|-----|---------|---------|-----------|---------|
| madenwear.com | 官网 | `DNS_FAILURE` | 域名失效 | ❌ | 搜 Wayback Machine |
| baike.baidu.com | 百科页 | `HTTP_403` | WAF 反爬 | ✅ | UA 轮换 + Header 增强 |
| post.smzdm.com | 值得买 | `FETCH_FAILED` | JS 渲染/Cloudflare | ✅ | Playwright 渲染 |

---

## 3. DirectHttpCollector 增强方案

### 3.1 增强内容概要

对 `backend/app/collectors/direct_http.py` 进行 8 项增强:

```
direct_http.py (当前 141 行 → 约 350 行)
├── UA 轮换池 (改进)
├── 连接/读取分隔超时 (改进)
├── gzip/brotli 显式处理 (新增)
├── Charset 自动检测 (新增)
├── Content-Type 智能判断 (新增)
├── Referer/Origin/Accept 伪装 (新增)
├── Retry delay + 退避 (新增)
└── Failure Intelligence 集成 (新增)
```

### 3.2 具体代码修改

#### 3.2.1 UA 轮换池

```python
# 在 direct_http.py 顶部新增
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0",
]
import random

def _select_user_agent(configured_ua: str) -> str:
    """返回配置 UA 或随机轮换 UA."""
    # 如果配置了自定义 UA 且非默认，则使用配置值
    if configured_ua and configured_ua not in ("CPIS-Bot/1.0", ""):
        return configured_ua
    return random.choice(_USER_AGENTS)
```

#### 3.2.2 分隔超时 (连接 vs 读取)

```python
# 替换当前的 timeout=kwargs.get("timeout", 20)
read_timeout = kwargs.get("timeout", 20)
connect_timeout = kwargs.get("connect_timeout", 10)
timeout_config = httpx.Timeout(
    connect=connect_timeout,
    read=read_timeout,
    write=10,
    pool=5,
)
```

#### 3.2.3 gzip/brotli 显式处理

```python
# 在 headers 中添加 Accept-Encoding
headers = {
    "User-Agent": ua,
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
# httpx 默认自动解压，但显式请求确保服务端发送压缩版本
```

#### 3.2.4 Charset 自动检测

```python
import re
import chardet  # 新增依赖

def _detect_charset(response_headers: dict, raw_content: bytes) -> str:
    """检测响应字符集."""
    # 1. Content-Type header
    ct = response_headers.get("content-type", "")
    m = re.search(r'charset\s*=\s*([\w-]+)', ct, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # 2. HTML meta charset
    meta_match = re.search(
        rb'<meta[^>]+charset\s*=\s*["\']?([\w-]+)',
        raw_content[:4096], re.IGNORECASE
    )
    if meta_match:
        return meta_match.group(1).decode().lower()
    # 3. chardet 检测
    detected = chardet.detect(raw_content[:10000])
    if detected and detected.get("encoding") and detected["confidence"] > 0.5:
        return detected["encoding"].lower()
    return "utf-8"

def _decode_content(raw: bytes, charset: str) -> str:
    """按检测到的 charset 解码内容."""
    try:
        return raw.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")
```

#### 3.2.5 Content-Type 智能判断

```python
def _classify_content_type(response_headers: dict) -> str:
    """判断响应内容类型: html / json / xml / pdf / image / other."""
    ct = response_headers.get("content-type", "").lower()
    if "text/html" in ct:
        return "html"
    if "application/json" in ct or "text/json" in ct:
        return "json"
    if "application/xml" in ct or "text/xml" in ct:
        return "xml"
    if "application/pdf" in ct:
        return "pdf"
    if "image/" in ct:
        return "image"
    if "text/plain" in ct:
        return "text"
    return "other"
```

#### 3.2.6 完整浏览器 Headers 伪装

```python
# 构建浏览器级 headers 包
def _build_headers(url: str, configured_ua: str) -> dict[str, str]:
    ua = _select_user_agent(configured_ua)
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.hostname}/"
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": referer,
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "DNT": "1",
    }
```

#### 3.2.7 Retry 延迟 + 指数退避

```python
# 在 fetch() 外层添加重试循环
async def fetch(self, url: str, **kwargs: Any) -> CollectResult:
    max_retries = kwargs.get("max_retries", 2)
    base_delay = kwargs.get("retry_base_delay", 1.0)
    
    for attempt in range(max_retries + 1):
        result = await self._do_fetch(url, **kwargs)
        if result.success:
            return result
        if not self._is_retryable(result):
            return result
        if attempt < max_retries:
            delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
            await asyncio.sleep(delay)
    return result

def _is_retryable(self, result: CollectResult) -> bool:
    """判断失败是否可重试."""
    retryable_codes = {"FETCH_TIMEOUT", "HTTP_429", "HTTP_503", "HTTP_403"}
    return result.error_code in retryable_codes
```

#### 3.2.8 Fetch result 增强 — Failure Intelligence 字段

```python
# 增强 CollectResult 增加 failure_intelligence 字段
@dataclass
class FailureIntelligence:
    failure_type: str = ""        # dns_failure / http_error / timeout / empty / too_large / blocked / unknown
    retryable: bool = False       # 是否可重试
    suggested_next: str = ""      # playwright / ua_rotate / skip / search_alternative
    blocked_reason: str = ""      # 更底层的阻塞原因
    user_visible_message: str = ""  # 用户可读的错误消息
    http_status: int = 0
    content_type: str = ""
```

### 3.3 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `app/collectors/direct_http.py` | **重写** ~350行 | 全部 8 项增强 |
| `app/collectors/base.py` | **修改** CollectResult | 增加 `failure_intelligence` 可选字段 |
| `app/collectors/registry.py` | **修改** CollectResult | 增加 `failure_intelligence` 可选字段 |
| `pyproject.toml` / `requirements.txt` | **新增依赖** | `chardet` 用于字符集检测 |

---

## 4. Failure Intelligence 数据模型

### 4.1 核心数据类

```python
# backend/app/collectors/failure_intelligence.py (新建)

@dataclass
class FailureAnalysis:
    """失败智能分析结果."""
    failure_type: str                    # dns_failure | http_error | timeout | empty_content | 
                                         # content_too_large | blocked_source | login_required | 
                                         # captcha_detected | connection_refused | unknown
    retryable: bool                      # 是否可以通过重试/更换策略恢复
    suggested_next: str                  # retry_same | retry_ua_rotate | retry_playwright | 
                                         # retry_scrapling | skip_permanent | search_alternative |
                                         # check_manually
    blocked_reason: str                  # 阻塞的详细技术原因
    user_visible_message: str            # 用户可见的简短中文/英文消息
    http_status: int = 0
    content_type: str = ""
    retry_after_seconds: int | None = None  # 建议多久后重试
```

### 4.2 Failure Type 分类逻辑

```python
FAILURE_CLASSIFICATION = {
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
        "user_visible_message": "请求过于频繁，等待后重试",
    },
    "HTTP_503": {
        "failure_type": "http_error",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "服务器暂时不可用，等待后重试",
    },
    "HTTP_4XX": {
        "failure_type": "http_error",
        "retryable": False,
        "suggested_next": "skip_permanent",
        "user_visible_message": "客户端请求错误",
    },
    "HTTP_5XX": {
        "failure_type": "http_error",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "服务器内部错误，等待后重试",
    },
    "FETCH_TIMEOUT": {
        "failure_type": "timeout",
        "retryable": True,
        "suggested_next": "retry_same",
        "user_visible_message": "请求超时，网络连接可能不稳定",
    },
    "CONTENT_TOO_LARGE": {
        "failure_type": "content_too_large",
        "retryable": False,
        "suggested_next": "skip_permanent",
        "user_visible_message": "内容超过大小限制(10MB)",
    },
    "CAPTCHA_DETECTED": {
        "failure_type": "captcha_detected",
        "retryable": False,
        "suggested_next": "check_manually",
        "user_visible_message": "检测到验证码，无法自动采集",
    },
    "LOGIN_REQUIRED": {
        "failure_type": "login_required",
        "retryable": False,
        "suggested_next": "search_alternative",
        "user_visible_message": "需要登录才能访问该页面",
    },
    "EMPTY_RESPONSE": {
        "failure_type": "empty_content",
        "retryable": True,
        "suggested_next": "retry_playwright",
        "user_visible_message": "返回内容为空，可能需JS渲染",
    },
    "CONNECTION_REFUSED": {
        "failure_type": "connection_refused",
        "retryable": False,
        "suggested_next": "search_alternative",
        "user_visible_message": "连接被拒绝，网站可能已下线或拦截了该请求",
    },
}
```

### 4.3 分析函数

```python
def analyze_failure(
    error_code: str | None,
    http_status: int,
    fetch_time_ms: int,
    content_length: int,
    response_headers: dict,
) -> FailureAnalysis:
    """
    对一次失败的 fetch 进行分析，返回 FailureAnalysis.
    
    输入: 来自 CollectResult 的字段
    输出: FailureAnalysis 包含 failure_type/retryable/suggested_next/blocked_reason/user_visible_message
    """
    ...

# 添加到 CollectResult:
# 在 DirectHttpCollector._do_fetch() 末尾，如果失败，调用 analyze_failure()
# 将结果存入 CollectResult.failure_intelligence
```

### 4.4 存储集成 — CollectorExecutionReport 模型扩展

```python
# 修改 backend/app/models/collector_execution_report.py
# 新增字段:
failure_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
retryable: Mapped[bool | None] = mapped_column(nullable=True)
suggested_next: Mapped[str | None] = mapped_column(String(48), nullable=True)
blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
user_visible_message: Mapped[str | None] = mapped_column(String(256), nullable=True)
```

需要对应的 Alembic migration 添加这 5 个字段。

### 4.5 Failure Intelligence 输出到 CollectorExecutionReport

在 `tasks/collection.py` 的 `_do_collect()` 中，当 fetch 失败时：

```python
# 在 report 写入时同时写入 failure_intelligence 字段
if not result.success and hasattr(result, 'failure_intelligence') and result.failure_intelligence:
    fi = result.failure_intelligence
    report.failure_type = fi.failure_type
    report.retryable = fi.retryable
    report.suggested_next = fi.suggested_next
    report.blocked_reason = fi.blocked_reason
    report.user_visible_message = fi.user_visible_message
```

---

## 5. Sitemap/RSS/Robots Discovery 实现方案

### 5.1 现状

当前 `RunPlanExecutor._resolve_urls()` 对 `sitemap` 和 `search` 类型仅输出 "MVP skippped" 日志，无实际实现。

### 5.2 Sitemap Discovery (新建)

**新增文件:** `backend/app/collectors/discovery/sitemap_discovery.py`

```python
"""
Sitemap Discovery — 从 sitemap.xml / robots.txt 发现公开 URL.

默认限制: ≤10 条 URL (受 run_plan scope.max_pages 控制)
不采集, 仅发现.
"""

from __future__ import annotations
import asyncio
import re
import httpx
from xml.etree import ElementTree
from urllib.parse import urljoin
from dataclasses import dataclass, field

@dataclass
class SitemapResult:
    success: bool
    urls: list[str] = field(default_factory=list)
    error: str = ""
    total_found: int = 0

class SitemapDiscoverer:
    """从 sitemap.xml / robots.txt 发现公开 URL."""
    
    DEFAULT_TIMEOUT = 15
    DEFAULT_MAX_URLS = 10
    
    async def discover(
        self, 
        base_url: str, 
        *,
        max_urls: int = DEFAULT_MAX_URLS,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> SitemapResult:
        """从 base_url 发现 sitemap URL 列表."""
        # 1. 尝试 robots.txt → Sitemap: 指令
        robots_url = urljoin(base_url, "/robots.txt")
        sitemap_urls = await self._find_sitemaps_from_robots(robots_url, timeout)
        
        # 2. 如果没有，尝试默认 sitemap.xml
        if not sitemap_urls:
            sitemap_urls.append(urljoin(base_url, "/sitemap.xml"))
        
        # 3. 解析每个 sitemap
        all_urls: list[str] = []
        for sm_url in sitemap_urls:
            urls = await self._parse_sitemap(sm_url, timeout)
            all_urls.extend(urls)
            if len(all_urls) >= max_urls:
                all_urls = all_urls[:max_urls]
                break
        
        return SitemapResult(
            success=len(all_urls) > 0,
            urls=all_urls,
            total_found=len(all_urls),
        )
    
    async def _find_sitemaps_from_robots(self, robots_url: str, timeout: int) -> list[str]:
        """从 robots.txt 提取 Sitemap: 指令."""
        sitemaps: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(robots_url, headers={"User-Agent": "CPIS-Bot/1.0"})
                if resp.status_code == 200:
                    for line in resp.text.splitlines():
                        if line.lower().startswith("sitemap:"):
                            sm_url = line.split(":", 1)[1].strip()
                            sitemaps.append(sm_url)
        except Exception:
            pass  # robots.txt 不可达时不阻塞
        return sitemaps
    
    async def _parse_sitemap(self, sitemap_url: str, timeout: int) -> list[str]:
        """解析单个 sitemap.xml (支持 sitemap index)."""
        urls: list[str] = []
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(sitemap_url, headers={"User-Agent": "CPIS-Bot/1.0"})
                if resp.status_code != 200:
                    return []
                root = ElementTree.fromstring(resp.content)
                # 命名空间
                ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                # 检查是否为 sitemap index
                sitemap_index = root.findall(".//ns:sitemap/ns:loc", ns)
                if sitemap_index:
                    # 递归解析子 sitemap
                    for loc in sitemap_index[:5]:  # 最多 5 个子 sitemap
                        sub_urls = await self._parse_sitemap(loc.text.strip(), timeout)
                        urls.extend(sub_urls)
                else:
                    # 普通 sitemap
                    for url_elem in root.findall(".//ns:url/ns:loc", ns):
                        urls.append(url_elem.text.strip())
        except Exception:
            pass
        return urls
```

### 5.3 RSS Discovery (新建)

```python
# backend/app/collectors/discovery/rss_discovery.py
# 从 RSS/Atom feed 发现公开 URL
# 功能:
# - 解析 RSS 2.0 / Atom feeds
# - 提取 <item>/<entry> 中的 <link>
# - 默认 ≤10 条
# - 纯发现, 不采集
```

### 5.4 Robots.txt Discovery (新建)

```python
# backend/app/collectors/discovery/robots_discovery.py
# 读取并解析 robots.txt
# 功能:
# - 判断是否允许采集某 URL
# - 提取 Crawl-delay 建议
# - 提取 Sitemap 引用 (委托给 SitemapDiscoverer)
```

### 5.5 集成到 RunPlanExecutor

修改 `backend/app/services/collection_runner_service.py` 的 `_resolve_urls()`，将 sitemap 类型从占位符改为实际调用：

```python
elif source.type == "sitemap" and source.sitemap_url:
    from app.collectors.discovery.sitemap_discovery import SitemapDiscoverer
    max_pages = plan.scope.max_pages if plan.scope else 10
    discoverer = SitemapDiscoverer()
    result = await discoverer.discover(
        source.sitemap_url,
        max_urls=min(max_pages, 10),  # 默认 ≤10
    )
    if result.success:
        for url in result.urls:
            all_urls.append({"url": url, ...})
```

### 5.6 马登工装 Sitemap 应用

马登工装没有可用的官网 sitemap (madenwear.com DNS 不可达)。但此功能可用于其他品牌：

- `https://www.books.toscrape.com/sitemap.xml` — 测试用
- 其他品牌的 `sitemap.xml` / `robots.txt`

---

## 6. Playwright/Scrapling/Crawl4AI 集成方案

### 6.1 PlaywrightCollector Feature Flag (改进)

**现状:** `PlaywrightRuntimeCollector` 已存在，但 feature flag 关闭时静默 fallback 到 direct_http，失败时不写入 report。

**改进方案:**

```python
# 修改 PlaywrightRuntimeCollector.fetch():
# 当 feature flag 关闭时:
# 1. 如果调用方指定了 force_playwright=True，则跳过检查直接使用 Playwright
# 2. 否则返回 CollectResult 且 failure_intelligence 包含:
#    suggested_next = "playwright"
#    user_visible_message = "当前页面可能需要JS渲染，开启Playwright后可采集"
```

**关键修改:**

| 文件 | 修改 |
|------|------|
| `app/collectors/playwright_runtime.py` | 增加 force 参数 + Failure Intelligence fallback 报告 |
| `app/collectors/playwright_collector.py` | 增加 page.wait_for_selector 等等待策略 |
| `app/core/__init__.py` / settings | 确保 `COLLECTOR_PLAYWRIGHT_ENABLED` 默认 `false` |

**JS 渲染 fallback 逻辑:**

```
direct_http fetch 失败
  └─ failure_intelligence.suggested_next == "retry_playwright"?
      ├─ Playwright feature flag enabled?
      │   ├─ Yes → 自动升级到 Playwright 重新采集 (在 _do_collect 中实现)
      │   └─ No → 在 report 中记录 "建议开启 Playwright 重新采集"
      └─ 完成
```

### 6.2 Crawl4AI Cleaner Adapter (新增, 默认关闭)

**现状:** `backend/app/collectors/crawl4ai_runtime.py` 只有 stub (raise NotImplementedError)。

**改进方案:**

将 Crawl4AI 仅作为 **cleaner** 增强（非 collector），新建：

```
backend/app/cleaners/crawl4ai_cleaner_adapter.py
```

```python
"""
Crawl4AI Cleaner Adapter — 仅增强 HTML→Markdown 清洗.

默认关闭 (feature flag: COLLECTOR_CRAWL4AI_ENABLED).
启用后替代 HtmlCleaner 进行更精准的正文提取.
不涉及采集/爬虫功能.
"""

from __future__ import annotations
from app.cleaners.html_cleaner import CleanResult

class Crawl4AICleanerAdapter:
    """Wrap crawl4ai's content cleaning for use as CPIS cleaner."""
    
    ENABLED = False  # feature flag controlled
    
    async def clean(self, html: bytes, page_url: str = "") -> CleanResult:
        if not self.ENABLED:
            raise NotImplementedError("Crawl4AI cleaner is not enabled")
        # ... 调用 crawl4ai 的 markdownify / content extraction
```

**注意:** Crawl4AI 默认 `ENABLED=False`，安装不强制，import 时缺包则静默降级到 HtmlCleaner。

### 6.3 Scrapling Adapter (新增, 默认关闭)

**现状:** `backend/app/collectors/scrapling_runtime.py` 只有 stub。

**改进方案:**

将 Scrapling 仅作为 **公开网页 fallback**（非默认 collector）：

```
backend/app/collectors/scrapling_runtime.py  (重写)
```

```python
"""
ScraplingRuntimeCollector — 公开网页智能采集.

仅当:
1. COLLECTOR_SCRAPLING_ENABLED=true
2. scrapling 包已安装
3. direct_http 失败且 failure_intelligence.suggested_next == "retry_scrapling"

禁用:
- 绕过验证码/登录/付费墙
- 采集小红书/抖音/B站等受限平台
"""
```

**关键限制:**

| 限制项 | 实现 |
|--------|------|
| 默认关闭 | `COLLECTOR_SCRAPLING_ENABLED=false` |
| 不绕过验证码 | 跳转页面时不自动填写/点击验证码 |
| 不登录 | 不提供凭据填入 |
| 不为受限平台工作 | URL 在 blocked_domains 列表中时跳过 |
| 仅公开网页 | 不处理需要认证的内容 |

### 6.4 Feature Flag 矩阵

| 功能 | 标志 | 默认 | 需要安装 | 备注 |
|------|------|------|---------|------|
| DirectHttpCollector | — | ON | httpx (已有) | 始终可用 |
| **Playwright** | `COLLECTOR_PLAYWRIGHT_ENABLED` | OFF | playwright | JS 渲染 fallback |
| **Scrapling** | `COLLECTOR_SCRAPLING_ENABLED` | OFF | scrapling | 智能采集 fallback |
| **Crawl4AI** | `COLLECTOR_CRAWL4AI_ENABLED` | OFF | crawl4ai | 仅 cleaner 增强 |
| **RSS** | `COLLECTOR_RSS_ENABLED` | OFF | — | RSS feed 采集 |
| **PDF** | `COLLECTOR_PDF_ENABLED` | OFF | — | PDF 文档采集 |

### 6.5 自动升级采集链

在 `tasks/collection.py` 的 `_do_collect()` 中新增升级逻辑：

```
当前 (Phase V):
  selector.select() → selected_collector.fetch()
  
Phase VII 升级:
  selector.select() → selected_collector.fetch()
  └─ 如果失败且 failure_intelligence.retryable=True:
      ├─ suggested_next == "retry_ua_rotate" → 更换 UA 重试 1 次
      ├─ suggested_next == "retry_playwright" AND PLAYWRIGHT_ENABLED → PlaywrightRuntimeCollector.fetch()
      └─ suggested_next == "retry_scrapling" AND SCRAPLING_ENABLED → ScraplingRuntimeCollector.fetch()
```

---

## 7. 测试方案

### 7.1 新增测试文件

| 文件 | 测试内容 | 测试数 |
|------|---------|-------|
| `tests/test_direct_http_enhanced.py` | DirectHttpCollector 8 项增强 | ~25 |
| `tests/test_failure_intelligence.py` | FailureAnalysis 分类逻辑 | ~15 |
| `tests/test_sitemap_discovery.py` | SitemapDiscoverer 解析 | ~10 |
| `tests/test_rss_discovery.py` | RSS Discovery 解析 | ~8 |
| `tests/test_robots_discovery.py` | Robots.txt 解析 | ~6 |
| `tests/test_playwright_feature_flag.py` | Playwright feature flag 逻辑 | ~8 |
| `tests/test_crawl4ai_cleaner.py` | Crawl4AI cleaner adapter | ~5 |
| `tests/test_scrapling_adapter.py` | Scrapling fallback 逻辑 | ~5 |

**总计新增:** ~82 个测试

### 7.2 DirectHttpCollector 增强测试

```python
# tests/test_direct_http_enhanced.py

class TestUARotation:
    def test_select_user_agent_returns_configured_ua(self):
        """配置了自定义 UA 时返回配置值."""
        ...
    def test_select_user_agent_random_when_default(self):
        """使用默认 UA 时从轮换池中选择."""
        ...

class TestCharsetDetection:
    def test_detect_from_content_type_header(self):
        """从 Content-Type 头检测 charset."""
        ...
    def test_detect_from_meta_tag(self):
        """从 HTML meta charset 检测."""
        ...
    def test_detect_fallback_to_utf8(self):
        """无 charset 信息时默认 utf-8."""
        ...
    def test_decode_with_detected_charset(self):
        """按检测到的编码正确解码."""
        ...

class TestContentTypeClassification:
    def test_html_content_type(self):
        """text/html 返回 html."""
        ...
    def test_json_content_type(self):
        """application/json 返回 json."""
        ...
    def test_pdf_content_type(self):
        """application/pdf 返回 pdf."""
        ...

class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """超时可重试."""
        ...
    @pytest.mark.asyncio
    async def test_retry_on_429(self):
        """429 可重试."""
        ...
    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """404 不可重试."""
        ...
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """指数退避生效."""
        ...

class TestBrowserHeaders:
    def test_build_headers_includes_all_fields(self):
        """构造的 headers 包含所有浏览器字段."""
        ...
    def test_referer_matches_domain(self):
        """Referer 与请求域名一致."""
        ...
```

### 7.3 Failure Intelligence 测试

```python
# tests/test_failure_intelligence.py

class TestFailureAnalysis:
    def test_dns_failure(self):
        """DNS_FAILURE → 不可重试, 建议搜索替代."""
        ...
    def test_http_403(self):
        """HTTP 403 → 可重试, 建议更换 UA."""
        ...
    def test_http_404(self):
        """HTTP 404 → 不可重试, 建议跳过."""
        ...
    def test_http_429(self):
        """HTTP 429 → 可重试, 建议等待后重试."""
        ...
    def test_timeout(self):
        """FETCH_TIMEOUT → 可重试."""
        ...
    def test_empty_response(self):
        """EMPTY_RESPONSE → 可重试, 建议 Playwright."""
        ...
    def test_captcha_detected(self):
        """CAPTCHA_DETECTED → 不可重试, 建议人工检查."""
        ...
    def test_login_required(self):
        """LOGIN_REQUIRED → 不可重试, 建议搜索替代."""
        ...
    def test_content_too_large(self):
        """CONTENT_TOO_LARGE → 不可重试."""
        ...
    def test_connection_refused(self):
        """CONNECTION_REFUSED → 不可重试."""
        ...
    def test_unknown_error(self):
        """未知错误 → 不可重试, 建议人工检查."""
        ...
```

### 7.4 Sitemap Discovery 测试

```python
# tests/test_sitemap_discovery.py

class TestSitemapDiscoverer:
    @pytest.mark.asyncio
    async def test_parse_sitemap_xml(self):
        """解析标准 sitemap.xml 返回 URL 列表."""
        ...
    @pytest.mark.asyncio
    async def test_parse_sitemap_index(self):
        """解析 sitemap index (包含子 sitemap)."""
        ...
    @pytest.mark.asyncio
    async def test_robots_txt_sitemap_discovery(self):
        """从 robots.txt 找到 Sitemap 引用."""
        ...
    @pytest.mark.asyncio
    async def test_discover_returns_max_urls(self):
        """返回不超过 max_urls 条 URL."""
        ...
    @pytest.mark.asyncio
    async def test_handles_missing_sitemap(self):
        """sitemap.xml 不存在时返回空列表."""
        ...
```

### 7.5 Playwright Feature Flag 测试

```python
# tests/test_playwright_feature_flag.py

class TestPlaywrightFeatureFlag:
    def test_default_disabled(self):
        """Playwright 默认不启用."""
        ...
    def test_fallback_writes_report(self):
        """fallback 时写入 execution report."""
        ...
    @pytest.mark.asyncio
    async def test_force_playwright_when_flag_off(self):
        """force=True 时跳过 flag 检查."""
        ...
```

### 7.6 Collector Auto-Upgrade 链测试

在 `tests/test_collectors.py` 和 `tests/test_collector_runtime.py` 中新增：

```python
class TestCollectorAutoUpgrade:
    @pytest.mark.asyncio
    async def test_ua_rotate_after_403(self):
        """403 后自动换 UA 重试."""
        ...
    @pytest.mark.asyncio
    async def test_playwright_fallback_when_enabled(self):
        """Playwright 启用时, empty_content 后自动升级到 Playwright."""
        ...
    @pytest.mark.asyncio
    async def test_no_playwright_fallback_when_disabled(self):
        """Playwright 禁用时, 不自动升级."""
        ...
```

### 7.7 现有测试兼容性

现有测试 (`test_collectors.py`: 273 行, `test_collector_runtime.py`: 696 行) **必须全部通过**。新增测试不能破坏现有行为。

```bash
# 验证命令
cd /home/ctyun/Competitive-Product-Intelligence-System/backend
pytest tests/test_collectors.py -v
pytest tests/test_collector_runtime.py -v
pytest tests/test_failure_intelligence.py -v
pytest tests/test_direct_http_enhanced.py -v
pytest tests/test_sitemap_discovery.py -v
pytest tests/test_playwright_feature_flag.py -v
pytest tests/test_crawl4ai_cleaner.py -v
pytest tests/test_scrapling_adapter.py -v
```

---

## 8. 文件清单

### 8.1 新增文件

| # | 文件路径 | 说明 | 行数(预估) |
|---|---------|------|-----------|
| 1 | `backend/app/collectors/failure_intelligence.py` | Failure Intelligence 分析引擎 | ~120 |
| 2 | `backend/app/collectors/discovery/__init__.py` | Discovery 包初始化 | ~10 |
| 3 | `backend/app/collectors/discovery/sitemap_discovery.py` | Sitemap URL 发现器 | ~150 |
| 4 | `backend/app/collectors/discovery/rss_discovery.py` | RSS Feed URL 发现器 | ~100 |
| 5 | `backend/app/collectors/discovery/robots_discovery.py` | Robots.txt 解析器 | ~80 |
| 6 | `backend/app/cleaners/crawl4ai_cleaner_adapter.py` | Crawl4AI Cleaner 适配器 | ~80 |
| 7 | `backend/tests/test_direct_http_enhanced.py` | DirectHttp 增强测试 | ~300 |
| 8 | `backend/tests/test_failure_intelligence.py` | Failure Intelligence 测试 | ~200 |
| 9 | `backend/tests/test_sitemap_discovery.py` | Sitemap Discovery 测试 | ~150 |
| 10 | `backend/tests/test_rss_discovery.py` | RSS Discovery 测试 | ~80 |
| 11 | `backend/tests/test_robots_discovery.py` | Robots Discovery 测试 | ~60 |
| 12 | `backend/tests/test_playwright_feature_flag.py` | Playwright 标志测试 | ~100 |
| 13 | `backend/tests/test_crawl4ai_cleaner.py` | Crawl4AI Cleaner 测试 | ~80 |
| 14 | `backend/tests/test_scrapling_adapter.py` | Scrapling 适配器测试 | ~80 |

**新增总计:** ~1,590 行

### 8.2 修改文件

| # | 文件路径 | 修改内容 | 预估变更 |
|---|---------|---------|---------|
| 1 | `backend/app/collectors/direct_http.py` | 8 项增强重写 | +210 行 |
| 2 | `backend/app/collectors/base.py` | CollectResult 增加 failure_intelligence | +10 行 |
| 3 | `backend/app/collectors/registry.py` | CollectResult 增加 failure_intelligence | +10 行 |
| 4 | `backend/app/collectors/playwright_runtime.py` | 增加 force 参数 + Failure Intelligence | +30 行 |
| 5 | `backend/app/collectors/scrapling_runtime.py` | 重写为真实适配器 (默认关闭) | +60 行 |
| 6 | `backend/app/models/collector_execution_report.py` | 增加 5 个 Failure Intelligence 字段 | +15 行 |
| 7 | `backend/app/schemas/collector_execution_report.py` | 增加对应 schema 字段 | +10 行 |
| 8 | `backend/app/services/collection_runner_service.py` | `_resolve_urls()` sitemap/rss 实现 | +50 行 |
| 9 | `backend/app/tasks/collection.py` | `_do_collect()` 增加自动升级链 | +50 行 |
| 10 | `backend/app/collectors/__init__.py` | 导出新模块 | +5 行 |
| 11 | `backend/alembic/versions/007_add_failure_intelligence.py` | 新增 migration | +40 行 |

**修改总计:** ~490 行

### 8.3 不修改文件

| 文件 | 原因 |
|------|------|
| `backend/app/collectors/httpx_collector.py` | 旧版 collector, 保持兼容 |
| `backend/app/collectors/selector.py` | 选择策略不变 |
| `backend/app/collectors/domain_lock.py` | 不变 |
| `backend/app/collectors/retry_policy.py` | 不变 |
| `backend/app/services/url_validator.py` | 不变 |
| `backend/.env` | 不提交 |
| `frontend/` | 无前端变更 |

---

## 9. 验证标准

### 9.1 增强验证 (DirectHttpCollector)

| # | 验证项 | 方法 | 预期 |
|---|--------|------|------|
| V1 | UA 轮换生效 | 模拟 2 次请求确认不同 UA | 每次 request headers 中的 User-Agent 不同 |
| V2 | Charset 检测正确 | 提供 gb2312/kr/euc-jp 编码 HTML | 正确解码输出 |
| V3 | Content-Type 判断 | 返回不同 content-type | html/json/pdf 识别正确 |
| V4 | gzip/brotli 解压 | 返回压缩内容 | 解压后内容正确 |
| V5 | 浏览器 headers 包 | 观察请求 headers | 包含所有 7 个浏览器字段 |
| V6 | Retry 退避 | 模拟 403 → 自动重试 | 重试间隔递增 |
| V7 | 非 retryable 不重试 | 模拟 404 | 不重试直接返回失败 |

### 9.2 Failure Intelligence 验证

| # | 验证项 | 方法 | 预期 |
|---|--------|------|------|
| F1 | 所有已知错误码覆盖 | 对每个 FAILURE_CLASSIFICATION 键值测试 | 分析结果正确 |
| F2 | 未知错误码处理 | 输入未知 error_code | 返回 unknown 类型 |
| F3 | Report 字段写入 | 采集失败后查 DB | failure_type/retryable/suggested_next 非空 |
| F4 | API 返回新字段 | `GET /reports/{id}` | 新字段可见 |

### 9.3 Sitemap Discovery 验证

| # | 验证项 | 方法 | 预期 |
|---|--------|------|------|
| S1 | 解析标准 sitemap.xml | 使用测试 XML | 返回 URL 列表 |
| S2 | 从 robots.txt 发现 sitemap | 模拟 robots.txt | 找到 Sitemap 指令 |
| S3 | 不超过 max_urls | 给定 100 条但 max=10 | 只返回 10 条 |
| S4 | RunPlan 集成 | 执行含 sitemap 的 plan | URL 正确解析 |

### 9.4 马登工装重新测试验证

| # | 验证项 | 预期 | 依赖 |
|---|--------|------|------|
| M1 | madenwear.com DNS 失败 | failure_type=dns_failure, retryable=false | DNS |
| M2 | baike.baidu.com 403 后 UA 轮换 | 首次 403, 换 UA 后可能 200 或仍 403, 但 error_code 正确 | 百度反爬 |
| M3 | post.smzdm.com | failed, suggested_next=retry_playwright | Playwright flag |
| M4 | Sitemap 发现 (如果域名恢复) | 找到页面 | DNS |
| M5 | Failure Intelligence 输出 | 3 个 URL 均有完整分析 | F1-F4 |

### 9.5 全部测试通过

```bash
cd /home/ctyun/Competitive-Product-Intelligence-System/backend
pytest -v --tb=short 2>&1 | tail -30
# 预期: 所有测试通过 (≥ 680 passed)
```

### 9.6 回归测试

```bash
# 确保不破坏已上线功能
pytest tests/test_collectors.py -v          # 273 行现有测试
pytest tests/test_collector_runtime.py -v   # 696 行现有测试
pytest tests/test_pipeline.py -v            # Pipeline 完整性
pytest tests/test_e2e_pipeline.py -v        # E2E 测试
```

---

## 10. 实施顺序与不接受清单

### 10.1 推荐实施顺序 (6 个步骤)

```
Step 1: Failure Intelligence 数据模型 + 分析引擎
        ├── 新建 failure_intelligence.py
        ├── 修改 base.py / registry.py (CollectResult 增加 fi 字段)
        └── 新增 migration (collector_execution_reports 加 5 字段)
        
Step 2: DirectHttpCollector 8 项增强
        ├── 重写 direct_http.py
        └── 新增依赖 chardet + 测试
        
Step 3: Playwright Feature Flag 改进
        ├── 修改 playwright_runtime.py
        └── 自动升级链集成到 tasks/collection.py
        
Step 4: Sitemap/RSS/Robots Discovery
        ├── 新建 discovery/ 目录 + 3 个文件
        ├── 修改 collection_runner_service.py _resolve_urls()
        └── 新建对应测试

Step 5: Scrapling + Crawl4AI Adapter
        ├── 重写 scrapling_runtime.py
        ├── 新建 crawl4ai_cleaner_adapter.py
        └── 新建对应测试

Step 6: 马登工装重新测试 + 全部测试通过
        ├── 运行所有测试
        └── 手动测试 3 个失败 URL 的新分析结果
```

### 10.2 不接受清单 (禁止)

| 禁止项 | 说明 |
|--------|------|
| ❌ 绕过验证码/登录/付费墙 | 不实现任何 captcha solving / login / paywall bypass |
| ❌ 采集小红书/抖音/B站/知乎/微博/贴吧 | blocked_domains 中的任何站点 |
| ❌ 大规模/定时采集 | 不做 bulk crawl / schedule crawl 增强 |
| ❌ 默认启用 Playwright/Scrapling/Crawl4AI | 所有 feature flag 默认 false |
| ❌ push/tag/merge/deploy | 待 Phase VII 全部完成后统一处理 |
| ❌ 提交 .env/secrets | 不修改或新提交敏感文件 |
| ❌ 修改旧版 HttpxCollector | 保持向后兼容 |
| ❌ Proxy 支持 | 不在 Phase VII 范围内 |
| ❌ Cookie 持久化/登录态保持 | 不实现 session/cookie 持久化 |

### 10.3 Phase VII 不包含 (但已记录为后续)

- **Proxy/IP 轮换池** — 需额外 ProxyProvider
- **Cookie 持久化** — 需 CookieJar 管理
- **定时增量采集** — 需 Crusher/Delta 逻辑
- **Site-specific 适配器** (如百度百科专用) — 属于 Phase VIII+
- **验证码识别** — 永不实现
- **API 级采集** (如淘宝开放平台) — 需商务合作

---

## 附录 A: 依赖变更

```python
# pyproject.toml 新增
[tool.poetry.dependencies]
chardet = "^5.2.0"  # 字符集检测
```

开发依赖不变。

## 附录 B: Migration SQL (007)

```sql
-- 新增 Failure Intelligence 字段到 collector_execution_reports
ALTER TABLE collector_execution_reports 
  ADD COLUMN failure_type VARCHAR(32) NULL,
  ADD COLUMN retryable BOOLEAN NULL,
  ADD COLUMN suggested_next VARCHAR(48) NULL,
  ADD COLUMN blocked_reason TEXT NULL,
  ADD COLUMN user_visible_message VARCHAR(256) NULL;
```

## 附录 C: 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| Failure Intelligence 在 CollectResult 层还是 Report 层 | 两者都有 | 采集链中即判断，report 中持久化 |
| UA 轮换池大小 | 5 个 | 足够规避基础反爬，不过度增加 |
| Sitemap 默认 max_urls | 10 | 避免大面积发现，符合「不大规模采集」禁令 |
| Charset 检测库 | chardet | 成熟稳定，Python 生态标准 |
| Retry 策略 | 指数退避 + 随机抖动 | 避免 thundering herd |
| Scrapling/Crawl4AI 集成方式 | Adapter 模式 | 降低耦合，默认关闭不影响主线 |
