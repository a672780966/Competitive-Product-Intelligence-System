# CPIS V1 代码审计报告

审计日期：2026-06-12
审计范围：全部后端 Python 文件（60+ 文件）
审计模式：只审计不改

---

## 🔴 严重（CONFIRMED — 可导致数据错误或任务挂起）

### 1. `services/product_service.py:148-154` — 缺失字段时仍自动审核通过

`elif` 分支与 `if` 分支代码完全一致。当 confidence ≥ 0.7 但 `missing_fields` 非空时，产品错误地被自动批准并推送到飞书，跳过了人工复核。

**修复建议**: `elif` 分支应设置 `NEEDS_REVIEW` 并跳过 `set_current_version`。

---

### 2. `services/task_service.py:243-249` — 验证失败且无 error_code 时任务永久卡在 VALIDATING

当 `validate_url()` 返回非 passing 状态但 `error_code` 为 `None` 时，`update_status` 被跳过。任务状态停留在 `VALIDATING`，既不能被采集流程拾取，也不能被重试。

**修复建议**: 移除 `if result.error_code` 守卫，无条件执行 `update_status`。

---

### 3. `models/collection_task.py:53` — DB 加载后 `__repr__` 崩溃

`status` 列定义为 `String(32)`，从数据库加载后是普通字符串，调用 `.value` 抛出 `AttributeError`。任何需要 `repr()` 任务对象的场景都会崩溃。

**修复建议**: `__repr__` 中使用 `self.status` 直接输出，或用 `getattr(self.status, 'value', self.status)`。

---

## 🟠 高（CONFIRMED — 运行时崩溃或数据丢失）

### 4. `extractors/product_extractor.py:100-101` — LLM 输出异常时 Pydantic 构造无异常保护

LLM 返回非 dict 或类型不匹配的值时，Pydantic 构造抛 `ValidationError/TypeError`，无 `try` 捕获。整个 `extract()` 返回 500。

**修复建议**: 用 `try/except pydantic.ValidationError` 包裹，失败时返回低置信度结果。

---

### 5. `cleaners/candidate_extractor.py:84` — 品牌检测错误地检查值而非属性名

对 `<meta itemprop="brand" content="Nike">`，检查 `"brand" in "nike"` 返回 `False`，所有通过 `itemprop="brand"` 标记的品牌都被遗漏。

**修复建议**: 先检查 `tag.get("itemprop")` 或 class 名是否包含 "brand"，而非检查 `content` 值。

---

### 6. `cleaners/candidate_extractor.py:120-122` — 价格 0 被当作 falsy 丢弃

`0 or ...` 落入无关分支，`if price:` 再次过滤 0。免费产品的价格永远无法进入候选列表。

**修复建议**: 使用 `is not None` 代替 `or` 回退，使用 `if price is not None` 代替 `if price:`。

---

### 7. `collectors/playwright_collector.py:61-77` — 浏览器进程泄漏

`new_context()` 或 `new_page()` 在进入 `try` 块之前抛出异常时，`browser.close()` 永不执行。孤立的 Chromium 子进程消耗资源。

**修复建议**: 将 `browser` 创建移到 `try/finally` 结构中，或用 `async with` 管理浏览器生命周期。

---

## 🟡 中（PLAUSIBLE — 边界条件或配置依赖性）

### 8. `integrations/feishu_client.py:91` — 缺少 `raise_for_status()`

飞书 API 返回代理错误页（502/504 HTML）时，`response.json()` 抛出 `json.JSONDecodeError`。

**修复建议**: 在 `response.json()` 前调用 `response.raise_for_status()`。

---

### 9. `schemas/task.py:40` — 时区敏感 datetimes 无时区信息

naive datetime 与数据库 `DateTime(timezone=True)` 列比较时，PostgreSQL 报操作符不存在错误。

**修复建议**: `date_from`/`date_to` 使用 `aware_datetime` 类型或添加 UTC 时区转换。

---

### 10. `integrations/field_mapping.py:67` — 最后采集时间硬编码为空

`build_feishu_record()` 不接受时间戳参数，没有任何代码路径可以填充此字段。

**修复建议**: 增加 `collected_at` 参数传入构建函数。

---

### 11. `integrations/field_mapping.py:43` — 两个飞书列映射到同一字段

"主要参数"和"功能列表"永远显示相同数据。"主要参数"本应映射到规格参数。

**修复建议**: "主要参数"映射到 `_build_specs(sd)` 的输出。

---

### 12. `cleaners/html_cleaner.py:77` — `page_url` 参数被忽略

`clean()` 方法接受 `page_url` 参数文档化用于解析相对路径，但管线中从未使用。清洗后的 Markdown 中相对链接不可点击。

**修复建议**: 在 `_to_markdown()` 中用 `page_url` 解析相对 `src`。

---

## ⚪ 低（PLAUSIBLE — 改进建议）

### 13. `extractors/product_extractor.py:105-107` — evidence 类型检查不完整

`evidence_raw` 被假定为 `dict`，若 LLM 返回 `[]` 或 `null` 则崩溃。

**修复建议**: 在 `.items()` 前加 `isinstance(evidence_raw, dict)` 检查。

---

## 汇总

| # | 文件 | 行 | 严重度 | 类型 |
|---|------|-----|--------|------|
| 1 | `services/product_service.py` | 148-154 | 🔴 严重 | 逻辑错误：缺失字段仍自动批准 |
| 2 | `services/task_service.py` | 243-249 | 🔴 严重 | 任务永久卡死 |
| 3 | `models/collection_task.py` | 53 | 🔴 严重 | `__repr__` 运行时崩溃 |
| 4 | `extractors/product_extractor.py` | 100-101 | 🟠 高 | LLM 异常导致 500 |
| 5 | `cleaners/candidate_extractor.py` | 84 | 🟠 高 | 品牌检测失效 |
| 6 | `cleaners/candidate_extractor.py` | 120-122 | 🟠 高 | 免费产品价格被丢弃 |
| 7 | `collectors/playwright_collector.py` | 61-77 | 🟠 高 | 浏览器进程泄漏 |
| 8 | `integrations/feishu_client.py` | 91 | 🟡 中 | 非 JSON 响应崩溃 |
| 9 | `schemas/task.py` | 40 | 🟡 中 | 时区不匹配 |
| 10 | `integrations/field_mapping.py` | 67 | 🟡 中 | 时间戳硬编码空值 |
| 11 | `integrations/field_mapping.py` | 43 | 🟡 中 | 列映射重复 |
| 12 | `cleaners/html_cleaner.py` | 77 | 🟡 中 | 相对链接未解析 |
| 13 | `extractors/product_extractor.py` | 105-107 | ⚪ 低 | 缺少类型守卫 |

**总计**: 13 个发现 | 3 🔴 严重 + 4 🟠 高 + 5 🟡 中 + 1 ⚪ 低
