// CPIS V1 — 人工复核详情页 (左右对照面板)

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Card, Descriptions, Tag, Button, Space, Spin, Input, Divider, message, Progress,
} from "antd";
import { ArrowLeftOutlined, CheckOutlined, CloseOutlined, SaveOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewsApi } from "../../api/client";
import type { EvidenceItem } from "../../types";

const { TextArea } = Input;

export default function ReviewDetailPage() {
  const { versionId } = useParams<{ versionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [comments, setComments] = useState("");

  const { data: detail, isLoading } = useQuery({
    queryKey: ["review", versionId],
    queryFn: () => reviewsApi.get(versionId!),
    enabled: !!versionId,
  });

  const approveMutation = useMutation({
    mutationFn: () => reviewsApi.approve(versionId!, { corrections, comments }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["review", versionId] }); message.success("已审核通过"); navigate("/reviews"); },
  });

  const rejectMutation = useMutation({
    mutationFn: () => reviewsApi.reject(versionId!, { comments }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["review", versionId] }); message.success("已驳回"); navigate("/reviews"); },
  });

  const draftMutation = useMutation({
    mutationFn: () => reviewsApi.saveDraft(versionId!, { corrections, comments }),
    onSuccess: () => message.success("草稿已保存"),
  });

  const updateMutation = useMutation({
    mutationFn: () => reviewsApi.update(versionId!, { corrections, comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review", versionId] });
      message.success("修改已保存");
    },
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!detail) return <p>未找到复核记录</p>;

  const sd = detail.structured_data as Record<string, unknown>;
  const currentReview = detail.current_review as {
    corrections?: Record<string, unknown>;
    changed_fields?: unknown;
  } | null;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/reviews")}>返回</Button>
        <Button onClick={() => draftMutation.mutate()} loading={draftMutation.isPending}>保存草稿</Button>
        <Button icon={<SaveOutlined />} onClick={() => updateMutation.mutate()} loading={updateMutation.isPending}>保存修改</Button>
        <Button type="primary" icon={<CheckOutlined />} onClick={() => approveMutation.mutate()}
          loading={approveMutation.isPending} danger={false}>审核通过</Button>
        <Button danger icon={<CloseOutlined />} onClick={() => rejectMutation.mutate()}
          loading={rejectMutation.isPending}>驳回</Button>
      </Space>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Left panel: source content */}
        <Card title="原文与证据" size="small">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="来源">
              <a href={detail.source_url || "#"} target="_blank" rel="noreferrer">{detail.source_url}</a>
            </Descriptions.Item>
            <Descriptions.Item label="置信度">
              <Progress percent={Math.round((detail.overall_confidence || 0) * 100)} size="small" />
            </Descriptions.Item>
            <Descriptions.Item label="AI 模型">{detail.ai_model || "—"}</Descriptions.Item>
          </Descriptions>

          <Divider>清洗正文</Divider>
          <div style={{ maxHeight: 400, overflow: "auto", fontSize: 13, lineHeight: 1.6, background: "#fafafa", padding: 12, borderRadius: 4, whiteSpace: "pre-wrap" }}>
            {detail.source_text || detail.cleaned_text || "无清洗文本"}
          </div>

          <Divider>字段证据</Divider>
          {detail.evidences?.length ? detail.evidences.map((ev: EvidenceItem) => (
            <Card key={ev.field_name} size="small" style={{ marginBottom: 8, background: "#fafafa" }}>
              <Space direction="vertical" size={2} style={{ width: "100%" }}>
                <Space>
                  <strong>{ev.field_name}</strong>
                  <Tag color={ev.confidence !== null && ev.confidence >= 0.7 ? "green" : "orange"}>
                    {ev.confidence !== null ? `${(ev.confidence * 100).toFixed(0)}%` : "—"}
                  </Tag>
                </Space>
                {ev.evidence_text && <div style={{ fontSize: 12, color: "#666", fontStyle: "italic" }}>"{ev.evidence_text}"</div>}
              </Space>
            </Card>
          )) : <span style={{ color: "#999" }}>无证据</span>}
        </Card>

        {/* Right panel: structured data form */}
        <Card title="结构化字段" size="small">
          {Object.entries(sd).filter(([_, v]) => v !== null && v !== "" && !Array.isArray(v)).map(([key, value]) => (
            <div key={key} style={{ marginBottom: 12 }}>
              <label style={{ fontWeight: 500, fontSize: 13 }}>{key}</label>
              <Input
                size="small" defaultValue={String(value)}
                onChange={e => setCorrections(prev => ({ ...prev, [key]: e.target.value }))}
                style={{ marginTop: 4 }}
              />
            </div>
          ))}

          {detail.analysis_data && Object.keys(detail.analysis_data).length > 0 && (
            <>
              <Divider>AI 分析字段（仅供参考）</Divider>
              {Object.entries(detail.analysis_data as Record<string, unknown>).filter(([_, v]) => v !== null).map(([key, value]) => (
                <div key={key} style={{ marginBottom: 8 }}>
                  <label style={{ fontWeight: 500, fontSize: 13 }}>{key}</label>
                  <div style={{ fontSize: 13, color: "#666", marginTop: 2 }}>
                    {Array.isArray(value) ? (value as string[]).join("; ") : String(value)}
                  </div>
                </div>
              ))}
            </>
          )}

          {currentReview?.corrections && Object.keys(currentReview.corrections).length > 0 && (
            <>
              <Divider>已保存修改</Divider>
              {Object.entries(currentReview.corrections).map(([key, value]) => (
                <div key={key} style={{ marginBottom: 8 }}>
                  <label style={{ fontWeight: 500, fontSize: 13 }}>{key}</label>
                  <div style={{ fontSize: 13, color: "#666", marginTop: 2, whiteSpace: "pre-wrap" }}>
                    {String(value)}
                  </div>
                </div>
              ))}
            </>
          )}

          {currentReview?.changed_fields ? (
            <>
              <Divider>变更字段</Divider>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {Array.isArray(currentReview.changed_fields)
                  ? (currentReview.changed_fields as Array<string | number | boolean>).map(field => <Tag key={String(field)}>{String(field)}</Tag>)
                  : <span style={{ fontSize: 13, color: "#666" }}>{String(currentReview.changed_fields)}</span>}
              </div>
            </>
          ) : null}

          <Divider>审核意见</Divider>
          <TextArea rows={3} placeholder="审核意见（可选）" value={comments} onChange={e => setComments(e.target.value)} />
        </Card>
      </div>
    </div>
  );
}
