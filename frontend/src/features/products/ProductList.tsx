// CPIS V1 — 产品信息库页面

import { useState } from "react";
import { Input, Select, Space, Table, Tag, Typography } from "antd";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { productsApi } from "../../api/client";
import type { ProductSummary } from "../../types";

const { Title } = Typography;

const statusColors: Record<string, string> = {
  pending: "default", auto_approved: "success", needs_review: "orange",
  in_review: "processing", approved: "success", rejected: "error",
};

const statusLabels: Record<string, string> = {
  pending: "待处理", auto_approved: "自动通过", needs_review: "待复核",
  in_review: "复核中", approved: "已通过", rejected: "已驳回",
};

export default function ProductListPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [domain, setDomain] = useState("");
  const [keyword, setKeyword] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["products", page, statusFilter, domain, keyword],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (statusFilter) params.set("status", statusFilter);
      if (domain) params.set("domain", domain);
      if (keyword) params.set("keyword", keyword);
      return productsApi.list(params.toString());
    },
  });

  const columns = [
    { title: "品牌", dataIndex: "brand", key: "brand", width: 120, render: (v: string | null) => v || "—" },
    { title: "产品名称", dataIndex: "name", key: "name", width: 200,
      render: (v: string | null, r: ProductSummary) => <a onClick={() => navigate(`/products/${r.id}`)}>{v || r.unique_key}</a> },
    { title: "型号", dataIndex: "model", key: "model", width: 120, render: (v: string | null) => v || "—" },
    { title: "品类", dataIndex: "category", key: "category", width: 120, render: (v: string | null) => v || "—" },
    { title: "状态", dataIndex: "review_status", key: "status", width: 110,
      render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
    { title: "飞书记录", dataIndex: "feishu_record_id", key: "feishu", width: 150, ellipsis: true,
      render: (v: string | null) => v || "—" },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN") },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>产品信息库</Title>
        <Space>
          <Input.Search placeholder="搜索产品关键词" allowClear onSearch={setKeyword} style={{ width: 220 }} />
          <Input.Search placeholder="域名筛选" allowClear onSearch={setDomain} style={{ width: 180 }} />
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 140 }}
            onChange={v => setStatusFilter(v || undefined)}
            options={Object.entries(statusLabels).map(([value, label]) => ({ value, label }))}
          />
        </Space>
      </div>

      <Table
        dataSource={data?.items}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={{ current: page, total: data?.total, pageSize: 20, onChange: setPage }}
        size="middle"
      />
    </div>
  );
}
