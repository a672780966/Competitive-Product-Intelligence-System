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
