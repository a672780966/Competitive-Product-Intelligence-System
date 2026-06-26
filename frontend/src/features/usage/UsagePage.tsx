// CPIS V1 — 用量统计 / Usage Chart page (Node 10)

import { useState } from "react";
import {
  Card, Row, Col, Statistic, Typography, Spin, Tag, Space, DatePicker,
} from "antd";
import {
  CheckCircleOutlined, CloseCircleOutlined, RiseOutlined,
  DollarOutlined, FileSearchOutlined, FileTextOutlined,
  ApiOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { usageApi } from "../../api/client";
import type { UsageDailyStat } from "../../types";
import dayjs from "dayjs";

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// ── SVG-based bar chart (no external chart library needed) ───────
function SimpleLineChart({
  data,
  lines,
  height = 240,
  width = "100%",
}: {
  data: UsageDailyStat[];
  lines: { key: keyof UsageDailyStat; label: string; color: string }[];
  height?: number;
  width?: string | number;
}) {
  if (data.length === 0) {
    return <div style={{ height, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>暂无数据</div>;
  }

  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartW = typeof width === "number" ? width : 800;
  const chartH = height;
  const plotW = chartW - padding.left - padding.right;
  const plotH = chartH - padding.top - padding.bottom;

  // Find max value across all lines
  const allValues = data.flatMap((d) => lines.map((l) => Number(d[l.key]) || 0));
  const maxVal = Math.max(...allValues, 1);

  const xStep = plotW / Math.max(data.length - 1, 1);

  // Date format
  const formatDate = (d: UsageDailyStat) => {
    const date = new Date(d.stat_date);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  };

  return (
    <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: "100%", height }} preserveAspectRatio="xMidYMid meet">
      {/* Grid lines */}
      {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
        const y = padding.top + plotH * (1 - frac);
        return (
          <g key={frac}>
            <line x1={padding.left} y1={y} x2={padding.left + plotW} y2={y} stroke="#f0f0f0" strokeWidth={1} />
            <text x={padding.left - 8} y={y + 4} textAnchor="end" fill="#999" fontSize={11}>
              {Math.round(maxVal * frac)}
            </text>
          </g>
        );
      })}

      {/* Lines */}
      {lines.map((line) => {
        const points = data.map((d, i) => {
          const x = padding.left + i * xStep;
          const y = padding.top + plotH * (1 - (Number(d[line.key]) || 0) / maxVal);
          return `${x},${y}`;
        });
        const pathD = points.length > 1
          ? points.map((p, i) => `${i === 0 ? "M" : "L"}${p}`).join(" ")
          : `M${points[0]}L${points[0]}`;

        return (
          <g key={line.key}>
            <path d={pathD} fill="none" stroke={line.color} strokeWidth={2} />
            {/* Dots */}
            {data.map((d, i) => {
              const x = padding.left + i * xStep;
              const y = padding.top + plotH * (1 - (Number(d[line.key]) || 0) / maxVal);
              return <circle key={i} cx={x} cy={y} r={3} fill={line.color} />;
            })}
          </g>
        );
      })}

      {/* X-axis labels */}
      {data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 10)) === 0).map((d, i) => {
        const idx = data.indexOf(d);
        const x = padding.left + idx * xStep;
        return (
          <text key={i} x={x} y={chartH - 8} textAnchor="middle" fill="#999" fontSize={11}>
            {formatDate(d)}
          </text>
        );
      })}
    </svg>
  );
}

// ── Main Component ───────────────────────────────────────────────

