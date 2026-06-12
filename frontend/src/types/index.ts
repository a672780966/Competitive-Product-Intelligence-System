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

export interface TaskDetailResponse extends TaskResponse {
  events: TaskEventResponse[];
}

export interface PaginatedTaskResponse {
  items: TaskResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ── Product ─────────────────────────────────────────────────────
export interface ProductSummary {
  id: string;
  unique_key: string;
  brand: string | null;
  name: string | null;
  model: string | null;
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
}
