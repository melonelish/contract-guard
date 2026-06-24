# 更新日志

## Phase 4 - 2026-06-22

### 新增

- 创建 `backend/app/services/queue.py` — Redis Stream 任务队列 + Pub/Sub 事件发布。review 任务通过 `enqueue_review_task()` 投递到 Redis Stream（`review:tasks`），进度事件通过 `publish_stage_event()` / `publish_complete_event()` / `publish_failed_event()` 发布到 `review:{id}:events` 频道。
- 创建 `backend/app/services/worker.py` — 后台 Worker 消费者，启动时自动创建 Redis Stream Consumer Group，循环读取任务并调用 `run_real_review()`。支持启动/停止生命周期管理。
- 创建 `backend/app/api/v1/ws.py` — WebSocket 实时进度端点。实现 ticket-in-query 认证方案（HMAC-SHA256 签名、60 秒 TTL、一次性使用），连接后订阅 Redis Pub/Sub 频道并转发事件到客户端。支持心跳保活和最大 30 分钟连接时长。
- 后端新增 `POST /api/v1/reviews/ws/ticket` 接口：签发 WebSocket 票据，绑定 user_id + review_id。
- 后端 `POST /api/v1/contracts/{id}/review` 改为 Redis Stream 投递，不再依赖 FastAPI BackgroundTasks（请求生命周期解耦）。
- 审查管线每个阶段转换时自动发布 Redis Pub/Sub 事件（parsing → analyzing → reporting → validating → completed/failed）。
- `ErrorCode` 枚举新增 `WS_TICKET_INVALID (5001)`、`WS_TICKET_EXPIRED (5002)`、`WS_TICKET_USED (5003)`。
- 前端 `stores/review.ts` 新增 `connectReviewWS()` 方法，实现 WebSocket 优先 + 轮询降级策略。
- 前端合同详情页显示实时连接模式标签（"实时" / "轮询"），WebSocket 连接成功后显示绿色 WifiOutlined 图标。
- 前端 `api/types.ts` 新增 `WSTicket`、`WSStageEvent`、`WSCompleteEvent`、`WSFailedEvent`、`WSPingEvent` 类型定义。
- 创建 `backend/tests/test_ws.py` — 覆盖 ticket 签发/校验、过期/重放/篡改防护、队列入队/发布、Worker 启停、事件结构契约等测试用例。

### 更新

- `backend/app/api/v1/contracts.py` — `trigger_review` 移除 `BackgroundTasks` 参数，改用 `enqueue_review_task()` 投递到 Redis Stream。
- `backend/app/services/review.py` — `run_real_review()` 每个阶段转换时调用 `_publish_stage()` / `_publish_complete()` / `_publish_failed()` 发布 Redis 事件。
- `backend/app/api/v1/reviews.py` — 新增 `POST /reviews/ws/ticket` 端点。
- `backend/app/main.py` — 注册 WS 路由（`/ws` 前缀），startup 时初始化 Redis Stream Group 并启动 Worker，shutdown 时停止 Worker 并关闭 Redis 连接。
- `backend/app/schemas/api.py` — 新增 `WSTicketPayload` schema。
- `backend/app/schemas/errors.py` — 新增 WS 错误码。
- `backend/pyproject.toml` — 新增 `redis>=5.0.0` 依赖。
- `.env.example` — 新增 `WS_TICKET_TTL`、`WS_MAX_DURATION` 配置说明。
- `frontend/src/pages/ContractDetailPage.tsx` — 重写进度监控逻辑：WebSocket 优先连接，3 秒内未成功自动降级为 HTTP 轮询（1.5s 间隔）。
- `backend/tests/test_reviews.py` — `test_trigger_review` 适配队列化改造。

### 说明

- 开发环境使用单节点 Redis，Worker 作为 asyncio Task 运行在 FastAPI 进程内。生产环境可部署独立 Worker 进程。
- WebSocket 认证采用一次性票据方案（安全设计.md §7），票据 HMAC 签名基于 JWT_SECRET，60 秒 TTL，Redis SET NX 保证一次性使用。
- 前端 WebSocket 断开后自动降级为 HTTP 轮询，确保审查进度始终可达。
- 服务重启时，Redis Stream 中未消费的任务会被 Worker 自动拾取；DB 中 stuck 的 running 状态 review 会被恢复为 failed。
- Redis Pub/Sub 为 fire-and-forget，事件不持久化。如果前端在事件发布前未连接 WebSocket，可通过轮询获取最终状态。

---

## Phase 3 - 2026-06-18

### 新增

