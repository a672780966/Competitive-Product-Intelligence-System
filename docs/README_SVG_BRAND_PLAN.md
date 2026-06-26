# CPIS README — SVG 品牌资产 + 多语言集成实施方案

> 生成日期：2026-06-26
> 状态：待执行
> 负责人：Codex（SVG 设计稿）+ OpenCode Worker（文件落盘 + README 修改）

---

## 一、当前状态摘要

| 项目 | 状态 |
|------|------|
| README.md（中文主版） | 229 行，含 badges + 语言切换器 + 纯文本标题头 |
| docs/README.en.md | 231 行，英文版，已翻译 |
| docs/README.ja.md | 126 行，日文版（精简版） |
| docs/README.ko.md | 113 行，韩文版（精简版） |
| docs/assets/ 目录 | **不存在** |
| 现有图片 | 无本地图片，全部为 shields.io badges（外链，保留） |
| README 标题头 | 纯 HTML 文本 `<p>` 包裹，无图片 |

---

## 二、SVG 设计稿（完整 XML）

### 2.1 Logo: `docs/assets/cpis-logo.svg`

**规格：**
- 尺寸：220 × 60
- 风格：企业级 SaaS，深蓝/青色，科技极简
- 约束：≤ 5KB，无外部资源，无 base64，无商标风险素材

**设计说明：**
- 左侧：正六边形数据节点图标 — 代表情报网络中的 AI 节点 + 数据连接
- 右侧：CPIS 文字，C 和 I 用青色渐变突出品牌首字母
- 底部小字："INTELLIGENCE PLATFORM" 作为品牌副标

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 60" width="220" height="60">
  <defs>
    <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1A73E8"/>
      <stop offset="100%" stop-color="#00BCD4"/>
    </linearGradient>
    <linearGradient id="logoBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F1B2D"/>
      <stop offset="100%" stop-color="#1A2A4A"/>
    </linearGradient>
  </defs>
  <!-- 六边形数据节点图标 -->
  <polygon points="25,5 45,15 45,35 25,45 5,35 5,15" fill="none" stroke="url(#logoGrad)" stroke-width="2.5"/>
  <polygon points="25,12 38,18 38,30 25,36 12,30 12,18" fill="url(#logoGrad)" opacity="0.12"/>
  <circle cx="25" cy="24" r="4" fill="url(#logoGrad)"/>
  <!-- 连接节点 -->
  <circle cx="12" cy="18" r="2" fill="#00BCD4"/>
  <circle cx="38" cy="18" r="2" fill="#00BCD4"/>
  <circle cx="12" cy="30" r="2" fill="#00BCD4"/>
  <circle cx="38" cy="30" r="2" fill="#00BCD4"/>
  <!-- CPIS 文字 -->
  <text x="58" y="30" font-family="Arial,Helvetica,sans-serif" font-size="24" font-weight="bold" fill="#0F1B2D">
    <tspan fill="url(#logoGrad)">C</tspan>P<tspan fill="url(#logoGrad)">I</tspan>S
  </text>
  <!-- 副标 -->
  <text x="58" y="46" font-family="Arial,Helvetica,sans-serif" font-size="9" fill="#667788" letter-spacing="1.5">
    INTELLIGENCE PLATFORM
  </text>
</svg>
```

**估算大小：** ~1.3 KB ✅ ≤ 5KB

---

### 2.2 Banner: `docs/assets/cpis-banner.svg`

**规格：**
- 尺寸：800 × 200
- 内容：标题 CPIS V1 + 中文副标题 + 英文副标题 + 关键词
- 背景：深色科技感，简洁数据流线条
- 约束：≤ 5KB，无外部资源，无 base64，无商标风险

**设计说明：**
- 深蓝渐变背景，带细微网格线和数据流曲线
- 左侧六边形小图标（与 Logo 呼应）
- 左侧对齐排版：大标题 → 中文副标题 → 英文副标题 → 关键词胶囊

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" width="800" height="200">
  <defs>
    <linearGradient id="bannerBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0A1628"/>
      <stop offset="100%" stop-color="#152238"/>
    </linearGradient>
    <linearGradient id="bannerAccent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#1A73E8"/>
      <stop offset="100%" stop-color="#00BCD4"/>
    </linearGradient>
    <linearGradient id="bannerGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1A73E8" stop-opacity="0.12"/>
      <stop offset="100%" stop-color="#00BCD4" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <!-- 背景 -->
  <rect width="800" height="200" fill="url(#bannerBg)" rx="8"/>
  <!-- 网格线 -->
  <line x1="0" y1="50" x2="800" y2="50" stroke="#1A2A4A" stroke-width="0.5"/>
  <line x1="0" y1="100" x2="800" y2="100" stroke="#1A2A4A" stroke-width="0.5"/>
  <line x1="0" y1="150" x2="800" y2="150" stroke="#1A2A4A" stroke-width="0.5"/>
  <!-- 数据流装饰曲线 -->
  <path d="M 0,185 Q 200,165 400,185 T 800,185" fill="none" stroke="url(#bannerGlow)" stroke-width="1"/>
  <path d="M 0,175 Q 150,195 350,175 T 800,175" fill="none" stroke="#1A73E8" stroke-width="0.5" opacity="0.25"/>
  <!-- 左上角六边形装饰 -->
  <polygon points="50,100 65,108 65,124 50,132 35,124 35,108" fill="none" stroke="url(#bannerAccent)" stroke-width="2"/>
  <circle cx="50" cy="116" r="3" fill="url(#bannerAccent)"/>
  <!-- 主标题 -->
  <text x="85" y="78" font-family="Arial,Helvetica,sans-serif" font-size="36" font-weight="bold" fill="#FFFFFF">CPIS V1</text>
  <!-- 中文副标题 -->
  <text x="85" y="112" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#D0D8E0">企业 AI 竞品情报平台</text>
  <!-- 英文副标题 -->
  <text x="85" y="136" font-family="Arial,Helvetica,sans-serif" font-size="13" fill="#7A8A9A">AI-Powered Competitive Product Intelligence Platform</text>
  <!-- 关键词标签 -->
  <rect x="85" y="150" width="630" height="28" rx="14" fill="#1A2A4A" opacity="0.8"/>
  <text x="100" y="168" font-family="Arial,Helvetica,sans-serif" font-size="11" fill="#7AACDD">
    Discovery · Collection · Analysis · Feishu · MCP
  </text>
</svg>
```

