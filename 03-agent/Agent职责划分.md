# Agent 职责划分

> 版本：v1.0 | 最后更新：2026-06-15

---

## 一、职责矩阵

| Agent | 职责 | 输入 | 输出 | 严禁行为 |
|---|---|---|---|---|
| **Supervisor** | 任务调度、分发、汇总 | 用户请求 | 完整审查报告 | 不做内容分析 |
| **Parser** | 文档结构化 | 原始文件字节流 | 结构化 JSON | 不做法律判断 |
| **Analyzer** | 条款风险分析 | 单条款 JSON | 风险分析结果 | 不编造法条 |
| **Report** | 报告生成 | 分析结果集合 | 审查报告 JSON | 不改分析结果 |
| **Validator** | 质量校验 | 审查报告 | 通过/不通过 | 不修改内容 |

---

## 二、拆 Agent 的决策依据

### 为什么拆成 5 个而不是 1 个？

| 考虑维度 | 1 个 Agent | 5 个 Agent（本方案） |
|---|---|---|
| **Prompt 复杂度** | 5000+ tokens 的一个超长 prompt | 每个 Agent 独立优化 500-1000 tokens |
| **可调试性** | 一条结果出错，排查全局 | 哪个环节出错定位到对应 Agent |
| **可替换性** | 改任何逻辑都要改整个 prompt | 改进 RAG 策略？只改 Analyzer。改进报告格式？只改 Report |
| **并行能力** | 只能串行 | Analyzer 可并行分析 50 条条款 |
| **评测粒度** | 只能端到端评测 | 每个 Agent 独立评测，精确知道瓶颈在哪 |
| **Token 消耗** | 长上下文 = 更多 Token 浪费 | 每个 Agent 只传必要数据 |

### 为什么不再拆得更细？

| 候选拆分 | 不拆的理由 |
|---|---|
| 法条检索Agent + 风险评估Agent 独立 | 法条检索和风险评估存在推理依赖，拆开反而增加消息传递开销 |
| 交叉校验独立成Agent | 交叉校验的分析深度与单条款分析相同，共用同一套 RAG，复用量大 |
| 表格解析独立Agent | 表格解析是 Parser 的子任务，依赖版面分析上下文，独立反而丢信息 |

---

## 三、每个 Agent 的资源配额

| Agent | 最大并发 | 单次超时 | 内存限制 | 重试次数 |
|---|---|---|---|---|
| Supervisor | 1（单实例） | - | 512MB | - |
| Parser | 5 | 120s | 1GB | 2 |
| Analyzer | 20 | 60s | 512MB | 3 |
| Report | 5 | 60s | 512MB | 2 |
| Validator | 3 | 30s | 256MB | 1 |

### 并发控制（防止 LLM API 超额）

```
全局 LLM Token 消耗速率上限：100,000 TPM

分配策略：
  Parser:    10,000 TPM (10%)
  Analyzer:  70,000 TPM (70%) ← 主力消耗
  Report:    15,000 TPM (15%)
  Validator:  5,000 TPM (5%)

当任一 Agent 达到配额 → 等待，不对全系统降级
```

---

## 四、Agent 的可观测性

### 每个 Agent 必须暴露

```json
{
  "agent_id": "analyzer-03",
  "task_id": "task-abc123",
  "started_at": "2026-06-15T10:30:00Z",
  "completed_at": "2026-06-15T10:30:45Z",
  "duration_ms": 45000,
  "llm_calls": [
    {
      "model": "gpt-4o",
      "prompt_tokens": 1200,
      "completion_tokens": 450,
      "duration_ms": 3800
    }
  ],
  "rag_calls": 2,
  "status": "completed"
}
```

这些数据聚合到 LangSmith（或自建 Trace 系统），提供：
- 全链路追踪：一步步看到 5 个 Agent 的执行过程
- 耗时分析：哪个 Agent 最慢
- Token 消耗：哪条条款用了最多 Token
