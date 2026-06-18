import { Button, Card, Form, Input, Segmented, Space, Typography } from "antd";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthStore } from "../stores/auth";

type Mode = "login" | "register";

export function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>("login");
  const [form] = Form.useForm();
  const { login, register, loading, error } = useAuthStore();

  const title = useMemo(
    () => (mode === "login" ? "进入合同工作台" : "创建你的合同审查空间"),
    [mode],
  );

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: 24,
      }}
    >
      <Card
        className="glass-card"
        style={{ width: "min(100%, 920px)", borderRadius: 32 }}
        styles={{ body: { padding: 36 } }}
      >
        <div
          style={{
            display: "grid",
            gap: 32,
            gridTemplateColumns: "1.1fr 0.9fr",
          }}
        >
          <div>
            <Typography.Text style={{ color: "#9a3412", fontWeight: 700 }}>
              PHASE 0 WORKSPACE
            </Typography.Text>
            <Typography.Title style={{ marginTop: 12, marginBottom: 12 }}>
              {title}
            </Typography.Title>
            <Typography.Paragraph style={{ fontSize: 16, maxWidth: 520 }}>
              这一版先把登录、上传、列表和合同详情打通。接下来每一轮迭代，我们都会在这套界面上继续长出真实的审查、报告和编辑能力。
            </Typography.Paragraph>
            <Space direction="vertical" size={18}>
              <Segmented<Mode>
                value={mode}
                onChange={(value) => setMode(value)}
                options={[
                  { label: "登录", value: "login" },
                  { label: "注册", value: "register" },
                ]}
              />
              <Form
                form={form}
                layout="vertical"
                onFinish={async (values) => {
                  if (mode === "login") {
                    await login({
                      email: values.email,
                      password: values.password,
                    });
                  } else {
                    await register({
                      email: values.email,
                      password: values.password,
                      name: values.name,
                      tenant_name: values.tenant_name,
                    });
                  }
                  navigate("/", { replace: true });
                }}
              >
                {mode === "register" ? (
                  <>
                    <Form.Item label="工作台名称" name="tenant_name" rules={[{ required: true }]}>
                      <Input placeholder="例如：法务一组" />
                    </Form.Item>
                    <Form.Item label="姓名" name="name">
                      <Input placeholder="你的名字" />
                    </Form.Item>
                  </>
                ) : null}
                <Form.Item label="邮箱" name="email" rules={[{ required: true, type: "email" }]}>
                  <Input placeholder="you@example.com" />
                </Form.Item>
                <Form.Item label="密码" name="password" rules={[{ required: true, min: 8 }]}>
                  <Input.Password placeholder="至少 8 位" />
                </Form.Item>
                {error ? (
                  <Typography.Text type="danger">{error}</Typography.Text>
                ) : null}
                <Form.Item style={{ marginTop: 20, marginBottom: 0 }}>
                  <Button type="primary" htmlType="submit" loading={loading} size="large" block>
                    {mode === "login" ? "进入工作台" : "创建并进入"}
                  </Button>
                </Form.Item>
              </Form>
            </Space>
          </div>
          <div
            style={{
              borderRadius: 28,
              padding: 28,
              background:
                "linear-gradient(145deg, rgba(154,52,18,0.94), rgba(120,53,15,0.86))",
              color: "#fff7ed",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <Typography.Text style={{ color: "#fed7aa", fontWeight: 700 }}>
                Road To MVP
              </Typography.Text>
              <Typography.Title level={3} style={{ color: "white", marginTop: 12 }}>
                先做出可用闭环，再让它长成最终产品。
              </Typography.Title>
            </div>
            <Space direction="vertical" size={14}>
              <Typography.Text style={{ color: "#ffedd5" }}>
                1. 登录与上传先跑通
              </Typography.Text>
              <Typography.Text style={{ color: "#ffedd5" }}>
                2. 列表与详情先落真数据
              </Typography.Text>
              <Typography.Text style={{ color: "#ffedd5" }}>
                3. 报告页和编辑页在这套外壳上继续演进
              </Typography.Text>
            </Space>
          </div>
        </div>
      </Card>
    </div>
  );
}
