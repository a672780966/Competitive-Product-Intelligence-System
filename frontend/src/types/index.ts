// CPIS V1 — TypeScript type definitions

// ── Common ─────────────────────────────────────────────────────
export interface PageParams {
  page?: number;
  page_size?: number;
}

// ── Task ───────────────────────────────────────────────────────
export interface TaskResponse {
  id: string;
  source_url: string;
  normalized_url: string | null;
  domain: string | null;
  status: string;
  priority: number;
  category_hint: string | null;
  language_hint: string | null;
  auto_sync_feishu: boolean;
  retry_count: number;
  max_retries: number;
  error_code: string | null;
  error_message: string | null;
  created_by: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskEventResponse {
  id: string;
  stage: string;
  status: string;
  message: string | null;
  duration_ms: number | null;
  error_code: string | null;
  created_at: string;
}

export interface CollectorExecutionReportResponse {
  id: string;
  task_id: string;
  snapshot_id: string | null;
  collector_runtime: string;
  url: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  content_size: number | null;
  retry_count: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskDetailResponse extends TaskResponse {
  events: TaskEventResponse[];
  execution_reports: CollectorExecutionReportResponse[];
  snapshot: SnapshotResponse | null;
  pipeline_status: PipelineStatusResponse | null;
}

export interface PaginatedTaskResponse {
  items: TaskResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SnapshotResponse {
  id: string;
  task_id: string;
  final_url: string | null;
  html_hash: string | null;
  content_hash: string | null;
  cleaned_text: string | null;
  cleaned_markdown: string | null;
  created_at: string;
}

export interface PipelineStageStatus {
  stage: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
}

export interface PipelineStatusResponse {
  stages: PipelineStageStatus[];
  current_stage: string | null;
  overall_status: string;
  retry_count: number;
  max_retries: number;
}

// ── Product ─────────────────────────────────────────────────────
export interface ProductSummary {
  id: string;
  unique_key: string;
  brand: string | null;
  name: string | null;
  model: string | null;
  category: string | null;
  review_status: string;
  current_version_id: string | null;
  feishu_record_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface VersionSummary {
  id: string;
  version_no: number;
  overall_confidence: number | null;
  ai_model: string | null;
  prompt_version: string | null;
  created_at: string;
}

export interface ProductDetailResponse extends ProductSummary {
  versions: VersionSummary[];
}

export interface PaginatedProductResponse {
  items: ProductSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Review ──────────────────────────────────────────────────────
export interface ReviewItem {
  product_version_id: string;
  version_no: number;
  product: ProductSummary;
  overall_confidence: number;
  review_status: string;
  ai_model: string | null;
  created_at: string;
}

export interface PaginatedReviewResponse {
  items: ReviewItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EvidenceItem {
  field_name: string;
  value: string | null;
  confidence: number | null;
  evidence_text: string | null;
}

export interface ReviewDetailResponse {
  product_version_id: string;
  version_no: number;
  product: ProductSummary;
  structured_data: Record<string, unknown>;
  analysis_data: Record<string, unknown>;
  evidences: EvidenceItem[];
  overall_confidence: number;
  ai_model: string | null;
  review_status: string;
  current_review: Record<string, unknown> | null;
  cleaned_text: string | null;
  source_url: string | null;
  source_text: string | null;
}

// ── Sync ────────────────────────────────────────────────────────
export interface SyncRecord {
  id: string;
  product_id: string;
  sync_status: string;
  sync_type: string;
  feishu_record_id: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  synced_at: string | null;
}

export interface PaginatedSyncResponse {
  items: SyncRecord[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Discovery ────────────────────────────────────────────────────
export interface DiscoverySession {
  id: string;
  query: string;
  target_brand: string | null;
  topic: string | null;
  status: string;
  model_provider: string | null;
  search_provider: string | null;
  error_message: string | null;
  candidate_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface SourceCandidate {
  id: string;
  discovery_session_id: string;
  title: string;
  url: string;
  domain: string;
  snippet: string | null;
  thumbnail_url: string | null;
  favicon_url: string | null;
  source_type: string;
  recommended_collector: string;
  risk_level: string;
  reason: string | null;
  selected: boolean;
  raw_metadata: Record<string, unknown> | null;
  sort_order: number;
  created_at: string;
}

export interface SessionDetailResponse {
  session: DiscoverySession;
  candidates: SourceCandidate[];
}

export interface CreateTemplateFromSelectionResponse {
  template_id: string;
  name: string;
  candidate_count: number;
  message: string;
}

export interface PaginatedDiscoverySessionResponse {
  items: DiscoverySession[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Collection Templates ─────────────────────────────────────────
export interface CollectionTemplate {
  id: string;
  name: string;
  description: string | null;
  target_brand: string | null;
  topic: string | null;
  source_plan: Record<string, unknown>;
  run_plan: Record<string, unknown>;
  feishu_sync_enabled: boolean;
  status: string;
  last_run_at: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface PaginatedTemplateResponse {
  items: CollectionTemplate[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface TemplateRunResponse {
  template_id: string;
  tasks_created: number;
  message: string;
}

// ── Scheduled Collections ────────────────────────────────────────
export interface ScheduledCollection {
  id: string;
  template_id: string;
  schedule_type: string;
  cron_expr: string | null;
  interval_minutes: number | null;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_status: string | null;
  failure_count: number;
  max_failures_before_pause: number;
  created_at: string;
  updated_at: string | null;
}

export interface ScheduledCollectionDetailResponse {
  schedule: ScheduledCollection;
  template: CollectionTemplate | null;
}

export interface PaginatedScheduledCollectionResponse {
  items: ScheduledCollection[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Usage ────────────────────────────────────────────────────────
export interface UsageDailyStat {
  id: string;
  stat_date: string;
  task_count: number;
  token_count: number;
  search_count: number;
  collected_page_count: number;
  success_count: number;
  failure_count: number;
  estimated_cost: number;
  raw_metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface UsageDailyStatListResponse {
  items: UsageDailyStat[];
  total: number;
  date_from: string | null;
  date_to: string | null;
}

export interface UsageSummaryResponse {
  total_task_count: number;
  total_token_count: number;
  total_search_count: number;
  total_collected_page_count: number;
  total_success_count: number;
  total_failure_count: number;
  total_estimated_cost: number;
  total_days: number;
}
