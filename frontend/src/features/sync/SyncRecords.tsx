// CPIS V1 — 飞书同步记录页面

import { useState } from "react";
import { Table, Tag, Typography, Button, Select, Space, message } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { syncApi } from "../../api/sync";
import type { SyncRecordItem } from "../../types";

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: "default",
  syncing: "processing",
  success: "success",
  failed: "error",
};

const statusLabels: Record<string, string> = {
  pending: "待同步",
  syncing: "同步中",
  success: "同步成功",
  failed: "同步失败",
};

export default function SyncRecordsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["sync-records", page, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (statusFilter) params.set("sync_status", statusFilter);
      return syncApi.list(params.toString());
    },
  });

  const retryMutation = useMutation({
    mutationFn: (syncId: string) => syncApi.retry(syncId),
    onSuccess: () => {
      message.success("已重试同步");
      queryClient.invalidateQueries({ queryKey: ["sync-records"] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const columns = [
    {
      title: "产品",
      key: "product",
      width: 200,
      render: (_: unknown, r: SyncRecordItem) => (
        <span>
          {r.product_brand || "—"}
          {r.product_name ? ` / ${r.product_name}` : ""}
        </span>
      ),
    },
    {
      title: "产品ID",
      dataIndex: "product_id",
      key: "product_id",
      width: 200,
      ellipsis: true,
    },
    {
      title: "状态",
      dataIndex: "sync_status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: "同步类型",
      dataIndex: "sync_type",
      key: "type",
      width: 100,
    },
    {
      title: "飞书记录ID",
      dataIndex: "feishu_record_id",
      key: "feishu_id",
      width: 150,
      ellipsis: true,
      render: (v: string | null) => v || "—",
    },
    {
      title: "错误信息",
      dataIndex: "error_message",
      key: "error",
      width: 200,
      ellipsis: true,
      render: (v: string | null) => v || "—",
    },
    {
      title: "重试次数",
      dataIndex: "retry_count",
      key: "retry",
      width: 80,
    },
    {
      title: "同步时间",
      dataIndex: "synced_at",
      key: "synced_at",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "—",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "actions",
      width: 100,
      render: (_: unknown, r: SyncRecordItem) =>
        r.sync_status === "failed" ? (
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => retryMutation.mutate(r.id)}
            loading={retryMutation.isPending}
          >
            重试
          </Button>
        ) : null,
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          飞书同步记录
        </Title>
        <Space>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 130 }}
            onChange={(v) => setStatusFilter(v || undefined)}
            options={Object.entries(statusLabels).map(([k, v]) => ({
              value: k,
              label: v,
            }))}
          />
        </Space>
      </div>
      <Table
        dataSource={data?.items}
        rowKey="id"
        loading={isLoading}
        columns={columns}
        pagination={{
          current: page,
          total: data?.total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        size="middle"
        locale={{ emptyText: "暂无同步记录" }}
        scroll={{ x: 1400 }}
      />
    </div>
  );
}
