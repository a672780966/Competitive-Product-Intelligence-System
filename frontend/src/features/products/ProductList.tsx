// CPIS V1 — 产品信息库页面

import { useState } from "react";
import { Table, Tag, Typography, Input, Select, Space } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { productsApi } from "../../api/products";
import type { ProductItem } from "../../types";

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: "default",
  auto_approved: "success",
  needs_review: "orange",
  in_review: "processing",
  approved: "success",
  rejected: "error",
  reopened: "warning",
};

const statusLabels: Record<string, string> = {
  pending: "待处理",
  auto_approved: "自动通过",
  needs_review: "待复核",
  in_review: "复核中",
  approved: "已通过",
  rejected: "已驳回",
  reopened: "已 reopen",
};

const categoryLabels: Record<string, string> = {
  smartphone: "手机",
  laptop: "笔记本",
  tablet: "平板",
  wearable: "穿戴",
  audio: "音频",
  accessory: "配件",
  smart_home: "智能家居",
  other: "其他",
};

export default function ProductListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState("");
  const [brandFilter, setBrandFilter] = useState<string | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ["products", page, keyword, brandFilter, categoryFilter, statusFilter],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (keyword) params.set("keyword", keyword);
      if (brandFilter) params.set("brand", brandFilter);
      if (categoryFilter) params.set("category", categoryFilter);
      if (statusFilter) params.set("review_status", statusFilter);
      return productsApi.list(params.toString());
    },
  });

  const columns = [
    {
      title: "品牌",
      dataIndex: "brand",
      key: "brand",
      width: 120,
      render: (v: string | null) => v || "—",
    },
    {
      title: "产品名称",
      dataIndex: "name",
      key: "name",
      width: 200,
      render: (v: string | null, r: ProductItem) => (
        <a onClick={() => navigate(`/products/${r.id}`)}>
          {v || r.unique_key}
        </a>
      ),
    },
    {
      title: "型号",
      dataIndex: "model",
      key: "model",
      width: 120,
      render: (v: string | null) => v || "—",
    },
    {
      title: "品类",
      dataIndex: "category",
      key: "category",
      width: 100,
      render: (v: string | null) =>
        v ? (categoryLabels[v] || v) : "—",
    },
    {
      title: "置信度",
      key: "confidence",
      width: 90,
      render: (_: unknown, r: ProductItem) =>
        r.overall_confidence !== null
          ? `${(r.overall_confidence * 100).toFixed(0)}%`
          : "—",
    },
    {
      title: "审核状态",
      dataIndex: "review_status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: "飞书记录",
      dataIndex: "feishu_record_id",
      key: "feishu",
      width: 150,
      ellipsis: true,
      render: (v: string | null) => v || "—",
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
          flexWrap: "wrap",
          gap: 8,
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          产品信息库
        </Title>
        <Space wrap>
          <Input.Search
            placeholder="搜索品牌/名称/型号"
            allowClear
            onSearch={setKeyword}
            style={{ width: 220 }}
          />
          <Input
            placeholder="品牌筛选"
            allowClear
            style={{ width: 130 }}
            value={brandFilter}
            onChange={(e) => setBrandFilter(e.target.value || undefined)}
          />
          <Select
            placeholder="品类筛选"
            allowClear
            style={{ width: 120 }}
            onChange={(v) => setCategoryFilter(v || undefined)}
            options={Object.entries(categoryLabels).map(([k, v]) => ({
              value: k,
              label: v,
            }))}
          />
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
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          total: data?.total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        size="middle"
        locale={{ emptyText: "暂无产品数据" }}
      />
    </div>
  );
}
