// CPIS V1 — Admin layout with sidebar navigation

import { Layout, Menu, Typography } from "antd";
import {
  LinkOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation, Outlet } from "react-router-dom";

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const menuItems = [
  { key: "/tasks", icon: <LinkOutlined />, label: "采集任务" },
  { key: "/products", icon: <DatabaseOutlined />, label: "产品信息库" },
  { key: "/reviews", icon: <CheckCircleOutlined />, label: "待复核" },
  { key: "/sync", icon: <SyncOutlined />, label: "同步记录" },
  { key: "/reports", icon: <FileTextOutlined />, label: "竞品简报" },
];

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const selectedKey = "/" + location.pathname.split("/")[1];

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider collapsible theme="dark">
        <div style={{ padding: "16px 24px", color: "#fff" }}>
          <Title level={4} style={{ color: "#fff", margin: 0 }}>CPIS V1</Title>
          <span style={{ fontSize: 12, opacity: 0.6 }}>竞品情报采集系统</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: "#fff", padding: "0 24px", borderBottom: "1px solid #f0f0f0" }}>
          <span style={{ fontSize: 16, fontWeight: 500 }}>管理后台</span>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: "#fff", borderRadius: 8, minHeight: 360 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
