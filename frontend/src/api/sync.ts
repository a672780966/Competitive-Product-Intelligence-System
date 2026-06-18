// CPIS V1 — Sync records API client

import { request } from "./client";

export const syncApi = {
  list: (params?: string) =>
    request<import("../types").SyncRecordListResponse>(`/sync-records?${params || ""}`),

  retry: (id: string) =>
    request<import("../types").SyncRecordItem>(`/sync-records/${id}/retry`, { method: "POST" }),
};
