[🇨🇳 中文](../README.md) · [🇺🇸 English](README.en.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md)

---

<p align="center">
  <img src="assets/cpis-logo.svg" alt="CPIS Logo" width="400">
</p>

<p align="center">
  <img src="assets/cpis-banner.svg" alt="CPIS V1 Banner" width="800">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT License">
  <img src="https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white" alt="React 19">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL 16">
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose">
  <img src="https://img.shields.io/badge/MCP-Ready-000000" alt="MCP Ready">
  <img src="https://img.shields.io/badge/Feishu-Sync-3370FF?logo=lark&logoColor=white" alt="Feishu Sync">
</p>

---

## CPIS とは

CPIS（Competitive Product Intelligence System）は、公開 Web ソースから競合製品情報を自動収集・抽出・分析するエンタープライズ向けプラットフォームです。AI 支援パイプラインにより、散在する競合情報を構造化されたデータベースとトレーサブルなビジネスインテリジェンスに変換します。

---

## 製品ワークフロー

```mermaid
flowchart LR
    A["🧠 自然言語リクエスト"] --> B["🔍 AI ソース発見"]
    B --> C["📋 候補ソース"]
    C --> D["👤 ユーザー選択"]
    D --> E["📄 収集テンプレート / RunPlan"]
    E --> F["🌐 収集ランタイム<br/>8 登録"]
    F --> G["🧹 クリーナー / AI 抽出"]
    G --> H["📊 製品バージョン / レビュー"]
    H --> I["📡 Feishu Sync / 使用量 / スケジューラー"]

    style A fill:#4A90D9,color:#fff,stroke:none
    style I fill:#34A853,color:#fff,stroke:none
```

---

## コアモジュール

| モジュール | 説明 |
|-----------|------|
| **AI ソース発見** | SearchProvider + LLMProvider による自然言語からのインテリジェントソース発見 |
| **候補ソース選定** | リスク評価、ソース種別分類、スコアリング |
| **RunPlan エンジン** | 宣言的 JSON 計画、URL パターン解決 |
| **収集ランタイム** | 8 種類の登録済みランタイム（HTTP/Playwright/予約済み） |
| **AI 抽出** | HTML → 構造化 Product + ProductVersion |
| **製品バージョン管理** | 差分追跡、Changelog、証拠ベース抽出 |
| **レビューワークフロー** | 承認/却下/再開、自動承認閾値 |
| **Feishu 同期** | 双方向 Bitable 同期、リトライ、ステータス追跡 |

---

## システムアーキテクチャ

```mermaid
graph TB
    subgraph Frontend["フロントエンド (React 19 + Ant Design)"]
        UI["発見 / テンプレート / スケジューラー / タスク / 製品 / 使用量 / レビュー"]
    end
    subgraph API["API レイヤー (FastAPI)"]
        DiscoveryAPI["/api/v1/discovery"]
        TemplatesAPI["/api/v1/collection-templates"]
        TasksAPI["/api/v1/collection-tasks/snapshots/events"]
        ProductsAPI["/api/v1/products/versions/reviews"]
        SyncAPI["/api/v1/sync-records"]
        UsageAPI["/api/v1/usage"]
    end
    subgraph Providers["Provider レイヤー"]
        Search["SearchProvider<br/>DuckDuckGo·Stub·OpenAI·Gemini·Claude"]
        LLM["LLMProvider<br/>Stub·OpenAI·Gemini·Claude·DeepSeek·Qwen"]
    end
    subgraph Pipeline["非同期パイプライン (Celery + Redis)"]
        Collect["収集ランタイム<br/>direct_http·playwright·scrapling·crawl4ai·rss·pdf·api"]
        Clean["HTML クリーナー"]
        Extract["AI 抽出器"]
    end
    subgraph Storage["永続化"]
        DB[("PostgreSQL 16")]
    UI --> API
    API --> Providers
    API --> Pipeline
    API --> Storage
    Pipeline --> Storage
    Storage --> Sync["統合"]
        Feishu["Feishu Bitable"]
        MCP["MCP サーバー"]
        Sched["定期収集"]
    end
    UI --> API --> Providers & Pipeline & Storage
    Pipeline --> Storage --> Sync
```

---

## クイックスタート

```bash
git clone https://github.com/a672780966/Competitive-Product-Intelligence-System.git
cd Competitive-Product-Intelligence-System
cp .env.example .env
docker compose -f docker-compose.demo.yml up -d
docker compose -f docker-compose.demo.yml exec backend python /app/scripts/seed_demo.py
```

[http://localhost:8000/docs](http://localhost:8000/docs) · [http://localhost:8080](http://localhost:8080)

---

## ライセンス

MIT License。詳細は [LICENSE](../release/LICENSE.md) をご覧ください。

---

> この文書は機械翻訳を含みます。正確な内容は中国語 README を基準とします。