- 新增 `law_articles` 数据库表（含 law_name、article_number、full_text、search_vector tsvector 等字段）与 Alembic 迁移（20260619_0003）。
- 创建 `scripts/law_corpus.json` — 民法典合同编 + 劳动合同法核心条文语料（43 条）。
- 创建 `scripts/import_laws.py` — 法条导入脚本，支持 PostgreSQL 全文检索向量自动生成。
- 创建 `backend/app/services/rag.py` — RAG 检索服务：extract_search_queries（从合同文本提取检索词）、search_law_articles（PostgreSQL tsvector 全文检索）、format_law_context（格式化 LLM 上下文）、format_law_basis_for_risk（为每条风险匹配最相关法条）。
- 重写审查管线 SYSTEM_PROMPT：要求 LLM 输出 legal_basis / basis_excerpt / basis_source 字段。
- 重写 USER_PROMPT_TEMPLATE：支持注入 law_context（RAG 检索结果）。
- 审查管线在 analyzing 阶段新增 RAG 检索步骤：提取检索词 → 检索法条 → 注入 LLM 上下文。
- 每条风险自动匹配最相关法条依据（基于关键词匹配 + 相关性评分）。
- 报告新增 `rag_meta` 字段：enabled / hit_count / mode / queries。
- 后端 schemas 新增 `ReviewRAGMetaPayload`，`ReviewRiskItem` 新增 legal_basis / basis_excerpt / basis_source。
- 前端报告页新增 RAG 元信息展示（审查模式、命中依据条数）。
- 前端每条风险卡片新增"法条依据"区块（含依据、条文摘录、来源）。
- 无依据风险显示"依据不足，基于法理分析"黄色提示。

### 更新

- `backend/app/services/review.py` — 集成 RAG 检索到审查管线，更新 clean_report 确保 legal_basis 字段存在。
- `backend/app/schemas/api.py` — ReviewRiskItem 新增 3 个字段，ReviewReportPayload 新增 rag_meta。
- `backend/app/api/v1/reviews.py` — 响应中包含 rag_meta。
- `frontend/src/api/types.ts` — ReviewRiskItem 新增 legal_basis / basis_excerpt / basis_source，新增 ReviewRAGMeta，ReviewReport 新增 rag_meta。
- `frontend/src/pages/ReviewReportPage.tsx` — 风险卡片展示法条依据，报告顶部展示 RAG 元信息。
- `backend/tests/test_reviews.py` — 测试数据更新，包含 legal_basis 和 rag_meta。
- `.env.example` — 新增 RAG 配置说明。

### 说明

- RAG 使用 PostgreSQL 内置全文检索（tsvector + tsquery），无需外部向量数据库或 Embedding 服务。
- 法条语料覆盖民法典合同编核心条文（33 条）+ 劳动合同法关键条文（10 条）。
- 检索策略：从合同文本中提取法律关键词（违约金、格式条款、质量标准等），用 OR 组合查询。
- 无匹配法条时，风险标记为"依据不足，基于法理分析"，不会伪造法条。
- RAG 失败为非致命错误，自动降级为模型直审模式。

---

## Phase 2 - 2026-06-18

### 新增

- 创建 `backend/app/llm/` 模块：统一封装层，支持 model/timeout/retry/error mapping/raw response logging。
- `backend/app/llm/client.py` — `llm_chat()` 单入口，OpenAI SDK 兼容，自动 fallback（MiMo ↔ DeepSeek），指数退避重试（最多 2 次），rate limit / timeout / connection error 分类处理。
- `backend/app/llm/config.py` — 模型注册表，从 `.env` 读取 API key / base URL / model ID。
- `backend/app/llm/exceptions.py` — `LLMError` / `LLMTimeoutError` / `LLMUnavailableError` / `LLMResponseError`。
- 创建 `backend/app/services/parser.py` — 文档文本提取服务：PDF（pypdf）、DOCX（python-docx）、图片（拒绝+明确错误）。
- 重写 `backend/app/services/review.py` — 将 `run_mock_review` 替换为 `run_real_review`，实现真实 LLM 审查管线。
- 审查管线阶段：parsing（文本提取）→ analyzing（LLM 分析）→ reporting（JSON 解析）→ validating（schema 校验）→ completed/failed。
- 新增报告 schema 校验层 `validate_report_schema()`：校验 summary/risks 必填字段、risk_level 合法性、confidence 范围。
- 新增报告清洗层 `clean_report()`：重新计算 summary 统计、填充缺失字段默认值、注入免责声明。
- LLM 输出 JSON 解析失败时尝试从 markdown code block 中提取，仍失败则标记 failed。
- schema 校验失败时自动重试一次（temperature=0），仍失败则标记 failed。
- `backend/app/config.py` 新增 LLM 配置字段：`mimo_api_key`、`mimo_base_url`、`mimo_model`、`deepseek_api_key`、`deepseek_base_url`、`deepseek_model`。

### 更新

