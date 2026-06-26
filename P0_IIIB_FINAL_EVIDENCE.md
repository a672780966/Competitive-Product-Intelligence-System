# Phase III-B + P0 Reality Alignment — Final Evidence

**Date:** 2026-06-26

## Phase III-B: 马登工装真实品牌采集补测

### 搜索发现
| 查询 | 结果数 | 安全 | 拦截 |
|------|--------|------|------|
| "马登工装" 品牌 官网 | 4 | 2 | 2 |
| "马登工装" Maden 男装 | 3 | 1 | 2 |
| "马登" 工装 品牌介绍 | 2 | 1 | 1 |
| Maden 工装 复古 男装 | 2 | 2 | 0 |
| **合计** | **11** | **6** | **5** |

### 安全候选 URL
| URL | 域 | 说明 |
|-----|-----|------|
| madenwear.com | 🔗 疑似官网 | ✅ low |
| baike.baidu.com/item/马登/9266132 | 📖 百度百科 | ✅ low |
| post.smzdm.com/p/akxw4nx4/ | 📰 什么值得买 | ✅ low |
| zhizhizhi.com (×2) | 🛍️ 商品推荐 | ✅ low |
| baicaio.com | 💰 优惠推荐 | ✅ low |

### 采集结果: BLOCKED_NO_SAFE_MADEN_URL_FOUND
| URL | 原因 |
|-----|------|
| madenwear.com | ❌ DNS 解析失败（域名可能已停用） |
| baike.baidu.com | ❌ HTTP 403（百度反爬） |
| smzdm.com | ❌ 获取内容失败（反爬） |

### CollectorExecutionReport 修复
- ✅ **成功路径**: 已写入（4条现存记录，含 example.com）
- ✅ **阻塞路径**: 已修复 `task_service.py` — validation 失败时创建 report
- ✅ **异常路径**: 已修复 — except 分支创建 report
- ✅ **API 路由**: `GET /api/v1/collection-tasks/{task_id}/execution-reports` 已注册
- ⚡ 修复要点: `_run_validation()` 的 else/except 分支新增 CollectorExecutionReport 写入

## P0 Reality Alignment: Overclaim 修复

### 修改文件清单（16 个文件）
| 文件 | 变更 | 说明 |
|------|------|------|
| README.md | 8处 | 首屏/流程图/功能模块/架构图/技术栈/路线图 |
| docs/README.en.md | 11处 | Hero/Why/流程/模块/Provider/栈/路线 |
| docs/README.ja.md | 4处 | Hero/流程/模块 |
| docs/README.ko.md | 4处 | Hero/流程/模块 |
| release/RELEASE_NOTES.md | 3处 | AI-powered → stub |
| release/CHANGELOG.md | 2处 | "麻登"→"马登", AI-powered→discovery provider interface |
| frontend/.../DiscoveryPage.tsx | 1处 | Mock Mode 告警 |
| backend/app/main.py | 1处 | 注册 provider_status 路由 |
| backend/app/api/provider_status.py | 新建 | Provider Status API |
| backend/tests/test_overclaim_protection.py | 新建 | 15个测试 |
| backend/app/services/task_service.py | 修复 | validation 失败写 report |
| REAL_PROVIDER_INTEGRATION_PLAN.md | 新建 | 真实 Provider 接入方案 |

### Provider Status API 当前状态
```json
{
  "current_search_provider": "duckduckgo",
  "current_llm_provider": "stub",
  "is_real_provider_enabled": true,
  "is_mock_mode": false,
  "llm_provider_details": { "has_api_key": false, "has_base_url": false }
}
```

### 真实能力边界
| 能力 | 状态 |
|------|------|
| Direct HTTP 采集 | ✅ 真实可用 |
| DB 入库/Review/Feishu | ✅ 真实可用 |
| DuckDuckGo SearchProvider | ⚠️ 代码就绪，但 duckduckgo_verified=false |
| LLM Provider (OpenAI) | ❌ 默认 Stub，缺 LLM_API_KEY/LLM_BASE_URL |
| Natural Language → Source Discovery | ❌ Mock 模式，无真实搜索 |
| MCP/Skills/Release | ✅ 真实可用 |

### 测试结果
- **full pytest**: 551 passed (34.87s)
- **overclaim tests**: 15/15 passed
- **collector tests**: 68/68 passed
- **frontend build**: ✅ 8.24s

## 裁决
→ 待 OpenCode Reviewer + Codex Final Gate
