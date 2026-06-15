# 为什么不用 LangChain/LangGraph — 自研 Agent 编排说明

> 版本：v1.0 | 最后更新：2026-06-15
> 归属：FAQ + 面试话术

---

## 一、LangChain/LangGraph 定位

LangChain/LangGraph **不是 AI 大模型开发的核心知识**。它们是**框架**，类似前端领域的 React/Vue —— 帮你省样板代码，但不代表原理。

真正的 AI Agent 核心能力：

```
Agent 开发核心能力
├── 任务拆解（Task Decomposition）         —— 框架帮不了你
├── 工具选择（Function Calling / Tool）     —— OpenAI SDK 原生支持
├── 上下文管理（Memory / State）            —— 自己写更灵活
├── 多 Agent 协作（Orchestration Pattern） —— 框架反而限制你
├── RAG 架构（Hybrid Retrieval + Rerank）  —— 框架只省 20 行代码
├── 幻觉控制（Hallucination Mitigation）   —— 框架完全没有
└── 评测体系（Evaluation）                  —— 框架完全没有
```

---

## 二、自研 vs LangChain 对比

| 维度 | LangChain/LangGraph | ContractGuard 自研方案 |
|---|---|---|
| **代码量** | 少（框架封装了） | 稍多（~300 行 Python Agent 编排类） |
| **可控性** | 黑盒（AgentExecutor 内部状态不可见） | 完全透明，每步都能打日志 |
| **面试能讲的** | "我用 LangChain 搭的 Agent" | "我设计的 Supervisor-Worker 模式，Redis Streams 消息中间件，每个 Agent 独立 System Prompt 和知识库" |
| **面试官反应** | "哦，调包侠" | **"这人真的懂 Agent 原理"** |
| **版本风险** | LangChain 0.1→0.3 全 Breaking Change | 自己写的永远不坑自己 |
| **调试难度** | Agent 死循环 → 很难定位 | 每条消息都在 Redis Stream 里有记录 |
| **定制灵活性** | 受框架 API 约束 | 完全自由 |
| **适用场景** | 快速原型验证 | **生产级企业交付 ← 本项目** |

---

## 三、自研 Agent 编排层架构

### 3.1 核心组件（~300 行 Python）

```
contractguard/core/agent_orchestrator.py
├── class SupervisorAgent       ← 任务调度中心
├── class WorkerAgent           ← 抽象基类（Parser/Analyzer/Report 都继承它）
├── class MessageBus            ← Redis Streams 封装
├── class AgentRegistry         ← Worker 注册/发现/心跳
└── class TaskContext            ← 任务上下文（task_id + 状态 + 重试计数）
```

### 3.2 为什么不直接调 API

```
❌ 简单调用链：
Parser(data) → Analyzer(clauses) → Report(results) → 返回

问题：
  - Parser 超时 → 整个请求挂
  - 无法并行处理条款
  - 中间任何一步失败 → 从头再来
  - 无法观察每步的耗时/成本

✅ Redis Streams 方案：
Supervisor ──XADD──▶ parser:tasks ──▶ Parser Worker
         ◀──XREAD── parser:results

Supervisor ──XADD──▶ analyzer:tasks ──▶ 10 个 Analyzer Worker 并行
         ◀──XREAD── analyzer:results     (Redis Consumer Group 自动负载均衡)

优势：
  - 解耦：Supervisor 不关心有多少个 Worker
  - 持久化：消息在 Redis 里，Worker 挂了也能恢复
  - 可观测：每条消息的发送/处理/完成时间都在 Stream 里
  - 水平扩展：加 Worker 只需启动新容器，改一行都不用
```

### 3.3 与 LangGraph 的 StateGraph 思想对比

LangGraph 的核心设计是**用图来管理 Agent 的状态流转**：

```python
# LangGraph 方式
graph = StateGraph(AgentState)
graph.add_node("parser", run_parser)
graph.add_node("analyzer", run_analyzer)
graph.add_node("report", run_report)
graph.add_edge("parser", "analyzer")
graph.add_conditional_edges("analyzer", check_confidence, {
    "high": "report",
    "low": "parser"  # 回头重解析
})
```

ContractGuard 的 Agent 协作相对固定（Parser → Analyzer → Report → Validator），不需要动态图：

