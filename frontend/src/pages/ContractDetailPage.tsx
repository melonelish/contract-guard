import { ArrowLeftOutlined, FileSearchOutlined, HourglassOutlined } from "@ant-design/icons";
import { Button, Card, Descriptions, Skeleton, Space, Tag, Typography } from "antd";
import dayjs from "dayjs";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useContractStore } from "../stores/contract";

export function ContractDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { selected, loading, fetchContractDetail } = useContractStore();

  useEffect(() => {
    if (id) {
      void fetchContractDetail(id);
    }
  }, [fetchContractDetail, id]);

  return (
    <Card className="glass-card" style={{ borderRadius: 28 }}>
      <Space direction="vertical" size={20} style={{ width: "100%" }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/")}>
          返回工作台
        </Button>
        {loading || !selected ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
              <div>
                <Typography.Text style={{ color: "#9a3412", fontWeight: 700 }}>
                  CONTRACT DETAIL
                </Typography.Text>
                <Typography.Title level={2} style={{ marginTop: 8, marginBottom: 8 }}>
                  {selected.title ?? "未命名合同"}
                </Typography.Title>
                <Typography.Paragraph type="secondary" style={{ maxWidth: 760 }}>
                  这一页是后续审查报告页的落点。Phase 0 先展示真实元信息与状态，下一阶段这里会继续接入条款解析结果和审查进度。
                </Typography.Paragraph>
              </div>
              <Space direction="vertical" align="end" size={12}>
                <Tag color="gold" style={{ fontSize: 14, padding: "6px 12px", borderRadius: 999 }}>
                  {selected.status}
                </Tag>
                <Tag icon={<HourglassOutlined />} color="processing" style={{ borderRadius: 999 }}>
                  待接入真实审查
                </Tag>
              </Space>
            </div>
            <Descriptions
              bordered
              column={2}
              styles={{
                label: { width: 180, fontWeight: 700 },
              }}
            >
              <Descriptions.Item label="合同 ID">{selected.id}</Descriptions.Item>
              <Descriptions.Item label="所属租户">{selected.tenant_id}</Descriptions.Item>
              <Descriptions.Item label="文件类型">{selected.file_type.toUpperCase()}</Descriptions.Item>
              <Descriptions.Item label="文件大小">{selected.file_size ?? 0} bytes</Descriptions.Item>
              <Descriptions.Item label="上传时间">
                {dayjs(selected.created_at).format("YYYY-MM-DD HH:mm")}
              </Descriptions.Item>
              <Descriptions.Item label="最近更新时间">
                {selected.updated_at ? dayjs(selected.updated_at).format("YYYY-MM-DD HH:mm") : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="文件地址" span={2}>
                {selected.file_url}
              </Descriptions.Item>
            </Descriptions>
            <Card
              style={{
                borderRadius: 24,
                background: "linear-gradient(180deg, #fff7ed 0%, #fffbf5 100%)",
              }}
            >
              <Space direction="vertical" size={12}>
                <Space>
                  <FileSearchOutlined style={{ color: "#9a3412" }} />
                  <Typography.Text strong>下一阶段将在这里接入：</Typography.Text>
                </Space>
                <Typography.Text>1. 条款解析结构</Typography.Text>
                <Typography.Text>2. 审查进度与阶段状态</Typography.Text>
                <Typography.Text>3. 报告页与原文定位联动</Typography.Text>
              </Space>
            </Card>
          </>
        )}
      </Space>
    </Card>
  );
}
