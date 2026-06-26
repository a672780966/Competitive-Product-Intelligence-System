"""
马登工装重测脚本 (Phase VII — Partition B4)

测试增强后的 DirectHttpCollector + Sitemap Discovery 对马登工装的采集能力。
"""
from __future__ import annotations

import asyncio
import json
import sys
from urllib.parse import urljoin

sys.path.insert(0, ".")

from app.collectors.direct_http import DirectHttpCollector
from app.collectors.sitemap_discovery import discover_from_sitemap, discover_from_robots
from app.collectors.failure_intelligence import FailureAnalysis


async def main() -> dict:
    collector = DirectHttpCollector()
    results: dict = {}

    # ── B4.1: Sitemap Discovery ──────────────────────────────────
    print("=" * 70)
    print("B4.1: Sitemap + Robots Discovery for madenwear.com")
    print("=" * 70)

    # Try with verify_ssl=False (self-signed cert)
    sitemap_urls = await discover_from_sitemap(
        "http://www.madenwear.com", max_urls=10, verify_ssl=False,
    )
    print(f"Sitemap found {len(sitemap_urls)} URLs: {sitemap_urls}")
    results["sitemap_urls"] = sitemap_urls

    robots_sitemap = await discover_from_robots(
        "http://www.madenwear.com", verify_ssl=False,
    )
    print(f"Robots.txt sitemap: {robots_sitemap}")
    results["robots_sitemap"] = robots_sitemap

    # ── B4.2: DuckDuckGo Search ──────────────────────────────────
    print("\n" + "=" * 70)
    print("B4.2: DuckDuckGo Search for Maden URLs")
    print("=" * 70)

    from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider

    provider = DuckDuckGoSearchProvider()
    queries = [
        '"马登工装" 品牌 官网',
        '"马登工装" Maden 男装',
    ]
    ddg_results = []
    seen_urls: set[str] = set()
    BANNED_DOMAINS = {
        "xiaohongshu.com", "xhscdn.com", "douyin.com", "iesdouyin.com",
        "bilibili.com", "b23.tv", "zhihu.com", "weibo.com", "weibo.cn",
        "tieba.baidu.com",
    }
    HIGH_RISK_DOMAINS = {
        "taobao.com", "tmall.com", "detail.tmall.com", "item.taobao.com",
        "1688.com", "alibaba.com", "jd.com", "pinduoduo.com",
    }

    for q in queries:
        try:
            results_q = await provider.search(q, max_results=10, language="zh-CN")
            for r in results_q:
                url_key = r.url.rstrip("/").lower()
                if url_key in seen_urls:
                    continue
                seen_urls.add(url_key)
                domain = r.url.split("/")[2].lower() if "//" in r.url else ""
                banned = any(b in domain for b in BANNED_DOMAINS)
                high_risk = any(h in domain for h in HIGH_RISK_DOMAINS)
                risk = "blocked" if banned or high_risk else "low"
                ddg_results.append({
                    "query": q,
                    "title": r.title,
                    "url": r.url,
                    "domain": domain,
                    "risk_level": risk,
                })
                print(f"  [{'🔴' if risk == 'blocked' else '🟢'}] {r.title}")
                print(f"         {r.url}")
        except Exception as e:
            print(f"  DDG error: {e}")
    results["ddg_results"] = ddg_results
    results["ddg_summary"] = {
        "total": len(ddg_results),
        "safe": sum(1 for r in ddg_results if r["risk_level"] == "low"),
        "blocked": sum(1 for r in ddg_results if r["risk_level"] == "blocked"),
    }
    print(f"  Total: {len(ddg_results)}, Safe: {results['ddg_summary']['safe']}, Blocked: {results['ddg_summary']['blocked']}")

    # ── B4.3: Madenwear Direct Fetch ─────────────────────────────
    print("\n" + "=" * 70)
    print("B4.3: Madenwear Direct HTTP Fetch (verify_ssl=False)")
    print("=" * 70)

    maden_urls = [
        "http://www.madenwear.com/",
        "http://www.madenwear.com/policy",
        "http://www.madenwear.com/categories/all",
    ]
    maden_results = []
    for url in maden_urls:
        result = await collector.fetch(url, max_retries=1, verify_ssl=False)
        status = "✅ SUCCESS" if result.success else "❌ FAILED"
        print(f"  {status} | {url}")
        print(f"         HTTP {result.http_status}, Final: {result.final_url}")
        print(f"         Size: {len(result.raw_html or b'')}B, Title: {result.page_title}")
        maden_results.append({
            "url": url,
            "success": result.success,
            "http_status": result.http_status,
            "final_url": result.final_url,
            "title": result.page_title,
            "content_size": len(result.raw_html or b""),
        })
    results["maden_results"] = maden_results

    # ── B4.4: Baike Baidu ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("B4.4: Baike Baidu (马登百科)")
    print("=" * 70)

    baike_url = "https://baike.baidu.com/item/%E9%A9%AC%E7%99%BB/9266132"
    result = await collector.fetch(baike_url, max_retries=2)
    fi = result.failure_intelligence
    print(f"  {'✅ SUCCESS' if result.success else '❌ FAILED'} | HTTP {result.http_status}")
    if fi:
        print(f"  Failure Type: {fi.failure_type}")
        print(f"  Retryable: {fi.retryable}")
        print(f"  Suggested Next: {fi.suggested_next}")
    results["baike"] = {
        "success": result.success,
        "http_status": result.http_status,
        "failure_type": fi.failure_type if fi else None,
        "retryable": fi.retryable if fi else None,
        "suggested_next": fi.suggested_next if fi else None,
    }

    # ── B4.5: SMZDM ─────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("B4.5: SMZDM (什么值得买)")
    print("=" * 70)

    smzdm_url = "https://post.smzdm.com/p/akxw4nx4/"
    result = await collector.fetch(smzdm_url, max_retries=2)
    fi = result.failure_intelligence
    content_size = len(result.raw_html or b"")
    print(f"  {'✅ SUCCESS' if result.success else '❌ FAILED'} | HTTP {result.http_status}")
    print(f"  Content size: {content_size}B")
    if fi:
        print(f"  Failure Type: {fi.failure_type}")
        print(f"  Retryable: {fi.retryable}")
        print(f"  Suggested Next: {fi.suggested_next}")
    # Even HTTP 202 with tiny content is effectively a failure
    effective_success = result.success and content_size > 2048
    if not effective_success:
        print(f"  ⚠️  Effective failure: Tiny content ({content_size}B) — needs Playwright")
    results["smzdm"] = {
        "success": result.success,
        "http_status": result.http_status,
        "content_size": content_size,
        "effective_success": effective_success,
        "failure_type": fi.failure_type if fi else ("empty_content" if content_size < 2048 else None),
        "suggested_next": fi.suggested_next if fi else "retry_playwright",
    }

    # ── Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"  Sitemap URLs discovered: {len(sitemap_urls)}")
    print(f"  Robot.txt sitemap: {robots_sitemap}")
    print(f"  DDG search results: {results['ddg_summary']['total']} ({results['ddg_summary']['safe']} safe, {results['ddg_summary']['blocked']} blocked)")
    for mr in maden_results:
        print(f"  {'✅' if mr['success'] else '❌'} {mr['url']} → HTTP {mr['http_status']}, {mr['content_size']}B")
    print(f"  {'✅' if results['baike']['success'] else '❌'} Baike Baidu → HTTP {results['baike']['http_status']} ({results['baike'].get('failure_type', 'N/A')})")
    smzdm_status = results["smzdm"]["effective_success"]
    print(f"  {'✅' if smzdm_status else '❌'} SMZDM → HTTP {results['smzdm']['http_status']}, {results['smzdm']['content_size']}B (effective: {smzdm_status})")

    # Failure Intelligence Classification
    print("\n" + "-" * 70)
    print("FAILURE INTELLIGENCE CLASSIFICATION")
    print("-" * 70)
    classifications = {
        "madenwear.com": {
            "failure_type": "ssl_cert_error" if not maden_results[0]["success"] else "none",
            "retryable": True,
            "suggested_next": "use_verify_false",
            "note": "DNS resolves, site accessible via HTTP→HTTPS with verify=False. Self-signed SSL cert.",
        },
        "baike.baidu.com": {
            "failure_type": "http_error" if not results["baike"]["success"] else "none",
            "http_status": results["baike"]["http_status"],
            "retryable": True,
            "suggested_next": "retry_playwright",
            "note": "Baidu WAF blocks direct HTTP with 403. Enhanced UA rotation still fails. Needs Playwright.",
        },
        "post.smzdm.com": {
            "failure_type": "empty_content",
            "retryable": True,
            "suggested_next": "retry_playwright",
            "note": "HTTP 202 with JS challenge page (209B). WAF probe needs JS execution.",
        },
    }
    for site, cls in classifications.items():
        print(f"  {site}:")
        for k, v in cls.items():
            print(f"    {k}: {v}")

    results["failure_intelligence"] = classifications

    # Save to file
    with open("maden_retest_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\nResults saved to maden_retest_results.json")

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
