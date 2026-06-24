import { FileSearchOutlined, LogoutOutlined } from "@ant-design/icons";
import { Avatar, Button, Layout, Space, Typography } from "antd";
import { useEffect } from "react";
import { Outlet, useNavigate } from "react-router-dom";

import { useAuthStore } from "../../stores/auth";

const { Header, Content } = Layout;

export function AppLayout() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.currentUser);
  const logout = useAuthStore((state) => state.logout);
  const hydrateCurrentUser = useAuthStore((state) => state.hydrateCurrentUser);

  useEffect(() => {
    void hydrateCurrentUser();
  }, [hydrateCurrentUser]);

  return (
    <Layout style={{ minHeight: "100vh", background: "transparent" }}>
      <Header
        style={{
          background: "transparent",
          padding: "24px 40px 0",
          height: "auto",
        }}
      >
        <div
          className="glass-card"
          style={{
            borderRadius: 28,
            padding: "18px 24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <Space size={14} style={{ cursor: "pointer" }} onClick={() => navigate("/workspace")}>
            <Avatar
              size={44}
              icon={<FileSearchOutlined />}
              style={{ background: "#9a3412" }}
            />
            <div>
              <Typography.Title level={4} style={{ margin: 0 }}>
                ContractGuard
              </Typography.Title>
              <Typography.Text type="secondary">
                工作台
              </Typography.Text>
            </div>
          </Space>
          <Space size={16}>
            <div style={{ textAlign: "right" }}>
              <Typography.Text strong>{currentUser?.name ?? currentUser?.email}</Typography.Text>
              <br />
              <Typography.Text type="secondary">{currentUser?.role ?? "member"}</Typography.Text>
            </div>
            <Button
              icon={<LogoutOutlined />}
              onClick={() => {
                logout();
                navigate("/login", { replace: true });
              }}
            >
              退出
            </Button>
          </Space>
        </div>
      </Header>
      <Content style={{ padding: "24px 40px 40px" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
