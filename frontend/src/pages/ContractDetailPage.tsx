import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  LoadingOutlined,
  PlayCircleOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
  SwapOutlined,
  WarningOutlined,
  WifiOutlined,
} from "@ant-design/icons";
import {
  Button,
  Card,
  Collapse,
  Descriptions,
  Empty,
  Progress,
  Skeleton,
  Space,
  Tag,
  Typography,
  message,
} from "antd";
import dayjs from "dayjs";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  lazy,
  Suspense,
  startTransition,
} from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import type {
  Review,
  ReviewReport,
  WSCompleteEvent,
  WSFailedEvent,
  WSStageEvent,
} from "../api/types";
import { useContractStore } from "../stores/contract";
import { useReviewStore } from "../stores/review";

// Lazy load EditMode to reduce initial bundle size
const EditMode = lazy(() => import("../components/Editor/EditMode").then(m => ({ default: m.EditMode })));

const { Title, Paragraph, Text } = Typography;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const RUNNING_STATUSES = [
  "queued",
  "parsing",
  "analyzing",
  "reporting",
  "validating",
];

const STAGE_LABELS: Record<string, string> = {
  queued: "排队中",
  parsing: "文档解析",
  analyzing: "条款分析",
  reporting: "报告生成",
  validating: "校验中",
  completed: "审查完成",
  failed: "审查失败",
};

const STAGE_DETAIL: Record<string, string> = {
  queued: "等待 Worker 拾取任务",
  parsing: "正在提取合同文本与条款结构",
  analyzing: "正在逐条分析法律风险，耗时较长属正常",
  reporting: "正在生成结构化审查报告",
  validating: "正在校验报告格式与法条引用",
};

// ---------------------------------------------------------------------------
// Risk level helpers
// ---------------------------------------------------------------------------

function riskLevelColor(level: string): string {
  if (level === "high") return "var(--danger)";
  if (level === "medium") return "var(--accent)";
  return "var(--brand)";
}

function riskLevelBg(level: string): string {
  if (level === "high") return "var(--danger-soft)";
  if (level === "medium") return "var(--accent-soft)";
  return "var(--brand-soft)";
}

function riskLevelLabel(level: string): string {
  if (level === "high") return "高风险";
  if (level === "medium") return "中风险";
  return "低风险";
}

function severityOrder(level: string): number {
  if (level === "high") return 0;
  if (level === "medium") return 1;
  return 2;
}

// ---------------------------------------------------------------------------
// Risk Card (right panel)
// ---------------------------------------------------------------------------

function RiskCard({
  risk,
  active,
  onClick,
}: {
  risk: ReviewReport["risks"][0];
  active: boolean;
  onClick: () => void;
}) {
  const hasBasis =
    risk.legal_basis &&
    risk.legal_basis !== "依据不足，基于法理分析" &&
    risk.basis_source;

  return (
    <div
      onClick={onClick}
      style={{
        padding: "14px 14px 12px",
        borderRadius: 20,
        border: active
          ? "2px solid rgba(45,94,137,0.5)"
          : "1px solid rgba(24,36,47,0.08)",
        background: active
          ? "linear-gradient(135deg, rgba(240,249,255,0.98), rgba(255,255,255,0.98))"
          : "rgba(255,255,255,0.8)",
        cursor: "pointer",
        boxShadow: active
          ? "0 8px 24px rgba(45,94,137,0.22)"
          : "var(--shadow-sm)",
        transform: active ? "scale(1.02)" : "none",
        transition: "all 200ms ease",
        position: "relative",
      }}
    >
      {/* Active indicator */}
      {active && (
        <div
          style={{
            position: "absolute",
            left: 0,
            top: "50%",
            transform: "translateY(-50%)",
            width: 4,
            height: "60%",
            borderRadius: "0 4px 4px 0",
            background: "linear-gradient(180deg, #2d5e89, #4b789f)",
          }}
        />
      )}
      {/* Top: dot + body + level badge */}
      <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
        {/* Severity dot */}
        <div
          style={{
            width: 9,
            height: 9,
            borderRadius: 999,
            marginTop: 4,
            flexShrink: 0,
            background: riskLevelColor(risk.risk_level),
          }}
        />

        {/* Body */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <strong
            style={{
              display: "block",
              marginBottom: 6,
              fontSize: 14,
            }}
          >
            {risk.risk_category}
          </strong>
          <p
            style={{
              margin: "0 0 8px",
              fontSize: 12,
              lineHeight: 1.8,
              color: "var(--ink-soft)",
            }}
          >
            {risk.legal_analysis.length > 80
              ? risk.legal_analysis.slice(0, 80) + "..."
              : risk.legal_analysis}
          </p>
          <div style={{ fontSize: 11, color: "var(--ink-muted)" }}>
            {risk.clause_code} · {riskLevelLabel(risk.risk_level)}
          </div>
        </div>

        {/* Level badge */}
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 26,
            padding: "0 9px",
            borderRadius: 999,
            fontSize: 10,
            fontWeight: 800,
            letterSpacing: "0.08em",
            background: riskLevelBg(risk.risk_level),
            color: riskLevelColor(risk.risk_level),
            flexShrink: 0,
          }}
        >
          {riskLevelLabel(risk.risk_level)}
        </span>
      </div>

      {/* Action links */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 10,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 28,
            padding: "0 10px",
            borderRadius: 999,
            border: "1px solid rgba(24,36,47,0.08)",
            background: active ? "rgba(45,94,137,0.08)" : "rgba(255,255,255,0.74)",
            fontSize: 10,
            color: active ? "var(--brand)" : "var(--ink-muted)",
            fontWeight: active ? 600 : 400,
          }}
        >
          {active ? "正在查看" : "点击查看"}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Document Section (left panel)
// ---------------------------------------------------------------------------

