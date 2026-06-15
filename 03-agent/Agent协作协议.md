# Agent Collaboration Protocol

> Version: v1.0 | Last Updated: 2026-06-15

---

## 1. Protocol Overview

ContractGuard's multi-agent system adopts an asynchronous collaboration model based on message queues, with the Supervisor Agent as the central node. All Worker Agents communicate through a standardized message protocol.

---

## 2. Message Queue Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Redis Streams                       │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ parser:   │   │analyzer: │   │report:   │  ...   │
│  │ tasks     │   │tasks     │   │tasks     │        │
│  └──────────┘   └──────────┘   └──────────┘        │
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ parser:   │   │analyzer: │   │report:   │  ...   │
│  │ results   │   │results   │   │results   │        │
│  └──────────┘   └──────────┘   └──────────┘        │
└─────────────────────────────────────────────────────┘
```

### Worker Registration & Discovery

When each Worker Agent starts:
1. Register with Redis (`workers:{worker_id}` key, includes heartbeat)
2. Declare the queue it consumes (e.g., `analyzer:tasks`)
3. Start heartbeat (updated every 5 seconds; considered down if no update for 15 seconds)

---

## 3. Task Lifecycle

```
┌─────────┐
│ CREATED │  ← Supervisor creates task
└────┬────┘
     │
     ▼
┌─────────┐
│ QUEUED  │  ← Task enters Worker queue
└────┬────┘
     │
     ▼
┌──────────┐
│ RUNNING  │  ← Worker picks up task and begins execution
└────┬─────┘
     │
     ├── Success → ┌──────────┐ → ┌─────────┐
     │             │ COMPLETED │   │ Return result │
     │             └──────────┘   └─────────┘
     │
     ├── Failure → ┌─────────┐
     │             │  RETRY   │ → Back to QUEUED (retry_count < 3)
     │             └─────────┘
     │
     └── 3 failures → ┌────────┐
                      │ FAILED  │ → Mark as permanently failed, write error log
                      └────────┘
```

---

## 4. Complete Collaboration Sequence Diagram

```
Supervisor      Redis         Parser       Analyzer      Report      Validator
    │             │              │            │            │            │
    │─Create task─→│              │            │            │            │
    │             │              │            │            │            │
    │─Publish task─→│              │            │            │            │
    │             │──Push task──→│            │            │            │
    │             │              │            │            │            │
    │             │←─Return result──│            │            │            │
    │←Read result─│              │            │            │            │
    │             │              │            │            │            │
    │─Publish 10──→│              │            │            │            │
    │  analysis   │─────────────────────────→│  (10 parallel) │            │
    │  tasks      │              │            │            │            │
    │             │←─Return result────────────│            │            │
    │←Collect result─│              │            │            │            │
    │             │              │            │            │            │
    │─Publish cross─→│              │            │            │            │
    │  validation  │─────────────────────────→│            │            │
    │  tasks       │←─Return conflicts──────────│            │            │
    │             │              │            │            │            │
    │─Publish report─→│              │            │            │            │
    │  generation  │─────────────────────────────────────→│            │
    │  task        │←─Return report─────────────────────────│            │
    │             │              │            │            │            │
    │─Publish validate─→│              │            │            │            │
    │  task        │─────────────────────────────────────────────────→│
    │             │←─Pass/Fail───────────────────────────────────────│
    │             │              │            │            │            │
    │─Update task─│              │            │            │            │
    │  completed  │              │            │            │            │
    │             │              │            │            │            │
    │─Notify frontend─│              │            │            │            │
```

---

## 5. Exception Handling Protocol

### 5.1 Worker Downtime

```python
# Supervisor monitors Worker heartbeats
def check_worker_health():
    workers = redis.keys("workers:*")
    for w in workers:
        last_heartbeat = redis.get(w)
        if now() - last_heartbeat > 15:  # Exceeds 15 seconds
            mark_worker_dead(w)
            reassign_tasks(w)  # Reassign the Worker's unfinished tasks
```

### 5.2 Task Timeout

```python
# Each task has a TTL; auto-retry on timeout
TASK_TIMEOUT = {
    "parse_document": 120,    # Document parsing: 2 minutes
    "analyze_clause": 60,     # Single clause analysis: 1 minute
    "cross_validate": 90,     # Cross-validation: 1.5 minutes
    "generate_report": 60,    # Report generation: 1 minute
    "validate_report": 30,    # Report validation: 30 seconds
}
```

### 5.3 Degradation Strategy

| Scenario | Degradation Strategy |
|---|---|
| All Analyzers down | Return "System busy, please try again later" (no data loss) |
| Single clause analysis fails | Mark as "Review failed"; other clauses output normally |
| Validator does not pass | Regenerate at most 2 times; output degraded if still failing |
| LLM API error | Switch to backup model (MiMo 2.5 → DeepSeek V4-Flash) |
