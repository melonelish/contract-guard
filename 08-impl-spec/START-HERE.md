# START-HERE — 编码顺序指南

> Agent 先读这个文件，然后按 Phase 顺序执行。每个 Phase 只读对应的小文件 + 01-07 中引用的架构文档。

---

## Phase 1：项目骨架 + 数据库（约 2 小时）

**读**：
- `01-project-structure.md` → 目录树
- `04-technical/数据库设计.md` → DDL 直接复制
- `.env.example` → 环境变量

**做**：
1. 按目录树创建 `backend/` 和 `frontend/` 骨架
2. 写 `pyproject.toml` + `package.json`（依赖从现有文档汇总）
3. 写 `backend/app/config.py`（从 `05-integration.md` 复制 Settings 类）
4. 写 `backend/app/db/session.py` + `models.py`（从数据库设计 DDL 转 SQLAlchemy）
5. 写 `docker-compose.yml`（从现有文档汇总）
6. Alembic init + 第一个 migration

**验证**：`docker compose up -d postgres redis` → `alembic upgrade head` → 表建好

---

## Phase 2：Agent 框架（约 3 小时）

**读**：
- `02-agent-framework.md` → Agent 基类 + Orchestrator 接口
- `03-agent/AGENTS.md` → 各 Agent 的职责和 I/O
- `03-agent/Agent职责划分.md` → 并发、超时、重试配置

**做**：
1. 写 `backend/app/core/agent.py`（WorkerAgent ABC）
2. 写 `backend/app/core/message_bus.py`（Redis Streams 封装）
3. 写 `backend/app/core/state_machine.py`（从 `03-state-machine.md` 复制）
4. 写 `backend/app/schemas/agent.py`（Agent I/O Pydantic 模型）
5. 写 `backend/app/core/orchestrator.py`（ReviewOrchestrator）
6. 写 `backend/app/core/supervisor.py`（SupervisorAgent）

**验证**：单元测试 — mock LLM 后跑一个最小审查流程

---

## Phase 3：LLM 层 + RAG（约 2 小时）

**读**：
- `04-technical/LLM Unified Wrapper Layer Design.md` → 统一接口
- `03-agent/工具调用规范.md` → rag_search 工具

**做**：
1. 写 `backend/app/llm/wrapper.py`（llm_chat / llm_embed）
2. 写 `backend/app/llm/registry.py`（模型注册表）
3. 写 `backend/app/llm/circuit_breaker.py`（熔断器）
4. 写 `backend/app/rag/search.py`（hybrid_search）
5. 写 `backend/app/rag/embed.py`（嵌入向量生成）

**验证**：调用 `llm_chat()` 返回结果，不报错

---

## Phase 4：第一个 Agent — Parser（约 2 小时）

**读**：
- `03-agent/AGENTS.md` Parser 章节
- `03-agent/系统提示词设计.md` Parser prompt

**做**：
1. 写 `backend/app/agents/parser.py`
2. 写 `backend/app/utils/pdf.py`（PDF 文本提取）
3. 写 Parser 的 Redis Stream 消费者

**验证**：上传一份测试 PDF → Parser Agent 解析出条款 → 条款存入 DB

---

## Phase 5：Analyzer + Report + Validator（约 3 小时）

**读**：
- `03-agent/AGENTS.md` 各 Agent 章节
- `03-agent/系统提示词设计.md` 各 Agent prompt

**做**：
1. 写 `backend/app/agents/analyzer.py`
2. 写 `backend/app/agents/report.py`
3. 写 `backend/app/agents/validator.py`
4. 串联完整审查流水线

**验证**：端到端测试 — 上传 PDF → 审查完成 → 返回报告 JSON

---

## Phase 6：API 层（约 2 小时）

**读**：
- `04-technical/接口设计.md` → 端点定义
- `04-technical/安全设计.md` → JWT + WebSocket 认证
- `05-integration.md` → 缺失的请求/响应体 + 错误码

**做**：
1. 写 `backend/app/api/deps.py`（get_db, get_current_user, get_redis）
2. 写 `backend/app/api/v1/auth.py`
3. 写 `backend/app/api/v1/contracts.py`
4. 写 `backend/app/api/v1/reviews.py`
5. 写 `backend/app/api/v1/health.py`
6. 写 `backend/app/services/auth.py` + `contract.py` + `review.py`

**验证**：`curl` 测试注册 → 登录 → 上传 → 触发审查 → 查询结果

---

## Phase 7：前端基础（约 3 小时）

**读**：
- `02-product/原型设计说明.md` → 页面路由
- `02-product/双屏对比与差异可视化设计.md` → 组件规格
- `04-technical/preview/index.html` → 设计系统

**做**：
1. 初始化 Vite + React + Ant Design + Zustand
2. 写 `src/api/client.ts`（Axios + JWT 拦截器）
3. 写 `src/api/types.ts`（TypeScript 类型）
4. 写 `src/stores/auth.ts` + `contract.ts` + `review.ts`
5. 写登录页 + 合同列表页

**验证**：登录 → 看到合同列表 → 上传合同

---

## Phase 8：审查 + 编辑（约 4 小时）

**读**：
- `02-product/双屏对比与差异可视化设计.md` → DiffViewer + ContractEditor
- `03-agent/起草审查闭环与Annotation桥.md` → Drafter 流程

**做**：
1. 写 `useWebSocket.ts` hook
2. 写 ReviewReport 组件
3. 写 DiffViewer 组件
4. 写 ContractEditor（TipTap）
5. 写 Drafter Agent

**验证**：触发审查 → 实时进度 → 查看报告 → 编辑 → 重新审查

---

## 每个 Phase 的原则

1. **先跑通再完善** — Phase 1-5 可以用 mock 数据跑通，不需要真实 LLM
2. **读 01-07 获取 why，读 08 获取 what** — 08 只补充 01-07 没有的实现细节
3. **每个 Phase 结束必须有验证步骤** — 跑不通就不进入下一个 Phase
4. **遇到 08 和 01-07 不一致时，以 01-07 为准** — 01-07 是设计源头，08 是补充
