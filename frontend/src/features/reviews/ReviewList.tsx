// CPIS V1 — 待复核列表页面

import React, { useState } from "react";
import { Table, Tag, Button, Typography, Select } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { reviewsApi } from "../../api/client";

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: "default", auto_approved: "success", needs_review: "orange",
  in_review: "processing", approved: "success", rejected: "error",
};
const statusLabels: Record<string, string> = {
  pending: "待处理", auto_approved: "自动通过", needs_review: "待复核",
  in_review: "复核中", approved: "已通过", rejected: "已驳回",
};

export default function ReviewListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["reviews", page, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (statusFilter) params.set("status", statusFilter);
      return reviewsApi.list(params.toString());
    },
  });

  const columns = [
    { title: "品牌", key: "brand", width: 100,
      render: (_: unknown, r: { product: { brand: string | null } }) => r.product?.brand || "—" },
    { title: "产品名称", key: "name", width: 200,
      render: (_: unknown, r: { product: { name: string | null } }) => r.product?.name || "—" },
    { title: "版本", dataIndex: "version_no", key: "version", width: 60 },
    { title: "置信度", dataIndex: "overall_confidence", key: "confidence", width: 100,
      render: (v: number) => v !== null ? `${(v * 100).toFixed(0)}%` : "—" },
    { title: "状态", dataIndex: "review_status", key: "status", width: 100,
      render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: "AI 模型", dataIndex: "ai_model", key: "model", width: 120 },
    { title: "时间", dataIndex: "created_at", key: "created_at", width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN") },
    { title: "操作", key: "actions", width: 100,
      render: (_: unknown, r: { product_version_id: string }) => (
        <Button size="small" type="primary" onClick={() => navigate(`/reviews/${r.product_version_id}`)}>复核</Button>
      ) },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>待复核</Title>
        <Select
          placeholder="状态筛选" allowClear style={{ width: 150 }}
          onChange={v => setStatusFilter(v || undefined)}
          options={[
            { value: "needs_review", label: "待复核" },
            { value: "auto_approved", label: "自动通过" },
            { value: "approved", label: "已通过" },
            { value: "rejected", label: "已驳回" },
          ]}
        />
      </div>
      <Table dataSource={data?.items} columns={columns} rowKey="product_version_id" loading={isLoading}
        pagination={{ current: page, total: data?.total, pageSize: 20, onChange: setPage }} size="middle" />
    </div>
  );
}
