# CLAUDE.md — ContractGuard AI Agent 治理入口

> 任何 AI Agent 进入本项目，必须首先阅读本文档。
> 完成阅读前，禁止生成代码、修改文件、提出方案。

---

## 1. 项目是什么

ContractGuard 是一套基于大语言模型（LLM）和多 Agent 协作架构的**企业级智能合同风险审查系统**。

- **核心价值**：用户上传合同 PDF → AI 自动逐条审查 → 生成带法条依据的修改建议报告
- **交付形态**：SaaS Web + 微信小程序 + 私有化部署
- **当前阶段**：MVP 文档设计完成，代码尚未开发

---

## 2. 文档导航（必须按顺序阅读）

```
# P0 — 项目级阅读（首次进入必读）
00-README.md                              ← 项目总览、核心指标、阅读指南
03-agent/AGENTS.md                        ← Agent 架构核心（Supervisor+Parser+Analyzer+Report+Validator+Drafter）
04-technical/系统架构设计.md                ← 技术栈、数据流、安全、运维

# P1 — 模块级阅读（按任务涉及模块选读）
01-business/                              ← 商业论证（计划书/模式/定价/竞争）
02-product/PRD.md                         ← 产品需求文档
03-agent/Agent协作协议.md                  ← Agent 间通信协议
03-agent/Agent职责划分.md                  ← 各 Agent 职责矩阵 + 资源配额
04-technical/数据库设计.md                 ← 全部 DDL、索引、RLS 策略
04-technical/接口设计.md                   ← REST + WebSocket API 规范
04-technical/安全设计.md                   ← JWT/CSRF/加密/审计/WSS认证

# P2 — 细节阅读（需要深入了解时）
03-agent/系统提示词设计.md                 ← 各 Agent Prompt 模板
03-agent/工具调用规范.md                   ← RAG/LLM 调用接口
03-agent/Agent评测标准.md                  ← 评测体系 + CI 门禁
03-agent/起草审查闭环与Annotation桥.md      ← 起草-审查四层隔离设计
04-technical/LLM Unified Wrapper Layer Design.md  ← 多模型适配 + 重试 + 成本追踪
```

---

## 3. 技术栈速查

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Ant Design + TipTap 编辑器 |
| 后端 | Python FastAPI + SQLAlchemy + Alembic |
| 消息队列 | Redis Streams（开发单节点，生产 Sentinel+NATS） |
| 数据库 | PostgreSQL 15（pgvector）+ Redis + Milvus + Elasticsearch |
| 文件存储 | MinIO（S3 兼容） |
| LLM | MiMo 2.5（法律分析主模型）+ DeepSeek V4-Flash（辅助） |
| Embedding | BGE-M3 |
| 部署 | Docker Compose（开发）→ K8s（生产） |
| 监控 | Prometheus + Grafana + structlog → Loki |

---

## 4. 执行规范（修改代码时必须遵守）

### 允许做的事
- 在已有文件上做最小修改
- 新增文档文件（.md）
- 新增配置项（.env.example / docker-compose.yml）
- 新增测试用例
- 启动前先输出修改计划，用户确认后执行

### 禁止做的事
- 禁止提前抽象（不到 3 处重复不提取公共模块）
- 禁止顺手重构（需求没要求的不碰）
- 禁止乱加依赖（必须通过 pyproject.toml 或 package.json 管理）
- 禁止跨模块修改（只改需求涉及的模块）
- 禁止跳过阅读直接写代码

### 修改原则
```
最小修改优先 → 一致性优先于优雅性 → 可回滚优先于完美
```

---

## 5. 测试规范（改完必须验证）

### 自动化检查
- 文档修改：`grep -r` 确认所有交叉引用文件存在（README 导航 ≠ 死链接）
- 代码修改：`ruff check` + `pytest` + Type A 幻觉检测规则引擎

### 手动检查清单
```
□ 所有变动的 .md 文件章节编号是否连续？
□ 数据库 DDL 字段是否与接口设计对齐？
□ 配置值是否与编码规范一致（如 line-length = 100）？
□ .env.example 是否包含所有必填项？
□ docker-compose 所有服务是否有 healthcheck？
□ 所有多租户表是否有 RLS 策略？
```

---

## 6. 已知 Gap（需要知道但暂时不做）

| Gap | 当前方案 | 计划 |
|---|---|---|
| API Gateway | FastAPI 中间件 | Phase 2 引入 Kong |
| Redis HA | 单节点 | Phase 2 Sentinel + NATS |
| JWT 签名算法 | HS256 | 生产切换 RS256 |
| 评测数据集 | 50 条标注用例 | Phase 2 扩充到 700 份 |
| 微信小程序 | 未开发 | M5 里程碑 |
| 英文文档 | main 分支落后 | 待同步 |

---

## 7. 输出规范（完成任务后必须汇报）

每次完成实质性修改后，输出格式：
```
## 已完成
- 改了什么文件、为什么改

## 修改范围
- 影响到的其他文档/模块

## 测试结果
- 跑了什么检查、结果如何

## 风险提示
- 有没有引入新矛盾或遗漏
```

---

## 8. Git 推送规则

```
master 分支（中文） → git push gitee master && git push github master
main 分支（英文）  → git push github main
提交信息：Gitee 用中文，GitHub 用英文
```
