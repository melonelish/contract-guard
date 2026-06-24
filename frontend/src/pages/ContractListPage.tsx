import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudUploadOutlined,
  EyeOutlined,
  FileProtectOutlined,
  InboxOutlined,
  LoadingOutlined,
  SyncOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Empty,
  Space,
  Tag,
  Typography,
  Upload,
  message,
} from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import type { Contract } from "../api/types";
import { useContractStore } from "../stores/contract";

const { Title, Paragraph, Text } = Typography;
const RUNNING_STATUSES = ["queued", "parsing", "analyzing", "reporting", "validating"];

function statusTag(lr: Contract["latest_review"]) {
  if (!lr) return <span className="workspace-tag">未审查</span>;
  switch (lr.status) {
    case "completed":
      return <span className="workspace-tag done">完成</span>;
    case "failed":
      return <span className="workspace-tag danger">失败</span>;
    case "queued":
      return <span className="workspace-tag warn">排队中</span>;
    default:
      return <span className="workspace-tag warn">审查中 {lr.progress}%</span>;
  }
}

export function ContractListPage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [messageApi, contextHolder] = message.useMessage();
  const { items, loading, uploadLoading, fetchContracts, uploadContract } = useContractStore();

  const runningCount = useMemo(
    () => items.filter((i) => i.latest_review && RUNNING_STATUSES.includes(i.latest_review.status)).length,
    [items],
  );
  const completedCount = useMemo(
    () => items.filter((i) => i.latest_review?.status === "completed").length,
    [items],
  );

  useEffect(() => { void fetchContracts(); }, [fetchContracts]);

  useEffect(() => {
    if (runningCount === 0) return undefined;
    const t = setTimeout(() => { void fetchContracts(); }, 3000);
    return () => clearTimeout(t);
  }, [fetchContracts, runningCount, items]);

  const handleUpload = async (file: File) => {
    try {
      const contractId = await uploadContract(file, title || undefined);
      messageApi.success("上传成功，已进入合同工作台。");
      setTitle("");
      navigate(`/contracts/${contractId}`);
    } catch {
      messageApi.error("上传失败，请检查文件类型或稍后重试。");
    }
    return false;
  };

  return (
    <>
      {contextHolder}
      <style>{`
        .workspace-tag {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-height: 28px;
          padding: 0 10px;
          border-radius: 999px;
          font-size: 10px;
          font-weight: 800;
          letter-spacing: 0.08em;
          background: var(--sage-soft);
          color: var(--sage);
        }
        .workspace-tag.done { background: rgba(95,119,104,0.18); color: var(--sage); }
        .workspace-tag.warn { background: var(--accent-soft); color: var(--accent); }
        .workspace-tag.danger { background: var(--danger-soft); color: var(--danger); }
        .contract-card {
          padding: 14px 15px;
          border-radius: 18px;
          background: rgba(255,255,255,0.74);
          border: 1px solid rgba(24,36,47,0.08);
          box-shadow: var(--shadow-sm);
          cursor: pointer;
          transition: transform 180ms ease, box-shadow 180ms ease;
        }
        .contract-card:hover { transform: translateY(-1px); box-shadow: var(--shadow-md); }
        .upload-zone {
          display: grid;
          place-items: center;
          min-height: 200px;
          padding: 24px;
          border-radius: 24px;
          border: 1px dashed rgba(45,94,137,0.28);
          background:
            radial-gradient(circle at top, rgba(45,94,137,0.08), transparent 46%),
            rgba(255,255,255,0.78);
          text-align: center;
          cursor: pointer;
          transition: border-color 180ms ease;
        }
        .upload-zone:hover { border-color: var(--brand); }
        .focus-item {
          padding: 16px 18px;
          border-radius: var(--radius-lg);
          background: rgba(255,255,255,0.78);
          border: 1px solid rgba(24,36,47,0.08);
          box-shadow: var(--shadow-sm);
          position: relative;
          overflow: hidden;
        }
        .focus-item::before {
          content: "";
          position: absolute;
          left: 0; top: 14px; bottom: 14px;
          width: 4px;
          border-radius: 999px;
        }
        .focus-item.risk::before { background: var(--danger); }
        .focus-item.stage::before { background: var(--brand); }
        .focus-item.goal::before { background: var(--accent); }
      `}</style>

      <div style={{ display: "grid", gap: 18 }}>
        {/* Hero card — overview */}
        <Card
          style={{
            borderRadius: 34,
            border: "1px solid rgba(24,36,47,0.10)",
            background:
              "radial-gradient(circle at top right, rgba(45,94,137,0.12), transparent 30%), linear-gradient(180deg, rgba(255,255,255,0.92), rgba(246,241,233,0.96))",
            boxShadow: "var(--shadow-lg)",
            backdropFilter: "blur(18px)",
            padding: 26,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 20 }}>
            <div>
              <Title level={2} style={{ margin: "0 0 8px", fontFamily: "var(--font-serif)", letterSpacing: "-0.04em" }}>
                工作台
              </Title>
              <Paragraph style={{ margin: 0, maxWidth: 620, fontSize: 14, lineHeight: 1.84, color: "var(--ink-soft)" }}>
                上传合同后 AI 自动审查，结果可查看、可协作、可交付。
              </Paragraph>
            </div>
            <Button
              type="primary"
              icon={<CloudUploadOutlined />}
              loading={uploadLoading}
              onClick={() => document.getElementById("workspace-upload-input")?.click()}
              style={{ borderRadius: 999, height: 44 }}
            >
              上传新合同
            </Button>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 12 }}>
            <div className="focus-item risk">
              <span style={{ display: "block", marginBottom: 6, fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
                审查中
              </span>
              <strong style={{ display: "block", fontSize: 15, paddingLeft: 10 }}>{runningCount} 份合同</strong>
            </div>
            <div className="focus-item stage">
              <span style={{ display: "block", marginBottom: 6, fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
                已完成
              </span>
              <strong style={{ display: "block", fontSize: 15, paddingLeft: 10 }}>{completedCount} 份报告</strong>
            </div>
            <div className="focus-item goal">
              <span style={{ display: "block", marginBottom: 6, fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
                合同总数
              </span>
              <strong style={{ display: "block", fontSize: 15, paddingLeft: 10 }}>{items.length} 份</strong>
            </div>
          </div>
        </Card>

        {/* Upload zone */}
        <Card
          style={{
            borderRadius: 34,
            border: "1px solid rgba(24,36,47,0.10)",
            background: "rgba(255,255,255,0.9)",
            boxShadow: "var(--shadow-lg)",
            backdropFilter: "blur(18px)",
            padding: 22,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <Title level={4} style={{ margin: 0, fontFamily: "var(--font-serif)", letterSpacing: "-0.03em" }}>
              新建审查任务
            </Title>
            <Text style={{ fontSize: 12, color: "var(--ink-muted)" }}>支持 PDF / DOCX / 图片</Text>
          </div>
          <Upload.Dragger
            multiple={false}
            showUploadList={false}
            beforeUpload={handleUpload}
          >
            <div className="upload-zone" id="workspace-upload-zone">
              <div>
                <strong style={{ display: "block", marginBottom: 8, fontSize: 20 }}>拖拽上传合同</strong>
                <p style={{ margin: 0, fontSize: 12, lineHeight: 1.84, color: "var(--ink-soft)" }}>
                  上传后自动识别合同结构并进入审查流程。
                </p>
              </div>
            </div>
          </Upload.Dragger>
          <input id="workspace-upload-input" type="file" accept=".pdf,.docx,.png,.jpg" style={{ display: "none" }} onChange={async (e) => {
            const file = e.target.files?.[0];
            if (file) await handleUpload(file);
            e.target.value = "";
          }} />
        </Card>

        {/* Contract list */}
        <Card
          style={{
            borderRadius: 34,
            border: "1px solid rgba(24,36,47,0.10)",
            background: "rgba(255,255,255,0.9)",
            boxShadow: "var(--shadow-lg)",
            backdropFilter: "blur(18px)",
            padding: 22,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <Title level={4} style={{ margin: 0, fontFamily: "var(--font-serif)", letterSpacing: "-0.03em" }}>
              最近合同
            </Title>
            <Text style={{ fontSize: 12, color: "var(--ink-muted)" }}>{items.length} 份</Text>
          </div>

          {items.length === 0 ? (
            <Empty description="还没有合同，先从上方上传一份开始。" />
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {items.map((item) => {
                const lr = item.latest_review;
                const isCompleted = lr?.status === "completed";
                const isFailed = lr?.status === "failed";
                const isRunning = lr && RUNNING_STATUSES.includes(lr.status);
                const hint = isCompleted && lr?.summary
                  ? `高${lr.summary.high} 中${lr.summary.medium} 低${lr.summary.low}`
                  : isFailed && lr?.error_detail
                    ? (lr.error_detail.length > 40 ? lr.error_detail.slice(0, 40) + "…" : lr.error_detail)
                    : null;

                return (
                  <div
                    key={item.id}
                    className="contract-card"
                    onClick={() => navigate(`/contracts/${item.id}`)}
                    style={{
                      borderLeft: isFailed
                        ? "4px solid var(--danger)"
                        : isCompleted
                          ? "4px solid var(--sage)"
                          : isRunning
                            ? "4px solid var(--brand)"
                            : "4px solid transparent",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <strong style={{ fontSize: 14 }}>{item.title ?? "未命名合同"}</strong>
                      {statusTag(lr)}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <span style={{ fontSize: 12, color: "var(--ink-soft)" }}>
                          {item.file_type.toUpperCase()} · {item.file_size ?? 0} bytes · 上传于 {dayjs(item.created_at).format("YYYY-MM-DD HH:mm")}
                        </span>
                        {hint && (
                          <div style={{ marginTop: 4, fontSize: 12, color: isFailed ? "var(--danger)" : "var(--ink-muted)" }}>
                            {isCompleted ? `风险分布：${hint}` : hint}
                          </div>
                        )}
                      </div>
                      <Space size={8}>
                        {isCompleted && (
                          <Button
                            type="primary"
                            ghost
                            size="small"
                            icon={<FileProtectOutlined />}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/reviews/${lr!.id}`);
                            }}
                            style={{ borderRadius: 999 }}
                          >
                            查看报告
                          </Button>
                        )}
                        <Button
                          type="link"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={(e) => {
                            e.stopPropagation();
                            navigate(`/contracts/${item.id}`);
                          }}
                        >
                          详情
                        </Button>
                      </Space>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
