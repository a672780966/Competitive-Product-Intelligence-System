// CPIS V1 — 采集任务列表 & 创建页面

import { useState } from "react";
import {
  Table, Button, Tag, Input, Space, Modal, Form, Select, message, Typography,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "../../api/client";
import { useNavigate } from "react-router-dom";
import type { TaskResponse } from "../../types";

const { TextArea } = Input;
const { Title } = Typography;

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

export default function TaskListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [keyword, setKeyword] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [batchOpen, setBatchOpen] = useState(false);
  const [createUrl, setCreateUrl] = useState("");
  const [batchText, setBatchText] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["tasks", page, statusFilter, keyword],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      if (statusFilter) params.set("status", statusFilter);
      if (keyword) params.set("keyword", keyword);
      return tasksApi.list(params.toString());
    },
  });

  const createMutation = useMutation({
    mutationFn: (url: string) => tasksApi.create({ source_url: url }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tasks"] }); message.success("任务已创建"); },
    onError: (e: Error) => message.error(e.message),
  });

  const batchMutation = useMutation({
    mutationFn: (urls: string[]) => tasksApi.batchCreate(urls.map(u => ({ source_url: u }))),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tasks"] }); message.success("批量创建完成"); },
    onError: (e: Error) => message.error(e.message),
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => tasksApi.retry(id),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["tasks"] }); message.success("已重试"); },
    onError: (e: Error) => message.error(e.message),
  });

  const columns = [
    { title: "URL", dataIndex: "source_url", key: "url", ellipsis: true, width: 300,
      render: (v: string, r: TaskResponse) => <a onClick={() => navigate(`/tasks/${r.id}`)}>{v}</a> },
    { title: "状态", dataIndex: "status", key: "status", width: 100,
      render: (v: string) => <Tag color={statusColors[v] || "default"}>{statusLabels[v] || v}</Tag> },
    { title: "域名", dataIndex: "domain", key: "domain", width: 150 },
    { title: "优先级", dataIndex: "priority", key: "priority", width: 80 },
    { title: "重试", dataIndex: "retry_count", key: "retry", width: 60 },
    { title: "错误", dataIndex: "error_message", key: "error", ellipsis: true, width: 200 },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", width: 180,
      render: (v: string) => new Date(v).toLocaleString("zh-CN") },
    { title: "操作", key: "actions", width: 120,
      render: (_: unknown, r: TaskResponse) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/tasks/${r.id}`)}>详情</Button>
          {["failed", "blocked"].includes(r.status) &&
            <Button size="small" onClick={() => retryMutation.mutate(r.id)} loading={retryMutation.isPending}>重试</Button>}
        </Space>
      ) },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>采集任务</Title>
        <Space>
          <Input.Search placeholder="搜索URL关键词" allowClear onSearch={setKeyword} style={{ width: 250 }} />
          <Select
            placeholder="状态筛选" allowClear style={{ width: 130 }}
            onChange={v => setStatusFilter(v || undefined)}
            options={Object.entries(statusLabels).map(([k, v]) => ({ value: k, label: v }))}
          />
          <Button icon={<PlusOutlined />} type="primary" onClick={() => setCreateOpen(true)}>创建任务</Button>
          <Button onClick={() => setBatchOpen(true)}>批量创建</Button>
        </Space>
      </div>

      <Table
        dataSource={data?.items} columns={columns} rowKey="id" loading={isLoading}
        pagination={{ current: page, total: data?.total, pageSize: 20, onChange: setPage }}
        size="middle"
      />

      {/* Single create modal */}
      <Modal title="创建采集任务" open={createOpen} onCancel={() => setCreateOpen(false)}
        onOk={() => { createMutation.mutate(createUrl); setCreateOpen(false); setCreateUrl(""); }}
        confirmLoading={createMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="采集链接" required>
            <Input placeholder="https://example.com/product" value={createUrl} onChange={e => setCreateUrl(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Batch create modal */}
      <Modal title="批量创建" open={batchOpen} onCancel={() => setBatchOpen(false)}
        onOk={() => {
          const urls = batchText.split("\n").map(s => s.trim()).filter(Boolean);
          batchMutation.mutate(urls);
          setBatchOpen(false); setBatchText("");
        }}
        confirmLoading={batchMutation.isPending}
      >
        <Form layout="vertical">
          <Form.Item label="每行一个链接" required>
            <TextArea rows={6} placeholder="https://example.com/p1&#10;https://example.com/p2" value={batchText} onChange={e => setBatchText(e.target.value)} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
