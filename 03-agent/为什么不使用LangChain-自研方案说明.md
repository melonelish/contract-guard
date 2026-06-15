# Why Not LangChain/LangGraph — Self-built Agent Orchestration Explained

> Version: v1.0 | Last Updated: 2026-06-15
> Category: FAQ + Interview Talking Points

---

## 1. LangChain/LangGraph Positioning

LangChain/LangGraph **are not core AI agent development competencies**. They are **frameworks**, similar to React/Vue in the frontend world — they save boilerplate code but don't represent the underlying principles.

True AI Agent core competencies:

```
Agent Development Core Competencies
├── Task Decomposition                 —— Frameworks can't help you
├── Tool Selection (Function Calling)  —— Native OpenAI SDK support
├── Context Management (Memory/State)  —— Writing your own is more flexible
├── Multi-Agent Collaboration          —— Frameworks actually constrain you
│   (Orchestration Patterns)
├── RAG Architecture                   —— Frameworks only save ~20 lines
│   (Hybrid Retrieval + Rerank)
├── Hallucination Control              —— Frameworks offer zero help
└── Evaluation System                  —— Frameworks offer zero help
```

---

## 2. Self-built vs LangChain Comparison

| Dimension | LangChain/LangGraph | ContractGuard Self-built Solution |
|---|---|---|
| **Code Volume** | Less (framework encapsulates) | Slightly more (~300 lines of Python Agent orchestration classes) |
| **Controllability** | Black box (AgentExecutor internal state invisible) | Fully transparent; every step loggable |
| **Interview Value** | "I built an Agent with LangChain" | "I designed a Supervisor-Worker pattern, Redis Streams messaging middleware, each Agent with independent System Prompts and knowledge bases" |
| **Interviewer Reaction** | "Oh, a package-wrapper" | **"This person truly understands Agent principles"** |
| **Version Risk** | LangChain 0.1→0.3 all Breaking Changes | What you write yourself will never shoot you in the foot |
| **Debugging Difficulty** | Agent dead loop → very hard to locate | Every message recorded in Redis Stream |
| **Customization Flexibility** | Constrained by framework API | Completely free |
| **Best Use Case** | Rapid prototyping | **Production-grade enterprise delivery ← This project** |

---

## 3. Self-built Agent Orchestration Layer Architecture

### 3.1 Core Components (~300 lines of Python)

```
contractguard/core/agent_orchestrator.py
├── class SupervisorAgent       ← Task scheduling center
├── class WorkerAgent           ← Abstract base class (Parser/Analyzer/Report all inherit it)
├── class MessageBus            ← Redis Streams wrapper
├── class AgentRegistry         ← Worker registration/discovery/heartbeat
└── class TaskContext            ← Task context (task_id + status + retry count)
```

### 3.2 Why Not Just Call APIs Directly

```
❌ Simple call chain:
Parser(data) → Analyzer(clauses) → Report(results) → Return

Problems:
  - Parser timeout → entire request hangs
  - Cannot process clauses in parallel
  - Any intermediate failure → start from scratch
  - Cannot observe per-step latency/cost

✅ Redis Streams approach:
Supervisor ──XADD──▶ parser:tasks ──▶ Parser Worker
         ◀──XREAD── parser:results

Supervisor ──XADD──▶ analyzer:tasks ──▶ 10 Analyzer Workers in parallel
         ◀──XREAD── analyzer:results     (Redis Consumer Group auto load-balancing)

Advantages:
  - Decoupled: Supervisor doesn't care how many Workers exist
  - Persistent: Messages in Redis; Worker crashes are recoverable
  - Observable: Every message's send/process/complete time in Stream
  - Horizontally scalable: Add Workers by just launching new containers, zero code changes
```

### 3.3 Comparison with LangGraph's StateGraph Philosophy

LangGraph's core design is **using graphs to manage Agent state transitions**:

```python
# LangGraph approach
graph = StateGraph(AgentState)
graph.add_node("parser", run_parser)
graph.add_node("analyzer", run_analyzer)
graph.add_node("report", run_report)
graph.add_edge("parser", "analyzer")
graph.add_conditional_edges("analyzer", check_confidence, {
    "high": "report",
    "low": "parser"  # Go back and re-parse
})
```

ContractGuard's Agent collaboration is relatively fixed (Parser → Analyzer → Report → Validator) and doesn't need dynamic graphs:

