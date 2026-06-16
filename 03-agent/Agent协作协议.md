# Agent 协作协议

> 版本：v1.0 | 最后更新：2026-06-15

---

## 一、协议概述

ContractGuard 的多 Agent 系统采用基于消息队列的异步协作模式，以 Supervisor Agent 为中心节点，所有 Worker Agent 通过标准化消息协议进行通信。

---

## 二、消息队列架构

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Redis Streams                                │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ parser:   │  │analyzer: │  │report:   │  │drafter:  │  ...      │
│  │ tasks     │  │tasks     │  │tasks     │  │tasks     │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ parser:   │  │analyzer: │  │report:   │  │drafter:  │  ...      │
│  │ results   │  │results   │  │results   │  │results   │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
└──────────────────────────────────────────────────────────────────────┘
```

### Worker 注册与发现

每个 Worker Agent 启动时：
1. 注册到 Redis（`workers:{worker_id}` 键，包含心跳）
2. 声明消费的队列（如 `analyzer:tasks`）
3. 启动心跳（每5秒更新，15秒未更新视为宕机）

---

## 三、任务生命周期

```
┌─────────┐
│ CREATED │  ← Supervisor 创建任务
└────┬────┘
     │
     ▼
┌─────────┐
│ QUEUED  │  ← 任务进入 Worker 队列
└────┬────┘
     │
     ▼
┌──────────┐
│ RUNNING  │  ← Worker 取出任务开始执行
└────┬─────┘
     │
     ├── 成功 → ┌──────────┐ → ┌─────────┐
     │         │ COMPLETED │   │ 返回结果  │
     │         └──────────┘   └─────────┘
     │
     ├── 失败 → ┌─────────┐
     │         │  RETRY   │ → 回到 QUEUED (retry_count < 3)
     │         └─────────┘
     │
     └── 3次失败 → ┌────────┐
                  │ FAILED  │ → 标记永久失败，写错误日志
                  └────────┘
```

---

## 四、起草流转协议（Drafter Pipeline）

起草流程与审查流程使用独立的消息队列管道，由 Supervisor 根据请求类型路由：

```
用户请求 → Supervisor
              │
              ├── 类型=起草？
              │       │
              │       ▼
              │   ┌──────────────┐
              │   │ drafter:tasks │ ← Drafter Agent 消费
              │   └──────┬───────┘
              │          │ 生成条款 + Annotation
              │          ▼
              │   ┌──────────────────┐
              │   │ 用户编辑/确认草稿  │
              │   └────────┬─────────┘
              │          │ 确认后
              │          ▼
              │   ┌──────────────────────────┐
              │   │ 切换到审查管道（parser →  │
              │   │  analyzer → report → val）│
              │   └──────────────────────────┘
              │
              └── 类型=审查？ → 直接走审查管道
```

### Worker 注册新增

Drafter Agent 启动时注册到 Redis：
```
workers:drafter-01 → {
  "status": "idle",
  "model": "mimo2.5",
  "last_heartbeat": "2026-06-15T10:30:00Z"
}
```

### 错误处理（Drafter 专用）

| 错误类型 | 处理策略 |
|---|---|
| 用户需求描述过于简略 | 返回引导性问题（"请问合同金额大约多少？主要交易标的是什么？"） |
| 合同范本库无匹配模板 | 基于通用结构生成，标注"无精确匹配模板，已用通用结构" |
| 起草超时（90s） | Supervisor 返回已生成的部分条款 + "可基于已有内容继续补充" |

---

## 五、完整协作时序图

```
Supervisor      Redis         Parser       Analyzer      Report      Validator
    │             │              │            │            │            │
    │─创建task────→│              │            │            │            │
    │             │              │            │            │            │
    │─发布任务────→│              │            │            │            │
    │             │──推送任务──→  │            │            │            │
    │             │              │            │            │            │
    │             │←──返回结果───│            │            │            │
    │←读取结果────│              │            │            │            │
    │             │              │            │            │            │
    │─发布10条────→│              │            │            │            │
    │  分析任务    │─────────────────────────→│  (并行10个) │            │
    │             │              │            │            │            │
    │             │←──返回结果────────────────│            │            │
    │←收集结果────│              │            │            │            │
    │             │              │            │            │            │
    │─发布交叉────→│              │            │            │            │
    │  校验任务    │─────────────────────────→│            │            │
    │             │←──返回矛盾────────────────│            │            │
    │             │              │            │            │            │
    │─发布报告────→│              │            │            │            │
    │  生成任务    │─────────────────────────────────────→│            │
    │             │←──返回报告───────────────────────────│            │
    │             │              │            │            │            │
    │─发布校验────→│              │            │            │            │
    │  任务        │─────────────────────────────────────────────────→│
    │             │←──通过/不通过─────────────────────────────────────│
    │             │              │            │            │            │
    │─更新task────│              │            │            │            │
    │  completed  │              │            │            │            │
    │             │              │            │            │            │
    │─通知前端────│              │            │            │            │
