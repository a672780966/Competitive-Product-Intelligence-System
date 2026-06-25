// CPIS V1 — 飞书同步记录页面

import { useState } from "react";
import { Select, Space, Table, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { syncApi } from "../../api/client";
import type { SyncRecord } from "../../types";

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: "default", syncing: "processing", success: "success", failed: "error",
};

const statusLabels: Record<string, string> = {
  pending: "待同步", syncing: "同步中", success: "同步成功", failed: "同步失败",
};

export default function SyncRecordsPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["sync-records", page, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (statusFilter) params.set("status", statusFilter);
      return syncApi.list(params.toString());
    },
  });

  const columns = [
    { title: "产品ID", dataIndex: "product_id", key: "product_id", width: 260, ellipsis: true },
    { title: "状态", dataIndex: "sync_status", key: "status", width: 120,
      render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: "飞书记录ID", dataIndex: "feishu_record_id", key: "feishu_id", width: 180, ellipsis: true,
      render: (v: string | null) => v || "—" },
    { title: "错误信息", dataIndex: "error_message", key: "error", ellipsis: true,
      render: (v: string | null) => v || "—" },
    { title: "同步时间", dataIndex: "synced_at", key: "synced_at", width: 180,
      render: (v: string | null) => v ? new Date(v).toLocaleString("zh-CN") : "—" },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>飞书同步记录</Title>
        <Space>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 140 }}
            onChange={v => setStatusFilter(v || undefined)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
        </Space>
      </div>
      <Table<SyncRecord>
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        columns={columns}
        locale={{ emptyText: "暂无同步记录" }}
        pagination={{ current: page, total: data?.total, pageSize: 20, onChange: setPage }}
        size="middle"
      />
    </div>
  );
}