export default function UsagePage() {
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([
    dayjs().subtract(30, "day"),
    dayjs(),
  ]);

  const dateFrom = dateRange[0]?.format("YYYY-MM-DD");
  const dateTo = dateRange[1]?.format("YYYY-MM-DD");

  // ── Queries ────────────────────────────────────────────────────
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["usage-summary", dateFrom, dateTo],
    queryFn: () => {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      return usageApi.summary(params.toString());
    },
  });

  const { data: dailyData, isLoading: dailyLoading } = useQuery({
    queryKey: ["usage-daily", dateFrom, dateTo],
    queryFn: () => {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      return usageApi.daily(params.toString());
    },
  });

  const dailyStats = dailyData?.items || [];
  const isLoading = summaryLoading || dailyLoading;

  // Derived values
  const successRate = summary && (summary.total_task_count > 0)
    ? ((summary.total_success_count / summary.total_task_count) * 100).toFixed(1)
    : "0.0";

  const failureRate = summary && (summary.total_task_count > 0)
    ? ((summary.total_failure_count / summary.total_task_count) * 100).toFixed(1)
    : "0.0";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, flexWrap: "wrap", gap: 12 }}>
        <Title level={4} style={{ margin: 0 }}>用量统计 / Usage</Title>
        <RangePicker
          value={[dateRange[0], dateRange[1]]}
          onChange={(dates) => {
            if (dates && dates[0] && dates[1]) {
              setDateRange([dates[0], dates[1]]);
            }
          }}
          allowClear={false}
        />
      </div>

      {isLoading ? (
        <Spin size="large" style={{ display: "block", margin: "100px auto" }} />
      ) : (
        <>
          {/* Summary Cards */}
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="总任务数"
                  value={summary?.total_task_count || 0}
                  prefix={<RiseOutlined />}
                  valueStyle={{ fontSize: 24 }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="Token 用量"
                  value={summary?.total_token_count || 0}
                  prefix={<FileSearchOutlined />}
                  valueStyle={{ fontSize: 24 }}
                  suffix={summary && summary.total_token_count > 1000000 ? "M" : summary && summary.total_token_count > 1000 ? "K" : ""}
                  precision={0}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="搜索调用"
                  value={summary?.total_search_count || 0}
                  prefix={<ApiOutlined />}
                  valueStyle={{ fontSize: 24 }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="采集页面"
                  value={summary?.total_collected_page_count || 0}
                  prefix={<FileTextOutlined />}
                  valueStyle={{ fontSize: 24 }}
                />
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="成功率"
                  value={successRate}
                  prefix={<CheckCircleOutlined style={{ color: "#52c41a" }} />}
                  suffix="%"
                  valueStyle={{ fontSize: 24, color: Number(successRate) >= 80 ? "#52c41a" : "#faad14" }}
                />
                <div style={{ marginTop: 4 }}>
                  <Space size={4}>
                    <Text style={{ fontSize: 12, color: "#52c41a" }}>
                      <CheckCircleOutlined /> {summary?.total_success_count || 0}
                    </Text>
                    <Text style={{ fontSize: 12, color: "#ff4d4f" }}>
                      <CloseCircleOutlined /> {summary?.total_failure_count || 0}
                    </Text>
                  </Space>
                </div>
              </Card>
            </Col>
            <Col xs={12} sm={8} md={6} lg={4}>
              <Card size="small" hoverable>
                <Statistic
                  title="预估费用"
                  value={summary?.total_estimated_cost || 0}
                  prefix={<DollarOutlined />}
                  suffix="$"
                  valueStyle={{ fontSize: 24 }}
                  precision={4}
                />
              </Card>
            </Col>
          </Row>

          {/* Success/Failure Rate Bar */}
          {summary && summary.total_task_count > 0 && (
            <Card size="small" style={{ marginBottom: 16 }}>
              <Space align="center" style={{ width: "100%" }}>
                <Text strong>任务成功率: </Text>
                <div style={{
                  flex: 1,
                  height: 24,
                  background: "#f0f0f0",
                  borderRadius: 12,
                  overflow: "hidden",
                  display: "flex",
                }}>
                  <div style={{
                    width: `${successRate}%`,
                    background: "linear-gradient(90deg, #52c41a, #73d13d)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 500,
                    minWidth: 40,
                    transition: "width 0.5s",
                  }}>
                    {successRate}% 成功
                  </div>
                  <div style={{
                    width: `${failureRate}%`,
                    background: "linear-gradient(90deg, #ff4d4f, #ff7875)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                    fontSize: 12,
                    fontWeight: 500,
                    minWidth: 40,
                    transition: "width 0.5s",
                  }}>
                    {failureRate}% 失败
                  </div>
                </div>
              </Space>
            </Card>
          )}

          {/* Chart */}
          <Card title="每日趋势" size="small">
            {dailyStats.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <Space>
                  <Tag color="#1677ff">任务数 (Task)</Tag>
                  <Tag color="#52c41a">Token 数</Tag>
                  <Tag color="#faad14">搜索次数</Tag>
                </Space>
              </div>
            )}
            <SimpleLineChart
              data={dailyStats}
              height={300}
              lines={[
                { key: "task_count", label: "任务数", color: "#1677ff" },
                { key: "token_count", label: "Token 数", color: "#52c41a" },
                { key: "search_count", label: "搜索次数", color: "#faad14" },
              ]}
            />
          </Card>

          {/* Daily data table */}
          <Card title="每日明细" size="small" style={{ marginTop: 16 }}>
            {dailyStats.length === 0 ? (
              <Text type="secondary">暂无数据</Text>
            ) : (
              <div style={{ maxHeight: 300, overflow: "auto" }}>
                <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#fafafa", position: "sticky", top: 0 }}>
                      <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid #f0f0f0" }}>日期</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>任务数</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>Token</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>搜索次数</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>采集页面</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>成功</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>失败</th>
                      <th style={{ padding: "8px 12px", textAlign: "right", borderBottom: "1px solid #f0f0f0" }}>费用 ($)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dailyStats.map((stat: UsageDailyStat) => (
                      <tr key={stat.id} style={{ borderBottom: "1px solid #f0f0f0" }}>
                        <td style={{ padding: "6px 12px" }}>{stat.stat_date}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right" }}>{stat.task_count}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right" }}>{stat.token_count.toLocaleString()}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right" }}>{stat.search_count}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right" }}>{stat.collected_page_count}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right", color: "#52c41a" }}>{stat.success_count}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right", color: stat.failure_count > 0 ? "#ff4d4f" : undefined }}>{stat.failure_count}</td>
                        <td style={{ padding: "6px 12px", textAlign: "right" }}>{stat.estimated_cost.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
