# Phase III-B — 马登工装/Maden 公开 URL 发现报告

## 1. 搜索策略

### 1.1 品牌标识

| 维度 | 值 |
|------|-----|
| 品牌中文名 | 马登工装 |
| 品牌英文名 | Maden / Madengz |
| 平台 | 淘宝/天猫为主 |
| 风格 | 男装工装/复古/军事风 |
| 风险等级 | **高风险**（淘宝/天猫 → login required, 反爬严格） |

### 1.2 搜索查询（4 组）

使用 `DuckDuckGoSearchProvider`（`language="zh-CN"`, `max_results=10`），执行以下 4 组独立查询：

| # | 查询词 | 预期目标 | 优先级 |
|---|--------|---------|--------|
| 1 | `"马登工装" 品牌 官网` | 寻找官方主页或品牌介绍页 | ⭐⭐⭐ |
| 2 | `"马登工装" Maden 男装` | 电商平台外的品牌文章 | ⭐⭐⭐ |
| 3 | `"马登" 工装 淘宝 品牌 评价` | 第三方评测/推荐文章 | ⭐⭐ |
| 4 | `Maden 工装 复古 男装 品牌介绍` | 新闻/媒体提及 | ⭐⭐ |

### 1.3 搜索实现脚本

```python
"""scripts/discover_maden_urls.py — 使用 DuckDuckGo 发现马登工装公开 URL"""
import asyncio
import json
import sys
from urllib.parse import urlparse

sys.path.insert(0, "/home/ctyun/Competitive-Product-Intelligence-System/backend")
from app.providers.duckduckgo_provider import DuckDuckGoSearchProvider

BANNED_DOMAINS = {
    "xiaohongshu.com", "xhscdn.com",
    "douyin.com", "iesdouyin.com",
    "bilibili.com", "b23.tv",
    "zhihu.com",
    "weibo.com", "weibo.cn",
    "tieba.baidu.com",
}

HIGH_RISK_DOMAINS = {
    "taobao.com", "tmall.com", "detail.tmall.com", "item.taobao.com",
    "1688.com", "alibaba.com",
}

async def discover():
    provider = DuckDuckGoSearchProvider()
    queries = [
        '"马登工装" 品牌 官网',
        '"马登工装" Maden 男装',
        '"马登" 工装 淘宝 品牌 评价',
        'Maden 工装 复古 男装 品牌介绍',
    ]
    
    all_results = []
    seen_urls = set()
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"查询 {i}/4: {query}")
        print(f"{'='*60}")
        
        results = await provider.search(query, max_results=10, language="zh-CN")
        
        for r in results:
            domain = urlparse(r.url).hostname or ""
            domain_lower = domain.lower()
            
            # 检查是否被禁止
            banned = any(b in domain_lower for b in BANNED_DOMAINS)
            high_risk = any(h in domain_lower for h in HIGH_RISK_DOMAINS)
            
            # 去重
            url_key = r.url.rstrip("/").lower()
            if url_key in seen_urls:
                continue
            seen_urls.add(url_key)
            
            entry = {
                "query": query,
                "title": r.title,
                "url": r.url,
                "domain": domain,
                "snippet": r.snippet[:200] if r.snippet else "",
                "banned": banned,
                "high_risk": high_risk,
                "risk_level": "blocked" if banned else ("high" if high_risk else "low"),
            }
            all_results.append(entry)
            
            risk_tag = "🔴 BLOCKED" if banned else ("🟡 HIGH-RISK" if high_risk else "🟢 LOW-RISK")
            print(f"\n  [{risk_tag}] {r.title}")
            print(f"  URL: {r.url}")
            print(f"  Snippet: {r.snippet[:120]}..." if r.snippet else "")
    
    # 输出结果
    output = {
        "brand": "马登工装 / Maden",
        "total_queries": len(queries),
        "total_results": len(all_results),
        "results": all_results,
        "summary": {
            "safe_count": sum(1 for r in all_results if r["risk_level"] == "low"),
            "high_risk_count": sum(1 for r in all_results if r["risk_level"] == "high"),
            "blocked_count": sum(1 for r in all_results if r["risk_level"] == "blocked"),
        }
    }
    
    with open("maden_discovery_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"发现汇总:")
    print(f"  总结果: {len(all_results)}")
    print(f"  安全可采: {output['summary']['safe_count']}")
    print(f"  高风险: {output['summary']['high_risk_count']}")
    print(f"  已拦截: {output['summary']['blocked_count']}")
    print(f"  结果已保存到 maden_discovery_results.json")
    
    return all_results

if __name__ == "__main__":
    asyncio.run(discover())
```

