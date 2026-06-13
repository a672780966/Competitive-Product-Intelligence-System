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
- `cpis-json-gate` v1.1.0 已加载。
- `before_tool_call` priority 为 1000。
- 飞书权限 `docs:document.media:upload` 已开通。
- 图片上传测试成功。
- 端到端恢复发布成功：
  - run_id：`amazon_us_tens_20260613_e2e001`
  - 飞书文档：https://feishu.cn/docx/TJBnduVpmofKEpxPP6dcRd3Ende
  - 图片：2/2 上传成功
  - 工具失败：0
  - `replayInvalid=false`
  - 数据状态：`partial`（只采集了前两名）

## 已定位问题

### 1. 长期使用 main 会话导致上下文爆炸

旧的 `cpis-knowledge-curator:main` 曾达到 `2.8m/100k`，并陷入 `message` 状态回报与 Agent 确认循环。

后续必须使用基于 `run_id` 的独立 session key，禁止所有任务继续堆入 `main`。

### 2. 中文输入乱码

恢复命令将长中文 JSON 直接粘贴进 shell，最终日志中的中文已在进入 Agent 前变为乱码。

修复方向：

- 将任务 JSON 保存为 UTF-8 文件。
- 调用 OpenClaw 时从文件读取消息，避免终端粘贴和 locale 转码。
- 提供一个统一的 UTF-8 调用脚本。

### 3. 最终输出不是严格 JSON

知识管理员最终结果包含英文说明和 Markdown 代码围栏，虽然内部 JSON 内容基本正确，但不符合硬约束；同时缺少：

```json
"object_type":"publish_result"
```

当前 Gate 只使用 `before_tool_call`，只能约束 `sessions_send`，无法约束最终回答。

## 已确认的正确 OpenClaw Hook

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

## 下一步必须实施

将 `cpis-json-gate` 升级为 v1.2.0：

1. 保留现有 `before_tool_call` 交接验证。
2. 新增 `validatePublishResult(text)`。
3. 新增 `before_agent_finalize` Hook，仅对 `cpis-knowledge-curator` 生效。
4. 最终文本必须是单个 JSON 对象：

```json
{
  "schema_version":"1.0",
  "object_type":"publish_result",
  "run_id":"...",
  "agent_id":"cpis-knowledge-curator",
  "status":"success|partial|failed",
  "published":true,
  "message_zh":"...",
  "message_en":"...",
  "feishu_url":"https://...",
  "images_expected":2,
  "images_uploaded":2,
  "image_failures":[]
}
```

5. 禁止 Markdown 围栏、JSON 前后附加文字及未知字段。
6. `images_uploaded < images_expected` 时，`status` 不得为 `success`。
7. `published=true` 时必须存在有效 `feishu_url`。
8. 验证失败时要求模型重写一次：`maxAttempts: 1`，不得重新调用飞书工具。
9. 增加验证器单元测试。
10. 增加 UTF-8 文件调用脚本和示例任务 JSON。
11. 更新插件版本、部署文档、验证脚本和 ZIP 包。

## 当前本地状态

上一轮在正式编辑文件前被中止，因此上述 v1.2 修改尚未写入仓库。本交接文件是云端继续工作的唯一新增提交。

## 云端聊天启动提示词

请在连接此 GitHub 仓库后执行：

> 读取 `CODEX-CLOUD-HANDOFF.md`，继续完成其中“下一步必须实施”的全部工作。先审计当前 `openclaw-plugins/cpis-json-gate` 和 `openclaw-agents-v2`，然后实现、测试、打包并提交到 main。不要重新设计项目，也不要改动三个 Agent 的业务职责。
