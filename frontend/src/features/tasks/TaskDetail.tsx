// CPIS V1 — 任务详情页面

import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Tag, Timeline, Button, Space, message, Spin, Table } from "antd";
import { ArrowLeftOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "../../api/client";
import type { PipelineStageStatus } from "../../types";

const statusColors: Record<string, string> = {
  pending: "default", validating: "processing", fetching: "processing",
  cleaning: "processing", extracting: "processing", review_pending: "orange",
  syncing: "processing", completed: "success", partial_success: "warning",
  failed: "error", cancelled: "default", blocked: "error",
};

const statusLabels: Record<string, string> = {
  pending: "待处理", validating: "校验中", fetching: "采集中",
  cleaning: "清洗中", extracting: "抽取中", review_pending: "待复核",
  syncing: "同步中", completed: "已完成", partial_success: "部分成功",
  failed: "失败", cancelled: "已取消", blocked: "已拦截",
};

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", id],
    queryFn: () => tasksApi.get(id!),
    enabled: !!id,
  });

  const retryMutation = useMutation({
    mutationFn: () => tasksApi.retry(id!),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["task", id] }); message.success("已重试"); },
  });

  const cancelMutation = useMutation({
    mutationFn: () => tasksApi.cancel(id!),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["task", id] }); message.success("已取消"); },
  });

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!task) return <p>任务不存在</p>;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/tasks")}>返回</Button>
        <Button icon={<ReloadOutlined />} onClick={() => retryMutation.mutate()} loading={retryMutation.isPending} disabled={!["failed", "blocked"].includes(task.status)}>重试</Button>
        <Button icon={<StopOutlined />} onClick={() => cancelMutation.mutate()} loading={cancelMutation.isPending} disabled={task.status === "completed"}>取消</Button>
      </Space>

      <Card title="任务信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="URL">{task.source_url}</Descriptions.Item>
          <Descriptions.Item label="标准化URL">{task.normalized_url || "—"}</Descriptions.Item>
          <Descriptions.Item label="域名">{task.domain || "—"}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag color={statusColors[task.status]}>{statusLabels[task.status] || task.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="优先级">{task.priority}</Descriptions.Item>
          <Descriptions.Item label="重试次数">{task.retry_count}/{task.max_retries}</Descriptions.Item>
          <Descriptions.Item label="错误码">{task.error_code || "—"}</Descriptions.Item>
          <Descriptions.Item label="错误信息">{task.error_message || "—"}</Descriptions.Item>
          <Descriptions.Item label="创建人">{task.created_by || "—"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{new Date(task.created_at).toLocaleString("zh-CN")}</Descriptions.Item>
          {task.started_at && <Descriptions.Item label="开始时间">{new Date(task.started_at).toLocaleString("zh-CN")}</Descriptions.Item>}
          {task.finished_at && <Descriptions.Item label="完成时间">{new Date(task.finished_at).toLocaleString("zh-CN")}</Descriptions.Item>}
        </Descriptions>
      </Card>

      <Card title="事件日志" style={{ marginBottom: 16 }}>
        {task.events && task.events.length > 0 ? (
          <Timeline items={task.events.map((e: { stage: string; status: string; message: string | null; created_at: string }) => ({
            color: e.status === "failed" || e.status === "blocked" ? "red" : e.status === "completed" ? "green" : "blue",
            children: (
              <>
                <strong>[{e.stage}]</strong> <Tag color={statusColors[e.status]}>{statusLabels[e.status] || e.status}</Tag>
                {e.message && <p style={{ margin: "4px 0" }}>{e.message}</p>}
                <small style={{ color: "#999" }}>{new Date(e.created_at).toLocaleString("zh-CN")}</small>
              </>
            ),
          }))} />
        ) : <p style={{ color: "#999" }}>暂无事件记录</p>}
      </Card>

      {task.snapshot && (
        <Card title="快照信息" style={{ marginBottom: 16 }}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="最终URL">
              {task.snapshot.final_url ? <a href={task.snapshot.final_url} target="_blank" rel="noreferrer">{task.snapshot.final_url}</a> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="内容哈希">{task.snapshot.content_hash || "—"}</Descriptions.Item>
            <Descriptions.Item label="HTML哈希">{task.snapshot.html_hash || "—"}</Descriptions.Item>
            <Descriptions.Item label="清洗文本预览">
              <div style={{ maxHeight: 160, overflow: "auto", whiteSpace: "pre-wrap", background: "#fafafa", padding: 12, borderRadius: 4 }}>
                {task.snapshot.cleaned_text ? task.snapshot.cleaned_text.slice(0, 1000) : "—"}
              </div>
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {task.pipeline_status && (
        <Card title="管道状态">
          <Descriptions column={2} size="small" style={{ marginBottom: 16 }}>
            <Descriptions.Item label="整体状态">
              <Tag color={statusColors[task.pipeline_status.overall_status]}>
                {statusLabels[task.pipeline_status.overall_status] || task.pipeline_status.overall_status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前阶段">
              {task.pipeline_status.current_stage ? <Tag>{task.pipeline_status.current_stage}</Tag> : "—"}
            </Descriptions.Item>
            <Descriptions.Item label="重试次数">
              {task.pipeline_status.retry_count}/{task.pipeline_status.max_retries}
            </Descriptions.Item>
          </Descriptions>
          <Table<PipelineStageStatus>
            dataSource={task.pipeline_status.stages}
            rowKey="stage"
            pagination={false}
            size="small"
            columns={[
              { title: "阶段", dataIndex: "stage", key: "stage" },
              { title: "状态", dataIndex: "status", key: "status",
                render: (v: string) => <Tag color={statusColors[v]}>{statusLabels[v] || v}</Tag> },
              { title: "错误码", dataIndex: "error_code", key: "error_code", render: (v: string | null) => v || "—" },
              { title: "错误信息", dataIndex: "error_message", key: "error_message", ellipsis: true, render: (v: string | null) => v || "—" },
            ]}
          />
        </Card>
      )}
    </div>
  );
}