## 2. URL 风险评估矩阵

### 2.1 已知的 Maden 相关域名风险

| 域名 | 平台 | 风险等级 | 原因 | 处理方式 |
|------|------|---------|------|---------|
| `*.taobao.com` | 淘宝 | **blocked** | 需登录，robots.txt 禁止 | 直接拦截 |
| `*.tmall.com` | 天猫 | **blocked** | 需登录，反爬严格 | 直接拦截 |
| `detail.tmall.com` | 天猫详情 | **blocked** | 需登录 | 直接拦截 |
| `item.taobao.com` | 淘宝商品 | **blocked** | 需登录 | 直接拦截 |
| `m.taobao.com` | 淘宝移动端 | **blocked** | 需登录 | 直接拦截 |
| `www.taobao.com` | 淘宝首页 | **blocked** | 需登录 | 直接拦截 |
| `www.1688.com` | 阿里巴巴 | **blocked** | B2B，需登录 | 直接拦截 |
| `maden.tmall.com` | 天猫品牌店 | **blocked** | 需登录 | 直接拦截 |
| `maden.taobao.com` | 淘宝店铺 | **blocked** | 需登录 | 直接拦截 |
| 第三方评测站 | 如什么值得买 | **low** | 公开可访问 | 安全可采 |
| 媒体报道 | 新闻网站 | **low** | 公开可访问 | 安全可采 |
| 品牌百科 | baike.baidu.com | **low** | 公开可访问 | 安全可采 |
| 电商导航站 | 品牌集合页 | **low** | 公开可访问 | 安全可采 |

### 2.2 判断逻辑

```python
def assess_url_risk(url: str) -> str:
    """评估 URL 风险等级：blocked / high / low"""
    domain = urlparse(url).hostname or ""
    
    # 完全禁止的源
    BLOCKED_PATTERNS = [
        "xiaohongshu", "douyin", "bilibili", "zhihu", 
        "weibo", "tieba.baidu.com",
    ]
    for p in BLOCKED_PATTERNS:
        if p in domain.lower():
            return "blocked"
    
    # 高风险（登录墙、反爬严格）
    HIGH_RISK_PATTERNS = [
        "taobao.com", "tmall.com", "1688.com",
    ]
    for p in HIGH_RISK_PATTERNS:
        if p in domain.lower():
            return "blocked"  # 直接拦截 — 无需尝试
    
    return "low"  # 其他公开站点安全
```

## 3. 预期发现场景

### 最佳情况（能找到安全可采的 URL）
- 马登工装的品牌介绍页（如百度百科）
- 第三方电商导购/评测文章
- 社交媒体之外的新闻报道
- 什么值得买等 UGC 内容

### 最差情况（所有结果均不可采）
所有搜索返回结果均为：
- 淘宝/天猫商品页（blocked）
- 小红书/抖音/B站/知乎/微博/贴吧（blocked 源）
- 无关结果（非马登内容）

此时必须如实报告 **`BLOCKED_NO_SAFE_MADEN_URL_FOUND`**。

## 4. 执行流程

```
开始发现
  │
  ├─ 1. 运行 DuckDuckGo 搜索（4 queries × 10 results）
  │      │
  │      ├─ 对每个结果评估风险
  │      │   ├─ blocked → 跳过（记录到拦截日志）
  │      │   ├─ high_risk → 跳过（记录）
  │      │   └─ low_risk → 加入候选列表
  │      │
  │      └─ 结果去重（标准化 URL 去重）
  │
  ├─ 2. 候选 URL 列表
  │      │
  │      ├─ 数量 > 0 → 进入采集阶段
  │      └─ 数量 = 0 → 报告 BLOCKED_NO_SAFE_MADEN_URL_FOUND
  │
  └─ 3. 输出 maden_discovery_results.json
```

## 5. 发现报告输出

发现阶段生成 `PHASE_III_B_MADEN_DISCOVERY_REPORT.md`，包含：
- 搜索查询及返回数量
- 每个 URL 的风险评估结果
- 拦截统计（今日拦截计数对比）
- 候选 URL 列表（安全可采的）
- 如果无安全 URL，报告 `BLOCKED_NO_SAFE_MADEN_URL_FOUND`
