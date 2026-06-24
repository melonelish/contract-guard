import {
  ArrowRightOutlined,
  CheckCircleOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { Button, Card, Col, Row, Space, Typography } from "antd";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/auth";

const { Title, Paragraph, Text } = Typography;

export function HomePage() {
  const navigate = useNavigate();
  const token = useAuthStore((s) => s.token);

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* Hero */}
      <section
        style={{
          position: "relative",
          padding: "120px 40px 80px",
          maxWidth: 1320,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "minmax(0, 1.04fr) minmax(460px, 0.96fr)",
          gap: 42,
          alignItems: "center",
        }}
      >
        <div style={{ maxWidth: 640 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 10,
              padding: "9px 16px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.58)",
              border: "1px solid rgba(24,36,47,0.08)",
              fontSize: 12,
              color: "var(--brand)",
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: 999,
                background: "linear-gradient(135deg, var(--accent), #efbe77)",
              }}
            />
            企业级智能合同风险审查系统
          </div>

          <Title
            level={1}
            style={{
              marginTop: 24,
              marginBottom: 18,
              fontFamily: "var(--font-serif)",
              fontSize: "clamp(44px, 5vw, 76px)",
              lineHeight: 1.06,
              letterSpacing: "-0.045em",
            }}
          >
            在签字之前，先看见真正的
            <span style={{ color: "var(--brand)" }}> 合同风险</span>
          </Title>

          <Paragraph
            style={{
              maxWidth: 560,
              fontSize: 16,
              lineHeight: 1.92,
              color: "var(--ink-soft)",
            }}
          >
            上传合同，AI 自动逐条审查，生成带法条依据、风险说明与修改建议的结果。它不应该只是一个"会标红的漂亮页面"，而应该是一套真的能进企业流程、能减少返工、能让团队愿意信任的工作系统。
          </Paragraph>

          <Space size={14} style={{ marginTop: 30, flexWrap: "wrap" }}>
            <Button
              type="primary"
              size="large"
              icon={<ArrowRightOutlined />}
              onClick={() => navigate(token ? "/workspace" : "/login")}
              style={{ borderRadius: 999, height: 46 }}
            >
              开始审查
            </Button>
            <Button
              size="large"
              onClick={() => {
                document.getElementById("preview-section")?.scrollIntoView({ behavior: "smooth" });
              }}
              style={{ borderRadius: 999, height: 46 }}
            >
              观看产品演示
            </Button>
          </Space>

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 18,
              marginTop: 24,
              fontSize: 12,
              color: "var(--ink-muted)",
            }}
          >
            <span>法条溯源可追踪</span>
            <span>审查到修改完整闭环</span>
            <span>SaaS 与私有化部署双支持</span>
          </div>
        </div>

        {/* Hero stage — simulated review card */}
        <div style={{ position: "relative", minHeight: 500 }}>
          <Card
            style={{
              borderRadius: 34,
              background: "rgba(255,255,255,0.66)",
              border: "1px solid rgba(24,36,47,0.08)",
              boxShadow: "var(--shadow-lg)",
              padding: 22,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 18,
              }}
            >
              <div style={{ display: "flex", gap: 8 }}>
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 999,
                    background: "rgba(24,36,47,0.12)",
                  }}
                />
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 999,
                    background: "rgba(24,36,47,0.12)",
                  }}
                />
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 999,
                    background: "rgba(24,36,47,0.12)",
                  }}
                />
              </div>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 12px",
                  borderRadius: 999,
                  background: "rgba(241,247,252,0.96)",
                  color: "var(--brand)",
                  fontSize: 11,
                  fontWeight: 700,
                }}
              >
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: 999,
                    background: "linear-gradient(135deg, #6fb8ff, #3e77b0)",
                  }}
                />
                CT-2026-001 审查进行中
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.08fr) 248px", gap: 18 }}>
              {/* Contract preview */}
              <div
                style={{
                  minHeight: 400,
                  padding: "26px 26px 30px",
                  borderRadius: 26,
                  background: "linear-gradient(180deg, #fff, #faf6ef)",
                  border: "1px solid rgba(24,36,47,0.08)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 20,
                    fontSize: 11,
                    color: "var(--ink-muted)",
                  }}
                >
                  <span>采购合同 / PDF / 15 页</span>
                  <span>甲方：粤教科技 · 乙方：广林家具</span>
                </div>
                <div
                  style={{
                    marginBottom: 20,
                    textAlign: "center",
                    fontFamily: "var(--font-serif)",
                    fontSize: 24,
                    fontWeight: 700,
                  }}
                >
                  办公家具采购合同
                </div>

                <div style={{ marginBottom: 22 }}>
                  <h4
                    style={{
                      margin: "0 0 10px",
                      paddingBottom: 6,
                      borderBottom: "1px dashed rgba(24,36,47,0.10)",
                      fontSize: 12,
                      color: "var(--ink)",
                    }}
                  >
                    第三条 付款条件
                  </h4>
                  <p
                    style={{
                      margin: 0,
                      fontFamily: "var(--font-serif)",
                      fontSize: 15,
                      lineHeight: 2,
                      color: "var(--ink-soft)",
                    }}
                  >
                    甲方应于合同签订后三日内支付总额{" "}
                    <span
                      style={{
                        color: "var(--danger)",
                        background:
                          "linear-gradient(180deg, transparent 48%, rgba(176,90,78,0.14) 48%)",
                        padding: "0 2px",
                      }}
                    >
                      50% 作为预付款
                    </span>
                    ；货到验收合格后支付 45%；剩余 5% 于质保期满后支付。
                  </p>
                </div>

                <div style={{ marginBottom: 22 }}>
                  <h4
                    style={{
                      margin: "0 0 10px",
                      paddingBottom: 6,
                      borderBottom: "1px dashed rgba(24,36,47,0.10)",
                      fontSize: 12,
                      color: "var(--ink)",
                    }}
                  >
                    第七条 违约责任
                  </h4>
                  <p
                    style={{
                      margin: 0,
                      fontFamily: "var(--font-serif)",
                      fontSize: 15,
                      lineHeight: 2,
                      color: "var(--ink-soft)",
                    }}
                  >
                    乙方逾期交付超过十五日，甲方有权解除合同，并要求乙方支付总额{" "}
                    <span
                      style={{
                        color: "var(--danger)",
                        background:
                          "linear-gradient(180deg, transparent 48%, rgba(176,90,78,0.14) 48%)",
                        padding: "0 2px",
                      }}
                    >
                      50% 违约金
                    </span>
                    。
                  </p>
                </div>
              </div>

              {/* Risk rail */}
              <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                <div
                  style={{
                    padding: "16px 16px 18px",
                    borderRadius: 20,
                    background: "rgba(255,255,255,0.94)",
                    border: "1px solid rgba(24,36,47,0.08)",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 8,
                      fontSize: 10,
                      fontWeight: 800,
                      letterSpacing: "0.12em",
                      color: "var(--danger)",
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        background: "var(--danger)",
                      }}
                    />
                    HIGH RISK
                  </div>
                  <strong style={{ display: "block", marginBottom: 8, fontSize: 14 }}>
                    预付款比例过高
                  </strong>
                  <p style={{ margin: 0, fontSize: 12, lineHeight: 1.8, color: "var(--ink-soft)" }}>
                    50% 预付款显著高于常见区间，建议降低比例并绑定履约保函或节点验收安排。
                  </p>
                </div>

                <div
                  style={{
                    padding: "16px 16px 18px",
                    borderRadius: 20,
                    background: "rgba(255,255,255,0.94)",
                    border: "1px solid rgba(24,36,47,0.08)",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 8,
                      fontSize: 10,
                      fontWeight: 800,
                      letterSpacing: "0.12em",
                      color: "var(--danger)",
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        background: "var(--danger)",
                      }}
                    />
                    HIGH RISK
                  </div>
                  <strong style={{ display: "block", marginBottom: 8, fontSize: 14 }}>
                    违约金约定过重
                  </strong>
                  <p style={{ margin: 0, fontSize: 12, lineHeight: 1.8, color: "var(--ink-soft)" }}>
                    违约责任表达明显偏重，可能在司法实践中被调减，建议回收至合理范围。
                  </p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Trust ribbon */}
      <section
        style={{
          maxWidth: 1320,
          margin: "0 auto",
          padding: "20px 40px 0",
        }}
      >
        <Row gutter={[14, 14]}>
          {[
            { label: "Review Logic", title: "逐条判断", desc: "不是关键词扫一遍，而是按条款语义、责任关系和上下文结构来审查。" },
            { label: "Action Output", title: "建议可执行", desc: "不仅告诉你哪里有风险，还给出更接近真实业务写法的修改建议。" },
            { label: "Team Workflow", title: "团队可协作", desc: "审查、编辑、复审、定稿、归档，应该是一条完整流程，不是一页孤立报告。" },
            { label: "Enterprise Ready", title: "适合企业上线", desc: "支持权限隔离、审计留痕、多租户管理与后续私有化落地。" },
          ].map((item) => (
            <Col span={6} key={item.title}>
              <Card
                style={{
                  borderRadius: 20,
                  background: "rgba(255,255,255,0.66)",
                  border: "1px solid rgba(24,36,47,0.08)",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <Text
                  style={{
                    display: "block",
                    marginBottom: 6,
                    fontSize: 10,
                    letterSpacing: "0.14em",
                    color: "var(--ink-muted)",
                    textTransform: "uppercase",
                  }}
                >
                  {item.label}
                </Text>
                <Title level={5} style={{ marginBottom: 4 }}>
                  {item.title}
                </Title>
                <Paragraph style={{ margin: 0, fontSize: 12, lineHeight: 1.8, color: "var(--ink-soft)" }}>
                  {item.desc}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* Preview section */}
      <section
        id="preview-section"
        style={{
          maxWidth: 1320,
          margin: "0 auto",
          padding: "88px 40px 0",
        }}
      >
        <div style={{ maxWidth: 650, marginBottom: 30 }}>
          <Text style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
            Product Preview
          </Text>
          <Title level={2} style={{ marginTop: 16, fontFamily: "var(--font-serif)", letterSpacing: "-0.04em" }}>
            一眼看懂产品如何工作
          </Title>
          <Paragraph style={{ fontSize: 15, lineHeight: 1.92, color: "var(--ink-soft)" }}>
            从审查、编辑到报告输出，完整展示产品的核心路径。
          </Paragraph>
        </div>

        <Card
          style={{
            borderRadius: 32,
            background: "rgba(255,255,255,0.72)",
            border: "1px solid rgba(24,36,47,0.08)",
            boxShadow: "var(--shadow-lg)",
            padding: 26,
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.08fr) 316px", gap: 18 }}>
            {/* Document preview */}
            <div
              style={{
                borderRadius: 26,
                background: "linear-gradient(180deg, #fff, #faf7f0)",
                border: "1px solid rgba(24,36,47,0.08)",
                padding: "24px 26px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20, fontSize: 11, color: "var(--ink-muted)" }}>
                <span>合同正文 / 风险标注模式</span>
                <span>实时定位对应条款</span>
              </div>
              <h3 style={{ margin: "0 0 18px", textAlign: "center", fontFamily: "var(--font-serif)", fontSize: 22 }}>
                办公家具采购合同
              </h3>
              <div style={{ marginBottom: 18 }}>
                <h4 style={{ margin: "0 0 10px", fontSize: 12, color: "var(--ink)" }}>第三条 付款条件</h4>
                <p style={{ margin: 0, fontFamily: "var(--font-serif)", lineHeight: 1.95, color: "var(--ink-soft)" }}>
                  甲方应于合同签订后三日内支付总额{" "}
                  <span style={{ color: "var(--danger)", background: "linear-gradient(180deg, transparent 48%, rgba(176,90,78,0.14) 48%)", padding: "0 2px" }}>
                    50% 作为预付款
                  </span>
                  ，建议改为分阶段付款并补充履约保障安排。
                </p>
              </div>
              <div style={{ marginBottom: 18 }}>
                <h4 style={{ margin: "0 0 10px", fontSize: 12, color: "var(--ink)" }}>第七条 违约责任</h4>
                <p style={{ margin: 0, fontFamily: "var(--font-serif)", lineHeight: 1.95, color: "var(--ink-soft)" }}>
                  逾期交付超过十五日，甲方有权解除合同，并要求乙方支付{" "}
                  <span style={{ color: "#a06b2d", background: "linear-gradient(180deg, transparent 48%, rgba(200,135,66,0.16) 48%)", padding: "0 2px" }}>
                    总额 50% 违约金
                  </span>
                  ，系统建议改为更合理区间。
                </p>
              </div>
            </div>

            {/* Risk panel */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 4px 2px" }}>
                <strong style={{ fontSize: 13 }}>风险审查结果</strong>
                <span style={{ fontSize: 11, color: "var(--ink-muted)" }}>5 处提示 / 逐条定位</span>
              </div>

              {[
                { level: "HIGH RISK", color: "var(--danger)", title: "预付款比例过高", desc: "当前比例偏高，建议降至更合理区间，并绑定节点交付或保函安排。", meta: "条款 3.1 · 已关联法条来源" },
                { level: "MEDIUM RISK", color: "var(--accent)", title: "违约金约定需收敛", desc: "系统建议将违约责任调整为与实际损失和司法裁量更匹配的表达。", meta: "条款 7.1 · 可一键应用建议" },
                { level: "LEGAL COMMENT", color: "var(--brand)", title: "保密条款建议设置期限", desc: "除商业秘密外，普通保密信息通常建议约定明确期限、范围和披露例外。", meta: "条款 12.1 · 报告页可查看说明" },
              ].map((risk) => (
                <Card
                  key={risk.title}
                  size="small"
                  style={{
                    borderRadius: 18,
                    background: "#fff",
                    border: "1px solid rgba(24,36,47,0.08)",
                  }}
                >
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      marginBottom: 10,
                      fontSize: 10,
                      fontWeight: 800,
                      letterSpacing: "0.12em",
                      color: risk.color,
                    }}
                  >
                    <span
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 999,
                        background: risk.color,
                      }}
                    />
                    {risk.level}
                  </div>
                  <strong style={{ display: "block", marginBottom: 8, fontSize: 14 }}>
                    {risk.title}
                  </strong>
                  <p style={{ margin: 0, fontSize: 12, lineHeight: 1.76, color: "var(--ink-soft)" }}>
                    {risk.desc}
                  </p>
                  <div style={{ marginTop: 10, fontSize: 11, color: "var(--ink-muted)" }}>
                    {risk.meta}
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </Card>
      </section>

      {/* Capabilities */}
      <section
        style={{
          maxWidth: 1320,
          margin: "0 auto",
          padding: "88px 40px 0",
        }}
      >
        <div style={{ maxWidth: 760, marginBottom: 30 }}>
          <Text style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
            Core Capabilities
          </Text>
          <Title level={2} style={{ marginTop: 16, fontFamily: "var(--font-serif)", letterSpacing: "-0.04em" }}>
            核心能力
          </Title>
          <Paragraph style={{ fontSize: 15, lineHeight: 1.92, color: "var(--ink-soft)" }}>
            从文档进入系统，到风险形成结论，再到建议落地与企业协作，能力是连成一条线的。
          </Paragraph>
        </div>

        <Row gutter={[22, 22]}>
          {[
            {
              num: "01",
              title: "让合同先被看懂，再被判断",
              desc: "系统先把 PDF、Word、扫描件和图片里的正文、条款、表格、主体信息拆出来，再进入后续审查。这样给出的风险判断才不是漂在空中的一句话，而是建立在真实文档结构之上。",
              icon: <FileSearchOutlined style={{ fontSize: 28, color: "var(--brand)" }} />,
            },
            {
              num: "02",
              title: "把风险说清楚，而不是只把条款标红",
              desc: "围绕付款、责任、违约、验收、知识产权、保密等核心条款做上下文判断，并同步挂接法条依据、风险解释与修改建议，让结果更接近真实法务工作方式。",
              icon: <SafetyCertificateOutlined style={{ fontSize: 28, color: "var(--accent)" }} />,
            },
            {
              num: "03",
              title: "把审查结果推进到定稿，而不是停在报告页",
              desc: "审查完成后，系统继续承接修改、复审、版本留痕和团队协作。对于企业来说，真正有价值的不是一份孤立报告，而是一套可以进入内部流程的定稿能力。",
              icon: <TeamOutlined style={{ fontSize: 28, color: "var(--sage)" }} />,
            },
          ].map((cap) => (
            <Col span={8} key={cap.num}>
              <Card
                style={{
                  borderRadius: 30,
                  background: "rgba(255,255,255,0.74)",
                  border: "1px solid rgba(24,36,47,0.08)",
                  boxShadow: "var(--shadow-md)",
                  padding: 28,
                  height: "100%",
                }}
              >
                <div
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 54,
                    height: 54,
                    borderRadius: 18,
                    marginBottom: 20,
                    background: "rgba(45,94,137,0.10)",
                    fontFamily: "var(--font-serif)",
                    fontSize: 24,
                    fontWeight: 700,
                    color: "var(--brand)",
                  }}
                >
                  {cap.num}
                </div>
                <Title level={4} style={{ fontFamily: "var(--font-serif)", letterSpacing: "-0.03em" }}>
                  {cap.title}
                </Title>
                <Paragraph style={{ fontSize: 14, lineHeight: 1.9, color: "var(--ink-soft)" }}>
                  {cap.desc}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* FAQ */}
      <section
        id="faq"
        style={{
          maxWidth: 1320,
          margin: "0 auto",
          padding: "88px 40px 0",
        }}
      >
        <div style={{ maxWidth: 650, marginBottom: 30 }}>
          <Text style={{ fontSize: 11, letterSpacing: "0.16em", textTransform: "uppercase", color: "var(--ink-muted)" }}>
            FAQ
          </Text>
          <Title level={2} style={{ marginTop: 16, fontFamily: "var(--font-serif)", letterSpacing: "-0.04em" }}>
            常见问题
          </Title>
        </div>

        <Row gutter={[18, 18]}>
          {[
            {
              q: "支持哪些合同文件格式？",
              a: "支持 PDF、DOCX、扫描件与常见图片格式（PNG、JPG），上传后自动完成文本提取、结构识别与条款切分。扫描件会按 OCR 质量分层处理，低质量文件会给出明确提示。",
            },
            {
              q: "审查结果是否带法条依据？",
              a: "每条风险都会挂接法条原文、条款编号与适用说明。系统基于 RAG 检索法律法规库，优先引用《民法典》等现行有效法条。无法找到直接依据时会标注「基于法理分析」，不会伪造法条。",
            },
            {
              q: "是否只给风险提示，还是有修改建议？",
              a: "不只标红。每条风险都会同步输出风险解释、法条依据和可执行的修改建议，建议尽量贴近真实业务写法，法务可直接参考或进入编辑流程。",
            },
            {
              q: "是否适合企业团队多人协作？",
              a: "支持多租户隔离、版本留痕、审查日志和权限控制。业务、法务和管理层可以围绕同一份合同连续推进，每次审查形成可回溯的操作痕迹。",
            },
          ].map((item) => (
            <Col span={6} key={item.q}>
              <Card
                style={{
                  borderRadius: 24,
                  background: "rgba(255,255,255,0.72)",
                  border: "1px solid rgba(24,36,47,0.08)",
                  boxShadow: "var(--shadow-sm)",
                  height: "100%",
                }}
              >
                <strong style={{ display: "block", marginBottom: 10, fontSize: 16 }}>
                  {item.q}
                </strong>
                <Paragraph style={{ margin: 0, fontSize: 13, lineHeight: 1.86, color: "var(--ink-soft)" }}>
                  {item.a}
                </Paragraph>
              </Card>
            </Col>
          ))}
        </Row>
      </section>

      {/* CTA */}
      <section style={{ maxWidth: 1320, margin: "0 auto", padding: "88px 40px 70px" }}>
        <Card
          style={{
            position: "relative",
            overflow: "hidden",
            padding: 42,
            borderRadius: 36,
            background:
              "radial-gradient(circle at top right, rgba(200,135,66,0.12), transparent 22%), radial-gradient(circle at left 30%, rgba(45,94,137,0.08), transparent 26%), linear-gradient(180deg, rgba(255,255,255,0.82), rgba(248,244,237,0.92))",
            border: "1px solid rgba(24,36,47,0.08)",
            boxShadow: "var(--shadow-lg)",
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) auto", gap: 24, alignItems: "center" }}>
            <div>
              <Title level={2} style={{ fontFamily: "var(--font-serif)", letterSpacing: "-0.03em" }}>
                开始让每一份合同审查更快、更稳、更可交付
              </Title>
              <Paragraph style={{ maxWidth: 640, fontSize: 14, lineHeight: 1.9, color: "var(--ink-soft)" }}>
                上传合同后即可获得逐条风险说明、法条依据与可执行修改建议，首轮审查、复核和报告输出在一个系统里完成。
              </Paragraph>
            </div>
            <Space>
              <Button
                type="primary"
                size="large"
                icon={<ArrowRightOutlined />}
                onClick={() => navigate(token ? "/workspace" : "/login")}
                style={{ borderRadius: 999, height: 46 }}
              >
                开始体验
              </Button>
            </Space>
          </div>
        </Card>
      </section>

      {/* Footer */}
      <footer style={{ padding: "0 40px 40px", textAlign: "center", fontSize: 11, color: "var(--ink-muted)" }}>
        &copy; 2026 ContractGuard &middot; Enterprise AI Contract Review
      </footer>
    </div>
  );
}