function DocumentSection({ risk }: { risk: ReviewReport["risks"][0] | null }) {
  if (!risk) {
    return (
      <div
        style={{
          borderRadius: 24,
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,246,238,0.98))",
          border: "1px solid rgba(24,36,47,0.08)",
          padding: "30px 34px 40px",
          minHeight: 400,
          display: "grid",
          placeItems: "center",
        }}
      >
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="点击右侧风险卡片查看对应条款原文"
        />
      </div>
    );
  }

  const hasBasis =
    risk.legal_basis &&
    risk.legal_basis !== "依据不足，基于法理分析" &&
    risk.basis_source;

  return (
    <div
      style={{
        borderRadius: 24,
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,246,238,0.98))",
        border: "1px solid rgba(24,36,47,0.08)",
        padding: "30px 34px 40px",
        minHeight: 400,
      }}
    >
      {/* Paper title */}
      <div
        style={{
          textAlign: "center",
          fontFamily: "var(--font-serif)",
          fontSize: 26,
          lineHeight: 1.12,
          letterSpacing: "-0.03em",
          marginBottom: 6,
        }}
      >
        合同条款审查
      </div>
      <div
        style={{
          textAlign: "center",
          fontSize: 12,
          color: "var(--ink-muted)",
          marginBottom: 12,
        }}
      >
        当前查看风险条款
      </div>

      {/* Current risk indicator */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          marginBottom: 24,
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 32,
            padding: "0 14px",
            borderRadius: 999,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.04em",
            background: riskLevelBg(risk.risk_level),
            color: riskLevelColor(risk.risk_level),
            border: `1px solid ${riskLevelColor(risk.risk_level)}33`,
          }}
        >
          {riskLevelLabel(risk.risk_level)}
        </span>
        <span
          style={{
            fontSize: 12,
            color: "var(--ink-soft)",
            fontWeight: 500,
          }}
        >
          {risk.risk_category}
        </span>
      </div>

      {/* Clause section */}
      <div style={{ marginBottom: 24 }}>
        <h3
          style={{
            margin: "0 0 10px",
            paddingBottom: 8,
            borderBottom: "1px dashed rgba(24,36,47,0.1)",
            fontSize: 13,
            letterSpacing: "0.04em",
            color: "var(--ink)",
          }}
        >
          {risk.clause_code} · {risk.risk_category}
        </h3>
        {risk.original_text && (
          <p
            style={{
              margin: "0 0 10px",
              fontFamily: "var(--font-serif)",
              fontSize: 15,
              lineHeight: 2,
              color: "var(--ink-soft)",
            }}
          >
            <span
              style={{
                color: riskLevelColor(risk.risk_level),
                background:
                  risk.risk_level === "high"
                    ? "linear-gradient(180deg, transparent 46%, rgba(176,90,78,0.16) 46%)"
                    : risk.risk_level === "medium"
                      ? "linear-gradient(180deg, transparent 46%, rgba(200,135,66,0.18) 46%)"
                      : "linear-gradient(180deg, transparent 46%, rgba(45,94,137,0.16) 46%)",
                padding: "0 2px",
                borderRadius: 4,
              }}
            >
              {risk.original_text}
            </span>
          </p>
        )}
      </div>

      {/* Analysis */}
      <div
        style={{
          borderRadius: 22,
          border: "1px solid rgba(24,36,47,0.08)",
          background: "rgba(255,255,255,0.82)",
          padding: "18px 18px 16px",
          marginBottom: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 10,
          }}
        >
          <strong style={{ fontSize: 15 }}>问题分析</strong>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 30,
              padding: "0 10px",
              borderRadius: 999,
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: "0.08em",
              background: riskLevelBg(risk.risk_level),
              color: riskLevelColor(risk.risk_level),
            }}
          >
            {riskLevelLabel(risk.risk_level)}
          </span>
        </div>
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontSize: 15,
            lineHeight: 1.9,
            color: "var(--ink-soft)",
          }}
        >
          {risk.legal_analysis}
        </p>
      </div>

      {/* Suggested revision */}
      <div
        style={{
          borderRadius: 22,
          border: "1px solid rgba(24,36,47,0.08)",
          background: "rgba(255,255,255,0.82)",
          padding: "18px 18px 16px",
          marginBottom: 14,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 10,
          }}
        >
          <strong style={{ fontSize: 15 }}>修改建议</strong>
          <span
            style={{
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: "0.08em",
              color: "var(--sage)",
            }}
          >
            SUGGESTED
          </span>
        </div>
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontSize: 15,
            lineHeight: 1.9,
            color: "var(--ink-soft)",
          }}
        >
          {risk.suggested_revision}
        </p>
      </div>

      {/* Legal basis */}
      <div
        style={{
          borderRadius: 22,
          border: "1px solid rgba(24,36,47,0.08)",
          background: hasBasis
            ? "rgba(240,249,255,0.82)"
            : "rgba(255,251,235,0.82)",
          padding: "18px 18px 16px",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 10,
          }}
        >
          <SafetyCertificateOutlined
            style={{ color: hasBasis ? "#0284c7" : "#d97706" }}
          />
          <strong
            style={{
              fontSize: 15,
              color: hasBasis ? "#0284c7" : "#d97706",
            }}
          >
            法条依据
          </strong>
        </div>
        <p
          style={{
            margin: "0 0 8px",
            fontFamily: "var(--font-serif)",
            fontSize: 15,
            lineHeight: 1.9,
            color: "var(--ink-soft)",
          }}
        >
          {risk.legal_basis || "依据不足，基于法理分析"}
        </p>
        {risk.basis_excerpt && (
          <p
            style={{
              margin: "0 0 4px",
              fontSize: 12,
              lineHeight: 1.8,
              color: "var(--ink-muted)",
            }}
          >
            条款摘录: {risk.basis_excerpt}
          </p>
        )}
        {risk.basis_source && (
          <p
            style={{
              margin: 0,
              fontSize: 11,
              color: "var(--ink-muted)",
            }}
          >
            来源: {risk.basis_source}
          </p>
        )}
      </div>

      {/* Plain explanation */}
      {risk.plain_explanation && (
        <p
          style={{
            marginTop: 14,
            fontSize: 12,
            lineHeight: 1.8,
            color: "var(--ink-muted)",
          }}
        >
          通俗解释: {risk.plain_explanation}
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Decision Strip (v12 hook - action buttons)
// ---------------------------------------------------------------------------

function DecisionStrip({
  onApply,
  onIgnore,
  onReReview,
}: {
  onApply: () => void;
  onIgnore: () => void;
  onReReview: () => void;
}) {
  return (
    <div
      style={{
        borderRadius: 32,
        padding: 20,
        marginTop: 18,
        border: "1px solid rgba(24,36,47,0.1)",
        background:
          "radial-gradient(circle at top right, rgba(200,135,66,0.08), transparent 30%), linear-gradient(180deg, rgba(255,255,255,0.94), rgba(247,242,234,0.94))",
        boxShadow: "var(--shadow-md)",
        backdropFilter: "blur(18px)",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <div>
          <h2
            style={{
              margin: 0,
              fontFamily: "var(--font-serif)",
              fontSize: 30,
              lineHeight: 1.08,
            }}
          >
            审查操作
          </h2>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-soft)" }}>
            整理审查建议，进入草稿模式编辑
          </p>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.08fr 1.08fr 0.84fr",
          gap: 14,
        }}
      >
        {/* Apply suggestion */}
        <div
          style={{
            padding: 18,
            borderRadius: 24,
            border: "1px solid rgba(24,36,47,0.08)",
            background: "rgba(255,255,255,0.8)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <span
            style={{
              display: "block",
              marginBottom: 8,
              fontSize: 10,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
            }}
          >
            插入建议
          </span>
          <strong style={{ display: "block", marginBottom: 10, fontSize: 16 }}>
            将修改建议插入到编辑区
          </strong>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.9, color: "var(--ink-soft)" }}>
            将当前风险的建议内容插入到草稿编辑器中，方便手动调整。
          </p>
          <button
            type="button"
            onClick={onApply}
            style={{
              marginTop: 14,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 18px",
              borderRadius: 999,
              border: "1px solid transparent",
              color: "#fff",
              background: "linear-gradient(135deg, #b67839 0%, #d29858 100%)",
              boxShadow: "0 18px 32px rgba(200,135,66,0.18)",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            插入建议内容
          </button>
        </div>

        {/* Manual edit */}
        <div
          style={{
            padding: 18,
            borderRadius: 24,
            border: "1px solid rgba(24,36,47,0.08)",
            background: "rgba(255,255,255,0.8)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <span
            style={{
              display: "block",
              marginBottom: 8,
              fontSize: 10,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
            }}
          >
            草稿整理
          </span>
          <strong style={{ display: "block", marginBottom: 10, fontSize: 16 }}>
            整理审查建议草稿
          </strong>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.9, color: "var(--ink-soft)" }}>
            进入草稿模式，整理审查建议内容（自动保存到服务器）
          </p>
          <button
            type="button"
            onClick={onIgnore}
            style={{
              marginTop: 14,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 18px",
              borderRadius: 999,
              border: "1px solid rgba(24,36,47,0.08)",
              background: "rgba(255,255,255,0.72)",
              color: "var(--ink)",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            进入草稿模式
          </button>
        </div>

        {/* Re-review */}
        <div
          style={{
            padding: 18,
            borderRadius: 24,
            border: "1px solid rgba(24,36,47,0.08)",
            background: "rgba(255,255,255,0.8)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <span
            style={{
              display: "block",
              marginBottom: 8,
              fontSize: 10,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: "var(--ink-muted)",
            }}
          >
            草稿审查
          </span>
          <strong style={{ display: "block", marginBottom: 10, fontSize: 16 }}>
            修改后重新审查
          </strong>
          <p style={{ margin: 0, fontSize: 13, lineHeight: 1.9, color: "var(--ink-soft)" }}>
            保存当前草稿后，直接基于修改后的内容重新发起审查。
          </p>
          <button
            type="button"
            onClick={onReReview}
            style={{
              marginTop: 14,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 18px",
              borderRadius: 999,
              border: "1px solid transparent",
              color: "#fff",
              background: "linear-gradient(135deg, #234c74 0%, #4b769f 100%)",
              boxShadow: "0 18px 32px rgba(45,94,137,0.22)",
              cursor: "pointer",
              fontSize: 14,
            }}
          >
            基于草稿重新审查
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export function ContractDetailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { id } = useParams();
  const { selected, loading, fetchContractDetail, error: contractError, clearError } = useContractStore();
  const {
    triggerReview,
    triggerLoading,
    pollStatus,
    connectReviewWS,
    wsConnected,
    wsError,
    fetchReport,
    current: reportData,
    clear: clearReviewStore,
  } = useReviewStore();
  const [messageApi, contextHolder] = message.useMessage();

  const [activeReview, setActiveReview] = useState<Review | null>(null);
  const [polling, setPolling] = useState(false);
  const [usingWS, setUsingWS] = useState(false);
  const [activeRiskIndex, setActiveRiskIndex] = useState(0);
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [hasAttemptedDetailLoad, setHasAttemptedDetailLoad] = useState(false);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wsCleanupRef = useRef<(() => void) | null>(null);

  // Clear review store when contract changes to prevent cross-contamination
  useEffect(() => {
    if (id) {
      setHasAttemptedDetailLoad(true);
      clearReviewStore();
      void fetchContractDetail(id).catch(() => {});
    }
  }, [id, clearReviewStore, fetchContractDetail]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      if (wsCleanupRef.current) wsCleanupRef.current();
    };
  }, []);

  // Fetch report when review completes 鈥?validate it belongs to current contract/review
  const report = useMemo(() => {
    if (!reportData) return null;
    // Only use report if it matches the current activeReview or current contract
    if (activeReview && reportData.id !== activeReview.id) return null;
    if (selected && reportData.contract_id !== selected.id) return null;
    return reportData as ReviewReport;
  }, [reportData, activeReview, selected]);

  const risks = useMemo(() => {
    if (!report) return [];
    return [...report.risks].sort(
      (a, b) => severityOrder(a.risk_level) - severityOrder(b.risk_level),
    );
  }, [report]);

  // Reset activeRiskIndex when report changes to avoid stale index
  useEffect(() => {
    setActiveRiskIndex(0);
  }, [report]);

  const activeRisk = risks[activeRiskIndex] ?? null;

  // High/medium/low counts
  const highCount = useMemo(
    () => risks.filter((r) => r.risk_level === "high").length,
    [risks],
  );
  const mediumCount = useMemo(
    () => risks.filter((r) => r.risk_level === "medium").length,
    [risks],
  );
  const lowCount = useMemo(
    () => risks.filter((r) => r.risk_level === "low").length,
    [risks],
  );

  // --- Polling fallback ---
  const startPolling = useCallback(
    (reviewId: string) => {
      if (pollTimerRef.current) {
        clearTimeout(pollTimerRef.current);
        pollTimerRef.current = null;
      }
      setPolling(true);
      setUsingWS(false);
      const poll = async () => {
        try {
          const status = await pollStatus(reviewId);
          setActiveReview(status);
          if (status.status === "completed") {
            setPolling(false);
            void fetchReport(reviewId);
            return;
          }
          if (status.status === "failed") {
            setPolling(false);
            messageApi.error("审查失败，请稍后重试。");
            void fetchReport(reviewId);
            return;
          }
          pollTimerRef.current = setTimeout(poll, 1500);
        } catch {
          setPolling(false);
        }
      };
      void poll();
    },
    [pollStatus, messageApi, fetchReport],
  );

  // --- WebSocket ---
  const startWebSocket = useCallback(
    (reviewId: string) => {
      setUsingWS(true);
      setPolling(false);

      const cleanup = connectReviewWS(
        reviewId,
        (evt: WSStageEvent) => {
          setActiveReview((prev) =>
            prev
              ? {
                  ...prev,
                  status: evt.stage,
                  progress: evt.progress,
                  current_stage: evt.stage,
                }
              : prev,
          );
        },
        (_evt: WSCompleteEvent) => {
          setUsingWS(false);
          setActiveReview((prev) =>
            prev ? { ...prev, status: "completed", progress: 100 } : prev,
          );
          void fetchReport(reviewId);
        },
        (evt: WSFailedEvent) => {
          setUsingWS(false);
          setActiveReview((prev) =>
            prev
              ? { ...prev, status: "failed", error_detail: evt.detail }
              : prev,
          );
          messageApi.error(`审查失败：${evt.detail || evt.message}`);
          void fetchReport(reviewId);
        },
        () => {
          setUsingWS(false);
          startPolling(reviewId);
        },
      );

      wsCleanupRef.current = cleanup;
    },
    [connectReviewWS, messageApi, fetchReport, startPolling],
  );

  const forcePolling =
    new URLSearchParams(location.search).get("forcePolling") === "1" ||
    import.meta.env.VITE_FORCE_POLLING === "true" ||
    localStorage.getItem("force_polling") === "true";

  const startMonitoring = useCallback(
    (reviewId: string) => {
      if (forcePolling) {
        startPolling(reviewId);
        return () => {
          if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
        };
      }
      startWebSocket(reviewId);
      const fallbackTimer = setTimeout(() => {
        const state = useReviewStore.getState();
        if (state.wsError || !state.wsConnected) {
          if (wsCleanupRef.current) {
            wsCleanupRef.current();
            wsCleanupRef.current = null;
          }
          startPolling(reviewId);
        }
      }, 3000);
      return () => clearTimeout(fallbackTimer);
    },
    [startWebSocket, startPolling, forcePolling],
  );

  // --- Initial state ---
  useEffect(() => {
    // Prevent running effect if component is still initializing or selected hasn't loaded
    if (!selected?.latest_review) {
      setActiveReview(null);
      return;
    }

    const lr = selected.latest_review;
    setActiveReview({
      id: lr.id,
      contract_id: selected.id,
      status: lr.status,
      progress: lr.progress,
      current_stage: null,
      schema_version: "1.0",
      error_detail: lr.error_detail ?? null,
      started_at: null,
      completed_at: null,
      created_at: lr.created_at,
    });

    if (RUNNING_STATUSES.includes(lr.status)) {
      startMonitoring(lr.id);
    } else if (lr.status === "completed") {
      void fetchReport(lr.id);
    }
  }, [selected?.latest_review?.id, selected?.latest_review?.status, startMonitoring, fetchReport]);

  // --- Trigger review ---
  const handleTriggerReview = async (useDraft = false) => {
    if (!id) return;
    try {
      const reviewId = await triggerReview(id, useDraft);
      messageApi.success(
        useDraft ? "草稿审查已发起，正在处理中.." : "原合同审查已发起，正在处理中..",
      );
      setActiveReview({
        id: reviewId,
        contract_id: id,
        status: "queued",
        progress: 0,
        current_stage: null,
        schema_version: "1.0",
        error_detail: null,
        started_at: null,
        completed_at: null,
        created_at: new Date().toISOString(),
      });
      startMonitoring(reviewId);
    } catch (err: unknown) {
      const axiosErr = err as {
        response?: { data?: { code?: number; message?: string } };
      };
      if (axiosErr.response?.data?.code === 4002) {
        messageApi.warning("该合同正在审查中，请稍后查看结果。");
      } else {
        messageApi.error("发起审查失败，请稍后重试。");
      }
    }
  };

  // --- Edit mode handlers ---
  const handleEnterEditMode = (insertSuggestion?: string) => {
    const draftKey = `contract-draft-${id}`;
    const savedDraft = sessionStorage.getItem(draftKey);

    let initialContent = '';

    if (insertSuggestion) {
      // 如果有建议需要插入，优先使用建议内容
      initialContent = `<p></p><p><em>以下为建议修改内容：</em></p><div style="padding: 16px; border-left: 3px solid #c88742; background: rgba(200, 135, 66, 0.08); margin: 12px 0; border-radius: 8px;"><p>${insertSuggestion}</p></div>`;
    } else if (savedDraft) {
      // 有保存的草稿，使用草稿
      initialContent = savedDraft;
    } else if (report?.risks.length) {
      // 没有草稿但有风险报告，生成默认内容
      initialContent = `<p></p><p><em>以下为审查报告中的风险条款，可编辑整理：</em></p>` +
        report.risks.map(risk =>
          `<h3>${risk.clause_code} · ${risk.risk_category}</h3><p>${risk.original_text || ''}</p>`
        ).join('');
    } else {
      // 兜底：空白内容
      initialContent = '<p>暂无审查内容，可在此记录备注</p>';
    }

    setEditedContent(initialContent);
    startTransition(() => {
      setIsEditMode(true);
    });
  };

  const handleExitEditMode = () => {
    setIsEditMode(false);
    setEditedContent('');
  };

  const handleSaveContent = (content: string) => {
    if (!id) return;
    const draftKey = `contract-draft-${id}`;
    sessionStorage.setItem(draftKey, content);
    setEditedContent(content);
  };

  const handleReReview = async (content: string) => {
    if (!id) return;
    // 保存编辑内容
    setEditedContent(content);
    const draftKey = `contract-draft-${id}`;
    sessionStorage.setItem(draftKey, content);

    // 退出编辑模式
    setIsEditMode(false);

    // 重新触发审查
    try {
      await handleTriggerReview(true);
      messageApi.success('已退出编辑模式并基于当前草稿重新发起审查');
    } catch (error) {
      console.error('Failed to trigger re-review:', error);
    }
  };

  const handleApplySuggestion = (suggestion: string) => {
    messageApi.success('已将建议内容插入编辑区');
  };

  const isRunning =
    activeReview && RUNNING_STATUSES.includes(activeReview.status);
  const isCompleted = activeReview?.status === "completed" || !!report;
  const isFailed = activeReview?.status === "failed";

  // Loading
  if (loading) {
    return (
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        {contextHolder}
        <Skeleton active paragraph={{ rows: 12 }} />
      </Card>
    );
  }

  // Error state - backend offline or network failure
  if (contractError || (hasAttemptedDetailLoad && !selected && !loading)) {
    return (
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        {contextHolder}
        <div
          style={{
            padding: 60,
            textAlign: 'center',
            minHeight: 400,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <ExclamationCircleOutlined
            style={{ fontSize: 48, color: 'var(--danger)', marginBottom: 24 }}
          />
          <Title level={3} style={{ margin: '0 0 12px' }}>
            {contractError || '加载合同详情失败'}
          </Title>
          <Paragraph style={{ margin: '0 0 24px', color: 'var(--ink-soft)', maxWidth: 480 }}>
            {contractError?.includes('后端服务')
              ? '请确认后端服务已启动并运行在 http://localhost:8000，或检查网络连接。'
              : '无法获取合同信息，请稍后重试。'}
          </Paragraph>
          <Space>
            <Button
              type="default"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/workspace')}
              style={{ borderRadius: 999 }}
            >
              返回工作台
            </Button>
            <Button
              type="primary"
              icon={<SyncOutlined />}
              onClick={() => {
                if (clearError) clearError();
                if (id) void fetchContractDetail(id).catch(() => {});
              }}
              style={{ borderRadius: 999 }}
            >
              重新加载
            </Button>
          </Space>
        </div>
      </Card>
    );
  }

  // Ensure selected is not null after error checks
  if (!selected) {
    return (
      <Card className="glass-card" style={{ borderRadius: 28 }}>
        {contextHolder}
        <Skeleton active paragraph={{ rows: 12 }} />
      </Card>
    );
  }

  // Edit mode
  if (isEditMode) {
    return (
      <>
        {contextHolder}
        <Suspense fallback={
          <Card className="glass-card" style={{ borderRadius: 28, minHeight: 600 }}>
            <div style={{ textAlign: 'center', padding: 60 }}>
              <LoadingOutlined style={{ fontSize: 32, color: 'var(--brand)', marginBottom: 16 }} />
              <p style={{ margin: 0, fontSize: 14, color: 'var(--ink-soft)' }}>正在加载编辑器...</p>
            </div>
          </Card>
        }>
          <EditMode
            contractId={selected.id}
            contractTitle={selected.title ?? '未命名合同'}
            originalContent={editedContent}
            report={report}
            activeRisk={activeRisk}
            onExit={handleExitEditMode}
            onSave={handleSaveContent}
            onReReview={handleReReview}
            onApplySuggestion={handleApplySuggestion}
          />
        </Suspense>
      </>
    );
  }

  return (
    <div style={{ display: "grid", gap: 18 }}>
      {contextHolder}

      {/* ── Top bar ── */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 18,
          padding: "16px 18px",
          borderRadius: 24,
          border: "1px solid rgba(24,36,47,0.1)",
          background: "rgba(255,255,255,0.9)",
          boxShadow: "var(--shadow-md)",
          backdropFilter: "blur(18px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            type="button"
            onClick={() => navigate("/workspace")}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              minHeight: 40,
              padding: "0 14px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.74)",
              border: "1px solid rgba(24,36,47,0.08)",
              boxShadow: "var(--shadow-sm)",
              fontSize: 12,
              color: "var(--ink-soft)",
              cursor: "pointer",
            }}
          >
            <ArrowLeftOutlined /> 返回工作台
          </button>
          <div>
            <strong style={{ display: "block", fontSize: 14 }}>
              ContractGuard
            </strong>
            <span style={{ fontSize: 11, color: "var(--ink-muted)" }}>
              合同审查工作台
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {isCompleted && (
            <button
              type="button"
              onClick={() => navigate(`/reviews/${activeReview?.id}`)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                minHeight: 44,
                padding: "0 18px",
                borderRadius: 999,
                border: "1px solid rgba(24,36,47,0.08)",
                background: "rgba(255,255,255,0.72)",
                color: "var(--ink)",
                cursor: "pointer",
              }}
            >
              查看完整报告
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              void handleTriggerReview();
            }}
            disabled={triggerLoading || !!isRunning}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 18px",
              borderRadius: 999,
              border: "1px solid transparent",
              color: "#fff",
              background: "linear-gradient(135deg, #234c74 0%, #4b769f 100%)",
              boxShadow: "0 18px 32px rgba(45,94,137,0.22)",
              cursor: triggerLoading || isRunning ? "not-allowed" : "pointer",
              opacity: triggerLoading || isRunning ? 0.6 : 1,
            }}
          >
            {isCompleted ? "基于原合同重新审查" : isRunning ? "审查中.." : "发起审查"}
          </button>
        </div>
      </div>

      {/* ── Detail header ── */}
      <div
        style={{
          borderRadius: 32,
          padding: "24px 26px",
          border: "1px solid rgba(24,36,47,0.1)",
          background:
            "radial-gradient(circle at top right, rgba(45,94,137,0.12), transparent 28%), linear-gradient(180deg, rgba(255,255,255,0.94), rgba(247,242,234,0.96))",
          boxShadow: "var(--shadow-md)",
          backdropFilter: "blur(18px)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 20,
            marginBottom: 18,
          }}
        >
          <div>
            <h1
              style={{
                margin: "0 0 8px",
                fontFamily: "var(--font-serif)",
                fontSize: "clamp(38px, 4vw, 54px)",
                lineHeight: 1.06,
                letterSpacing: "-0.04em",
              }}
            >
              {selected.title ?? "未命名合同"}
            </h1>
            <p style={{ margin: 0, maxWidth: 760, fontSize: 14, lineHeight: 1.84, color: "var(--ink-soft)" }}>
              {isRunning
                ? `审查进行中 · ${STAGE_DETAIL[activeReview?.status ?? ""] ?? "处理中，请耐心等待"}`
                : isCompleted
                  ? "审查已完成，可逐条查看风险分析与修改建议。"
                  : isFailed
                    ? "审查未能完成，请查看错误详情或重新发起。"
                    : "发起审查后，系统将自动解析条款并生成风险报告。"}
            </p>
            {/* Phase v12: Show review source — 原合同审查 vs 草稿审查 */}
            {activeReview?.reviewed_draft != null && (
              <Tag
                color={activeReview.reviewed_draft ? "orange" : "blue"}
                style={{ marginTop: 8, fontWeight: 600 }}
              >
                {activeReview.reviewed_draft ? "草稿审查" : "原合同审查"}
              </Tag>
            )}
            {report?.reviewed_draft && activeReview?.reviewed_draft == null && (
              <Tag color="orange" style={{ marginTop: 8, fontWeight: 600 }}>
                草稿审查
              </Tag>
            )}
          </div>

          {/* Status cluster */}
          <div
            style={{
              minWidth: 280,
              padding: 16,
              borderRadius: 28,
              background: "rgba(255,255,255,0.76)",
              border: "1px solid rgba(24,36,47,0.08)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <strong style={{ display: "block", marginBottom: 10, fontSize: 15 }}>
              当前任务
            </strong>
            <div style={{ display: "grid", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-soft)" }}>
                <span>合同</span>
                <b style={{ color: "var(--ink)", fontSize: 13 }}>
                  {selected.title ?? "未命名"}
                </b>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-soft)" }}>
                <span>状态</span>
                <b style={{ color: "var(--ink)", fontSize: 13 }}>
                  {isRunning
                    ? STAGE_LABELS[activeReview?.status ?? ""] ?? "处理中"
                    : isCompleted
                      ? "审查完成"
                      : isFailed
                        ? "审查失败"
                        : "待审查"}
                </b>
              </div>
              {isRunning && (
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--ink-soft)" }}>
                  <span>连接</span>
                  <b style={{ color: "var(--ink)", fontSize: 13 }}>
                    {usingWS && wsConnected ? "实时" : polling ? "轮询" : "连接中..."}
                  </b>
                </div>
              )}
              {isRunning && (
                <div style={{ marginTop: 4 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 12, color: "var(--ink-soft)" }}>
                    <span>进度</span>
                    <span>{activeReview?.progress ?? 0}%</span>
                  </div>
                  <div
                    style={{
                      width: "100%",
                      height: 8,
                      borderRadius: 999,
                      background: "rgba(24,36,47,0.08)",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        borderRadius: 999,
                        background: "linear-gradient(90deg, var(--brand), var(--accent))",
                        width: `${activeReview?.progress ?? 0}%`,
                        transition: "width 300ms ease",
                      }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Meta chips */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              minHeight: 38,
              padding: "0 14px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.78)",
              border: "1px solid rgba(24,36,47,0.08)",
              fontSize: 12,
              color: "var(--ink-soft)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: 999, background: "rgba(24,36,47,0.2)" }} />
            {selected.file_type.toUpperCase()} · {selected.file_size ?? 0} bytes
          </span>
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              minHeight: 38,
              padding: "0 14px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.78)",
              border: "1px solid rgba(24,36,47,0.08)",
              fontSize: 12,
              color: "var(--ink-soft)",
              boxShadow: "var(--shadow-sm)",
            }}
          >
            <span style={{ width: 7, height: 7, borderRadius: 999, background: "rgba(24,36,47,0.2)" }} />
            上传于{dayjs(selected.created_at).format("YYYY-MM-DD HH:mm")}
          </span>
          {report && (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                minHeight: 38,
                padding: "0 14px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.78)",
                border: "1px solid rgba(24,36,47,0.08)",
                fontSize: 12,
                color: "var(--ink-soft)",
                boxShadow: "var(--shadow-sm)",
              }}
            >
              <span style={{ width: 7, height: 7, borderRadius: 999, background: "var(--danger)" }} />
              高风险 {highCount} 处
            </span>
          )}
        </div>
      </div>

      {/* ── Failed alert ── */}
      {isFailed && activeReview?.error_detail && (
        <div
          style={{
            borderRadius: 20,
            padding: 18,
            background: "linear-gradient(135deg, #fef2f2 0%, #fff1f2 100%)",
            border: "1px solid #fecaca",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <ExclamationCircleOutlined style={{ fontSize: 20, color: "#dc2626" }} />
            <strong style={{ fontSize: 16, color: "#991b1b" }}>审查未能完成</strong>
          </div>
          <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--ink-soft)" }}>
            {activeReview.error_detail}
          </p>
          <button
            type="button"
            onClick={() => {
              void handleTriggerReview();
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 44,
              padding: "0 18px",
              borderRadius: 999,
              border: "1px solid transparent",
              color: "#fff",
              background: "linear-gradient(135deg, #234c74 0%, #4b769f 100%)",
              boxShadow: "0 18px 32px rgba(45,94,137,0.22)",
              cursor: "pointer",
            }}
          >
            基于原合同重新审查
          </button>
        </div>
      )}

      {/* ── Running indicator ── */}
      {isRunning && (
        <div
          style={{
            borderRadius: 20,
            padding: 18,
            background:
              "linear-gradient(180deg, rgba(239,246,255,0.9), rgba(240,249,255,0.9))",
            border: "1px solid rgba(45,94,137,0.12)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <SyncOutlined spin style={{ color: "var(--brand)" }} />
            <strong style={{ fontSize: 15 }}>
              {STAGE_LABELS[activeReview?.status ?? ""] ?? "处理中"}
            </strong>
            <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>
              · {STAGE_DETAIL[activeReview?.status ?? ""] ?? "处理中，请耐心等待"}
            </span>
          </div>
          <Progress
            percent={activeReview?.progress ?? 0}
            status="active"
            strokeColor={{ from: "#2d5e89", to: "#c88742" }}
            style={{ marginTop: 10 }}
          />
          {polling && (
            <p style={{ margin: "8px 0 0", fontSize: 12, color: "var(--ink-muted)" }}>
              <SyncOutlined spin style={{ marginRight: 4 }} />
              当前使用轮询模式（每 1.5 秒自动刷新）
            </p>
          )}
        </div>
      )}

      {/* ── Dual-panel workspace ── */}
      {report && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.14fr) 390px",
              gap: 18,
              alignItems: "start",
            }}
          >
            {/* Left: Document / Original text */}
            <div
              style={{
                borderRadius: 30,
                padding: 18,
                border: "1px solid rgba(24,36,47,0.1)",
                background: "var(--surface)",
                boxShadow: "var(--shadow-md)",
                backdropFilter: "blur(18px)",
                overflow: "hidden",
              }}
            >
              {/* Mode tabs placeholder (v12) */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  marginBottom: 16,
                }}
              >
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minHeight: 42,
                      padding: "0 16px",
                      borderRadius: 999,
                      color: "#fff",
                      background: "linear-gradient(135deg, #234c74 0%, #4b789f 100%)",
                      border: "1px solid transparent",
                      boxShadow: "0 16px 28px rgba(45,94,137,0.2)",
                      fontSize: 13,
                    }}
                  >
                    审查视图
                  </span>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minHeight: 42,
                      padding: "0 16px",
                      borderRadius: 999,
                      border: "1px solid rgba(24,36,47,0.08)",
                      background: "rgba(255,255,255,0.72)",
                      color: "var(--ink-soft)",
                      fontSize: 13,
                      opacity: 0.5,
                    }}
                    title="v12: 建议稿视图"
                  >
                    建议稿
                  </span>
                  <span
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      minHeight: 42,
                      padding: "0 16px",
                      borderRadius: 999,
                      border: "1px solid rgba(24,36,47,0.08)",
                      background: "rgba(255,255,255,0.72)",
                      color: "var(--ink-soft)",
                      fontSize: 13,
                      opacity: 0.5,
                    }}
                    title="v12: 报告摘要视图"
                  >
                    报告摘要
                  </span>
                </div>
                <span style={{ fontSize: 12, color: "var(--ink-muted)" }}>
                  当前显示合同原文与风险定位
                </span>
              </div>

              {/* Paper shell */}
              <div
                style={{
                  padding: 18,
                  borderRadius: 26,
                  background:
                    "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(250,246,238,0.98))",
                  border: "1px solid rgba(24,36,47,0.08)",
                  minHeight: 500,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 18,
                    fontSize: 11,
                    color: "var(--ink-muted)",
                  }}
                >
                  <span>合同正文 / 风险定位模式</span>
                  <span>点击右侧风险卡片查看对应条款</span>
                </div>

                <DocumentSection risk={activeRisk} />
              </div>
            </div>

            {/* Right: Risk panel */}
            <div
              style={{
                position: "sticky",
                top: 22,
                borderRadius: 30,
                padding: 18,
                border: "1px solid rgba(24,36,47,0.1)",
                background: "var(--surface)",
                boxShadow: "var(--shadow-md)",
                backdropFilter: "blur(18px)",
                overflow: "hidden",
              }}
            >
              {/* Summary card */}
              <div
                style={{
                  borderRadius: 22,
                  border: "1px solid rgba(24,36,47,0.08)",
                  background:
                    "linear-gradient(180deg, rgba(255,255,255,0.96), rgba(247,242,234,0.94))",
                  padding: 18,
                  marginBottom: 14,
                }}
              >
                <strong style={{ display: "block", marginBottom: 8, fontSize: 16 }}>
                  {activeRisk?.risk_category ?? "审查概览"}
                </strong>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.8, color: "var(--ink-soft)" }}>
                  {activeRisk
                    ? "点击下方风险卡片切换查看对应条款原文与分析。"
                    : "审查完成后可逐条查看风险分析与修改建议。"}
                </p>
                <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid rgba(24,36,47,0.08)", fontSize: 12 }}>
                    <span style={{ color: "var(--ink-soft)" }}>高风险</span>
                    <b style={{ fontSize: 13 }}>{highCount} 条</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid rgba(24,36,47,0.08)", fontSize: 12 }}>
                    <span style={{ color: "var(--ink-soft)" }}>中风险</span>
                    <b style={{ fontSize: 13 }}>{mediumCount} 条</b>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid rgba(24,36,47,0.08)", fontSize: 12 }}>
                    <span style={{ color: "var(--ink-soft)" }}>低风险</span>
                    <b style={{ fontSize: 13 }}>{lowCount} 条</b>
                  </div>
                  {report.contradictions.length > 0 && (
                    <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid rgba(24,36,47,0.08)", fontSize: 12 }}>
                      <span style={{ color: "var(--ink-soft)" }}>条款矛盾</span>
                      <b style={{ fontSize: 13 }}>{report.contradictions.length} 条</b>
                    </div>
                  )}
                  {report.missing_clauses.length > 0 && (
                    <div style={{ display: "flex", justifyContent: "space-between", padding: "10px 0", borderTop: "1px solid rgba(24,36,47,0.08)", fontSize: 12 }}>
                      <span style={{ color: "var(--ink-soft)" }}>缺失条款</span>
                      <b style={{ fontSize: 13 }}>{report.missing_clauses.length} 条</b>
                    </div>
                  )}
                </div>
              </div>

              {/* Panel title */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  marginBottom: 12,
                }}
              >
                <h2
                  style={{
                    margin: 0,
                    fontFamily: "var(--font-serif)",
                    fontSize: 28,
                    lineHeight: 1.08,
                  }}
                >
                  风险队列
                </h2>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    minWidth: 30,
                    height: 30,
                    padding: "0 10px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.82)",
                    border: "1px solid rgba(24,36,47,0.08)",
                    fontSize: 12,
                    color: "var(--ink-soft)",
                  }}
                >
                  {risks.length} 项                </span>
              </div>

              {/* Risk list */}
              {risks.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="未检测到风险"
                />
              ) : (
                <div style={{ display: "grid", gap: 12, marginBottom: 14 }}>
                  {risks.map((risk, idx) => (
                    <RiskCard
                      key={`${risk.clause_id}-${idx}`}
                      risk={risk}
                      active={idx === activeRiskIndex}
                      onClick={() => setActiveRiskIndex(idx)}
                    />
                  ))}
                </div>
              )}

              {/* Contradictions */}
              {report.contradictions.length > 0 && (
                <div
                  style={{
                    borderRadius: 22,
                    border: "1px solid rgba(24,36,47,0.08)",
                    background: "rgba(255,255,255,0.82)",
                    padding: 16,
                    marginBottom: 14,
                  }}
                >
                  <strong style={{ display: "block", marginBottom: 8, fontSize: 14 }}>
                    条款矛盾
                  </strong>
                  <div style={{ display: "grid", gap: 10 }}>
                    {report.contradictions.map((c, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "12px 14px",
                          borderRadius: 18,
                          background: "rgba(255,255,255,0.72)",
                          border: "1px solid rgba(24,36,47,0.06)",
                        }}
                      >
                        <b style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
                          {c.clause_a} <SwapOutlined style={{ margin: "0 4px", color: "#94a3b8" }} /> {c.clause_b}
                        </b>
                        <span style={{ display: "block", fontSize: 11, lineHeight: 1.8, color: "var(--ink-muted)" }}>
                          {c.description}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Missing clauses */}
              {report.missing_clauses.length > 0 && (
                <div
                  style={{
                    borderRadius: 22,
                    border: "1px solid rgba(24,36,47,0.08)",
                    background: "rgba(255,255,255,0.82)",
                    padding: 16,
                  }}
                >
                  <strong style={{ display: "block", marginBottom: 8, fontSize: 14 }}>
                    缺失条款
                  </strong>
                  <div style={{ display: "grid", gap: 10 }}>
                    {report.missing_clauses.map((m, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "12px 14px",
                          borderRadius: 18,
                          background: "rgba(255,255,255,0.72)",
                          border: "1px solid rgba(24,36,47,0.06)",
                        }}
                      >
                        <b style={{ display: "block", marginBottom: 4, fontSize: 12 }}>
                          {m.name}
                        </b>
                        <span style={{ display: "block", fontSize: 11, lineHeight: 1.8, color: "var(--ink-muted)" }}>
                          {m.reason}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* ── Decision strip (v12 hooks) ── */}
          <DecisionStrip
            onApply={() => {
              if (activeRisk) {
                handleEnterEditMode(activeRisk.suggested_revision);
              } else {
                handleEnterEditMode();
              }
            }}
            onIgnore={() => handleEnterEditMode()}
            onReReview={() => {
              void handleTriggerReview();
            }}
          />
        </>
      )}

      {/* ── No review state ── */}
      {!activeReview && !report && (
        <div
          style={{
            borderRadius: 20,
            padding: 40,
            textAlign: "center",
            border: "1px solid rgba(24,36,47,0.1)",
            background: "rgba(255,255,255,0.9)",
            boxShadow: "var(--shadow-md)",
          }}
        >
          <FileTextOutlined style={{ fontSize: 40, color: "var(--ink-muted)", marginBottom: 16 }} />
          <Title level={4} style={{ margin: "0 0 8px" }}>
            尚未发起审查
          </Title>
          <Paragraph style={{ margin: "0 0 20px", color: "var(--ink-soft)" }}>
            发起审查后，系统将自动解析合同条款并生成风险报告。          </Paragraph>
          <button
            type="button"
            onClick={() => {
              void handleTriggerReview();
            }}
            disabled={triggerLoading}
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              minHeight: 46,
              padding: "0 22px",
              borderRadius: 999,
              border: "1px solid transparent",
              color: "#fff",
              background: "linear-gradient(135deg, #234c74 0%, #4b769f 100%)",
              boxShadow: "0 18px 32px rgba(45,94,137,0.22)",
              cursor: triggerLoading ? "not-allowed" : "pointer",
            }}
          >
            发起审查
          </button>
        </div>
      )}
    </div>
  );
}
