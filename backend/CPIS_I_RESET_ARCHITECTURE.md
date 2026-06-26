# CPIS Phase I-Reset — Architecture Redesign

## 1. Data Flow Diagram (Text-Based)

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         CPIS Phase I-Reset Data Flow                    │
└──────────────────────────────────────────────────────────────────────────┘

User / Agent / Frontend
        │
        ├── POST /api/v1/discovery/sessions (initiate discovery on a URL)
        │   └── SourceDiscoveryService
        │       ├── 1. URL validation (existing url_validator)
        │       ├── 2. SourceDiscoverySession created (status=running)
        │       ├── 3. Built-in Collector (whitelist executor) fetches URL
        │       │   ├── direct_http (httpx)  ← primary path
        │       │   ├── playwright (fallback for JS-heavy)
        │       │   └── scrapling / crawl4ai (feature-flag gated)
        │       ├── 4. HTML cleaner (existing HtmlCleaner)
        │       ├── 5. Candidate extractor → SourceCandidate records
        │       ├── 6. Session status → completed
        │       └── 7. User reviews candidates → promotes to CollectionTask
        │
        ├── POST /api/v1/collection-templates
        │   └── CollectionTemplate stored (declarative RunPlan JSON only)
        │       ├── name, description, source_configs[]
        │       ├── run_plan (declarative JSON — see RUNPLAN_DECLARATIVE_SPEC.md)
        │       └── schedule (optional cron expression)
        │
        ├── POST /api/v1/scheduled-collections
        │   └── ScheduledCollection
        │       ├── links to CollectionTemplate
        │       ├── celery_beat schedule (cron)
        │       └── produces CollectionTasks on each tick
        │
        ├── POST /api/v1/openclaw/evidence  ← EXISTING BRIDGE (unchanged)
        │
        └── GET /api/v1/usage/*  ← aggregated stats

Existing Pipeline (unchanged):
  CollectionTask → (validator) → collect_url → clean_content → extract_structured_data
  → ProductVersioning → Review → FeishuSync → ReportGeneration

New Discovery Pipeline:
  SourceDiscoverySession → URL validation → Built-in Collector → HTML Cleaning
  → Candidate Extraction → SourceCandidate[] → User Review → Promote to CollectionTask
```

## 2. Module Responsibility Map

```
app/
├── models/
│   ├── base.py                              [EXISTING — unchanged]
│   ├── enums.py                             [EXTEND — new enum values]
│   ├── types.py                             [EXISTING — unchanged]
│   ├── collection_task.py                   [EXISTING — unchanged]
│   ├── task_event.py                        [EXISTING — unchanged]
│   ├── source_snapshot.py                   [EXISTING — unchanged]
│   ├── product.py                           [EXISTING — unchanged]
│   ├── product_version.py                   [EXISTING — unchanged]
│   ├── product_evidence.py                  [EXISTING — unchanged]
│   ├── review_record.py                     [EXISTING — unchanged]
│   ├── feishu_sync_record.py                [EXISTING — unchanged]
│   ├── prompt_template.py                   [EXISTING — unchanged]
│   ├── audit_log.py                         [EXISTING — unchanged]
│   │
│   ├── source_discovery_session.py          [NEW]  Discovery session
│   ├── source_candidate.py                  [NEW]  Discovered candidates
│   ├── collection_template.py               [NEW]  Named collection template
│   ├── scheduled_collection.py              [NEW]  Scheduled run config
│   └── usage_daily_stat.py                  [NEW]  Aggregated usage stats
│
├── repositories/
│   ├── __init__.py                          [EXISTING]
│   ├── task_repository.py                   [EXISTING — unchanged]
│   ├── product_repository.py                [EXISTING — unchanged]
│   └── sync_repository.py                   [EXISTING — unchanged]
│   │
│   ├── discovery_repository.py              [NEW]  Session + Candidate CRUD
│   ├── template_repository.py               [NEW]  CollectionTemplate CRUD
│   ├── schedule_repository.py               [NEW]  ScheduledCollection CRUD
│   └── usage_repository.py                  [NEW]  UsageDailyStat CRUD
│
├── services/
│   ├── __init__.py                          [EXISTING]
│   ├── task_service.py                      [EXISTING — extended with discovery→task promotion]
│   ├── product_service.py                   [EXISTING — unchanged]
│   ├── review_service.py                    [EXISTING — unchanged]
│   ├── report_service.py                    [EXISTING — unchanged]
│   ├── feishu_sync_service.py               [EXISTING — unchanged]
│   ├── openclaw_bridge_service.py           [EXISTING — unchanged]
│   ├── url_validator.py                     [EXISTING — unchanged]
│   │
│   ├── discovery_service.py                 [NEW]  Orchestrates discovery flow
│   ├── template_service.py                  [NEW]  Template CRUD + RunPlan validation
│   ├── schedule_service.py                  [NEW]  Scheduler lifecycle
│   └── usage_service.py                     [NEW]  Usage stat aggregation
│
├── collectors/
│   ├── __init__.py                          [MODIFIED — add WhitelistExecutor]
│   ├── base.py                              [EXISTING — unchanged]
│   ├── httpx_collector.py                   [EXISTING — unchanged]
│   ├── playwright_collector.py              [EXISTING — unchanged]
│   ├── selector.py                          [EXISTING — unchanged]
│   ├── domain_lock.py                       [EXISTING — unchanged]
│   │
│   ├── whitelist_executor.py                [NEW]  RunPlan-safe collector runtime
│   └── feature_gate.py                      [NEW]  scrapling/crawl4ai feature flags
│
├── api/
│   ├── __init__.py                          [EXISTING — unchanged]
│   ├── tasks.py                             [EXISTING — unchanged]
│   ├── products.py                          [EXISTING — unchanged]
│   ├── reviews.py                           [EXISTING — unchanged]
│   ├── reports.py                           [EXISTING — unchanged]
│   ├── sync.py                              [EXISTING — unchanged]
│   ├── openclaw.py                          [EXISTING — unchanged]
│   │
│   ├── discovery.py                         [NEW]  /api/v1/discovery/*
│   ├── collection_templates.py              [NEW]  /api/v1/collection-templates/*
│   ├── scheduled_collections.py             [NEW]  /api/v1/scheduled-collections/*
│   └── usage.py                             [NEW]  /api/v1/usage/*
│
├── schemas/
│   ├── __init__.py                          [EXISTING — unchanged]
│   ├── task.py                              [EXISTING — unchanged]
│   ├── product.py                           [EXISTING — unchanged]
│   ├── review.py                            [EXISTING — unchanged]
│   ├── sync.py                              [EXISTING — unchanged]
│   ├── openclaw.py                          [EXISTING — unchanged]
│   ├── extraction.py                        [EXISTING — unchanged]
│   │
│   ├── discovery.py                         [NEW]  Session + Candidate schemas
│   ├── collection_template.py               [NEW]  Template schemas
│   ├── scheduled_collection.py              [NEW]  Schedule schemas
│   ├── usage.py                             [NEW]  Usage stat schemas
│   └── run_plan.py                          [NEW]  RunPlan validation schema
│
├── tasks/
│   ├── __init__.py                          [EXISTING — unchanged]
│   ├── worker.py                            [EXISTING — unchanged]
│   ├── collection.py                        [EXISTING — unchanged]
│   │
│   └── scheduled.py                         [NEW]  Celery Beat periodic tasks
│
├── core/
│   ├── __init__.py                          [MODIFIED — extend Settings]
│   ├── database.py                          [EXISTING — unchanged]
│   ├── exceptions.py                        [EXISTING — unchanged]
│   ├── logging.py                           [EXISTING — unchanged]
│   └── middleware.py                         [EXISTING — unchanged]
│
├── collectors/whitelist_executor.py         [NEW]  (see above)
├── prompts/                                 [EXISTING — unchanged]
├── extractors/                              [EXISTING — unchanged]
├── cleaners/                                [EXISTING — unchanged]
└── integrations/                            [EXISTING — unchanged]
```

## 3. New vs Changed Files List

### NEW files (to create):

| File | Purpose |
|------|---------|
| `app/models/source_discovery_session.py` | SourceDiscoverySession model |
| `app/models/source_candidate.py` | SourceCandidate model |
| `app/models/collection_template.py` | CollectionTemplate model |
| `app/models/scheduled_collection.py` | ScheduledCollection model |
| `app/models/usage_daily_stat.py` | UsageDailyStat model |
| `app/repositories/discovery_repository.py` | Repository for discovery models |
| `app/repositories/template_repository.py` | Repository for template models |
| `app/repositories/schedule_repository.py` | Repository for schedule models |
| `app/repositories/usage_repository.py` | Repository for usage stats |
| `app/services/discovery_service.py` | Discovery orchestration service |
| `app/services/template_service.py` | Template management service |
| `app/services/schedule_service.py` | Schedule management service |
| `app/services/usage_service.py` | Usage statistics service |
| `app/collectors/whitelist_executor.py` | RunPlan-safe collector executor |
| `app/collectors/feature_gate.py` | scrapling/crawl4ai feature gate |
| `app/api/discovery.py` | Discovery API routes |
| `app/api/collection_templates.py` | Collection template API routes |
| `app/api/scheduled_collections.py` | Scheduled collection API routes |
| `app/api/usage.py` | Usage API routes |
| `app/schemas/discovery.py` | Discovery Pydantic schemas |
| `app/schemas/collection_template.py` | Collection template schemas |
| `app/schemas/scheduled_collection.py` | Scheduled collection schemas |
| `app/schemas/usage.py` | Usage stat schemas |
| `app/schemas/run_plan.py` | RunPlan declarative JSON schema |
| `app/tasks/scheduled.py` | Celery Beat periodic scheduler |
| `alembic/versions/003_phase_i_reset.py` | Migration for all new models |
| `frontend/src/features/discovery/DiscoveryPage.tsx` | Discovery frontend page |
| `frontend/src/features/collection-templates/TemplatesPage.tsx` | Template frontend page |
| `frontend/src/features/usage/UsagePage.tsx` | Usage frontend page |
| `frontend/src/api/discovery.ts` | Discovery API client module |
| `frontend/src/api/templates.ts` | Template API client module |
| `frontend/src/api/usage.ts` | Usage API client module |

### CHANGED files (to modify):

| File | Change |
|------|--------|
| `app/models/__init__.py` | Add new model imports |
| `app/models/enums.py` | Add DiscoveryStatus, CandidateStatus, ScheduleStatus enums |
| `app/collectors/__init__.py` | Export WhitelistExecutor |
| `app/main.py` | Register new routers |
| `app/core/__init__.py` | Extend Settings with new config vars |
| `frontend/src/App.tsx` | Add 3 new routes |
| `frontend/src/components/Layout.tsx` | Add 3 new menu items |
| `frontend/src/api/client.ts` | Rename to index.ts or extend with discovery/template/usage modules |
| `frontend/src/types/index.ts` | Add new TypeScript interfaces |

## 4. Route Design

### `/api/v1/discovery/*` — Source Discovery Session

```
POST   /api/v1/discovery/sessions
  → Create a discovery session from a URL or search query
  → Request: { source_type: "url"|"search", source_value: str, category_hint?: str }
  → Response: SourceDiscoverySession (id, status, created_at)
  → Action: starts async Celery task for discovery

GET    /api/v1/discovery/sessions
  → List discovery sessions (with status filter, pagination)
  → Response: PaginatedResponse<SourceDiscoverySession>

GET    /api/v1/discovery/sessions/{session_id}
  → Get session detail with its candidates
  → Response: SessionDetailResponse (session + list[SourceCandidate])

POST   /api/v1/discovery/sessions/{session_id}/cancel
  → Cancel a running discovery session

GET    /api/v1/discovery/candidates
  → List candidates across sessions (with status filter)
  → Response: PaginatedResponse<SourceCandidate>

POST   /api/v1/discovery/candidates/{candidate_id}/promote
  → Promote a candidate to a CollectionTask
  → Request: { category_hint?: str, auto_sync_feishu?: bool }
  → Response: TaskResponse (the created CollectionTask)

POST   /api/v1/discovery/candidates/{candidate_id}/dismiss
  → Dismiss a candidate (mark as dismissed so user doesn't see it again)

POST   /api/v1/discovery/candidates/batch-promote
  → Promote multiple candidates in one request
  → Request: { candidate_ids: uuid[], category_hint?: str }
  → Response: list[TaskResponse]
```

### `/api/v1/collection-templates/*` — Collection Templates

```
POST   /api/v1/collection-templates
  → Create a new collection template
  → Request: { name, description, source_configs[], run_plan, schedule? }
  → Response: CollectionTemplate (with validated run_plan)

GET    /api/v1/collection-templates
  → List templates (with optional name search)
  → Response: PaginatedResponse<CollectionTemplate>

GET    /api/v1/collection-templates/{template_id}
  → Get template detail

PUT    /api/v1/collection-templates/{template_id}
  → Update template (re-validates run_plan)

DELETE /api/v1/collection-templates/{template_id}
  → Soft-delete a template (cascades to schedules)

POST   /api/v1/collection-templates/{template_id}/run
  → Execute a template immediately (creates CollectionTasks)
  → Response: list[TaskResponse]
```

### `/api/v1/scheduled-collections/*` — Scheduled Collections

```
POST   /api/v1/scheduled-collections
  → Create a scheduled run
  → Request: { template_id, cron_expression, enabled, timezone }
  → Response: ScheduledCollection

GET    /api/v1/scheduled-collections
  → List all schedules
  → Response: PaginatedResponse<ScheduledCollection>

GET    /api/v1/scheduled-collections/{schedule_id}
  → Get schedule detail

PUT    /api/v1/scheduled-collections/{schedule_id}
  → Update schedule (cron, enabled, etc.)

DELETE /api/v1/scheduled-collections/{schedule_id}
  → Remove schedule (removes Celery Beat entry)

POST   /api/v1/scheduled-collections/{schedule_id}/enable
  → Enable a schedule

POST   /api/v1/scheduled-collections/{schedule_id}/disable
  → Disable a schedule

GET    /api/v1/scheduled-collections/{schedule_id}/executions
  → List past executions of this schedule
```

### `/api/v1/usage/*` — Usage Statistics

```
GET    /api/v1/usage/daily
  → Daily stats: collections count, success rate, avg duration
  → Query: date_from, date_to, group_by: "day"|"week"|"month"
  → Response: list[UsageDailyStat]

GET    /api/v1/usage/summary
  → Overall summary: total tasks, total products, storage used
  → Response: UsageSummaryResponse

GET    /api/v1/usage/by-domain
  → Stats grouped by domain (top N)
  → Query: limit=10, date_from, date_to

GET    /api/v1/usage/by-source
  → Stats grouped by discovery vs collection vs openclaw bridge
```

## 5. Provider Interface Design

### ModelProvider Interface (for AI extraction)

The existing `AIProvider` in `app/extractors/ai_provider.py` already provides the right abstraction. No changes needed — it supports OpenAI-compatible APIs. However, to make it extensible, we formalize it:

```python
# app/extractors/ai_provider.py (already exists, unchanged)

class AIProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> str:
        ...
```

### SearchProvider Interface (new — for discovery search)

```python
# app/services/search_provider.py (NEW)
from abc import ABC, abstractmethod

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str = ""
    source: str = "web"

class SearchProvider(ABC):
    """Abstract search provider — used during source discovery."""
    
    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        max_results: int = 10,
        language: str = "zh-CN",
    ) -> list[SearchResult]:
        ...

class DuckDuckGoSearchProvider(SearchProvider):
    """Free search provider using duckduckgo_search library."""
    ...

class BingSearchProvider(SearchProvider):
    """Bing Search API provider (requires API key)."""
    ...

class SerpApiProvider(SearchProvider):
    """SerpApi.com provider (requires API key)."""
    ...

def create_search_provider() -> SearchProvider:
    """Factory: returns configured search provider based on settings."""
    settings = get_settings()
    if settings.BING_SEARCH_API_KEY:
        return BingSearchProvider(api_key=settings.BING_SEARCH_API_KEY)
    return DuckDuckGoSearchProvider()
```

### CollectorProvider Interface (new — for whitelist executor)

```python
# app/collectors/whitelist_executor.py (NEW)

from abc import ABC, abstractmethod
from enum import Enum

class CollectorKind(str, Enum):
    DIRECT_HTTP = "direct_http"       # always allowed
    PLAYWRIGHT = "playwright"         # fallback, always allowed
    SCRAPLING = "scrapling"           # feature-gated
    CRAWL4AI = "crawl4ai"             # feature-gated

class BaseCollectorProvider(ABC):
    """Interface for a named collector in the whitelist."""
    
    kind: CollectorKind
    
    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> CollectResult:
        ...

class DirectHttpProvider(BaseCollectorProvider):
    kind = CollectorKind.DIRECT_HTTP
    # Wraps existing HttpxCollector

class PlaywrightProvider(BaseCollectorProvider):
    kind = CollectorKind.PLAYWRIGHT
    # Wraps existing PlaywrightCollector

class ScraplingProvider(BaseCollectorProvider):
    kind = CollectorKind.SCRAPLING
    # Feature-gated (only available if SCRAPLING_ENABLED=true)

class Crawl4aiProvider(BaseCollectorProvider):
    kind = CollectorKind.CRAWL4AI
    # Feature-gated (only available if CRAWL4AI_ENABLED=true)
```

## 6. Collector Runtime Design

### Whitelist Executor

```python
# app/collectors/whitelist_executor.py (NEW)

class WhitelistExecutor:
    """
    RunPlan-safe collector runtime.
    
    Only executes collectors listed in the RunPlan's 'collectors' array.
    Each collector must be in the whitelist: DIRECT_HTTP, PLAYWRIGHT,
    or feature-gated (SCRAPLING, CRAWL4AI).
    
    NO dynamic code execution. NO eval. NO exec. NO external scripts.
    The RunPlan is pure declarative JSON — it cannot encode logic.
    """
    
    WHITELIST: dict[CollectorKind, type[BaseCollectorProvider]] = {
        CollectorKind.DIRECT_HTTP: DirectHttpProvider,
        CollectorKind.PLAYWRIGHT: PlaywrightProvider,
    }
    
    FEATURE_GATED: dict[CollectorKind, type[BaseCollectorProvider]] = {}
    
    def __init__(self):
        self._providers: dict[CollectorKind, BaseCollectorProvider] = {}
        self._limiter = DomainConcurrencyLimiter(max_per_domain=2)
    
    def register_optional(self, kind: CollectorKind, provider_cls: type[BaseCollectorProvider]) -> None:
        """Register a feature-gated provider (scrapling, crawl4ai)."""
        self.FEATURE_GATED[kind] = provider_cls
    
    async def execute(self, plan: RunPlan) -> list[CollectResult]:
        """
        Execute a RunPlan.
        
        For each source/URL in the plan, runs the specified collector
        in the specified order. Returns results for all URLs.
        
        Raises RunPlanValidationError if the plan references an
        unregistered collector kind.
        """
        results: list[CollectResult] = []
        for entry in plan.collection_scope:
            collector_kind = entry.collector or CollectorKind.DIRECT_HTTP
            provider = self._get_provider(collector_kind)
            
            for url in entry.urls:
                async with self._limiter.limit(extract_domain(url)):
                    result = await provider.fetch(url, **entry.collector_params or {})
                    results.append(result)
        
        return results
    
    def _get_provider(self, kind: CollectorKind) -> BaseCollectorProvider:
        if kind in self._providers:
            return self._providers[kind]
        
        if kind in self.WHITELIST:
            provider = self.WHITELIST[kind]()
        elif kind in self.FEATURE_GATED:
            if not is_feature_enabled(kind):
                raise FeatureNotEnabledError(f"Collector '{kind.value}' is not enabled")
            provider = self.FEATURE_GATED[kind]()
        else:
            raise UnknownCollectorError(f"Unknown collector kind: {kind}")
        
        self._providers[kind] = provider
        return provider
```

### Feature Gate (scrapling/crawl4ai)

```python
# app/collectors/feature_gate.py (NEW)

from app.core import get_settings

FEATURE_FLAGS: dict[CollectorKind, str] = {
    CollectorKind.SCRAPLING: "SCRAPLING_ENABLED",
    CollectorKind.CRAWL4AI: "CRAWL4AI_ENABLED",
}

def is_feature_enabled(kind: CollectorKind) -> bool:
    """Check if a feature-gated collector is enabled via settings."""
    settings = get_settings()
    flag_name = FEATURE_FLAGS.get(kind)
    if flag_name is None:
        return False
    return getattr(settings, flag_name, False)
```

### Collector Selection Strategy (for Discovery)

Unlike the existing `CollectorSelector` (which is used by the existing pipeline), the new discovery path uses the `WhitelistExecutor`:

```
Discovery Flow:
  1. Start with DIRECT_HTTP for all URLs
  2. If DIRECT_HTTP returns empty/suspicious → retry with PLAYWRIGHT
  3. Feature-gated collectors (SCRAPLING, CRAWL4AI) only activate if:
     a. The RunPlan explicitly specifies them
     b. The feature flag is enabled in .env
  4. NEVER exec code from RunPlan — parse JSON only
```

## 7. Template / Scheduler Design

### CollectionTemplate Model

```python
# app/models/collection_template.py (NEW)

class CollectionTemplate(Base, TimestampMixin):
    __tablename__ = "collection_templates"
    
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    
    # Declarative RunPlan JSON (validated by RunPlanSchema)
    run_plan: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    # Source configurations (JSON array of {source_type, source_config})
    source_configs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    
    # Optional default schedule
    default_cron: Mapped[str | None] = mapped_column(String(64))
    default_timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128))
    
    # relationships
    schedules: Mapped[list["ScheduledCollection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan",
    )
```

### ScheduledCollection Model

```python
# app/models/scheduled_collection.py (NEW)

class ScheduleStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    ARCHIVED = "archived"

class ScheduledCollection(Base, TimestampMixin):
    __tablename__ = "scheduled_collections"
    
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("collection_templates.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Shanghai")
    status: Mapped[ScheduleStatus] = mapped_column(
        String(32), default=ScheduleStatus.ACTIVE, nullable=False,
    )
    
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_run_status: Mapped[str | None] = mapped_column(String(32))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(128))
    
    # relationships
    template: Mapped["CollectionTemplate"] = relationship(back_populates="schedules")
```

### Celery Beat Integration

```python
# app/tasks/scheduled.py (NEW)

@celery_app.task
def execute_scheduled_collection(schedule_id: str) -> dict:
    """
    Celery Beat periodic task.
    
    When the cron triggers, this task:
    1. Loads the ScheduledCollection + CollectionTemplate
    2. Validates the RunPlan
    3. Runs WhitelistExecutor.execute(plan)
    4. Creates CollectionTasks for discovered URLs
    5. Records execution in ScheduledCollection (last_run_at, run_count)
    6. Creates SourceDiscoverySession if discovery is needed
    """
    ...

# Celery Beat schedule is managed dynamically:
# When a ScheduledCollection is created/updated/deleted,
# the schedule service calls celery_app.conf.beat_schedule update.
```

### Template Service Flow

```python
# app/services/template_service.py (NEW)

class TemplateService:
    async def create_template(self, req: CreateTemplateRequest) -> CollectionTemplate:
        # 1. Validate RunPlan schema (RUNPLAN_DECLARATIVE_SPEC.md)
        validate_run_plan(req.run_plan)
        
        # 2. Validate source_configs
        validate_source_configs(req.source_configs)
        
        # 3. Create template
        template = CollectionTemplate(...)
        template = await self._repo.create(template)
        
        # 4. If schedule provided, auto-create ScheduledCollection
        if req.schedule:
            await self._schedule_service.create_from_template(template, req.schedule)
        
        return template
    
    async def execute_template(self, template_id: uuid.UUID) -> list[TaskResponse]:
        # 1. Load template
        template = await self._repo.get_by_id(template_id)
        
        # 2. Parse RunPlan
        plan = RunPlan.model_validate(template.run_plan)
        
        # 3. Execute via WhitelistExecutor
        executor = WhitelistExecutor()
        results = await executor.execute(plan)
        
        # 4. Create CollectionTasks for successful results
        tasks = []
        for result in results:
            if result.success:
                task = await self._task_service.create_task_from_collect_result(result, plan)
                tasks.append(task)
        
        return tasks
```

## 8. Usage Stats Design

### UsageDailyStat Model

```python
# app/models/usage_daily_stat.py (NEW)

class UsageDailyStat(Base):
    __tablename__ = "usage_daily_stats"
    
    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    # Collection metrics
    collections_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collections_success: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collections_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    collections_by_source: Mapped[dict] = mapped_column(JSONB, default=dict)  
    # e.g. {"direct_http": 42, "playwright": 10, "openclaw": 5, "scrapling": 0}
    
    # Duration metrics
    avg_fetch_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    avg_clean_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    avg_extract_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Data volume
    total_bytes_fetched: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes_cleaned: Mapped[int] = mapped_column(Integer, default=0)
    
    # Product metrics
    products_created: Mapped[int] = mapped_column(Integer, default=0)
    products_updated: Mapped[int] = mapped_column(Integer, default=0)
    versions_created: Mapped[int] = mapped_column(Integer, default=0)
    
    # Discovery metrics
    discovery_sessions: Mapped[int] = mapped_column(Integer, default=0)
    candidates_found: Mapped[int] = mapped_column(Integer, default=0)
    candidates_promoted: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    
    __table_args__ = (
        UniqueConstraint("stat_date", name="uq_usage_daily_stat_date"),
    )
```

### Usage Aggregation Strategy

The `usage_service.py` provides two aggregation paths:

1. **Real-time counters** (via `UsageCollectorMiddleware` or service hooks):
   - After each collection/extraction/discovery completes, increment counters
   - Updates the current day's `UsageDailyStat` row (upsert by `stat_date`)

2. **Daily cron aggregation** (for recovery/backfill):
   - Celery Beat task `aggregate_daily_usage` runs at 00:05 daily
   - Queries `collection_tasks`, `products`, `source_candidates` from the previous day
   - Computes all metrics and upserts into `usage_daily_stats`

```python
# app/services/usage_service.py (NEW)

class UsageService:
    async def record_collection(
        self, *, task_id, source_type: str, duration_ms: int,
        success: bool, bytes_fetched: int = 0, bytes_cleaned: int = 0,
    ) -> None:
        """Record a single collection event (real-time)."""
        stat = await self._get_or_create_today_stat()
        stat.collections_total += 1
        if success:
            stat.collections_success += 1
        else:
            stat.collections_failed += 1
        by_source = stat.collections_by_source or {}
        by_source[source_type] = by_source.get(source_type, 0) + 1
        stat.collections_by_source = by_source
        stat.total_bytes_fetched += bytes_fetched
        stat.total_bytes_cleaned += bytes_cleaned
        # Exponential moving average for durations
        n = stat.collections_total
        stat.avg_fetch_duration_ms = int(
            (stat.avg_fetch_duration_ms * (n - 1) + duration_ms) / n
        )
        await self._repo.upsert(stat)
    
    async def get_daily_stats(
        self, date_from: date, date_to: date,
        group_by: str = "day",
    ) -> list[UsageDailyStat]:
        """Get aggregated daily stats for a date range."""
        return await self._repo.get_range(date_from, date_to, group_by)
```

## 9. Skills Design

Skills are Hermes skills that expose CPIS capabilities to the agent. They live in `~/.hermes/profiles/default/skills/` and provide a natural language → API bridge.

### `cpis_discovery` Skill

**Name:** `cpis_discovery`  
**Trigger keywords:** discover, find products, competitive intel, research competitor

**Capabilities:**
- `discover_from_url(url, category)` → Creates a SourceDiscoverySession, returns candidates
- `discover_from_search(query, source_type)` → Searches web, creates discovery session
- `list_candidates(session_id, status)` → Lists candidates from a session
- `promote_candidate(candidate_id, category)` → Promotes candidate to CollectionTask
- `batch_promote(candidate_ids, category)` → Promotes multiple candidates

**Implementation:** Each capability is a function that calls the discovery API via httpx to `http://localhost:8000/api/v1/discovery/...`

### `cpis_collect` Skill

**Name:** `cpis_collect`  
**Trigger keywords:** collect, crawl, scrape, template, schedule

**Capabilities:**
- `create_template(name, run_plan_json, description)` → Creates a CollectionTemplate
- `run_template(template_id)` → Executes template immediately
- `create_schedule(template_id, cron_expression)` → Creates a ScheduledCollection
- `list_templates()` → Lists all templates
- `list_schedules()` → Lists all schedules

### `cpis_query` Skill

**Name:** `cpis_query`  
**Trigger keywords:** query, search products, show tasks, usage, stats

**Capabilities:**
- `list_tasks(status, page)` → Lists collection tasks
- `get_task_status(task_id)` → Gets detailed task status
- `search_products(query)` → Searches product database
- `get_usage_stats(date_from, date_to)` → Gets usage statistics
- `get_system_summary()` → Overall system health summary

## 10. MCP Tool Design

MCP (Model Context Protocol) tools are defined as Hermes MCP tool manifests for direct tool-calling by agent models.

### `cpis_discover` MCP Tool

```json
{
  "name": "cpis_discover",
  "description": "Discover competitor products from a URL or web search. Creates a discovery session and returns candidates that can be promoted to collection tasks.",
  "input_schema": {
    "type": "object",
    "properties": {
      "source_type": {
        "type": "string",
        "enum": ["url", "search"],
        "description": "Type of discovery source"
      },
      "source_value": {
        "type": "string",
        "description": "URL or search query"
      },
      "category_hint": {
        "type": "string",
        "description": "Optional product category hint"
      },
      "max_candidates": {
        "type": "integer",
        "default": 10,
        "description": "Maximum candidates to return"
      }
    },
    "required": ["source_type", "source_value"]
  }
}
```

### `cpis_promote` MCP Tool

```json
{
  "name": "cpis_promote",
  "description": "Promote discovered candidates to full collection tasks. Triggers the full pipeline: fetch → clean → extract → version → review.",
  "input_schema": {
    "type": "object",
    "properties": {
      "candidate_ids": {
        "type": "array",
        "items": {"type": "string", "format": "uuid"},
        "description": "List of candidate IDs to promote"
      },
      "category_hint": {
        "type": "string",
        "description": "Optional category to apply to all promoted tasks"
      },
      "auto_sync_feishu": {
        "type": "boolean",
        "default": false,
        "description": "Auto-sync to Feishu after completion"
      }
    },
    "required": ["candidate_ids"]
  }
}
```

### `cpis_run_template` MCP Tool

```json
{
  "name": "cpis_run_template",
  "description": "Execute a collection template immediately. Creates collection tasks for all sources defined in the template's RunPlan.",
  "input_schema": {
    "type": "object",
    "properties": {
      "template_id": {
        "type": "string",
        "format": "uuid",
        "description": "ID of the collection template to execute"
      }
    },
    "required": ["template_id"]
  }
}
```

### `cpis_create_schedule` MCP Tool

```json
{
  "name": "cpis_create_schedule",
  "description": "Create a scheduled collection that runs a template on a cron schedule.",
  "input_schema": {
    "type": "object",
    "properties": {
      "template_id": {
        "type": "string",
        "format": "uuid",
        "description": "ID of the template to schedule"
      },
      "name": {
        "type": "string",
        "description": "Human-readable name for this schedule"
      },
      "cron_expression": {
        "type": "string",
        "pattern": "^(@(annually|yearly|monthly|weekly|daily|hourly))|((\\*|[0-9]|,[0-9]|-[0-9]|/[0-9])+\\s+){4}(\\*|[0-9]|,[0-9]|-[0-9]|/[0-9])+$",
        "description": "Cron expression (e.g., '0 9 * * 1' for every Monday at 9am)"
      },
      "timezone": {
        "type": "string",
        "default": "Asia/Shanghai",
        "description": "Timezone for the cron schedule"
      }
    },
    "required": ["template_id", "name", "cron_expression"]
  }
}
```

### `cpis_query_usage` MCP Tool

```json
{
  "name": "cpis_query_usage",
  "description": "Query system usage statistics and health metrics.",
  "input_schema": {
    "type": "object",
    "properties": {
      "metric": {
        "type": "string",
        "enum": ["daily", "summary", "by_domain", "health"],
        "description": "Metric to query"
      },
      "date_from": {
        "type": "string",
        "format": "date",
        "description": "Start date (YYYY-MM-DD)"
      },
      "date_to": {
        "type": "string",
        "format": "date",
        "description": "End date (YYYY-MM-DD)"
      }
    },
    "required": ["metric"]
  }
}
```

---

## Appendix A: Settings Changes

```python
# app/core/__init__.py — Extend Settings class

class Settings(BaseSettings):
    # ... existing settings ...
    
    # ── Feature Flags ──────────────────────────────────────────
    SCRAPLING_ENABLED: bool = False
    CRAWL4AI_ENABLED: bool = False
    
    # ── Discovery ──────────────────────────────────────────────
    DISCOVERY_MAX_CANDIDATES: int = 50
    DISCOVERY_DEFAULT_COLLECTOR: str = "direct_http"
    DISCOVERY_USER_AGENT: str = "CPIS-Discovery/1.0"
    
    # ── Search Provider ────────────────────────────────────────
    BING_SEARCH_API_KEY: str = ""
    SERPAPI_API_KEY: str = ""
    SEARCH_PROVIDER: str = "duckduckgo"  # duckduckgo | bing | serpapi
    
    # ── Scheduler ──────────────────────────────────────────────
    SCHEDULER_MAX_PER_SCHEDULE: int = 50  # max tasks per scheduled run
    SCHEDULER_DEFAULT_TIMEZONE: str = "Asia/Shanghai"
    
    # ── Usage ──────────────────────────────────────────────────
    USAGE_RETENTION_DAYS: int = 365
    
    # ── OpenClaw (unchanged) ──────────────────────────────────
    # ... existing OPENCLAW_* settings ...
```

## Appendix B: New Enum Values

```python
# app/models/enums.py — Additions

class DiscoveryStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class CandidateStatus(str, enum.Enum):
    NEW = "new"
    PROMOTED = "promoted"
    DISMISSED = "dismissed"
    DUPLICATE = "duplicate"

class ScheduleStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    ARCHIVED = "archived"
```

## Appendix C: Migration Strategy

```
Step 1: Add new models (003_phase_i_reset.py)
  - Create tables: source_discovery_sessions, source_candidates,
    collection_templates, scheduled_collections, usage_daily_stats

Step 2: Deploy backend code changes
  - New routers, services, repositories, schema files
  - WhitelistExecutor added to collectors/
  - main.py registers new routers

Step 3: Deploy frontend changes
  - New pages: /discovery, /collection-templates, /usage
  - New menu items in Layout sidebar
  - New API client modules

Step 4: Activate Celery Beat
  - Add celery beat schedule for scheduled collections
  - Add daily usage aggregation task

Step 5: Install skills and MCP tools
  - Copy skill files to ~/.hermes/profiles/default/skills/
  - Register MCP tool manifests

ALL STEPS are backward-compatible — existing models, tables,
and API endpoints remain untouched.
```