**估算大小：** ~2.1 KB ✅ ≤ 5KB

---

## 三、实施步骤

### 3.1 Codex 负责 — SVG 设计稿

1. **根据上方 XML 生成两个 SVG 文件**
   - `docs/assets/cpis-logo.svg` — 220×60 logo
   - `docs/assets/cpis-banner.svg` — 800×200 banner
2. **验证设计要求**
   - SVG 语法正确（标准 `<svg>` 命名空间）
   - 无 `<image>` 标签或外部引用
   - 无 `data:image/...` base64 内容
   - 文件大小 ≤ 5KB 每个
   - 无真实公司商标/Logo

### 3.2 OpenCode Worker 负责 — 文件落盘

1. **创建 assets 目录**
   ```bash
   mkdir -p /home/ctyun/Competitive-Product-Intelligence-System/docs/assets/
   ```

2. **写入 SVG 文件**
   - `docs/assets/cpis-logo.svg`
   - `docs/assets/cpis-banner.svg`

3. **验证文件**
   - `ls -la docs/assets/` 确认文件存在
   - `wc -c docs/assets/*.svg` 确认 ≤ 5120 bytes each
   - Python/Node SVG 解析器检查语法是否有效

### 3.3 OpenCode Worker 负责 — README 图片引用插入

#### README.md（中文主版）

**替换位置：** 第 5-9 行（当前纯文本标题头）

**当前内容（第 5-14 行）：**
```html
<p align="center">
  <b>CPIS V1</b><br>
  <b>企业 AI 竞品情报平台</b><br>
  <i>AI-Powered Competitive Product Intelligence Platform</i>
</p>

<p align="center">
  AI 驱动的竞品信息自动采集、结构化提取与分析系统。<br>
  将散落在互联网上的公开竞品信息，转化为结构化的产品数据库和可追溯的商业情报。
</p>
```

**替换为：**
```html
<p align="center">
  <img src="docs/assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="docs/assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>

<p align="center">
  AI 驱动的竞品信息自动采集、结构化提取与分析系统。<br>
  将散落在互联网上的公开竞品信息，转化为结构化的产品数据库和可追溯的商业情报。
</p>
```

> **注意：** 保留第 12-14 行的描述文字。Logo 和 Banner 替换原有的纯文本标题头。

#### docs/README.en.md（英文版）

**替换位置：** 第 5-13 行

**当前内容：**
```html
<p align="center">
  <b>CPIS V1</b><br>
  <b>AI-Powered Competitive Product Intelligence Platform</b>
</p>

<p align="center">
  Automatically collect, extract, and analyze competitive product information<br>
  from public web sources — transforming raw data into structured, actionable insights.
</p>
```

**替换为：**
```html
<p align="center">
  <img src="assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>

<p align="center">
  Automatically collect, extract, and analyze competitive product information<br>
  from public web sources — transforming raw data into structured, actionable insights.
</p>
```

> **注意：** 路径为 `assets/...`（相对于 docs/ 目录），而非 `docs/assets/...`。

#### docs/README.ja.md（日文版）

**替换位置：** 第 5-13 行

**当前内容：**
```html
<p align="center">
  <b>CPIS V1</b><br>
  <b>エンタープライズ AI 競合情報プラットフォーム</b><br>
  <i>AI-Powered Competitive Product Intelligence Platform</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT License">
  ...
</p>
```

**替换为：**
```html
<p align="center">
  <img src="assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>
```

