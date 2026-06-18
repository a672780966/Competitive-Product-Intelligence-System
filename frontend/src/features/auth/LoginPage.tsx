// CPIS V1 — Login page

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Card, Form, Input, Button, Typography, Alert, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { login, setToken } from "../../api/auth";

const { Title } = Typography;

export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (data) => {
      setToken(data.access_token);
      message.success("登录成功");
      navigate("/tasks", { replace: true });
    },
    onError: (err: Error) => {
      setError(err.message || "登录失败，请检查用户名和密码");
    },
  });

  const onFinish = (values: { username: string; password: string }) => {
    setError(null);
    mutation.mutate(values);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 400, boxShadow: "0 2px 8px rgba(0,0,0,0.09)" }}>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Title level={3}>CPIS V1</Title>
          <span style={{ color: "#666" }}>竞品情报采集系统</span>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 16 }}
            closable
            onClose={() => setError(null)}
          />
        )}

        <Form onFinish={onFinish} layout="vertical" size="large">
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: "请输入用户名" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: "请输入密码" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={mutation.isPending}
              block
            >
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
