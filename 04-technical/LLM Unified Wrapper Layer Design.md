# LLM Unified Wrapper Layer Design

> Version: v1.0 | Last Updated: 2026-06-16

---

## 1. Purpose

ContractGuard integrates multiple LLM providers (MiMo 2.5, DeepSeek V4-Flash, BGE-M3 embeddings). Without a unified abstraction, every Agent module would contain provider-specific SDK calls, retry logic, and model-switching code — a maintenance nightmare.

The **LLM Unified Wrapper Layer** solves this by providing a single interface for all LLM operations, enabling hot-switching between models with zero code changes in Agent logic.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Agent Layer                          │
│  Supervisor / Parser / Analyzer / Report / Validator│
└────────────────────┬────────────────────────────────┘
                     │  llm_chat(model="mimo2.5", ...)
                     ▼
┌─────────────────────────────────────────────────────┐
│              LLM Unified Wrapper Layer               │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  Model       │  │  Retry &     │  │  Cost       │ │
│  │  Registry    │  │  Fallback    │  │  Tracker    │ │
│  └──────┬──────┘  └──────┬───────┘  └─────┬──────┘ │
│         │                │                │         │
│  ┌──────▼────────────────▼────────────────▼──────┐ │
│  │            Provider Adapters                   │ │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐  │ │
│  │  │  MiMo    │  │ DeepSeek │  │ BGE (Embed) │  │ │
│  │  │  Adapter │  │ Adapter  │  │  Adapter    │  │ │
│  │  └──────────┘  └──────────┘  └────────────┘  │ │
│  └───────────────────────────────────────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
```

---

## 3. Core Interface

```python
from typing import Literal, Optional, AsyncIterator
from pydantic import BaseModel

class LLMRequest(BaseModel):
    """Unified request format — identical across providers."""
    model: Literal["mimo2.5", "deepseek-v4-flash", "bge-m3"]
    system_prompt: Optional[str] = None
    user_message: str
    temperature: float = 0.1
    max_tokens: int = 2000
    response_format: Optional[dict] = None  # {"type": "json_object"}
    stream: bool = False


class LLMResponse(BaseModel):
    """Unified response format — identical across providers."""
    content: str
    model: str
    usage: dict  # {"prompt_tokens": X, "completion_tokens": Y}
    cost: float  # Calculated in real-time based on provider pricing
    latency_ms: int
    finish_reason: str


async def llm_chat(request: LLMRequest) -> LLMResponse:
    """Single entry point for all LLM calls."""
    ...

async def llm_chat_stream(request: LLMRequest) -> AsyncIterator[str]:
    """Streaming variant."""
    ...

async def llm_embed(texts: list[str]) -> list[list[float]]:
    """Embedding — always routes to BGE-M3."""
    ...
```

---

## 4. Model Registry & Hot-Switching

```python
# backend/app/llm/registry.py

MODEL_REGISTRY = {
    "mimo2.5": {
        "provider": "openai_compatible",
        "base_url": "https://api.xiaomimimo.com/v1",
        "api_key_env": "MIMO_API_KEY",
        "pricing": {
            "input": 0.02,   # ¥ per 1K tokens
            "output": 0.02,
        },
        "capabilities": ["chat", "json_mode"],
        "max_tokens": 32768,
    },
    "deepseek-v4-flash": {
        "provider": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_env": "DEEPSEEK_API_KEY",
        "pricing": {
            "input": 0.001,
            "output": 0.002,
        },
        "capabilities": ["chat", "json_mode"],
        "max_tokens": 131072,
    },
    "bge-m3": {
        "provider": "openai_compatible",
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key_env": "EMBEDDING_API_KEY",
        "pricing": {"input": 0.0005, "output": 0},
        "capabilities": ["embedding"],
    },
}
```

To switch the model used by an Agent, change one string in config — nothing else:

```python
# Before: Analyzer uses MiMo 2.5
ANALYZER_MODEL = "mimo2.5"

# After: Switch to DeepSeek for cost savings
ANALYZER_MODEL = "deepseek-v4-flash"

# No code changes needed in Analyzer Agent — the wrapper handles routing.
```

---

## 5. Retry & Fallback

```python
async def llm_chat_with_fallback(request: LLMRequest) -> LLMResponse:
    """Internal: retry with exponential backoff, then fall back."""
    
    FALLBACK_CHAIN = {
        "mimo2.5": ["deepseek-v4-flash"],        # MiMo fails → DeepSeek
        "deepseek-v4-flash": ["mimo2.5"],         # DeepSeek fails → MiMo
    }
    
    models_to_try = [request.model] + FALLBACK_CHAIN.get(request.model, [])
    
    for attempt, model in enumerate(models_to_try):
        try:
            response = await _call_provider(model, request)
            return response
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            continue
        except (ServiceUnavailableError, TimeoutError):
            continue
    
    raise AllLLMsUnavailable("All LLM models unavailable")
```

---

## 6. Cost Tracking

Every LLM call records cost to the `llm_usage_logs` table for monitoring and cost control:

```sql
CREATE TABLE llm_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    model VARCHAR(50) NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    cost DECIMAL(10, 6) NOT NULL,
    latency_ms INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usage_task ON llm_usage_logs(task_id);
CREATE INDEX idx_usage_date ON llm_usage_logs(created_at);
```

---

## 7. Secret Management with Vault

API keys are never hardcoded. At startup:

```python
# backend/app/llm/secrets.py
import hvac  # HashiCorp Vault client

async def load_api_key(model: str) -> str:
    """Fetch API key from Vault, with 60-second in-memory cache."""
    if cached := _cache.get(model):
        if cached["expires"] > time.time():
            return cached["value"]
    
    client = hvac.Client(url=settings.VAULT_ADDR)
    secret = client.secrets.kv.read_secret_version(
        path=f"contractguard/llm/{model}"
    )
    key = secret["data"]["data"]["api_key"]
    
    _cache[model] = {"value": key, "expires": time.time() + 60}
    return key
```
