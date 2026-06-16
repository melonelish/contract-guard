# 集成规格：Redis 命名空间 + Settings + 调用链

> 01-07 分散提到了 Redis key、Settings 引用、调用链，但没有统一收口。本文补全。

---

## 1. Redis Key 命名空间

```python
# ── Stream（Agent 间消息队列） ──
parser:tasks             # Stream → Parser Agent 消费
parser:results           # Stream → Supervisor 消费 Parser 结果
analyzer:tasks           # Stream → Analyzer Agent 消费
analyzer:results         # Stream → Supervisor 消费 Analyzer 结果
report:tasks             # Stream → Report Agent 消费
report:results           # Stream → Supervisor 消费 Report 结果
validator:tasks          # Stream → Validator Agent 消费
validator:results        # Stream → Supervisor 消费 Validator 结果
drafter:tasks            # Stream → Drafter Agent 消费
drafter:results          # Stream → Supervisor 消费 Drafter 结果

# ── Hash（审查状态） ──
task:{task_id}:state     # Hash → {status, progress, current_phase}
task:{task_id}:meta      # Hash → {contract_id, tenant_id, started_at}

# ── Prompt 缓存 ──
review:{task_id}:clauses    # Hash → clause_id → clause JSON
review:{task_id}:analyses   # Hash → clause_id → analysis JSON
review:{task_id}:conflicts  # List → conflict JSON
review:{task_id}:metadata   # String → contract metadata JSON

# ── Worker 注册 ──
workers:{agent_name}     # Set → 活跃 worker ID 列表
worker:{worker_id}:heartbeat  # String → 最后心跳时间戳

# ── WebSocket 票据 ──
ws:ticket:{ticket}       # String → task_id（TTL 60s，一次性使用）
```

---

## 2. Settings 类

```python
# backend/app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ── 应用 ──
    APP_NAME: str = "ContractGuard"
    DEBUG: bool = False
    SECRET_KEY: str                          # 必填，64 字符
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    # ── 数据库 ──
    DATABASE_URL: str                        # postgresql+asyncpg://...
    DATABASE_MAX_CONNECTIONS: int = 20

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_MAX_LEN: int = 10000

    # ── LLM ──
    MIMO_API_KEY: str                        # 必填
    MIMO_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    MIMO_MODEL: str = "mimo-2.5"
    DEEPSEEK_API_KEY: str                    # 必填
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_API_KEY: str = ""

    # ── Elasticsearch ──
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "law_articles"

    # ── Milvus ──
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "contractguard"

    # ── MinIO ──
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "contractguard"
    MINIO_SECURE: bool = False

    # ── Vault ──
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = ""
    VAULT_BACKEND_PATH: str = "contractguard"

    # ── JWT ──
    JWT_SECRET: str = ""                     # 必填，与 SECRET_KEY 分开
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Agent ──
    AGENT_MAX_CONCURRENCY: int = 10
    AGENT_TOTAL_TPM: int = 100000
    AGENT_PARSE_TIMEOUT: int = 120
    AGENT_ANALYZE_TIMEOUT: int = 60
    AGENT_REPORT_TIMEOUT: int = 120
    AGENT_VALIDATE_TIMEOUT: int = 30

    # ── 文件上传 ──
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── 监控 ──
    PROMETHEUS_METRICS_PORT: int = 9090
    SENTRY_DSN: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

> **需同步 .env.example**：新增 `JWT_REFRESH_TOKEN_EXPIRE_DAYS`、`AGENT_MAX_CONCURRENCY`、`AGENT_TOTAL_TPM`、`AGENT_PARSE_TIMEOUT`、`AGENT_ANALYZE_TIMEOUT`、`AGENT_REPORT_TIMEOUT`、`AGENT_VALIDATE_TIMEOUT`。

---

## 3. FastAPI → Agent 调用链

```
HTTP 请求
  → API Route Handler (v1/reviews.py)
    → ReviewOrchestrator.start_review()
      → 写入 reviews 表 (status=created)
      → MessageBus.publish("parser", task_id, payload)
      → 返回 {task_id, status: "queued"}

Worker 消费 (worker/run.py)
  → MessageBus.consume(agent_name, consumer_id)
  → 反序列化 payload → 构造 TaskContext
  → agent.execute(task_context)
  → 结果写入 DB
  → MessageBus.publish(f"{agent_name}:results", task_id, result)
  → MessageBus.ack(agent_name, message_id)

Supervisor 监听
  → 监听 {agent}:results Stream
  → 收到结果 → SupervisorAgent.on_agent_result()
  → 推进状态机 → 如果阶段完成 → dispatch_next_phase()
  → 下一阶段 → MessageBus.publish(next_agent, task_id, next_payload)
```