```python
# ContractGuard 方式（Pipeline + 并行）
results = await orchestrator.run_pipeline([
    ParserTask(file),
    ParallelAnalyzerTask(clauses, max_concurrency=10),
    CrossValidateTask(),
    ReportTask(),
    ValidateTask(),
])
# 简单直接，所有状态在 TaskContext 里
```

**决策逻辑**：如果未来需要复杂条件分支（比如"审查不通过时回退到哪一步取决于风险类型"），会引入类似 StateGraph 的思想，但底层还是自己控制。

---

## 四、常见质疑与回应

### Q：你不用 LangChain，RAG 怎么做的？

> LangChain 的 RAG 封装了文档加载 → 切片 → 向量化 → 检索这四个步骤。我用 Unstructured.io 做解析、自研语义切片（识别条款边界后切、不是固定字数）、BGE-M3 做 Embedding、Milvus 做向量存储。混合检索是自研的——语义检索 + BM25 关键词 + 结构化 SQL，三路召回后用 Reciprocal Rank Fusion 重排序。LangChain 在每一步只省了 5-10 行代码，代价是把整个流程锁死在它的抽象里。

### Q：你不用 LangSmith，怎么观测 Agent？

> OpenTelemetry + 自建 Trace。每条 Agent 调用都记录：task_id → agent_name → input → output → latency → token_cost。效果跟 LangSmith 一样，但数据在我自己这里，不依赖 SaaS，没有数据泄露风险。

### Q：你不会 LangChain，去公司了怎么办？

> LangChain 的核心思想我全懂——Agent / Tool / Chain / Memory / RAG——只是没用它封装好的 API。给我一个下午看文档，第二天就能上手。框架是术，Agent 设计是道。我证明了我有道。

### Q：你们为什么不用 Dify/Coze 这种零代码平台？

> Dify 和 Coze 适合非技术人员快速搭建智能客服，不适合我们的场景。合同审查需要：① 自定义的多 Agent 协作架构 ② 细粒度的知识库分层和混合检索 ③ 幻觉控制和安全护栏 ④ 结构化 diff 输出 ⑤ 内置编辑器和打印功能。这些在低代码平台上要么做不到，要么需要大量 Hack。

---

## 五、面试完整话术

> "我没有用 LangChain。LangChain 本质是一个框架，帮开发者省了 Agent 循环和工具调用的样板代码。但它的抽象层太重，出了问题很难定位——比如 Agent 死循环了，LangChain 的 AgentExecutor 内部状态你看不到。
>
> 我选择自己写 Agent 编排层，核心就 300 行 Python。架构是 Supervisor-Worker 模式：Supervisor 负责任务拆解和分发，Worker 通过 Redis Streams 消息队列接收任务，Consumer Group 自动负载均衡。每个 Worker Agent 有独立的 System Prompt 和知识库，LLM 调用封装了统一层，支持 MiMo 2.5 和 DeepSeek V4-Flash 热切换。
>
> 我也研究过 LangGraph 的 StateGraph 设计思想——用图管理 Agent 状态流转。但我项目的 Agent 协作相对固定（Parser → Analyzer → Report → Validator），不需要动态图，一个简单的 Pipeline + 并行调用就够了。如果未来需要复杂条件分支，我会考虑引入 StateGraph 思想，但底层还是自己控制。
>
> RAG 部分也没用 LangChain 的封装。Unstructured.io 做文档解析，自研基于条款边界的语义切片，BGE-M3 做 Embedding，Milvus 做向量存储，混合检索是三路召回 + Reciprocal Rank Fusion 重排序。可观测性用 OpenTelemetry + 自建 Trace，所有 Agent 调用都有完整的 task_id → agent → latency → cost 链路。
>
> 总结：我对 LangChain 的理念完全理解，选择自研不是为了炫技，是为了在生产环境里能够精确控制每一步行为，出了问题能在 5 分钟内定位。"

---

## 六、参考资源

- LangChain 官方文档：https://python.langchain.com/
- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- Anthropic Building Effective Agents：https://www.anthropic.com/engineering/building-effective-agents
- Redis Streams 文档：https://redis.io/docs/latest/develop/data-types/streams/
