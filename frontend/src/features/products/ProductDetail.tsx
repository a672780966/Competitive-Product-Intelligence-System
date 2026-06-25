// CPIS V1 — 产品详情页面

import { useNavigate, useParams } from "react-router-dom";
import { Button, Card, Descriptions, Spin, Table, Tag, Typography } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { productsApi } from "../../api/client";
import type { VersionSummary } from "../../types";

const { Text } = Typography;

const statusColors: Record<string, string> = {
  pending: "default", auto_approved: "success", needs_review: "orange",
  in_review: "processing", approved: "success", rejected: "error",
};

const statusLabels: Record<string, string> = {
  pending: "待处理", auto_approved: "自动通过", needs_review: "待复核",
  in_review: "复核中", approved: "已通过", rejected: "已驳回",
};

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: product, error, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => productsApi.get(id!),
    enabled: !!id,
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (error) return <Text type="danger">{(error as Error).message}</Text>;
  if (!product) return <p>产品不存在</p>;

  const versionColumns = [
    { title: "版本", dataIndex: "version_no", key: "version_no", width: 100 },
    { title: "置信度", dataIndex: "overall_confidence", key: "overall_confidence", width: 120,
      render: (v: number | null) => v !== null ? `${(v * 100).toFixed(0)}%` : "—" },
    { title: "AI 模型", dataIndex: "ai_model", key: "ai_model", width: 180, render: (v: string | null) => v || "—" },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN") },
  ];

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/products")} style={{ marginBottom: 16 }}>
        返回
      </Button>

      <Card title="产品信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="品牌">{product.brand || "—"}</Descriptions.Item>
          <Descriptions.Item label="产品名称">{product.name || "—"}</Descriptions.Item>
          <Descriptions.Item label="型号">{product.model || "—"}</Descriptions.Item>
          <Descriptions.Item label="品类">{product.category || "—"}</Descriptions.Item>
          <Descriptions.Item label="复核状态">
            <Tag color={statusColors[product.review_status]}>{statusLabels[product.review_status] || product.review_status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="唯一键">{product.unique_key}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{new Date(product.created_at).toLocaleString("zh-CN")}</Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="版本历史">
        <Table<VersionSummary>
          dataSource={product.versions}
          columns={versionColumns}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  );
}
