// CPIS V1 — 模板详情 / Template Detail page (Node 9)

import { useState } from "react";
import {
  Card, Descriptions, Tag, Button, Space, Typography, message,
  Spin, Collapse, Table, Modal, Input, Form, Switch,
  Select, InputNumber,
} from "antd";
import {
  ArrowLeftOutlined, PlayCircleOutlined, EditOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi, schedulesApi } from "../../api/client";
import type { ScheduledCollection } from "../../types";

const { Text, Paragraph } = Typography;
const { Panel } = Collapse;
const { TextArea } = Input;

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

const scheduleStatusLabels: Record<string, string> = {
  pending: "待执行",
  running: "运行中",
  success: "成功",
  failed: "失败",
  paused: "已暂停",
};
const scheduleStatusColors: Record<string, string> = {
  pending: "default",
  running: "processing",
  success: "success",
  failed: "error",
  paused: "warning",
};

export default function TemplateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [scheduleType, setScheduleType] = useState("daily");
  const [scheduleCron, setScheduleCron] = useState("");
  const [scheduleInterval, setScheduleInterval] = useState<number | null>(60);
  const [scheduleEnabled, setScheduleEnabled] = useState(true);

  // ── Queries ────────────────────────────────────────────────────
  const { data: template, isLoading } = useQuery({
    queryKey: ["template", id],
    queryFn: () => templatesApi.get(id!),
    enabled: !!id,
  });

  const { data: schedulesData } = useQuery({
    queryKey: ["schedules", id],
    queryFn: () => schedulesApi.list(`page=1&page_size=50`),
  });

  const schedules = schedulesData?.items?.filter(
    (s: ScheduledCollection) => s.template_id === id
  ) || [];

  // ── Mutations ──────────────────────────────────────────────────
  const runMutation = useMutation({
    mutationFn: () => templatesApi.run(id!),
    onSuccess: (data) => {
      message.success(`模板已执行，创建了 ${data.tasks_created} 个采集任务`);
      queryClient.invalidateQueries({ queryKey: ["template", id] });
    },
    onError: (e: Error) => message.error("执行失败: " + e.message),
  });

  const updateMutation = useMutation({
    mutationFn: (body: { name?: string; description?: string }) =>
      templatesApi.update(id!, body),
    onSuccess: () => {
      message.success("模板已更新");
      setEditModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["template", id] });
    },
    onError: (e: Error) => message.error("更新失败: " + e.message),
  });

  const createScheduleMutation = useMutation({
    mutationFn: (body: {
      template_id: string;
      schedule_type: string;
      cron_expr?: string;
      interval_minutes?: number;
      enabled: boolean;
    }) => schedulesApi.create(body),
    onSuccess: () => {
      message.success("定时采集已创建");
      setScheduleModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["schedules", id] });
    },
    onError: (e: Error) => message.error("创建失败: " + e.message),
  });

  const toggleScheduleMutation = useMutation({
    mutationFn: ({ scheduleId, enabled }: { scheduleId: string; enabled: boolean }) =>
      schedulesApi.update(scheduleId, { enabled }),
    onSuccess: () => {
      message.success("定时任务状态已更新");
      queryClient.invalidateQueries({ queryKey: ["schedules", id] });
    },
    onError: (e: Error) => message.error("更新失败: " + e.message),
  });

  // ── Helpers ────────────────────────────────────────────────────
  const openEdit = () => {
    if (!template) return;
    setEditName(template.name);
    setEditDesc(template.description || "");
    setEditModalOpen(true);
  };

  if (isLoading) return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  if (!template) return <p>模板不存在</p>;

  const sourcePlanUrls: string[] = template.source_plan?.urls
    ? (template.source_plan as any).urls
    : [];

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/collection-templates")}>返回</Button>
        <Button icon={<PlayCircleOutlined />} type="primary"
          onClick={() => runMutation.mutate()} loading={runMutation.isPending}>
          立即运行
        </Button>
        <Button icon={<EditOutlined />} onClick={openEdit}>编辑</Button>
        <Button icon={<ClockCircleOutlined />} onClick={() => setScheduleModalOpen(true)}>
          创建定时
        </Button>
      </Space>

      {/* Template Info */}
      <Card title="模板信息" style={{ marginBottom: 16 }}>
        <Descriptions column={2} size="small">
          <Descriptions.Item label="名称">{template.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={statusColors[template.status]}>{statusLabels[template.status] || template.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{template.description || "—"}</Descriptions.Item>
          <Descriptions.Item label="目标品牌">{template.target_brand || "—"}</Descriptions.Item>
          <Descriptions.Item label="主题">{template.topic || "—"}</Descriptions.Item>
          <Descriptions.Item label="飞书同步">
            <Tag color={template.feishu_sync_enabled ? "blue" : "default"}>
              {template.feishu_sync_enabled ? "已启用" : "未启用"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="上次运行">
            {template.last_run_at ? new Date(template.last_run_at).toLocaleString("zh-CN") : "从未运行"}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(template.created_at).toLocaleString("zh-CN")}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* Source Plan */}
      <Card title="来源计划" size="small" style={{ marginBottom: 16 }}>
        {sourcePlanUrls.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {sourcePlanUrls.map((url, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                <a href={url} target="_blank" rel="noopener noreferrer">{url}</a>
              </li>
            ))}
          </ul>
        ) : (
          <Text type="secondary">暂无来源计划</Text>
        )}
      </Card>

      {/* Run Plan */}
      <Card title="运行计划 (Run Plan)" size="small" style={{ marginBottom: 16 }}>
        <Collapse ghost size="small">
          <Panel header="查看运行计划 JSON" key="1">
            <pre style={{
              background: "#f5f5f5",
              padding: 12,
              borderRadius: 4,
              maxHeight: 300,
              overflow: "auto",
              fontSize: 12,
            }}>
              {JSON.stringify(template.run_plan, null, 2)}
            </pre>
          </Panel>
        </Collapse>
      </Card>

      {/* Schedules */}
      <Card title="定时采集" style={{ marginBottom: 16 }}>
        {schedules.length === 0 ? (
          <Paragraph type="secondary">暂无定时采集计划。点击"创建定时"按钮添加。</Paragraph>
        ) : (
          <Table<ScheduledCollection>
            dataSource={schedules}
            rowKey="id"
            size="small"
            pagination={false}
            columns={[
              {
                title: "类型",
                dataIndex: "schedule_type",
                key: "type",
                width: 100,
                render: (v: string) => {
                  const typeMap: Record<string, string> = {
                    cron: "Cron",
                    interval: "间隔",
                    daily: "每日",
                    weekly: "每周",
                    monthly: "每月",
                  };
                  return typeMap[v] || v;
                },
              },
              {
                title: "表达式",
                key: "expr",
                width: 140,
                render: (_: unknown, r: ScheduledCollection) =>
                  r.cron_expr || (r.interval_minutes ? `每${r.interval_minutes}分钟` : "—"),
              },
              {
                title: "状态",
                dataIndex: "enabled",
                key: "enabled",
                width: 80,
                render: (v: boolean) => (
                  <Tag color={v ? "success" : "default"}>{v ? "启用" : "停用"}</Tag>
                ),
              },
              {
                title: "上次运行",
                dataIndex: "last_run_at",
                key: "last_run",
                width: 160,
                render: (v: string | null) => v ? new Date(v).toLocaleString("zh-CN") : "—",
              },
              {
                title: "上次状态",
                dataIndex: "last_status",
                key: "last_status",
                width: 100,
                render: (v: string | null) => v
                  ? <Tag color={scheduleStatusColors[v]}>{scheduleStatusLabels[v] || v}</Tag>
                  : "—",
              },
              {
                title: "失败次数",
                dataIndex: "failure_count",
                key: "failures",
                width: 80,
                render: (v: number) => v > 0 ? <Text type="danger">{v}</Text> : v,
              },
              {
                title: "下次运行",
                dataIndex: "next_run_at",
                key: "next_run",
                width: 160,
                render: (v: string | null) => v ? new Date(v).toLocaleString("zh-CN") : "—",
              },
              {
                title: "操作",
                key: "actions",
                width: 80,
                render: (_: unknown, r: ScheduledCollection) => (
                  <Switch
                    size="small"
                    checked={r.enabled}
                    onChange={(checked) =>
                      toggleScheduleMutation.mutate({ scheduleId: r.id, enabled: checked })
                    }
                  />
                ),
              },
            ]}
          />
        )}
      </Card>

      {/* Edit Modal */}
      <Modal
        title="编辑模板"
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        onOk={() => updateMutation.mutate({
          name: editName,
          description: editDesc || undefined,
        })}
        confirmLoading={updateMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="名称" required>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </Form.Item>
          <Form.Item label="描述">
            <TextArea rows={3} value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Create Schedule Modal */}
      <Modal
        title="创建定时采集"
        open={scheduleModalOpen}
        onCancel={() => setScheduleModalOpen(false)}
        onOk={() => {
          const body: any = {
            template_id: id!,
            schedule_type: scheduleType,
            enabled: scheduleEnabled,
          };
          if (scheduleType === "cron") {
            if (!scheduleCron.trim()) {
              message.warning("请输入 Cron 表达式");
              return;
            }
            body.cron_expr = scheduleCron.trim();
          } else if (scheduleType === "interval") {
            if (!scheduleInterval) {
              message.warning("请输入间隔分钟数");
              return;
            }
            body.interval_minutes = scheduleInterval;
          }
          createScheduleMutation.mutate(body);
        }}
        confirmLoading={createScheduleMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="调度类型" required>
            <Select value={scheduleType} onChange={setScheduleType}
              options={[
                { value: "daily", label: "每日" },
                { value: "weekly", label: "每周" },
                { value: "monthly", label: "每月" },
                { value: "cron", label: "Cron 表达式" },
                { value: "interval", label: "固定间隔（分钟）" },
              ]}
            />
          </Form.Item>
          {scheduleType === "cron" && (
            <Form.Item label="Cron 表达式" required>
              <Input
                placeholder="例如: 0 8 * * * (每天早上8点)"
                value={scheduleCron}
                onChange={(e) => setScheduleCron(e.target.value)}
              />
            </Form.Item>
          )}
          {scheduleType === "interval" && (
            <Form.Item label="间隔分钟" required>
              <InputNumber
                min={1}
                max={44640}
                value={scheduleInterval}
                onChange={(v) => setScheduleInterval(v)}
                style={{ width: "100%" }}
                addonAfter="分钟"
              />
            </Form.Item>
          )}
          <Form.Item label="启用">
            <Switch checked={scheduleEnabled} onChange={setScheduleEnabled} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
