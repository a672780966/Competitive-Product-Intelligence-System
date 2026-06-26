// CPIS V1 — API client

import type {
  PaginatedProductResponse,
  PaginatedReviewResponse,
  PaginatedSyncResponse,
  PaginatedTaskResponse,
  ProductDetailResponse,
  ReviewDetailResponse,
  SyncRecord,
  TaskDetailResponse,
  TaskEventResponse,
  TaskResponse,
  SessionDetailResponse,
  PaginatedDiscoverySessionResponse,
  CreateTemplateFromSelectionResponse,
  PaginatedTemplateResponse,
  CollectionTemplate,
  TemplateRunResponse,
  PaginatedScheduledCollectionResponse,
  ScheduledCollection,
  ScheduledCollectionDetailResponse,
  UsageDailyStatListResponse,
  UsageSummaryResponse,
} from "../types";

const BASE = "";

// Re-usable request function
export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${body.slice(0, 200)}`);
  }
  // Handle non-JSON responses (e.g. markdown reports)
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("text/markdown")) {
    return (await res.text()) as unknown as T;
  }
  return res.json();
}

// ── Tasks ──────────────────────────────────────────────────────
export const tasksApi = {
  list: (params?: string) =>
    request<PaginatedTaskResponse>(`/api/v1/collection-tasks?${params || ""}`),

  get: (id: string) =>
    request<TaskDetailResponse>(`/api/v1/collection-tasks/${id}`),

  create: (body: { source_url: string; category_hint?: string }) =>
    request<TaskResponse>("/api/v1/collection-tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  batchCreate: (tasks: { source_url: string }[]) =>
    request<{ created: number; tasks: TaskResponse[] }>(
      "/api/v1/collection-tasks/batch",
      { method: "POST", body: JSON.stringify({ tasks }) },
    ),

  retry: (id: string) =>
    request<TaskDetailResponse>(`/api/v1/collection-tasks/${id}/retry`, { method: "POST" }),

  cancel: (id: string) =>
    request<TaskDetailResponse>(`/api/v1/collection-tasks/${id}/cancel`, { method: "POST" }),

  events: (id: string) =>
    request<TaskEventResponse[]>(`/api/v1/collection-tasks/${id}/events`),
};

// ── Reviews ─────────────────────────────────────────────────────
export const reviewsApi = {
  list: (params?: string) =>
    request<PaginatedReviewResponse>(`/api/v1/reviews?${params || ""}`),

  get: (versionId: string) =>
    request<ReviewDetailResponse>(`/api/v1/reviews/${versionId}`),

  update: (versionId: string, body: { corrections?: Record<string, string>; comments?: string }) =>
    request<ReviewDetailResponse>(`/api/v1/reviews/${versionId}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  saveDraft: (versionId: string, body: { corrections?: Record<string, string>; comments?: string }) =>
    request<ReviewDetailResponse>(`/api/v1/reviews/${versionId}/draft`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  approve: (versionId: string, body?: { corrections?: Record<string, string>; comments?: string }) =>
    request<ReviewDetailResponse>(`/api/v1/reviews/${versionId}/approve`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),

  reject: (versionId: string, body?: { comments?: string }) =>
    request<ReviewDetailResponse>(`/api/v1/reviews/${versionId}/reject`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
};

// ── Products ────────────────────────────────────────────────────
export const productsApi = {
  list: (params?: string) =>
    request<PaginatedProductResponse>(`/api/v1/products?${params || ""}`),

  get: (id: string) =>
    request<ProductDetailResponse>(`/api/v1/products/${id}`),
};

// ── Sync Records ────────────────────────────────────────────────
export const syncApi = {
  list: (params?: string) =>
    request<PaginatedSyncResponse>(`/api/v1/sync-records?${params || ""}`),

  get: (id: string) =>
    request<SyncRecord>(`/api/v1/sync-records/${id}`),
};

// ── Reports ─────────────────────────────────────────────────────
export const reportsApi = {
  product: async (productId: string): Promise<string> => {
    const res = await fetch(`${BASE}/api/v1/reports/product/${productId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },

  compare: async (productIds: string[]): Promise<string> => {
    const res = await fetch(`${BASE}/api/v1/reports/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_ids: productIds }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },
};

// ── Discovery ────────────────────────────────────────────────────
export const discoveryApi = {
  createSession: (body: { query: string; target_brand?: string; topic?: string }) =>
    request<SessionDetailResponse>("/api/v1/discovery/sessions", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listSessions: (params?: string) =>
    request<PaginatedDiscoverySessionResponse>(`/api/v1/discovery/sessions?${params || ""}`),

  getSession: (id: string) =>
    request<SessionDetailResponse>(`/api/v1/discovery/sessions/${id}`),

  getCandidates: (sessionId: string, params?: string) =>
    request<{ items: import("../types").SourceCandidate[]; total: number; page: number; page_size: number; total_pages: number }>(
      `/api/v1/discovery/sessions/${sessionId}/candidates?${params || ""}`,
    ),

  updateCandidate: (candidateId: string, selected: boolean) =>
    request<import("../types").SourceCandidate>(
      `/api/v1/discovery/candidates/${candidateId}`,
      { method: "PATCH", body: JSON.stringify({ selected }) },
    ),

  batchSelect: (sessionId: string, candidateIds: string[], selected: boolean) =>
    request<{ updated: number; selected: boolean }>(
      `/api/v1/discovery/sessions/${sessionId}/select`,
      { method: "POST", body: JSON.stringify({ candidate_ids: candidateIds, selected }) },
    ),

  createTemplate: (sessionId: string, body: { name: string; description?: string; feishu_sync_enabled?: boolean }) =>
    request<CreateTemplateFromSelectionResponse>(
      `/api/v1/discovery/sessions/${sessionId}/create-template`,
      { method: "POST", body: JSON.stringify(body) },
    ),
};

// ── Collection Templates ─────────────────────────────────────────
export const templatesApi = {
  list: (params?: string) =>
    request<PaginatedTemplateResponse>(`/api/v1/collection-templates?${params || ""}`),

  get: (id: string) =>
    request<CollectionTemplate>(`/api/v1/collection-templates/${id}`),

  update: (id: string, body: { name?: string; description?: string; status?: string }) =>
    request<CollectionTemplate>(`/api/v1/collection-templates/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  run: (id: string) =>
    request<TemplateRunResponse>(`/api/v1/collection-templates/${id}/run`, { method: "POST" }),
};

// ── Scheduled Collections ────────────────────────────────────────
export const schedulesApi = {
  list: (params?: string) =>
    request<PaginatedScheduledCollectionResponse>(`/api/v1/scheduled-collections?${params || ""}`),

  get: (id: string) =>
    request<ScheduledCollectionDetailResponse>(`/api/v1/scheduled-collections/${id}`),

  create: (body: { template_id: string; schedule_type?: string; cron_expr?: string; interval_minutes?: number; enabled?: boolean }) =>
    request<ScheduledCollection>(`/api/v1/scheduled-collections`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  update: (id: string, body: { schedule_type?: string; cron_expr?: string; interval_minutes?: number; enabled?: boolean }) =>
    request<ScheduledCollection>(`/api/v1/scheduled-collections/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
};

// ── Usage ────────────────────────────────────────────────────────
export const usageApi = {
  daily: (params?: string) =>
    request<UsageDailyStatListResponse>(`/api/v1/usage/daily?${params || ""}`),

  summary: (params?: string) =>
    request<UsageSummaryResponse>(`/api/v1/usage/summary?${params || ""}`),
};
