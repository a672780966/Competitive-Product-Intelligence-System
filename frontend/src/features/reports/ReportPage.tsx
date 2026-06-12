// CPIS V1 — 竞品简报页面

import React, { useState } from "react";
import { Card, Button, Input, Typography, message, Space, Divider } from "antd";
import { FileTextOutlined, DownloadOutlined } from "@ant-design/icons";
import { useMutation } from "@tanstack/react-query";
import { reportsApi } from "../../api/client";

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

export default function ReportPage() {
  const [productId, setProductId] = useState("");
  const [compareIds, setCompareIds] = useState("");

  const singleMutation = useMutation({
    mutationFn: (id: string) => reportsApi.product(id),
    onSuccess: (md) => {
      downloadMd(md, `product-${productId}.md`);
      message.success("单产品简报已生成");
    },
    onError: (e: Error) => message.error(e.message),
  });

  const compareMutation = useMutation({
    mutationFn: (ids: string[]) => reportsApi.compare(ids),
    onSuccess: (md) => {
      downloadMd(md, "comparison-report.md");
      message.success("对比简报已生成");
    },
    onError: (e: Error) => message.error(e.message),
  });

  function downloadMd(content: string, filename: string) {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <Title level={4}>竞品简报</Title>

      <Card title="单产品简报" style={{ marginBottom: 24 }}>
        <Paragraph type="secondary">输入产品 UUID 后生成单产品分析简报。简报包含页面事实和 AI 分析两个独立章节。</Paragraph>
        <Space style={{ width: "100%" }}>
          <Input placeholder="产品 UUID" value={productId} onChange={e => setProductId(e.target.value)} style={{ width: 350 }} />
          <Button type="primary" icon={<FileTextOutlined />} onClick={() => singleMutation.mutate(productId)}
            loading={singleMutation.isPending} disabled={!productId}>生成并下载</Button>
        </Space>
      </Card>

      <Card title="多产品对比简报">
        <Paragraph type="secondary">输入多个产品 UUID，每行一个，生成对比分析简报。</Paragraph>
        <TextArea rows={4} placeholder="产品 UUID 1&#10;产品 UUID 2&#10;产品 UUID 3" value={compareIds}
          onChange={e => setCompareIds(e.target.value)} style={{ maxWidth: 400 }} />
        <div style={{ marginTop: 12 }}>
          <Button type="primary" icon={<DownloadOutlined />} onClick={() => {
            const ids = compareIds.split("\n").map(s => s.trim()).filter(Boolean);
            if (ids.length < 2) { message.warning("至少需要 2 个产品 UUID"); return; }
            compareMutation.mutate(ids);
          }} loading={compareMutation.isPending} disabled={compareIds.split("\n").filter(Boolean).length < 2}>
            生成并下载对比简报
          </Button>
        </div>
      </Card>
    </div>
  );
}