> **注意：** 日文版和无 badges 之间没有 description 段落，直接从标题跳到 badges。Logo+Banner 替换纯文本标题头即可，保留后续内容。

#### docs/README.ko.md（韩文版）

**替换位置：** 第 5-10 行

**当前内容：**
```html
<p align="center">
  <b>CPIS V1</b><br>
  <b>엔터프라이즈 AI 경쟁사 제품 인텔리전스 플랫폼</b><br>
  <i>AI-Powered Competitive Product Intelligence Platform</i>
</p>
```

**替换为：**
```html
<p align="center">
  <img src="assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>
```

---

## 四、检查点清单

### 4.1 SVG 可渲染检查
- [ ] 用浏览器打开 `docs/assets/cpis-logo.svg` 确认正确渲染
- [ ] 用浏览器打开 `docs/assets/cpis-banner.svg` 确认正确渲染
- [ ] 用 `python -c "import xml.etree.ElementTree as ET; ET.parse('file')"` 验证 XML 语法

### 4.2 文件大小检查
- [ ] `wc -c docs/assets/cpis-logo.svg` ≤ 5120
- [ ] `wc -c docs/assets/cpis-banner.svg` ≤ 5120

### 4.3 无外链图片检查
- [ ] `grep -r '<image' docs/assets/` 无结果（无 `<image>` 标签）
- [ ] `grep -r 'href=' docs/assets/cpis-*.svg` 仅含 SVG 命名空间定义，无外部 URL
- [ ] `grep -r 'data:image' docs/assets/` 无结果

### 4.4 无 base64 检查
- [ ] `grep -r 'base64' docs/assets/` 无结果

### 4.5 README 图片不破损
- [ ] 所有 `src` 路径指向本地 SVG 文件而非 URL
- [ ] README.md 路径为 `docs/assets/...`（相对于 repo root）
- [ ] docs/README.*.md 路径为 `assets/...`（相对于 docs/ 目录）
- [ ] 路径文件名与实际文件完全一致（大小写敏感）

### 4.6 无过度营销
- [ ] SVG 中不包含 "best", "leading", "#1", "最先进" 等营销词汇
- [ ] SVG 仅展示产品名称、版本号、功能描述关键词

### 4.7 多语言入口正确
- [ ] 语言切换器中的各 README 链接未因修改而破坏
- [ ] 中文主版内容无误
- [ ] 英文版路径 `assets/...` 正确

### 4.8 商标合规
- [ ] SVG 中无其他公司的 Logo、图标、品牌名称
- [ ] SVG 中无 ™ / ® 标记（除非属于 CPIS 自身）
- [ ] 关键词 "Feishu" / "MCP" 仅作文字描述使用，不含飞书 Logo

---

## 五、风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| SVG 在某些 GitHub 主题（Dark Mode）下不可见 | 已使用深色背景 Banner，文字为亮色；Logo 背景透明但文字为深蓝，需在浅色背景查看 — GitHub README 背景为白色，兼容良好 |
| 多语言 README 路径不一致导致图片破损 | 严格区分 `docs/assets/`（从 root）和 `assets/`（从 docs/）路径 |
| SVG 过大超 5KB | Banner 当前 ~2.1KB，Logo ~1.3KB，远低于限制；如需添加内容注意控制 |
| 中文字体在 SVG 中的渲染 | SVG 使用系统字体 `Arial,Helvetica,sans-serif` + fallback；中文部分依赖浏览器默认中文字体，GitHub 和主流系统均可正确显示 |

---

## 六、执行顺序

```
Step 1: Codex 生成 SVG 设计稿（XML 确认）
    ↓
Step 2: OpenCode Worker 创建 docs/assets/ 并写入 SVG 文件
    ↓
Step 3: OpenCode Worker 修改 README.md 标题头（替换为图片）
    ↓
Step 4: OpenCode Worker 修改 docs/README.en.md 标题头
    ↓
Step 5: OpenCode Worker 修改 docs/README.ja.md 标题头
    ↓
Step 6: OpenCode Worker 修改 docs/README.ko.md 标题头
    ↓
Step 7: 逐项执行检查点清单
    ↓
Step 8: 报告结果
```

---

## 七、完成标准

当以下条件全部满足时任务完成：

1. ✅ `docs/assets/cpis-logo.svg` 存在，可渲染，≤ 5KB
2. ✅ `docs/assets/cpis-banner.svg` 存在，可渲染，≤ 5KB
3. ✅ 两个 SVG 均无外部资源引用
4. ✅ 两个 SVG 均无 base64 编码内容
5. ✅ 两个 SVG 均无第三方商标/Logo
6. ✅ README.md 顶部展示 Logo + Banner 图片
7. ✅ docs/README.en.md 顶部图片路径正确（`assets/...`）
8. ✅ docs/README.ja.md 顶部图片路径正确
9. ✅ docs/README.ko.md 顶部图片路径正确
10. ✅ 所有图片链接不破损，路径大小写匹配
11. ✅ 中文主版内容完整保留，多语言切换器未破坏
