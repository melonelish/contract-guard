# Agent Role Division

> Version: v1.0 | Last Updated: 2026-06-15

---

## 1. Responsibility Matrix

| Agent | Responsibility | Input | Output | Strictly Forbidden |
|---|---|---|---|---|
| **Supervisor** | Task scheduling, distribution, aggregation | User request | Complete review report | Must not perform content analysis |
| **Parser** | Document structuring | Raw file byte stream | Structured JSON | Must not make legal judgments |
| **Analyzer** | Clause risk analysis | Single clause JSON | Risk analysis result | Must not fabricate legal provisions |
| **Report** | Report generation | Collection of analysis results | Review report JSON | Must not modify analysis results |
| **Validator** | Quality validation | Review report | Pass/Fail | Must not modify content |

---

## 2. Rationale for Splitting Agents

### Why 5 Agents Instead of 1?

| Consideration | 1 Agent | 5 Agents (Our Approach) |
|---|---|---|
| **Prompt Complexity** | One ultra-long prompt of 5000+ tokens | Each Agent independently optimized at 500-1000 tokens |
| **Debuggability** | One wrong result, must troubleshoot globally | Pinpoint which step failed to the corresponding Agent |
| **Replaceability** | Changing any logic requires editing the entire prompt | Improve RAG strategy? Only modify Analyzer. Improve report format? Only modify Report |
| **Parallelism** | Sequential only | Analyzer can analyze 50 clauses in parallel |
| **Evaluation Granularity** | Only end-to-end evaluation | Each Agent evaluated independently, precisely identifying bottlenecks |
| **Token Consumption** | Long context = more token waste | Each Agent only receives necessary data |

### Why Not Split Further?

| Candidate Split | Reason Not to Split |
|---|---|
| Separate Law Retrieval Agent + Risk Assessment Agent | Law retrieval and risk assessment have reasoning dependencies; splitting adds messaging overhead |
| Cross-validation as independent Agent | Cross-validation has the same analytical depth as single-clause analysis, sharing the same RAG with high reuse |
| Table parsing as independent Agent | Table parsing is a sub-task of Parser, depending on layout analysis context; independence would lose information |

---

## 3. Resource Quotas Per Agent

| Agent | Max Concurrency | Single Timeout | Memory Limit | Retry Count |
|---|---|---|---|---|
| Supervisor | 1 (single instance) | - | 512MB | - |
| Parser | 5 | 120s | 1GB | 2 |
| Analyzer | 20 | 60s | 512MB | 3 |
| Report | 5 | 60s | 512MB | 2 |
| Validator | 3 | 30s | 256MB | 1 |

### Concurrency Control (Prevent LLM API Overrun)

```
Global LLM Token consumption rate cap: 100,000 TPM

Allocation strategy:
  Parser:    10,000 TPM (10%)
  Analyzer:  70,000 TPM (70%) ← Primary consumer
  Report:    15,000 TPM (15%)
  Validator:  5,000 TPM (5%)

When any Agent hits quota → wait; no system-wide degradation
```

---

## 4. Agent Observability

### Each Agent Must Expose

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

This data is aggregated into LangSmith (or a self-built Trace system), providing:
- Full-chain tracing: Step-by-step visibility into all 5 Agents' execution
- Latency analysis: Which Agent is slowest
- Token consumption: Which clause consumed the most tokens
