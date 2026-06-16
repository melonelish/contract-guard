# Agent 框架类定义

> 01-07 文档描述了 Agent 的职责和 I/O，但没有给出 Python 类接口。以下补充 01-07 缺失的类定义。

---

## 1. WorkerAgent 基类

```python
# backend/app/core/agent.py

from abc import ABC, abstractmethod
from uuid import UUID

class WorkerAgent(ABC):
    """所有 Agent 的抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent 名称，用于 Redis Stream 路由。如 "parser", "analyzer" """
        ...

    @property
    @abstractmethod
    def timeout_seconds(self) -> int:
        """单次执行超时（秒）。"""
        ...

    @property
    @abstractmethod
    def max_retries(self) -> int:
        """最大重试次数。"""
        ...

    @abstractmethod
    async def execute(self, task_context: "TaskContext") -> dict:
        """
        执行任务，返回结果 dict（对应各 Agent 的 Output schema）。

        Args:
            task_context: 包含 task_id, payload, db, redis, llm 等依赖

        Returns:
            Agent 输出 dict

        Raises:
            AgentTimeoutError: 超时
            AgentExecutionError: 执行失败
        """
        ...
```

---

## 2. TaskContext — 任务上下文

```python
# backend/app/core/agent.py

from dataclasses import dataclass, field
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

@dataclass
class TaskContext:
    """Agent 执行时的上下文，由 Worker 从 Redis 消息反序列化后构造。"""
    task_id: str
    review_id: UUID
    contract_id: UUID
    tenant_id: UUID
    payload: dict                           # 各 Agent 的 Input schema 展开后的 dict
    llm: "LLMWrapper"                       # llm_chat / llm_embed 统一接口
    db: AsyncSession
    redis: Redis
    retry_count: int = 0
```

---

## 3. ReviewOrchestrator — FastAPI ↔ Agent 桥接

> 这是 01-07 中唯一完全没有类定义的组件。架构图里有这个框，但没有任何接口。

```python
# backend/app/core/orchestrator.py

from uuid import UUID

class ReviewOrchestrator:
    """
    审查编排器。FastAPI 路由通过它触发审查、取消、查询。
    它不执行任何 Agent 逻辑，只负责：写 DB → 投递 Redis → 返回 task_id。
    """

    def __init__(self, db_factory, redis: Redis):
        self._db_factory = db_factory
        self._redis = redis

    async def start_review(
        self,
        contract_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
        contract_type: str | None = None,
    ) -> str:
        """
        触发一次完整审查。

        1. 写入 reviews 表（status=created）
        2. 投递到 parser:tasks Stream
        3. 返回 task_id

        Returns:
            task_id (str) — 用于后续查询和 WebSocket 关联
        """
        ...

    async def cancel_review(self, task_id: str, tenant_id: UUID) -> bool:
        """
        取消审查。发送 cancel 事件到 Supervisor。
        只能取消 PARSING / ANALYZING / REPORTING 等运行中状态。
        """
        ...

    async def get_review_status(self, task_id: str, tenant_id: UUID) -> dict:
        """查询审查当前状态和进度。"""
        ...
```

---

## 4. SupervisorAgent

```python
# backend/app/core/supervisor.py

class SupervisorAgent:
    """
    审查流水线的总控。监听各 Agent 完成事件，推进状态机。
    单实例运行。
    """

    def __init__(self, redis: Redis, db_factory, orchestrator: ReviewOrchestrator):
        self._redis = redis
        self._db_factory = db_factory
        self._orchestrator = orchestrator

    async def on_agent_result(
        self,
        agent_name: str,
        task_id: str,
        result: dict,
    ) -> None:
        """
        收到 Agent 完成结果后的处理：
        1. 更新 DB 中对应条款的分析结果
        2. 推进状态机
        3. 如果当前阶段所有 Agent 都完成 → 触发下一阶段
        4. 如果有失败 → 决定重试或放弃
        """
        ...

    async def check_completion(self, task_id: str) -> bool:
        """检查某个 task_id 下所有 Agent 是否都完成了。"""
        ...

    async def dispatch_next_phase(self, task_id: str) -> None:
        """根据状态机当前状态，决定下一步做什么。"""
        ...
```

---

## 5. MessageBus — Redis Streams 封装

```python
# backend/app/core/message_bus.py

import json
from redis.asyncio import Redis

# Stream 命名（与 Agent协作协议.md 保持一致）
STREAM_NAMES = {
    "parser":    "parser:tasks",
    "analyzer":  "analyzer:tasks",
    "report":    "report:tasks",
    "validator": "validator:tasks",
    "drafter":   "drafter:tasks",
}

CONSUMER_GROUPS = {
    "parser":    "parser-workers",
    "analyzer":  "analyzer-workers",
    "report":    "report-workers",
    "validator": "validator-workers",
}

class MessageBus:
    def __init__(self, redis: Redis):
        self._redis = redis

    async def publish(self, agent_name: str, task_id: str, payload: dict) -> None:
        """投递任务到对应 Agent 的 Stream。"""
        stream = STREAM_NAMES[agent_name]
        await self._redis.xadd(stream, {
            "task_id": task_id,
            "payload": json.dumps(payload),
        })

    async def consume(
        self, agent_name: str, consumer_id: str, timeout_ms: int = 5000
    ) -> tuple[str, dict] | None:
        """
        阻塞消费一条消息。

        Returns:
            (message_id, {"task_id": ..., "payload": ...}) 或 None（超时）
        """
        stream = STREAM_NAMES[agent_name]
        group = CONSUMER_GROUPS[agent_name]
        results = await self._redis.xreadgroup(
            group, consumer_id, {stream: ">"}, count=1, block=timeout_ms
        )
        if not results:
            return None
        msg_id, data = results[0][1][0]
        return msg_id, json.loads(data[b"payload"])

    async def ack(self, agent_name: str, message_id: str) -> None:
        """确认消息已处理。"""
        stream = STREAM_NAMES[agent_name]
        group = CONSUMER_GROUPS[agent_name]
        await self._redis.xack(stream, group, message_id)
```

> **注意**：Stream 命名与 Agent协作协议.md 一致（`parser:tasks`），不是 `agent:parser:tasks`。
