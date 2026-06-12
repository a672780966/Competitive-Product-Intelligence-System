// CPIS V1 — 任务详情页面

import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Tag, Timeline, Button, Space, message, Spin } from "antd";
import { ArrowLeftOutlined, ReloadOutlined, StopOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "../../api/client";

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

      <Card title="事件日志">
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
    </div>
  );
}
