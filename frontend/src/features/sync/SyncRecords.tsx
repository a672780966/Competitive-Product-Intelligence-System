// CPIS V1 — 飞书同步记录页面

import React, { useState } from "react";
import { Table, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { tasksApi } from "../../api/client";

const { Title } = Typography;

interface SyncRecord {
  id: string;
  product_id: string;
  sync_status: string;
  feishu_record_id: string | null;
  error_message: string | null;
  created_at: string;
  synced_at: string | null;
}

const statusColors: Record<string, string> = {
  pending: "default", syncing: "processing", success: "success", failed: "error",
};
const statusLabels: Record<string, string> = {
  pending: "待同步", syncing: "同步中", success: "同步成功", failed: "同步失败",
};

export default function SyncRecordsPage() {
  const [page, setPage] = useState(1);

  // Use tasks list as a proxy until a dedicated /sync endpoint exists
  const { data, isLoading } = useQuery({
    queryKey: ["sync-records", page],
    queryFn: () => tasksApi.list(`page=${page}&page_size=20`),
  });

  // For V1, we show a placeholder — sync records will be accessible
  // via product detail once we build the full product list
  const emptyData = { items: [], total: 0 };

  return (
    <div>
      <Title level={4}>飞书同步记录</Title>
      <p style={{ color: "#999", marginBottom: 16 }}>
        同步记录将在产品通过复核后自动生成。每个产品的同步状态可在产品详情页查看。
      </p>
      <Table
        dataSource={[]} rowKey="id" loading={false}
        columns={[
          { title: "产品ID", dataIndex: "product_id", key: "product_id" },
          { title: "状态", dataIndex: "sync_status", key: "status", render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
          { title: "飞书记录ID", dataIndex: "feishu_record_id", key: "feishu_id", ellipsis: true },
          { title: "错误信息", dataIndex: "error_message", key: "error", ellipsis: true },
          { title: "同步时间", dataIndex: "synced_at", key: "synced_at", render: (v: string | null) => v ? new Date(v).toLocaleString("zh-CN") : "—" },
        ]}
        locale={{ emptyText: "暂无同步记录" }}
        pagination={{ current: page, total: 0, onChange: setPage }}
        size="middle"
      />
    </div>
  );
}
