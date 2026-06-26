"""Sitemap-based URL discovery for public web pages."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urljoin

import httpx

SITEMAP_URLS = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/sitemap.xml"]
DEFAULT_MAX_URLS = 10


async def discover_from_sitemap(
    base_url: str,
    max_urls: int = DEFAULT_MAX_URLS,
    verify_ssl: bool = True,
) -> list[str]:
    """从 sitemap.xml 发现公开 URL.

    流程:
    1. 尝试常见 sitemap 路径
    2. 解析 XML, 提取 <loc>
    3. 如果是 sitemap 索引, 递归解析子 sitemap
    4. 返回最多 max_urls 个 URL

    Args:
        base_url: 网站基础 URL (例如 https://example.com)
        max_urls: 最大返回 URL 数量
        verify_ssl: 是否验证 SSL 证书 (对自签名证书站点设为 False)

    返回: list[str] — 发现的 URL 列表
    """
    urls: list[str] = []
    for path in SITEMAP_URLS:
        sitemap_url = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        try:
            async with httpx.AsyncClient(
                timeout=10, follow_redirects=True, verify=verify_ssl,
            ) as client:
                resp = await client.get(sitemap_url)
                if resp.status_code != 200:
                    continue
                content = resp.text
                root = ET.fromstring(content)
                # 命名空间处理
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                locs = root.findall(".//sm:loc", ns) or root.findall(".//loc")
                for loc in locs:
                    if loc.text and len(urls) < max_urls:
                        if loc.text.endswith(".xml"):
                            # 子 sitemap — 递归
                            try:
                                async with httpx.AsyncClient(
                                    timeout=10, verify=verify_ssl,
                                ) as client2:
                                    sub_resp = await client2.get(loc.text)
                                    if sub_resp.status_code == 200:
                                        sub_root = ET.fromstring(sub_resp.text)
                                        sub_locs = sub_root.findall(
                                            ".//sm:loc", ns,
                                        ) or sub_root.findall(".//loc")
                                        for sub_loc in sub_locs:
                                            if sub_loc.text and len(urls) < max_urls:
                                                urls.append(sub_loc.text.strip())
                            except Exception:
                                continue
                        else:
                            urls.append(loc.text.strip())
                if urls:
                    break
        except Exception:
            continue
    return urls[:max_urls]


async def discover_from_robots(
    base_url: str,
    verify_ssl: bool = True,
) -> Optional[str]:
    """从 robots.txt 发现 Sitemap 路径.

    Args:
        base_url: 网站基础 URL
        verify_ssl: 是否验证 SSL 证书

    返回: Sitemap URL 字符串，如果没有找到则返回 None
    """
    robots_url = urljoin(base_url.rstrip("/") + "/", "robots.txt")
    try:
        async with httpx.AsyncClient(
            timeout=10, follow_redirects=True, verify=verify_ssl,
        ) as client:
            resp = await client.get(robots_url)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None
