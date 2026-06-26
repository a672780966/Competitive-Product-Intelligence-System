"""
搜索马登工装公开 URL
"""
import asyncio, json, sys, os
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["CPIS_ENV"] = "test"

# 方法1: 通过 DuckDuckGoSearchProvider
from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider

BANNED_DOMAINS = {"xiaohongshu.com","xhscdn.com","douyin.com","iesdouyin.com","bilibili.com","b23.tv","zhihu.com","weibo.com","weibo.cn","tieba.baidu.com"}
HIGH_RISK_DOMAINS = {"taobao.com","tmall.com","detail.tmall.com","item.taobao.com","1688.com","alibaba.com","jd.com","pinduoduo.com"}

async def discover():
    provider = DuckDuckGoSearchProvider()
    queries = [
        '"马登工装" 品牌 官网',
        '"马登工装" Maden 男装',
        '"马登" 工装 品牌介绍',
        'Maden 工装 复古 男装',
    ]
    all_results, seen_urls = [], set()
    for i, q in enumerate(queries, 1):
        print(f"\n查询 {i}/4: {q}")
        try:
            results = await provider.search(q, max_results=10, language="zh-CN")
        except Exception as e:
            print(f"  错误: {e}")
            continue
        for r in results:
            domain = (urlparse(r.url).hostname or "").lower()
            url_key = r.url.rstrip("/").lower()
            if url_key in seen_urls: continue
            seen_urls.add(url_key)
            banned = any(b in domain for b in BANNED_DOMAINS)
            high_risk = any(h in domain for h in HIGH_RISK_DOMAINS)
            risk = "blocked" if banned or high_risk else "low"
            entry = {"query": q, "title": r.title, "url": r.url, "domain": domain, "snippet": (r.snippet or "")[:200], "risk_level": risk}
            all_results.append(entry)
            print(f"  [{'🔴' if risk=='blocked' else '🟢'}] {r.title}")
            print(f"  URL: {r.url}")
    output = {"brand": "马登工装 / Maden", "total_queries": len(queries), "total_results": len(all_results), "results": all_results,
              "summary": {"safe_count": sum(1 for r in all_results if r["risk_level"]=="low"),
                          "blocked_count": sum(1 for r in all_results if r["risk_level"]=="blocked")}}
    with open("maden_discovery_results.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n总结果: {len(all_results)}, 安全: {output['summary']['safe_count']}, 拦截: {output['summary']['blocked_count']}")

if __name__ == "__main__":
    asyncio.run(discover())