```

---

## 六、异常处理协议

### 6.1 Worker 宕机

```python
# Supervisor 监控 Worker 心跳
def check_worker_health():
    workers = redis.keys("workers:*")
    for w in workers:
        last_heartbeat = redis.get(w)
        if now() - last_heartbeat > 15:  # 超15秒
            mark_worker_dead(w)
            reassign_tasks(w)  # 重新分配该 Worker 的未完成任务
```

### 6.2 任务超时

```python
# 每条任务设置 TTL，超时自动重试
TASK_TIMEOUT = {
    "parse_document": 120,    # 文档解析：2分钟
    "analyze_clause": 60,     # 单条款分析：1分钟
    "cross_validate": 90,     # 交叉校验：1.5分钟
    "generate_report": 60,    # 报告生成：1分钟
    "validate_report": 30,    # 报告校验：30秒
}
```

### 6.3 降级策略

| 场景 | 降级策略 |
|---|---|
| Analyzer 全部宕机 | 返回"系统繁忙，请稍后重试"（不丢数据） |
| 单个条款分析失败 | 标记为"审查失败"，其他条款正常输出 |
| Validator 不通过 | 最多重新生成 2 次，仍不通过则降级输出 |
| LLM API 错误 | 切换备用模型（MiMo 2.5 → DeepSeek V4-Flash） |

---

## Supervisor 崩溃恢复机制

### 问题

Supervisor 单实例进程崩溃时，内存中的任务编排状态（哪些 Agent 已分发、哪些结果已收集、任务进度百分比）会丢失。Redis Streams 保证消息不丢，但 Supervisor 恢复后不知道自己之前"做到哪了"。

### 恢复策略

```
Supervisor 启动 / 崩溃后重新上线
      │
      ▼
┌─────────────────────────────┐
│ 1. 扫描 Redis 中所有 PENDING  │
│    状态的任务 (task_status 键) │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 2. 逐任务重建编排状态          │
│    ├── 查询已完成的 Agent 结果 │
│    │   (parser:result:task_id │
│    │    analyzer:result:*)    │
│    ├── 识别未完成的 Agent 步骤 │
│    └── 标记为 "恢复中"         │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 3. 对未完成步骤重新分发         │
│    ├── 已完成的 → 跳过         │
│    └── 未完成的 → 重新写入     │
│        Worker 队列            │
└─────────────────────────────┘
```

### 状态持久化到 Redis

```python
# 每个任务的状态不再只存内存，同步写入 Redis
def dispatch_agent(task_id, agent_name, payload):
    # 写消息队列
    redis.xadd(f"{agent_name}:tasks", payload)
    
    # 同时写状态追踪
    redis.hset(f"task:{task_id}:state", agent_name, "dispatched")
    redis.hset(f"task:{task_id}:meta", mapping={
        "status": "in_progress",
        "total_steps": "5",
        "completed_steps": str(len(completed_steps)),
        "last_update": time.time()
    })
    redis.expire(f"task:{task_id}:state", 86400)  # 24h TTL

# Worker 完成后更新状态
def on_agent_complete(task_id, agent_name, result):
    redis.hset(f"task:{task_id}:state", agent_name, "completed")
    redis.hset(f"task:{task_id}:state", f"{agent_name}:result", json.dumps(result))
    redis.hincrby(f"task:{task_id}:meta", "completed_steps", 1)
