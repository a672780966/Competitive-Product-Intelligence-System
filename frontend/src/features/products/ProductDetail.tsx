// CPIS V1 — 产品详情页面

import { useParams, useNavigate } from "react-router-dom";
import {
  Card,
  Descriptions,
  Tag,
  Table,
  Timeline,
  Button,
  Space,
  Spin,
  Divider,
  Typography,
  message,
} from "antd";
import {
  ArrowLeftOutlined,
  ReloadOutlined,
  SyncOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { productsApi } from "../../api/products";
import type { ProductVersionItem } from "../../types";

const { Title, Text } = Typography;

const reviewStatusColors: Record<string, string> = {
  pending: "default",
  auto_approved: "success",
  needs_review: "orange",
  in_review: "processing",
  approved: "success",
  rejected: "error",
};

const reviewStatusLabels: Record<string, string> = {
  pending: "待处理",
  auto_approved: "自动通过",
  needs_review: "待复核",
  in_review: "复核中",
  approved: "已通过",
  rejected: "已驳回",
};

const syncStatusColors: Record<string, string> = {
  pending: "default",
  syncing: "processing",
  success: "success",
  failed: "error",
};

const syncStatusLabels: Record<string, string> = {
  pending: "待同步",
  syncing: "同步中",
  success: "同步成功",
  failed: "同步失败",
};

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => productsApi.get(id!),
    enabled: !!id,
  });

  const recollectMutation = useMutation({
    mutationFn: () => productsApi.recollect(id!),
    onSuccess: () => {
      message.success("已创建新的采集任务");
      queryClient.invalidateQueries({ queryKey: ["product", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  const syncMutation = useMutation({
    mutationFn: () => productsApi.syncFeishu(id!),
    onSuccess: () => {
      message.success("已触发飞书同步");
      queryClient.invalidateQueries({ queryKey: ["product", id] });
    },
    onError: (e: Error) => message.error(e.message),
  });

  if (isLoading) {
    return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  }
  if (!product) {
    return <p>产品不存在</p>;
  }

  const sd = product.current_version?.structured_data || {};
  const ad = product.current_version?.analysis_data || {};

  return (
    <div>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/products")}>
            返回
          </Button>
          <Title level={4} style={{ margin: 0 }}>
            {product.name || product.unique_key}
          </Title>
          <Tag color={reviewStatusColors[product.review_status]}>
            {reviewStatusLabels[product.review_status] || product.review_status}
          </Tag>
        </Space>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => recollectMutation.mutate()}
            loading={recollectMutation.isPending}
          >
            重新采集
          </Button>
          <Button
            icon={<SyncOutlined />}
            onClick={() => syncMutation.mutate()}
            loading={syncMutation.isPending}
          >
            同步飞书
          </Button>
          <Button
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/reports?productId=${product.id}`)}
          >
            导出简报
          </Button>
        </Space>
      </div>

      {/* Product Info Card */}
      <Card title="基本信息" style={{ marginBottom: 16 }} size="small">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="唯一标识">
            {product.unique_key}
          </Descriptions.Item>
          <Descriptions.Item label="品牌">
            {product.brand || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="产品名称">
            {product.name || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="型号">
            {product.model || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="品类">
            {product.category || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="来源">
            {product.source_url ? (
              <a href={product.source_url} target="_blank" rel="noreferrer">
                {product.source_url}
              </a>
            ) : (
              "—"
            )}
          </Descriptions.Item>
          <Descriptions.Item label="飞书记录ID">
            {product.feishu_record_id || "—"}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(product.created_at).toLocaleString("zh-CN")}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Current Version Card */}
      {product.current_version && (
        <Card
          title={
            <Space>
              <span>当前版本 v{product.current_version.version_no}</span>
              <Tag>
                置信度{" "}
                {product.current_version.overall_confidence !== null
                  ? `${(product.current_version.overall_confidence * 100).toFixed(0)}%`
                  : "—"}
              </Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                AI: {product.current_version.ai_model || "—"}
              </Text>
            </Space>
          }
          style={{ marginBottom: 16 }}
          size="small"
        >
          {/* Structured Data */}
          <Divider orientation="left" orientationMargin={0}>
            结构化字段
          </Divider>
          <Descriptions column={2} size="small" bordered>
            {Object.entries(sd)
              .filter(
                ([, v]) =>
                  v !== null && v !== "" && !Array.isArray(v) && typeof v !== "object",
              )
              .map(([key, value]) => (
                <Descriptions.Item label={key} key={key}>
                  {String(value)}
                </Descriptions.Item>
              ))}
          </Descriptions>

          {Object.keys(sd).filter(
            (k) => Array.isArray(sd[k]) || (typeof sd[k] === "object" && sd[k] !== null),
          ).length > 0 && (
            <>
              <Divider orientation="left" orientationMargin={0}>
                结构化列表字段
              </Divider>
              {Object.entries(sd)
                .filter(
                  ([, v]) =>
                    v !== null && (Array.isArray(v) || typeof v === "object"),
                )
                .map(([key, value]) => (
                  <div key={key} style={{ marginBottom: 8 }}>
                    <Text strong>{key}: </Text>
                    <Text>
                      {Array.isArray(value)
                        ? (value as string[]).join("; ")
                        : JSON.stringify(value)}
                    </Text>
                  </div>
                ))}
            </>
          )}

          {/* Analysis Data */}
          {Object.keys(ad).length > 0 && (
            <>
              <Divider orientation="left" orientationMargin={0}>
                AI 分析
              </Divider>
              <Descriptions column={1} size="small">
                {Object.entries(ad)
                  .filter(([, v]) => v !== null)
                  .map(([key, value]) => (
                    <Descriptions.Item label={key} key={key}>
                      {Array.isArray(value)
                        ? (value as string[]).join("; ")
                        : String(value)}
                    </Descriptions.Item>
                  ))}
              </Descriptions>
            </>
          )}

          {/* Evidences */}
          {product.evidences.length > 0 && (
            <>
              <Divider orientation="left" orientationMargin={0}>
                字段证据
              </Divider>
              <Table
                dataSource={product.evidences}
                columns={[
                  {
                    title: "字段",
                    dataIndex: "field_name",
                    key: "field",
                    width: 140,
                  },
                  {
                    title: "值",
                    dataIndex: "value",
                    key: "value",
                    width: 200,
                    ellipsis: true,
                  },
                  {
                    title: "置信度",
                    dataIndex: "confidence",
                    key: "confidence",
                    width: 90,
                    render: (v: number | null) =>
                      v !== null ? `${(v * 100).toFixed(0)}%` : "—",
                  },
                  {
                    title: "证据原文",
                    dataIndex: "evidence_text",
                    key: "evidence",
                    ellipsis: true,
                  },
                ]}
                rowKey="field_name"
                size="small"
                pagination={false}
              />
            </>
          )}
        </Card>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Version History */}
        <Card title="版本历史" size="small">
          {product.versions.length > 0 ? (
            <Timeline
              items={product.versions.map((v: ProductVersionItem) => ({
                color:
                  v.id === product.current_version?.id ? "green" : "blue",
                children: (
                  <div>
                    <strong>v{v.version_no}</strong>
                    {v.overall_confidence !== null && (
                      <Tag style={{ marginLeft: 8 }}>
                        {`${(v.overall_confidence * 100).toFixed(0)}%`}
                      </Tag>
                    )}
                    {v.id === product.current_version?.id && (
                      <Tag color="green" style={{ marginLeft: 4 }}>
                        当前
                      </Tag>
                    )}
                    <div style={{ fontSize: 12, color: "#999" }}>
                      {v.ai_model || "—"} |{" "}
                      {new Date(v.created_at).toLocaleString("zh-CN")}
                    </div>
                  </div>
                ),
              }))}
            />
          ) : (
            <Text type="secondary">暂无版本记录</Text>
          )}
        </Card>

        {/* Sync & Review Status */}
        <div>
          {/* Latest Sync Record */}
          <Card title="同步状态" size="small" style={{ marginBottom: 16 }}>
            {product.latest_sync ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="状态">
                  <Tag
                    color={
                      syncStatusColors[product.latest_sync.sync_status]
                    }
                  >
                    {syncStatusLabels[product.latest_sync.sync_status] ||
                      product.latest_sync.sync_status}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="飞书记录ID">
                  {product.latest_sync.feishu_record_id || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="错误信息">
                  {product.latest_sync.error_message || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="重试次数">
                  {product.latest_sync.retry_count}
                </Descriptions.Item>
                <Descriptions.Item label="同步时间">
                  {product.latest_sync.synced_at
                    ? new Date(product.latest_sync.synced_at).toLocaleString("zh-CN")
                    : "—"}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">暂无同步记录</Text>
            )}
          </Card>

          {/* Latest Review Record */}
          <Card title="审核记录" size="small">
            {product.latest_review ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="审核人">
                  {product.latest_review.reviewer as string || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="决策">
                  <Tag
                    color={
                      reviewStatusColors[
                        product.latest_review.decision as string
                      ]
                    }
                  >
                    {reviewStatusLabels[
                      product.latest_review.decision as string
                    ] || (product.latest_review.decision as string)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="意见">
                  {(product.latest_review.comments as string) || "—"}
                </Descriptions.Item>
                <Descriptions.Item label="时间">
                  {product.latest_review.created_at
                    ? new Date(
                        product.latest_review.created_at as string,
                      ).toLocaleString("zh-CN")
                    : "—"}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">暂无审核记录</Text>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
