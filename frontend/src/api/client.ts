// CPIS V1 — API client

const BASE = "/api/v1";

/** Build headers with optional auth token injection. */
function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = localStorage.getItem("cpis_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return { ...headers, ...extra };
}

// Re-usable request function
export async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...options,
    headers: buildHeaders(options?.headers as Record<string, string> | undefined),
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

/** Generic API helper (auto-injects auth token). */
export const api = {
  get: <T>(path: string): Promise<T> => request<T>(path),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),
  put: <T>(path: string, body?: unknown): Promise<T> =>
    request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),
};

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
