// CPIS V1 — Product API client

import { request } from "./client";

export const productsApi = {
  list: (params?: string) =>
    request<import("../types").ProductListResponse>(`/products?${params || ""}`),

  get: (id: string) =>
    request<import("../types").ProductDetail>(`/products/${id}`),

  versions: (id: string) =>
    request<import("../types").ProductVersionItem[]>(`/products/${id}/versions`),

  recollect: (id: string) =>
    request<import("../types").TaskResponse>(`/products/${id}/recollect`, { method: "POST" }),

  syncFeishu: (id: string) =>
    request<import("../types").SyncRecordItem>(`/products/${id}/sync-feishu`, { method: "POST" }),

  syncRecords: (id: string) =>
    request<import("../types").SyncRecordListResponse>(`/products/${id}/sync-records`),
};