```python
# ContractGuard approach (Pipeline + Parallel)
results = await orchestrator.run_pipeline([
    ParserTask(file),
    ParallelAnalyzerTask(clauses, max_concurrency=10),
    CrossValidateTask(),
    ReportTask(),
    ValidateTask(),
])
# Simple and direct; all state in TaskContext
```

**Decision logic**: If complex conditional branching is needed in the future (e.g., "which step to roll back to when review fails depends on risk type"), ideas similar to StateGraph will be introduced, but the underlying implementation will remain self-controlled.

---

## 4. Common Questions & Responses

### Q: You don't use LangChain — how did you build RAG?

> LangChain's RAG encapsulates four steps: Document Loading → Chunking → Vectorization → Retrieval. I use Unstructured.io for parsing, a self-built semantic chunker (identifies clause boundaries before splitting, not fixed character count), BGE-M3 for Embedding, and Milvus for vector storage. Hybrid retrieval is self-built — semantic search + BM25 keywords + structured SQL, three-way recall with Reciprocal Rank Fusion re-ranking. LangChain only saves 5-10 lines per step at the cost of locking the entire pipeline into its abstractions.

### Q: You don't use LangSmith — how do you observe Agents?

> OpenTelemetry + self-built Trace. Every Agent call is recorded: task_id → agent_name → input → output → latency → token_cost. Same effect as LangSmith, but data stays with me, no SaaS dependency, no data leakage risk.

### Q: If you don't know LangChain, what will you do when you join a company?

> I fully understand LangChain's core concepts — Agent / Tool / Chain / Memory / RAG — I just didn't use its packaged API. Give me an afternoon to read the docs, and I can start using it the next day. Frameworks are technique; Agent design is philosophy. I've proven I have the philosophy.

### Q: Why don't you use no-code platforms like Dify/Coze?

> Dify and Coze are suitable for non-technical people to quickly build customer service bots, not for our scenario. Contract review requires: ① Custom multi-agent collaboration architecture ② Fine-grained knowledge base layering and hybrid retrieval ③ Hallucination control and safety guardrails ④ Structured diff output ⑤ Built-in editor and print functionality. These are either impossible on low-code platforms or require extensive hacking.

---

## 5. Complete Interview Talking Points

> "I didn't use LangChain. LangChain is essentially a framework that helps developers save boilerplate code for Agent loops and tool calling. But its abstraction layer is too heavy; problems are hard to diagnose — for example, if an Agent dead-loops, LangChain's AgentExecutor internal state is invisible to you.
>
> I chose to write my own Agent orchestration layer, with a core of about 300 lines of Python. The architecture is a Supervisor-Worker pattern: the Supervisor handles task decomposition and distribution; Workers receive tasks via Redis Streams message queues with Consumer Group auto load-balancing. Each Worker Agent has an independent System Prompt and knowledge base. LLM calls are wrapped in a unified layer supporting hot-switching between MiMo 2.5 and DeepSeek V4-Flash.
>
> I also studied LangGraph's StateGraph design philosophy — managing Agent state transitions with graphs. But my project's Agent collaboration is relatively fixed (Parser → Analyzer → Report → Validator) and doesn't need dynamic graphs. A simple Pipeline + parallel invocation suffices. If complex conditional branching is needed in the future, I would consider introducing StateGraph ideas, but with the underlying implementation still under my control.
>
> For RAG, I also didn't use LangChain's wrappers. Unstructured.io for document parsing, self-built clause-boundary-based semantic chunking, BGE-M3 for Embedding, Milvus for vector storage. Hybrid retrieval is three-way recall + Reciprocal Rank Fusion re-ranking. Observability uses OpenTelemetry + self-built Trace, with all Agent calls carrying complete task_id → agent → latency → cost traces.
>
> In summary: I fully understand LangChain's philosophy. Choosing to self-build isn't about showing off — it's about being able to precisely control every step of behavior in production and diagnose issues within 5 minutes."

---

## 6. Reference Resources

- LangChain Official Documentation: https://python.langchain.com/
- LangGraph Official Documentation: https://langchain-ai.github.io/langgraph/
- Anthropic Building Effective Agents: https://www.anthropic.com/engineering/building-effective-agents
- Redis Streams Documentation: https://redis.io/docs/latest/develop/data-types/streams/
