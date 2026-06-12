// CPIS V1 — 产品信息库页面

import React, { useState } from "react";
import { Table, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

const { Title } = Typography;

interface ProductItem {
  id: string;
  unique_key: string;
  brand: string | null;
  name: string | null;
  model: string | null;
  category: string | null;
  review_status: string;
  feishu_record_id: string | null;
  created_at: string;
}

interface ProductListResponse {
  items: ProductItem[];
  total: number;
}

// Extend request to talk to a future /products endpoint
// For now, we use a hack: get products from reviews as a proxy
async function fetchProducts(page: number): Promise<ProductListResponse> {
  // Products endpoint is not yet implemented, use empty placeholder
  // Once implemented, replace with: return request(`/products?page=${page}&page_size=20`)
  return { items: [], total: 0 };
}

export default function ProductListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["products", page],
    queryFn: () => fetchProducts(page),
  });

  const statusColors: Record<string, string> = {
    pending: "default", auto_approved: "success", needs_review: "orange",
    in_review: "processing", approved: "success", rejected: "error",
  };
  const statusLabels: Record<string, string> = {
    pending: "待处理", auto_approved: "自动通过", needs_review: "待复核",
    in_review: "复核中", approved: "已通过", rejected: "已驳回",
  };

  const columns = [
    { title: "品牌", dataIndex: "brand", key: "brand", width: 120 },
    { title: "产品名称", dataIndex: "name", key: "name", width: 200,
      render: (v: string, r: ProductItem) => <a onClick={() => navigate(`/products/${r.id}`)}>{v || r.unique_key}</a> },
    { title: "型号", dataIndex: "model", key: "model", width: 120 },
    { title: "品类", dataIndex: "category", key: "category", width: 100 },
    { title: "状态", dataIndex: "review_status", key: "status", width: 100,
      render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: "飞书记录", dataIndex: "feishu_record_id", key: "feishu", width: 150, ellipsis: true },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN") },
  ];

  return (
    <div>
      <Title level={4}>产品信息库</Title>
      <Table
        dataSource={data?.items} columns={columns} rowKey="id" loading={isLoading}
        pagination={{ current: page, total: data?.total, pageSize: 20, onChange: setPage }}
        size="middle" locale={{ emptyText: "暂无可显示的产品数据。请先创建采集任务。后续将实现 /api/v1/products 端点。" }}
      />
    </div>
  );
}