```

### 恢复优先级

| 任务类型 | 崩溃时状态 | 恢复策略 |
|---|---|---|
| 已分发但未完成的 Worker | 消息在 Redis Stream PEL 中 | Consumer Group XCLAIM 自动转给新 Worker |
| 已完成但 Supervisor 未处理的 | 结果在 result stream 中 | Supervisor 重启后重新读取 |
| 排队中（Redis 队列） | 消息在 Stream 中持久化 | Supervisor 重启后继续消费 |

---

## 断点续审机制

> Supervisor 崩溃恢复解决的是"调度器挂了怎么办"，断点续审解决的是"某个 Worker 在第 12 分钟超时了怎么办"。两者互补。

### 问题

审查流水线是串行+并行的混合结构：

```
Parser(3min) → Analyzer×60(8min) → Report(2min) → Validator(2min) = 15min
```

如果 Analyzer 在第 48 条条款时 LLM 超时（第 12 分钟），传统做法是整个任务标记失败，用户重传合同 → 全部重跑。**已完成的 47 条条款白算了。**

### 状态机设计

```
┌─────────────────────────────────────────────────────┐
│              审查任务状态机                            │
│                                                      │
│  CREATED → PARSING → PARSED → ANALYZING             │
│                                  │                   │
│                    ┌─────────────┼─────────────┐     │
│                    ▼             ▼             ▼     │
│               ANALYZED     PARTIAL_FAIL    FAILED   │
│                    │             │                   │
│                    ▼             ▼                   │
│               REPORTING → REPORTED → VALIDATING     │
│                                              │      │
│                                        ┌─────┴────┐ │
│                                        ▼          ▼ │
│                                    APPROVED   REJECTED│
│                                        │          │  │
│                                        ▼          ▼  │
│                                    COMPLETED  RETRYING│
└─────────────────────────────────────────────────────┘

PARTIAL_FAIL: 部分条款分析失败，其余成功 → 重试仅处理失败条款
```

### 检查点持久化

```python
# Supervisor 在每个 Agent 完成后写检查点
async def on_worker_complete(task_id: str, agent: str, result: dict):
    """Worker 返回结果时立即持久化检查点"""
    
    # 1. 写检查点到 Redis（快速恢复）
    checkpoint = {
        "task_id": task_id,
        "agent": agent,
        "status": result.get("status"),
        "completed_at": time.time(),
        "result": result
    }
    redis.hset(
        f"checkpoint:{task_id}", 
        f"step:{agent}:{result.get('clause_id', 'all')}", 
        json.dumps(checkpoint)
    )
    
    # 2. 关键 Agent 结果同步落库（PostgreSQL，长期保存）
    if agent in ("parser", "report", "validator"):
        await db.save_checkpoint(checkpoint)
    
    # 3. 更新任务进度
    total = int(redis.hget(f"task:{task_id}:meta", "total_steps") or 0)
    done = redis.hincrby(f"task:{task_id}:meta", "completed_steps", 1)
    progress = int(done / total * 100) if total else 0
    
    # 4. WebSocket 推送进度
    await ws_publish(task_id, {"progress": progress, "agent": agent})
```

### 失败恢复流程

```python
async def retry_from_checkpoint(task_id: str, failed_clause_ids: list[str] = None):
    """从上一个检查点恢复，只重跑失败的步骤"""
    
    # 1. 读取所有检查点
    checkpoints = redis.hgetall(f"checkpoint:{task_id}")
    
    # 2. 找到最后一个成功的检查点
    last_success = max(
        [json.loads(v) for v in checkpoints.values()],
        key=lambda x: x["completed_at"]
    )
    
    # 3. 判断恢复起点
    if last_success["agent"] == "parser":
        # Parser 完成，Analyzer 部分失败 → 只重跑失败的条款
        logger.info(f"断点续审：从 Analyzer 恢复，重试 {len(failed_clause_ids)} 条")
        pending_clauses = [c for c in all_clauses if c.id in failed_clause_ids]
        await dispatch_analyzer_parallel(task_id, pending_clauses)  # 只重试失败的
        
    elif last_success["agent"] == "report":
        # Report 已完成，Validator 失败 → 直接重跑 Validator
        logger.info("断点续审：从 Validator 恢复")
        await dispatch_validator(task_id, last_success["result"])
        
    elif last_success["agent"] == "validator":
        # 全部完成
        return last_success["result"]
    
    # 4. 已有结果不重复算，直接合并
    cached_results = [json.loads(v)["result"] for v in checkpoints.values() 
                      if json.loads(v)["agent"] == "analyzer"]
    # 将缓存结果和新结果合并后传给 Report Agent
```

### 成本节省

| 场景 | 无断点续审 | 有断点续审 | 节省 |
|---|---|---|---|
| Parser 后 Analyzer 第 48/60 条超时 | 重跑全部 15min，~¥1.04 | 仅重试 12 条失败条款，~¥0.20 | **80%** |
| Report 完成后 Validator 超时 | 重跑全部 15min | 仅重跑 Validator ~2min | **87%** |
| 网络抖动导致 3 个 Analyzer 同时超时 | 重跑全部 | 仅重试 3 条 + 合并其余 57 条已有结果 | **91%** |
