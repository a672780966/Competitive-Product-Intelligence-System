# Codex 云端继续工作交接

更新时间：2026-06-13（Asia/Shanghai）

## 当前目标

完善 OpenClaw 三 Agent 竞品情报流水线：

1. `cpis-info-collector` 采集公开证据。
2. `cpis-product-analyst` 基于证据分析。
3. `cpis-knowledge-curator` 发布中文 + English 飞书报告，包含可点击链接和产品图片。
4. Agent 内部严格使用 JSON。

`main` 不属于此工作流。

## 已验证成功

- 三个 Agent 已完成串联。
- `cpis-json-gate` v1.2.0 已发布。
- `before_tool_call` priority 为 1000。
- **新增 `before_agent_finalize` Hook，仅对 curator 生效**。
- 飞书权限 `docs:document.media:upload` 已开通。
- 图片上传测试成功。
- 端到端恢复发布成功：
  - run_id：`amazon_us_tens_20260613_e2e001`
  - 飞书文档：https://feishu.cn/docx/TJBnduVpmofKEpxPP6dcRd3Ende
  - 图片：2/2 上传成功
  - 工具失败：0
  - `replayInvalid=false`
  - 数据状态：`partial`（只采集了前两名）

## 已解决问题

### 1. before_agent_finalize Hook ✅ (v1.2)

- 新增 `validatePublishResult(text)` 验证函数。
- 注册 `before_agent_finalize` Hook，仅对 `cpis-knowledge-curator` 生效。
- 结果必须是单个 `publish_result` JSON，禁止 Markdown 围栏和额外文字。
- `maxAttempts: 1`，不得重新调用飞书工具。
- 配置需开启：`plugins.entries.cpis-json-gate.hooks.allowConversationAccess = true`

### 2. 长期使用 main 会话导致上下文爆炸 ✅

旧问题已定位。后续必须使用基于 `run_id` 的独立 session key，禁止所有任务继续堆入 `main`。

### 3. 中文输入乱码 ✅

- 新增 `scripts/send-task-utf8.sh`：从 UTF-8 文件读取消息，避免终端转码。
- 新增 `examples/` 目录，包含示例任务 JSON 和参考 publish_result。

### 4. 最终输出不是严格 JSON ✅

- `before_agent_finalize` 强制硬约束：最终回答必须为严格 publish_result JSON。
- 缺少 `object_type: "publish_result"`、Markdown 围栏、未知字段全部拒绝。
- 图片约束：`images_uploaded < images_expected` 时 `status` 不得为 `success`。
- `published=true` 时 `feishu_url` 必须为有效 http/https URL。

### 5. 单元测试 ✅

`test/publish-validator.test.js`：
- 25 个 validatePublishResult 测试 + 2 个 validateSessionsSend 基线测试
- 全部 27 个测试通过

## 验证过的正确 OpenClaw Hook

OpenClaw 官方源码提供 `before_agent_finalize`：

- 可检查 `lastAssistantMessage`。
- 不合格时返回 `action: "revise"`。
- 可通过 `retry.maxAttempts` 限制最多重写一次，避免循环。
- 非内置插件使用会话内容 Hook 时，配置必须开启：

```json
{
  "plugins": {
    "entries": {
      "cpis-json-gate": {
        "hooks": {
          "allowConversationAccess": true
        }
      }
    }
  }
}
```

官方资料：https://github.com/openclaw/openclaw/blob/main/docs/plugins/hooks.md

## 已交付物品

### v1.2 升级（11 项全部完成）

| # | 项目 | 状态 |
|---|------|------|
| 1 | 保留现有 `before_tool_call` 交接验证 | ✅ |
| 2 | 新增 `validatePublishResult(text)` 验证器 | ✅ |
| 3 | 新增 `before_agent_finalize` Hook，仅对 curator 生效 | ✅ |
| 4 | 最终文本必须是单个 JSON 对象（schema_version, object_type, run_id, agent_id, status, published, message_zh/message_en, feishu_url, images_expected, images_uploaded, image_failures） | ✅ |
| 5 | 禁止 Markdown 围栏、JSON 前后附加文字及未知字段 | ✅ |
| 6 | images_uploaded < images_expected 时 status 不得为 success | ✅ |
| 7 | published=true 时必须存在有效 feishu_url | ✅ |
| 8 | 验证失败时要求模型重写一次（maxAttempts: 1），不得重新调用飞书工具 | ✅ |
| 9 | 增加验证器单元测试（27 个测试全部通过） | ✅ |
| 10 | 增加 UTF-8 文件调用脚本和示例任务 JSON | ✅ |
| 11 | 更新版本（1.2.0）、部署文档、验证脚本和 ZIP 包 | ✅ |

### 文件清单

```
openclaw-plugins/cpis-json-gate/
├── dist/
│   ├── index.js              # 注册 before_tool_call + before_agent_finalize
│   ├── validator.js           # validateSessionsSend + validatePublishResult
│   └── cpis-json-gate-v1.2.0.zip  # 分发包
├── test/
│   └── publish-validator.test.js # 27 个单元测试
├── openclaw.plugin.json       # version: 1.2.0
├── package.json               # version: 1.2.0
└── install-on-lx.sh           # 安装脚本（含 allowConversationAccess 提醒）

scripts/
├── send-task-utf8.sh          # UTF-8 安全调用脚本
├── verify-deploy.sh           # 部署后验证脚本
└── build-zip.sh               # 打包构建脚本

examples/
├── task-evidence.json          # 示例采集任务
├── task-publish.json           # 示例发布任务
├── valid-publish-result.json   # 完整成功示例
├── partial-publish-result.json # 部分成功示例
└── failed-publish-result.json  # 失败示例
```

### agent 规则

```
openclaw-agents-v2/
├── collector-rules.md          # 含 CPIS V2 图片交接硬约束
├── analyst-rules.md            # 含 CPIS V2 图片字段透传硬约束
├── curator-rules.md            # 含 CPIS V2 飞书图片发布硬约束
├── IMAGE-WORKFLOW.md           # 飞书图片工作流文档
├── install-rules.sh            # 规则安装脚本
└── verify-rules.sh             # 规则验证脚本
```

## 部署步骤

```bash
# 1. 推送代码
git add -A && git commit -m "cpis-json-gate: v1.2.0 — add before_agent_finalize for publish_result" && git push

# 2. 安装/升级插件
bash openclaw-plugins/cpis-json-gate/install-on-lx.sh

# 3. 配置 allowConversationAccess
openclaw config set plugins.entries.cpis-json-gate.hooks.allowConversationAccess true

# 4. 验证
bash scripts/verify-deploy.sh

# 5. 安装 Agent 规则
bash openclaw-agents-v2/install-rules.sh
bash openclaw-agents-v2/verify-rules.sh
```
