// CPIS V1 — 来源发现 / Source Discovery page (Node 8)

import { useState, useCallback } from "react";
import {
  Card, Input, Button, Space, Tag, Typography, Row, Col, Checkbox,
  message, Spin, Modal, Form, Alert,
} from "antd";
import {
  SearchOutlined, LinkOutlined, CheckOutlined,
  CloseOutlined, FileAddOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { discoveryApi } from "../../api/client";
import { useNavigate } from "react-router-dom";
import type { SourceCandidate, DiscoverySession } from "../../types";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ── Label/color maps ─────────────────────────────────────────────

const sourceTypeLabels: Record<string, string> = {
  official_homepage: "官方",
  product_detail: "产品详情",
  documentation: "文档",
  news: "新闻",
  review: "评测",
  forum: "论坛",
  social: "社交",
  other: "其他",
};

const sourceTypeColors: Record<string, string> = {
  official_homepage: "blue",
  product_detail: "cyan",
  documentation: "purple",
  news: "green",
  review: "orange",
  forum: "geekblue",
  social: "red",
  other: "default",
};

const riskLevelColors: Record<string, string> = {
  low: "success",
  medium: "warning",
  high: "error",
  blocked: "#ff4d4f",
};

const riskLevelLabels: Record<string, string> = {
  low: "低",
  medium: "中",
  high: "高",
  blocked: "禁止",
};

const collectorLabels: Record<string, string> = {
  direct_http: "HTTP",
  playwright: "Playwright",
  scrapling_feature_flag: "Scrapling",
  crawl4ai_feature_flag: "Crawl4AI",
  requires_confirmation: "待确认",
};

const collectorColors: Record<string, string> = {
  direct_http: "green",
  playwright: "blue",
  scrapling_feature_flag: "purple",
  crawl4ai_feature_flag: "purple",
  requires_confirmation: "orange",
};

// ── Component ────────────────────────────────────────────────────

export default function DiscoveryPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [query, setQuery] = useState("");
  const [targetBrand, setTargetBrand] = useState("");
  const [currentSession, setCurrentSession] = useState<DiscoverySession | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [templateModalOpen, setTemplateModalOpen] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");
  const [createdTemplate, setCreatedTemplate] = useState<{ id: string; name: string } | null>(null);

  // Create session
  const createMutation = useMutation({
    mutationFn: (body: { query: string; target_brand?: string }) =>
      discoveryApi.createSession(body),
    onSuccess: (data) => {
      setCurrentSession(data.session);
      // Set selected for all candidates initially
      setSelectedIds(new Set(data.candidates.map((c: SourceCandidate) => c.id)));
      message.success("发现完成，共发现 " + data.candidates.length + " 个来源");
    },
    onError: (e: Error) => message.error("发现失败: " + e.message),
  });

  // Batch select/deselect
  const batchSelectMutation = useMutation({
    mutationFn: ({ candidateIds, selected }: { candidateIds: string[]; selected: boolean }) =>
      discoveryApi.batchSelect(currentSession!.id, candidateIds, selected),
    onError: (e: Error) => message.error("操作失败: " + e.message),
  });

  // Create template
  const templateMutation = useMutation({
    mutationFn: (body: { name: string; description?: string }) =>
      discoveryApi.createTemplate(currentSession!.id, body),
    onSuccess: (data) => {
      setCreatedTemplate({ id: data.template_id, name: data.name });
      setTemplateModalOpen(false);
      setTemplateName("");
      setTemplateDesc("");
      message.success("模板已创建: " + data.name);
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (e: Error) => message.error("创建模板失败: " + e.message),
  });

  // Toggle single candidate
  const toggleCandidate = useCallback((candidateId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(candidateId)) {
        next.delete(candidateId);
      } else {
        next.add(candidateId);
      }
      return next;
    });
  }, []);

  // Select all
  const selectAll = useCallback(() => {
    if (!createMutation.data) return;
    const allIds = (createMutation.data.candidates || []).map((c: SourceCandidate) => c.id);
    setSelectedIds(new Set(allIds));
    if (allIds.length > 0 && currentSession) {
      batchSelectMutation.mutate({ candidateIds: allIds, selected: true });
    }
  }, [createMutation.data, currentSession, batchSelectMutation]);

  // Deselect all
  const deselectAll = useCallback(() => {
    const currentSelected = Array.from(selectedIds);
    setSelectedIds(new Set());
    if (currentSelected.length > 0 && currentSession) {
      batchSelectMutation.mutate({ candidateIds: currentSelected, selected: false });
    }
  }, [selectedIds, currentSession, batchSelectMutation]);

  const handleSubmit = () => {
    if (!query.trim()) {
      message.warning("请输入搜索关键词");
      return;
    }
    setCreatedTemplate(null);
    createMutation.mutate({
      query: query.trim(),
      target_brand: targetBrand.trim() || undefined,
    });
  };

  const candidates: SourceCandidate[] = createMutation.data?.candidates || [];

  // Show recent sessions
  const { data: sessionsData } = useQuery({
    queryKey: ["discovery-sessions"],
    queryFn: () => discoveryApi.listSessions("page=1&page_size=10"),
    enabled: !currentSession,
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>来源发现 / Source Discovery</Title>
      </div>

      {/* Search Card */}
      <Card style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <div>
            <Text strong>搜索关键词</Text>
            <TextArea
              rows={2}
              placeholder='例如: "帮我采集彪马竞品内容"'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ marginTop: 4 }}
            />
          </div>
          <Space>
            <Input
              placeholder="目标品牌 (可选)"
              value={targetBrand}
              onChange={(e) => setTargetBrand(e.target.value)}
              style={{ width: 200 }}
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSubmit}
              loading={createMutation.isPending}
            >
              开始发现
            </Button>
          </Space>
        </Space>
      </Card>

      {/* Loading */}
      {createMutation.isPending && (
        <div style={{ textAlign: "center", padding: 60 }}>
          <Spin size="large" />
          <Paragraph style={{ marginTop: 16, color: "#999" }}>正在搜索并分析来源...</Paragraph>
          <Alert
            type="warning"
            showIcon
            message="⚠️ Discovery Provider Ready / Mock Mode — 当前使用模拟数据，未调用真实搜索引擎"
            style={{ marginTop: 16, maxWidth: 500, marginLeft: "auto", marginRight: "auto" }}
          />
        </div>
      )}

      {/* Candidates */}
      {currentSession && !createMutation.isPending && (
        <>
          {/* Session info */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Text strong>会话: </Text>
              <Text>{currentSession.query}</Text>
              <Tag color={currentSession.status === "completed" ? "success" : "processing"}>
                {currentSession.status === "completed" ? "已完成" : currentSession.status === "failed" ? "失败" : "进行中"}
              </Tag>
              {currentSession.target_brand && (
                <Tag>{currentSession.target_brand}</Tag>
              )}
              <Text type="secondary">
                共 {candidates.length} 个来源 | 已选 {selectedIds.size} 个
              </Text>
            </Space>
          </Card>

          {/* Actions */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Button size="small" icon={<CheckOutlined />} onClick={selectAll}>
                全选
              </Button>
              <Button size="small" icon={<CloseOutlined />} onClick={deselectAll}>
                取消全选
              </Button>
              <Button
                type="primary"
                icon={<FileAddOutlined />}
                disabled={selectedIds.size === 0}
                onClick={() => setTemplateModalOpen(true)}
              >
                创建模板 ({selectedIds.size})
              </Button>
            </Space>
          </Card>

          {/* Candidate cards */}
          <Row gutter={[16, 16]}>
            {candidates.map((candidate) => (
              <Col xs={24} sm={12} lg={8} xl={6} key={candidate.id}>
                <Card
                  size="small"
                  hoverable
                  style={{
                    border: selectedIds.has(candidate.id) ? "2px solid #1677ff" : "1px solid #f0f0f0",
                  }}
                  onClick={() => toggleCandidate(candidate.id)}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
                    <img
                      src={candidate.favicon_url || `https://www.google.com/s2/favicons?domain=${candidate.domain}`}
                      alt=""
                      style={{ width: 16, height: 16, marginTop: 4 }}
                      onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <Text strong ellipsis style={{ display: "block", marginBottom: 2 }}>
                        {candidate.title || candidate.url}
                      </Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>{candidate.domain}</Text>
                    </div>
                    <Checkbox checked={selectedIds.has(candidate.id)} onClick={(e) => e.stopPropagation()} />
                  </div>

                  {candidate.snippet && (
                    <Paragraph
                      type="secondary"
                      ellipsis={{ rows: 2 }}
                      style={{ fontSize: 12, marginBottom: 8 }}
                    >
                      {candidate.snippet}
                    </Paragraph>
                  )}

                  <Space size={4} wrap>
                    <Tag color={sourceTypeColors[candidate.source_type] || "default"} style={{ fontSize: 11 }}>
                      {sourceTypeLabels[candidate.source_type] || candidate.source_type}
                    </Tag>
                    <Tag color={riskLevelColors[candidate.risk_level] || "default"} style={{ fontSize: 11 }}>
                      {riskLevelLabels[candidate.risk_level] || candidate.risk_level}
                    </Tag>
                    <Tag color={collectorColors[candidate.recommended_collector] || "default"} style={{ fontSize: 11 }}>
                      {collectorLabels[candidate.recommended_collector] || candidate.recommended_collector}
                    </Tag>
                  </Space>

                  <div style={{ marginTop: 8 }}>
                    <a
                      href={candidate.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      style={{ fontSize: 12 }}
                    >
                      <LinkOutlined /> 打开链接
                    </a>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </>
      )}

      {/* Recent sessions (when no active session) */}
      {!currentSession && sessionsData?.items && sessionsData.items.length > 0 && (
        <Card title="最近发现会话">
          {sessionsData.items.map((s: DiscoverySession) => (
            <div
              key={s.id}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid #f0f0f0",
                cursor: "pointer",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
              onClick={() => {
                discoveryApi.getSession(s.id).then((data) => {
                  setCurrentSession(data.session);
                  setSelectedIds(new Set(data.candidates.filter((c: SourceCandidate) => c.selected).map((c: SourceCandidate) => c.id)));
                });
              }}
            >
              <Space>
                <Text>{s.query}</Text>
                <Tag color={s.status === "completed" ? "success" : "processing"}>
                  {s.status === "completed" ? "已完成" : s.status === "failed" ? "失败" : "进行中"}
                </Tag>
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {s.candidate_count} 个来源 | {new Date(s.created_at).toLocaleString("zh-CN")}
              </Text>
            </div>
          ))}
        </Card>
      )}

      {/* Created template alert */}
      {createdTemplate && (
        <Alert
          type="success"
          showIcon
          style={{ marginTop: 16 }}
          message={
            <Space>
              <Text>模板已创建: <strong>{createdTemplate.name}</strong></Text>
              <Button size="small" type="primary" onClick={() => navigate(`/collection-templates/${createdTemplate.id}`)}>
                查看模板
              </Button>
            </Space>
          }
          closable
          onClose={() => setCreatedTemplate(null)}
        />
      )}

      {/* Create Template Modal */}
      <Modal
        title="创建采集模板"
        open={templateModalOpen}
        onCancel={() => setTemplateModalOpen(false)}
        onOk={() => {
          if (!templateName.trim()) {
            message.warning("请输入模板名称");
            return;
          }
          templateMutation.mutate({
            name: templateName.trim(),
            description: templateDesc.trim() || undefined,
          });
        }}
        confirmLoading={templateMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="模板名称" required>
            <Input
              placeholder="例如: 彪马竞品采集"
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
            />
          </Form.Item>
          <Form.Item label="描述 (可选)">
            <TextArea
              rows={3}
              placeholder="模板用途说明"
              value={templateDesc}
              onChange={(e) => setTemplateDesc(e.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
