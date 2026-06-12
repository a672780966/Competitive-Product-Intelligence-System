// CPIS V1 — API client

const BASE = "/api/v1";

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
    request<import("../types").PaginatedTaskResponse>(`/collection-tasks?${params || ""}`),

  get: (id: string) =>
    request<import("../types").TaskDetailResponse>(`/collection-tasks/${id}`),

  create: (body: { source_url: string; category_hint?: string }) =>
    request<import("../types").TaskResponse>("/collection-tasks", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  batchCreate: (tasks: { source_url: string }[]) =>
    request<{ created: number; tasks: import("../types").TaskResponse[] }>(
      "/collection-tasks/batch",
      { method: "POST", body: JSON.stringify({ tasks }) },
    ),

  retry: (id: string) =>
    request<import("../types").TaskDetailResponse>(`/collection-tasks/${id}/retry`, { method: "POST" }),

  cancel: (id: string) =>
    request<import("../types").TaskDetailResponse>(`/collection-tasks/${id}/cancel`, { method: "POST" }),

  events: (id: string) =>
    request<import("../types").TaskEventResponse[]>(`/collection-tasks/${id}/events`),
};

// ── Reviews ─────────────────────────────────────────────────────
export const reviewsApi = {
  list: (params?: string) =>
    request<import("../types").PaginatedReviewResponse>(`/reviews?${params || ""}`),

  get: (versionId: string) =>
    request<import("../types").ReviewDetailResponse>(`/reviews/${versionId}`),

  saveDraft: (versionId: string, body: { corrections?: Record<string, string>; comments?: string }) =>
    request<import("../types").ReviewDetailResponse>(`/reviews/${versionId}/draft`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  approve: (versionId: string, body?: { corrections?: Record<string, string>; comments?: string }) =>
    request<import("../types").ReviewDetailResponse>(`/reviews/${versionId}/approve`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),

  reject: (versionId: string, body?: { comments?: string }) =>
    request<import("../types").ReviewDetailResponse>(`/reviews/${versionId}/reject`, {
      method: "POST",
      body: JSON.stringify(body || {}),
    }),
};

// ── Reports ─────────────────────────────────────────────────────
export const reportsApi = {
  product: async (productId: string): Promise<string> => {
    const res = await fetch(`${BASE}/reports/product/${productId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },

  compare: async (productIds: string[]): Promise<string> => {
    const res = await fetch(`${BASE}/reports/compare`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ product_ids: productIds }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.text();
  },
};