- `backend/app/api/v1/contracts.py` — `trigger_review` 调用 `run_real_review` 并传递 `file_url`、`file_type`。
- `backend/pyproject.toml` — 新增 `openai>=1.30.0`、`pypdf>=4.2.0`、`python-docx>=1.1.0` 依赖。
- `backend/tests/test_reviews.py` — mock 目标从 `run_mock_review` 更新为 `run_real_review`。

### 说明

- 当前 MiMo API key 为占位符（`sk-your-mimo-api-key`），真实 LLM 调用会返回 401。
- 填入真实 API key 后，审查管线即可端到端运行。
- 图片格式（png/jpg/jpeg）暂不支持真实解析，会返回明确错误提示。
- 前端页面无需任何改动，继续复用 Phase 1 的报告渲染逻辑。

---

## Phase 1 - 2026-06-18

### 新增

- 新增 `reviews` 数据库表（含 contract_id、status、progress、report_json、schema_version 等字段）与 Alembic 迁移。
- 后端新增 `POST /api/v1/contracts/{id}/review` 接口：发起审查（含同合同并发拦截，返回 409）。
- 后端新增 `GET /api/v1/reviews/{id}` 接口：获取完整审查报告（含 risks、contradictions、missing_clauses、disclaimer）。
- 后端新增 `GET /api/v1/reviews/{id}/status` 接口：轻量轮询审查进度。
- 实现 mock 审查后台任务：自动推进 parsing→analyzing→reporting→validating→completed，生成带 `schema_version` 的固定结构报告。
- 后端启动时自动恢复卡死的 running 状态审查（标记为 failed）。
- 前端合同详情页新增"发起审查"按钮与实时进度条（轮询模式）。
- 前端新增审查报告页（`/reviews/:id`），渲染风险清单、统计概览、条款矛盾、缺失条款与免责声明。
- 前端合同列表页显示每份合同的最近审查状态（未审查/审查中/审查完成/审查失败）。
- 合同列表接口返回 `latest_review` 字段，含审查状态与风险统计摘要。
- 新增 review 相关 TypeScript 类型定义（Review、ReviewReport、ReviewRiskItem 等）。
- 新增 review Zustand store（triggerReview、fetchReport、pollStatus）。
- 新增 6 个 review API 测试用例，覆盖触发、冲突、报告、状态、未找到等场景。

### 更新

- `ErrorCode` 枚举新增 `REVIEW_NOT_FOUND (4001)`、`REVIEW_IN_PROGRESS (4002)`、`REVIEW_FAILED (4003)`、`LLM_UNAVAILABLE (4004)`。
- `ContractPayload` 新增可选 `latest_review` 字段。
- 合同详情页重写：移除 Phase 0 占位内容，接入真实审查流程。
- 合同列表页重写：显示审查状态标签与"查看报告"快捷入口。
- `test_contracts.py` 适配新接口，补充 `get_latest_reviews_for_contracts` mock。

### 说明

- 当前审查为 mock 实现，不调用真实 LLM，报告结构尽量贴近黄金样例。
- 审查进度采用 HTTP 轮询（1.5s 间隔），Phase 2 可切换为 WebSocket 推送。
- mock 报告包含 4 条风险（2 高 1 中 1 低）、1 条交叉矛盾、2 条缺失条款。

---

## Phase 0 - 2026-06-18

### 新增

- 搭建 `backend/` FastAPI 服务骨架，补齐认证、合同列表/详情、健康检查与基础异常结构。
- 新增 Alembic 初始化迁移、SQLAlchemy 模型和测试用例，完成 Phase 0 的最小后端闭环。
- 搭建 `frontend/` React + TypeScript + Ant Design 工作台，提供登录、合同列表、合同详情三类基础页面。
- 新增前端状态管理与 API 客户端，为后续真实审查流程接入预留接口。
- 增加开发期 `Dockerfile`、前后端联调配置、`Makefile` 与示例环境变量，降低本地启动成本。
- 新增多份技术与实现规格文档，补齐 API 契约、错误处理、测试夹具、页面状态机与多版预览稿。

### 更新

- 修订 `00-README.md`、`04-technical/`、`08-impl-spec/` 等核心文档，使 Phase 0 的代码落地与文档设计保持一致。
- 补充仓库级治理入口 `AGENTS.md` 与 `CLAUDE.md`，统一 Agent 阅读顺序和执行边界。
- 调整 `.gitignore`，排除日志、前端构建产物、依赖目录、测试缓存和临时 PDF，避免将本地产物推送到远程。

### 说明

- 当前为 Phase 0 基础设施与工作台落地版本，重点在于把开发骨架、接口雏形和文档契约跑通。
- 后续 Phase 1 可在此基础上继续接入真实上传、审查编排和报告生成链路。
