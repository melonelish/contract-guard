import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  Descriptions,
  Divider,
  Empty,
  Row,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import dayjs from "dayjs";
import { useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";

import type {
  ReviewContradiction,
  ReviewMissingClause,
  ReviewReport,
  ReviewRiskItem,
} from "../api/types";
import { useReviewStore } from "../stores/review";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function riskLevelTag(level: string) {
  switch (level) {
    case "high":
      return (
        <Tag color="error" icon={<ExclamationCircleOutlined />}>
          高风险
        </Tag>
      );
    case "medium":
      return (
        <Tag color="warning" icon={<WarningOutlined />}>
          中风险
        </Tag>
      );
    case "low":
      return (
        <Tag color="success" icon={<InfoCircleOutlined />}>
          低风险
        </Tag>
      );
    default:
      return <Tag>{level}</Tag>;
  }
}

function severityOrder(level: string): number {
  switch (level) {
    case "high":
      return 0;
    case "medium":
      return 1;
    default:
      return 2;
  }
}

function formatDuration(
  startedAt: string | null,
  completedAt: string | null,
): string | null {
  if (!startedAt || !completedAt) return null;
  const ms = dayjs(completedAt).diff(dayjs(startedAt));
  if (ms < 0) return null;
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${Math.round(ms / 1000)} 秒`;
  return `${Math.round(ms / 60000)} 分钟`;
}

// ---------------------------------------------------------------------------
// Risk Card
// ---------------------------------------------------------------------------

function RiskCard({ risk }: { risk: ReviewRiskItem }) {
  const borderColor =
    risk.risk_level === "high"
      ? "#ef4444"
      : risk.risk_level === "medium"
        ? "#f59e0b"
        : "#22c55e";
  const hasBasis =
    risk.legal_basis &&
    risk.legal_basis !== "依据不足，基于法理分析" &&
    risk.basis_source;

  return (
    <Card
      size="small"
      style={{
        borderRadius: 12,
        borderLeft: `4px solid ${borderColor}`,
        marginBottom: 16,
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
      }}
    >
      <Space direction="vertical" size={12} style={{ width: "100%" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8,
          }}
        >
          <Space size={8}>
            <Typography.Text strong style={{ fontSize: 15 }}>
              {risk.risk_category}
            </Typography.Text>
            {risk.clause_code &&
              risk.clause_code !== risk.risk_category && (
                <Typography.Text type="secondary" style={{ fontSize: 13 }}>
                  ({risk.clause_code})
                </Typography.Text>
              )}
            {riskLevelTag(risk.risk_level)}
          </Space>
          <Tooltip title="AI 置信度">
            <Tag style={{ borderRadius: 999 }}>
              置信度 {Math.round(risk.confidence * 100)}%
            </Tag>
          </Tooltip>
        </div>

        {/* Original text */}
        {risk.original_text && (
          <div
            style={{
              background: "#f8fafc",
              borderLeft: "3px solid #cbd5e1",
              borderRadius: "0 8px 8px 0",
              padding: "10px 14px",
            }}
          >
            <Typography.Text
              type="secondary"
              style={{ fontSize: 13, fontStyle: "italic" }}
            >
              {risk.original_text}
            </Typography.Text>
          </div>
        )}

        {/* Analysis */}
        <div>
          <Typography.Text
            strong
            style={{
              fontSize: 13,
              color: "#334155",
              display: "block",
              marginBottom: 4,
            }}
          >
            问题分析
          </Typography.Text>
          <Typography.Paragraph
            style={{ marginBottom: 0, fontSize: 13, lineHeight: 1.7 }}
          >
            {risk.legal_analysis}
          </Typography.Paragraph>
        </div>

        {/* Suggested revision */}
        <div
          style={{
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: 10,
            padding: "10px 14px",
          }}
        >
          <Typography.Text
            strong
            style={{
              fontSize: 13,
              color: "#166534",
              display: "block",
              marginBottom: 4,
            }}
          >
            修改建议
          </Typography.Text>
          <Typography.Paragraph
            style={{ marginBottom: 0, fontSize: 13, lineHeight: 1.7 }}
          >
            {risk.suggested_revision}
          </Typography.Paragraph>
        </div>

        {/* Legal basis */}
        <Card
          size="small"
          style={{
            background: hasBasis ? "#f0f9ff" : "#fffbeb",
            borderRadius: 10,
            border: hasBasis ? "1px solid #bae6fd" : "1px solid #fde68a",
          }}
        >
          <Space direction="vertical" size={4} style={{ width: "100%" }}>
            <Space>
              <SafetyCertificateOutlined
                style={{ color: hasBasis ? "#0284c7" : "#d97706" }}
              />
              <Typography.Text
                strong
                style={{
                  fontSize: 13,
                  color: hasBasis ? "#0284c7" : "#d97706",
                }}
              >
                法条依据
              </Typography.Text>
            </Space>
            <Typography.Text style={{ fontSize: 13 }}>
              {risk.legal_basis || "依据不足，基于法理分析"}
            </Typography.Text>
            {risk.basis_excerpt && (
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                条文摘录: {risk.basis_excerpt}
              </Typography.Text>
            )}
            {risk.basis_source && (
              <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                来源: {risk.basis_source}
              </Typography.Text>
            )}
          </Space>
        </Card>

        {/* Plain explanation */}
        {risk.plain_explanation && (
          <Typography.Text
            type="secondary"
            style={{ fontSize: 12, display: "block" }}
          >
            通俗解释: {risk.plain_explanation}
          </Typography.Text>
        )}
      </Space>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Contradiction Card
// ---------------------------------------------------------------------------

function ContradictionCard({
  c,
  index,
}: {
  c: ReviewContradiction;
  index: number;
}) {
  return (
    <Card
      size="small"
      style={{
        borderRadius: 10,
        borderLeft: "4px solid #f59e0b",
        marginBottom: 12,
      }}
    >
      <Space direction="vertical" size={6} style={{ width: "100%" }}>
        <Space>
          <Tag color="warning" style={{ borderRadius: 999 }}>
            矛盾 #{index + 1}
          </Tag>
          <Typography.Text strong style={{ fontSize: 13 }}>
            {c.clause_a}{" "}
            <SwapOutlined style={{ margin: "0 4px", color: "#94a3b8" }} />{" "}
            {c.clause_b}
          </Typography.Text>
          <Tag style={{ borderRadius: 999 }}>{c.conflict_type}</Tag>
        </Space>
        <Typography.Paragraph style={{ marginBottom: 0, fontSize: 13 }}>
          {c.description}
        </Typography.Paragraph>
      </Space>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Missing Clause Card
// ---------------------------------------------------------------------------

function MissingClauseCard({ m }: { m: ReviewMissingClause }) {
  return (
    <Card
      size="small"
      style={{
        borderRadius: 10,
        borderLeft: "4px solid #8b5cf6",
        marginBottom: 12,
      }}
    >
      <Space direction="vertical" size={4} style={{ width: "100%" }}>
        <Typography.Text strong style={{ fontSize: 14 }}>
          {m.name}
        </Typography.Text>
        <Typography.Text type="secondary" style={{ fontSize: 13 }}>
          {m.reason}
        </Typography.Text>
      </Space>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Risk Section — grouped by severity
// ---------------------------------------------------------------------------

function RiskSection({
  level,
  label,
  color,
  risks,
  defaultOpen,
}: {
  level: string;
  label: string;
  color: string;
  risks: ReviewRiskItem[];
  defaultOpen: boolean;
}) {
  if (risks.length === 0) return null;

  return (
    <div style={{ marginBottom: 24 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 12,
        }}
      >
        <div
          style={{
            width: 4,
            height: 20,
            borderRadius: 2,
            background: color,
          }}
        />
        <Typography.Text strong style={{ fontSize: 15, color }}>
          {label}
        </Typography.Text>
        <Tag
          color={
            level === "high" ? "error" : level === "medium" ? "warning" : "success"
          }
          style={{ borderRadius: 999 }}
        >
          {risks.length} 项
        </Tag>
      </div>
      {defaultOpen ? (
        risks.map((risk, idx) => (
          <RiskCard key={`${risk.clause_id}-${idx}`} risk={risk} />
        ))
      ) : (
        <Collapse
          defaultActiveKey={[]}
          items={[
            {
              key: "1",
              label: `展开查看 ${risks.length} 项${label}`,
              children: risks.map((risk, idx) => (
                <RiskCard key={`${risk.clause_id}-${idx}`} risk={risk} />
              )),
            },
          ]}
          style={{ borderRadius: 10 }}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading state component
// ---------------------------------------------------------------------------

function LoadingState() {
  return (
    <Card className="glass-card" style={{ borderRadius: 28 }}>
      <Skeleton active paragraph={{ rows: 12 }} />
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Error state component
// ---------------------------------------------------------------------------

function ErrorState({
  message,
  onRetry,
  onBack,
}: {
  message: string;
  onRetry: () => void;
  onBack: () => void;
}) {
  return (
    <Card className="glass-card" style={{ borderRadius: 28 }}>
      <Space direction="vertical" size={16} style={{ width: "100%", textAlign: "center" }}>
        <ExclamationCircleOutlined style={{ fontSize: 40, color: "#ef4444" }} />
        <Typography.Title level={4} style={{ margin: 0 }}>
          报告加载失败
        </Typography.Title>
        <Typography.Text type="secondary">{message}</Typography.Text>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
            返回合同列表
          </Button>
          <Button type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
            重新加载
          </Button>
        </Space>
      </Space>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export function ReviewReportPage() {
  const navigate = useNavigate();
  const { id } = useParams();
  const { current: reportData, loading, loadError, fetchReport, clear } = useReviewStore();

  // Clear store on mount to prevent cross-contamination, fetch report for current review
  useEffect(() => {
    if (id) {
      clear(); // Clear first to avoid showing old report
      void fetchReport(id);
    }
  }, [fetchReport, clear, id]);

  // Validate report belongs to current review ID before using it
  const report = useMemo(() => {
    if (!reportData) return null;
    // Only use report if it matches the current review ID from URL
    if (reportData.id !== id) return null;
    return reportData as ReviewReport;
  }, [reportData, id]);

  const { highRisks, mediumRisks, lowRisks } = useMemo(() => {
    if (!report) {
      return { highRisks: [], mediumRisks: [], lowRisks: [] };
    }
    const sorted = [...report.risks].sort(
      (a, b) => severityOrder(a.risk_level) - severityOrder(b.risk_level),
    );
    return {
      highRisks: sorted.filter((r) => r.risk_level === "high"),
      mediumRisks: sorted.filter((r) => r.risk_level === "medium"),
      lowRisks: sorted.filter((r) => r.risk_level === "low"),
    };
  }, [report]);

  const summary = report?.summary ?? null;
  const isFailed = report?.status === "failed";
  const durationText = report
    ? formatDuration(report.started_at, report.completed_at)
    : null;
  const contradictionCount = report?.contradictions.length ?? 0;
  const missingCount = report?.missing_clauses.length ?? 0;

  // Conditional returns AFTER all hooks
  if (loading && !report) {
    return <LoadingState />;
  }

  if (loadError && !report) {
    return (
      <ErrorState
        message={loadError}
        onRetry={() => id && void fetchReport(id)}
        onBack={() => navigate("/workspace")}
      />
    );
  }

  if (!report) {
    return (
      <ErrorState
        message="未找到审查报告数据"
        onRetry={() => id && void fetchReport(id)}
        onBack={() => navigate("/workspace")}
      />
    );
  }

  return (
    <Space direction="vertical" size={20} style={{ width: "100%" }}>
      {/* 1. Report Header */}
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        <Space direction="vertical" size={16} style={{ width: "100%" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
            }}
          >
            <Space direction="vertical" size={8}>
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={() => navigate(`/contracts/${report.contract_id}`)}
              >
                返回合同详情
              </Button>
              <Typography.Text style={{ color: "#9a3412", fontWeight: 700 }}>
                REVIEW REPORT
              </Typography.Text>
              <Typography.Title
                level={2}
                style={{ marginTop: 0, marginBottom: 0 }}
              >
                {report.contract_title ?? "审查报告"}
              </Typography.Title>
            </Space>
            <Space direction="vertical" align="end" size={8}>
              <Tag
                color={isFailed ? "error" : "success"}
                icon={
                  isFailed ? (
                    <ExclamationCircleOutlined />
                  ) : (
                    <CheckCircleOutlined />
                  )
                }
                style={{ fontSize: 14, padding: "6px 14px", borderRadius: 999 }}
              >
                {isFailed ? "审查失败" : "审查完成"}
              </Tag>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                schema v{report.schema_version}
              </Typography.Text>
            </Space>
          </div>

          <Descriptions column={4} size="small" bordered>
            <Descriptions.Item label="审查 ID">
              <Typography.Text copyable style={{ fontSize: 12 }}>
                {report.id}
              </Typography.Text>
            </Descriptions.Item>
            <Descriptions.Item label="发起时间">
              {dayjs(report.created_at).format("YYYY-MM-DD HH:mm")}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {report.completed_at
                ? dayjs(report.completed_at).format("YYYY-MM-DD HH:mm")
                : "-"}
            </Descriptions.Item>
            <Descriptions.Item label="耗时">
              {durationText ?? "-"}
            </Descriptions.Item>
          </Descriptions>
        </Space>
      </Card>

      {/* 2. Failed state */}
      {isFailed && (
        <Card
          style={{
            borderRadius: 20,
            background: "linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%)",
            border: "1px solid #fecaca",
          }}
        >
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Space>
              <ExclamationCircleOutlined
                style={{ fontSize: 20, color: "#dc2626" }}
              />
              <Typography.Text strong style={{ fontSize: 16, color: "#991b1b" }}>
                审查未能完成
              </Typography.Text>
            </Space>
            {report.error_detail && (
              <Alert
                type="error"
                showIcon={false}
                description={report.error_detail}
                style={{
                  borderRadius: 10,
                  background: "#fff",
                  border: "none",
                }}
              />
            )}
            <Typography.Text type="secondary" style={{ fontSize: 13 }}>
              系统在审查过程中遇到错误，您可以返回合同详情页重新发起审查。
            </Typography.Text>
            <Button
              type="primary"
              onClick={() => navigate(`/contracts/${report.contract_id}`)}
            >
              返回合同详情
            </Button>
          </Space>
        </Card>
      )}

      {/* 3. Executive Summary */}
      {summary && summary.total_risks > 0 && (
        <Card className="glass-card" style={{ borderRadius: 28 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 20,
            }}
          >
            <Typography.Title
              level={4}
              style={{ marginTop: 0, marginBottom: 0 }}
            >
              <FileTextOutlined style={{ marginRight: 8, color: "#9a3412" }} />
              审查概览
            </Typography.Title>
            <Tag
              color={
                summary.high > 0
                  ? "error"
                  : summary.medium > 0
                    ? "warning"
                    : "success"
              }
              style={{ borderRadius: 999, fontSize: 13, padding: "2px 12px" }}
            >
              {summary.high > 0
                ? "存在高风险"
                : summary.medium > 0
                  ? "存在中风险"
                  : "风险较低"}
            </Tag>
          </div>

          <Row gutter={[16, 16]}>
            <Col span={6}>
              <Card
                style={{
                  borderRadius: 14,
                  textAlign: "center",
                  borderTop: "3px solid #9a3412",
                }}
              >
                <Statistic
                  title="风险总数"
                  value={summary.total_risks}
                  valueStyle={{ color: "#1e293b", fontSize: 28 }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card
                style={{
                  borderRadius: 14,
                  textAlign: "center",
                  background: summary.high > 0 ? "#fef2f2" : "#f8fafc",
                  borderTop: `3px solid ${summary.high > 0 ? "#ef4444" : "#e2e8f0"}`,
                }}
              >
                <Statistic
                  title="高风险"
                  value={summary.high}
                  valueStyle={{
                    color: summary.high > 0 ? "#ef4444" : "#94a3b8",
                    fontSize: 28,
                  }}
                  prefix={<ExclamationCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card
                style={{
                  borderRadius: 14,
                  textAlign: "center",
                  background: summary.medium > 0 ? "#fffbeb" : "#f8fafc",
                  borderTop: `3px solid ${summary.medium > 0 ? "#f59e0b" : "#e2e8f0"}`,
                }}
              >
                <Statistic
                  title="中风险"
                  value={summary.medium}
                  valueStyle={{
                    color: summary.medium > 0 ? "#f59e0b" : "#94a3b8",
                    fontSize: 28,
                  }}
                  prefix={<WarningOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card
                style={{
                  borderRadius: 14,
                  textAlign: "center",
                  background: "#f8fafc",
                  borderTop: "3px solid #e2e8f0",
                }}
              >
                <Statistic
                  title="低风险"
                  value={summary.low}
                  valueStyle={{ color: "#94a3b8", fontSize: 28 }}
                  prefix={<InfoCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>

          <Divider style={{ margin: "20px 0 12px" }} />
          <div style={{ display: "flex", gap: 24 }}>
            <Space>
              <SwapOutlined
                style={{
                  color: contradictionCount > 0 ? "#f59e0b" : "#94a3b8",
                }}
              />
              <Typography.Text
                type={contradictionCount > 0 ? undefined : "secondary"}
              >
                条款矛盾: <strong>{contradictionCount}</strong> 项
              </Typography.Text>
            </Space>
            <Space>
              <InfoCircleOutlined
                style={{ color: missingCount > 0 ? "#8b5cf6" : "#94a3b8" }}
              />
              <Typography.Text
                type={missingCount > 0 ? undefined : "secondary"}
              >
                缺失条款: <strong>{missingCount}</strong> 项
              </Typography.Text>
            </Space>
            {durationText && (
              <Space>
                <ClockCircleOutlined style={{ color: "#94a3b8" }} />
                <Typography.Text type="secondary">
                  审查耗时: {durationText}
                </Typography.Text>
              </Space>
            )}
          </div>
        </Card>
      )}

      {/* 4. Risk Distribution Bar */}
      {summary && summary.total_risks > 0 && (
        <Card
          className="glass-card"
          style={{ borderRadius: 20, padding: "12px 0" }}
        >
          <div style={{ padding: "0 24px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                marginBottom: 6,
              }}
            >
              <Typography.Text strong style={{ fontSize: 13 }}>
                风险分布
              </Typography.Text>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                高 {summary.high} · 中 {summary.medium} · 低 {summary.low}
              </Typography.Text>
            </div>
            <div
              style={{
                display: "flex",
                height: 10,
                borderRadius: 5,
                overflow: "hidden",
                background: "#f1f5f9",
              }}
            >
              {summary.high > 0 && (
                <div
                  style={{
                    width: `${(summary.high / summary.total_risks) * 100}%`,
                    background: "#ef4444",
                  }}
                />
              )}
              {summary.medium > 0 && (
                <div
                  style={{
                    width: `${(summary.medium / summary.total_risks) * 100}%`,
                    background: "#f59e0b",
                  }}
                />
              )}
              {summary.low > 0 && (
                <div
                  style={{
                    width: `${(summary.low / summary.total_risks) * 100}%`,
                    background: "#22c55e",
                  }}
                />
              )}
            </div>
          </div>
        </Card>
      )}

      {/* 5. RAG metadata */}
      {report.rag_meta && (
        <Card className="glass-card" style={{ borderRadius: 20 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <Space>
              <SafetyCertificateOutlined
                style={{
                  color: report.rag_meta.enabled ? "#22c55e" : "#f59e0b",
                }}
              />
              <Typography.Text strong>
                审查模式:{" "}
                {report.rag_meta.enabled ? "RAG 增强审查" : "模型直审"}
              </Typography.Text>
            </Space>
            <Space>
              {report.rag_meta.enabled && (
                <Tag color="success" style={{ borderRadius: 999 }}>
                  命中依据 {report.rag_meta.hit_count} 条
                </Tag>
              )}
              <Tag style={{ borderRadius: 999 }}>
                {report.rag_meta.mode === "rag_enhanced"
                  ? "带法条依据"
                  : "纯模型分析"}
              </Tag>
            </Space>
          </div>
        </Card>
      )}

      {/* 6. Risks — grouped by severity */}
      {!isFailed && (
        <Card className="glass-card" style={{ borderRadius: 28 }}>
          <Typography.Title
            level={4}
            style={{ marginTop: 0, marginBottom: 20 }}
          >
            <ExclamationCircleOutlined
              style={{ marginRight: 8, color: "#9a3412" }}
            />
            风险清单
          </Typography.Title>

          {report.risks.length === 0 ? (
            <Empty description="未检测到风险" />
          ) : (
            <>
              <RiskSection
                level="high"
                label="高风险"
                color="#ef4444"
                risks={highRisks}
                defaultOpen={true}
              />
              <RiskSection
                level="medium"
                label="中风险"
                color="#f59e0b"
                risks={mediumRisks}
                defaultOpen={highRisks.length === 0}
              />
              <RiskSection
                level="low"
                label="低风险"
                color="#22c55e"
                risks={lowRisks}
                defaultOpen={false}
              />
            </>
          )}
        </Card>
      )}

      {/* 7. Contradictions */}
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <Typography.Title
            level={4}
            style={{ marginTop: 0, marginBottom: 0 }}
          >
            <WarningOutlined style={{ marginRight: 8, color: "#f59e0b" }} />
            条款矛盾
          </Typography.Title>
          {contradictionCount > 0 && (
            <Tag color="warning" style={{ borderRadius: 999 }}>
              {contradictionCount} 项
            </Tag>
          )}
        </div>
        {contradictionCount === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未检测到条款矛盾"
            style={{ padding: "24px 0" }}
          />
        ) : (
          report.contradictions.map((c, idx) => (
            <ContradictionCard key={idx} c={c} index={idx} />
          ))
        )}
      </Card>

      {/* 8. Missing Clauses */}
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 16,
          }}
        >
          <Typography.Title
            level={4}
            style={{ marginTop: 0, marginBottom: 0 }}
          >
            <InfoCircleOutlined style={{ marginRight: 8, color: "#8b5cf6" }} />
            缺失条款
          </Typography.Title>
          {missingCount > 0 && (
            <Tag color="purple" style={{ borderRadius: 999 }}>
              {missingCount} 项
            </Tag>
          )}
        </div>
        {missingCount === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="未检测到缺失条款"
            style={{ padding: "24px 0" }}
          />
        ) : (
          report.missing_clauses.map((m, idx) => (
            <MissingClauseCard key={idx} m={m} />
          ))
        )}
      </Card>

      {/* 9. LLM Meta */}
      {report.llm_meta && (
        <Card className="glass-card" style={{ borderRadius: 20 }}>
          <Typography.Title level={5} style={{ marginTop: 0, marginBottom: 12 }}>
            审查信息
          </Typography.Title>
          <Descriptions column={4} size="small">
            <Descriptions.Item label="模型">
              {report.llm_meta.provider_model}
            </Descriptions.Item>
            <Descriptions.Item label="输入 Token">
              {report.llm_meta.prompt_tokens.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="输出 Token">
              {report.llm_meta.completion_tokens.toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="模型耗时">
              {(report.llm_meta.latency_ms / 1000).toFixed(1)} 秒
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {/* 10. Disclaimer */}
      {report.disclaimer && (
        <Card
          style={{
            borderRadius: 20,
            background: "#fffbeb",
            border: "1px solid #fde68a",
          }}
        >
          <Typography.Paragraph
            style={{
              whiteSpace: "pre-line",
              margin: 0,
              fontSize: 13,
              lineHeight: 1.8,
            }}
          >
            {report.disclaimer}
          </Typography.Paragraph>
        </Card>
      )}
    </Space>
  );
}
