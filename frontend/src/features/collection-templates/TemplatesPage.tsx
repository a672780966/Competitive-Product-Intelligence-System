// CPIS V1 — 采集模板列表 / Collection Templates page (Node 9)

import { useState } from "react";
import {
  Table, Tag, Button, Typography,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { templatesApi } from "../../api/client";
import { useNavigate } from "react-router-dom";
import type { CollectionTemplate } from "../../types";

const { Title } = Typography;

const statusLabels: Record<string, string> = {
  active: "活跃",
  paused: "已暂停",
  archived: "已归档",
};

const statusColors: Record<string, string> = {
  active: "success",
  paused: "warning",
  archived: "default",
};

export default function TemplatesPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["templates", page],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      return templatesApi.list(params.toString());
    },
  });

  const columns = [
    {
      title: "名称",
      dataIndex: "name",
      key: "name",
      width: 200,
      render: (v: string, r: CollectionTemplate) => (
        <a onClick={() => navigate(`/collection-templates/${r.id}`)}>{v}</a>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      width: 250,
      render: (v: string | null) => v || "—",
    },
    {
      title: "品牌",
      dataIndex: "target_brand",
      key: "brand",
      width: 120,
      render: (v: string | null) => v || "—",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={statusColors[v] || "default"}>{statusLabels[v] || v}</Tag>
      ),
    },
    {
      title: "来源数",
      dataIndex: "source_plan",
      key: "sources",
      width: 80,
      render: (v: Record<string, unknown> | null) => {
        if (!v) return 0;
        const urls = (v as any).urls;
        return Array.isArray(urls) ? urls.length : 0;
      },
    },
    {
      title: "上次运行",
      dataIndex: "last_run_at",
      key: "last_run",
      width: 180,
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "从未运行",
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
      width: 120,
      render: (_: unknown, r: CollectionTemplate) => (
        <Button size="small" onClick={() => navigate(`/collection-templates/${r.id}`)}>
          详情
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>采集模板 / Collection Templates</Title>
        <Button icon={<PlusOutlined />} type="primary" onClick={() => navigate("/discovery")}>
          从发现创建
        </Button>
      </div>

      <Table<CollectionTemplate>
        dataSource={data?.items}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          total: data?.total,
          pageSize: 20,
          onChange: setPage,
        }}
        size="middle"
        locale={{ emptyText: "暂无采集模板" }}
      />
    </div>
  );
}
