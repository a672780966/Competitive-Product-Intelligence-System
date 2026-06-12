import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Button, Typography } from "antd";

const { Title, Paragraph } = Typography;

function Home() {
  return (
    <div style={{ padding: 48, textAlign: "center" }}>
      <Title>CPIS V1</Title>
      <Paragraph>竞品公开信息自动采集与分析系统</Paragraph>
      <Paragraph type="secondary">
        Competitive Product Intelligence System
      </Paragraph>
      <Button type="primary" size="large" disabled>
        进入管理后台
      </Button>
      <Paragraph type="secondary" style={{ marginTop: 24 }}>
        后台管理页面将在后续节点开发
      </Paragraph>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
      </Routes>
    </BrowserRouter>
  );
}
