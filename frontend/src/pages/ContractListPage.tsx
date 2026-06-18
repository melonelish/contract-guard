import {
  CloudUploadOutlined,
  EyeOutlined,
  FileProtectOutlined,
  InboxOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  List,
  Row,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import dayjs from "dayjs";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useContractStore } from "../stores/contract";

export function ContractListPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [messageApi, contextHolder] = message.useMessage();
  const { items, loading, uploadLoading, fetchContracts, uploadContract } = useContractStore();

  useEffect(() => {
    void fetchContracts();
  }, [fetchContracts]);

  return (
    <>
      {contextHolder}
      <Row gutter={[24, 24]}>
        <Col xs={24} xl={8}>
          <Card className="glass-card" style={{ borderRadius: 28 }}>
            <Space direction="vertical" size={18} style={{ width: "100%" }}>
              <div>
                <Typography.Text style={{ color: "#9a3412", fontWeight: 700 }}>
                  CONTRACT INTAKE
                </Typography.Text>
                <Typography.Title level={3} style={{ marginTop: 8, marginBottom: 8 }}>
                  上传第一份真实合同
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
                  Phase 0 先把文件记录和工作台跑起来。下一阶段，这里上传的合同会直接进入真实审查流。
                </Typography.Paragraph>
              </div>
              <Form layout="vertical">
                <Form.Item label="合同标题（可选）">
                  <Input
                    placeholder="例如：设备采购合同"
                    value={title}
                    onChange={(event) => setTitle(event.target.value)}
                  />
                </Form.Item>
                <Upload.Dragger
                  multiple={false}
                  showUploadList={false}
                  beforeUpload={async (file) => {
                    try {
                      const contractId = await uploadContract(file, title || undefined);
                      messageApi.success("上传成功，已进入合同工作台。");
                      setTitle("");
                      navigate(`/contracts/${contractId}`);
                    } catch (_error) {
                      messageApi.error("上传失败，请检查文件类型或稍后重试。");
                    }
                    return false;
                  }}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined />
                  </p>
                  <p className="ant-upload-text">
                    拖拽 PDF / Word / 图片文件到这里，或点击上传
                  </p>
                  <p className="ant-upload-hint">
                    当前阶段支持记录上传与归档，下一阶段接入真实 Parser。
                  </p>
                </Upload.Dragger>
                <Button
                  type="primary"
                  icon={<CloudUploadOutlined />}
                  loading={uploadLoading}
                  size="large"
                  style={{ marginTop: 16, width: "100%" }}
                >
                  等待选择文件
                </Button>
              </Form>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={16}>
          <Card className="glass-card" style={{ borderRadius: 28 }}>
            <Space direction="vertical" size={18} style={{ width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <Typography.Text style={{ color: "#9a3412", fontWeight: 700 }}>
                    WORKSPACE ARCHIVE
                  </Typography.Text>
                  <Typography.Title level={3} style={{ marginTop: 8, marginBottom: 0 }}>
                    合同列表
                  </Typography.Title>
                </div>
                <Tag
                  icon={<FileProtectOutlined />}
                  color="orange"
                  style={{ paddingInline: 12, paddingBlock: 6, borderRadius: 999 }}
                >
                  已接入真实后端数据
                </Tag>
              </div>
              <List
                loading={loading}
                locale={{
                  emptyText: (
                    <Empty description="还没有合同，先从左侧上传一份开始。" />
                  ),
                }}
                dataSource={items}
                renderItem={(item) => (
                  <List.Item
                    style={{
                      borderRadius: 20,
                      padding: 20,
                      marginBottom: 12,
                      background: "rgba(255,255,255,0.66)",
                    }}
                    actions={[
                      <Button
                        key={item.id}
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => navigate(`/contracts/${item.id}`)}
                      >
                        查看
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={<Typography.Text strong>{item.title ?? "未命名合同"}</Typography.Text>}
                      description={
                        <Space direction="vertical" size={4}>
                          <Typography.Text type="secondary">
                            {item.file_type.toUpperCase()} · {item.file_size ?? 0} bytes
                          </Typography.Text>
                          <Typography.Text type="secondary">
                            上传于 {dayjs(item.created_at).format("YYYY-MM-DD HH:mm")}
                          </Typography.Text>
                        </Space>
                      }
                    />
                    <Tag color="gold">{item.status}</Tag>
                  </List.Item>
                )}
              />
            </Space>
          </Card>
        </Col>
      </Row>
    </>
  );
}
