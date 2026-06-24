"""Unified LLM client with retry, timeout, fallback, and raw response logging.

Supports two provider formats:
- Anthropic Messages API (MiMo 2.5 Pro)
- OpenAI Chat Completions API (DeepSeek V4-Flash)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.llm.config import ModelConfig, get_model_config
from app.llm.exceptions import LLMError, LLMTimeoutError, LLMUnavailableError

logger = logging.getLogger("contractguard.llm")


def _classify_error(exc: Exception, model_name: str) -> LLMError:
    """Classify an exception into a specific LLMError with clear message."""
    error_str = str(exc)
    lower = error_str.lower()

    # Check for status code on Anthropic/OpenAI exceptions
    status_code = getattr(exc, "status_code", None)

    # 401 / invalid key
    if status_code == 401 or ("invalid" in lower and "key" in lower):
        return LLMError(
            f"模型 {model_name} API Key 无效或已过期",
            model=model_name, retryable=False,
        )

    # 403 / access denied
    if status_code == 403 or "access" in lower or "permission" in lower:
        return LLMError(
            f"模型 {model_name} 无访问权限（API Key 可能没有该模型的使用权限）",
            model=model_name, retryable=False,
        )

    # 429 / rate limit
    if status_code == 429 or "rate" in lower or "limit" in lower:
        return LLMError(
            f"模型 {model_name} 触发速率限制，请稍后重试",
            model=model_name, retryable=True,
        )

    # 500/502/503 / server error
    if status_code in (500, 502, 503) or any(k in lower for k in ["overloaded", "503", "502"]):
        return LLMError(
            f"模型 {model_name} 服务端异常（HTTP {status_code}）",
            model=model_name, retryable=True,
        )

    # Timeout
    if "timeout" in lower or "timed out" in lower:
        return LLMTimeoutError(model=model_name, timeout=120)

    # Connection error
    if "connection" in lower or "connect" in lower:
        return LLMError(
            f"模型 {model_name} 网络连接失败，请检查网络或 API 地址",
            model=model_name, retryable=True,
        )

    # Unknown
    return LLMError(
        f"模型 {model_name} 调用失败: {error_str[:200]}",
        model=model_name, retryable=False,
    )


def _is_retryable(exc: Exception) -> bool:
    """Determine if an LLM error is retryable."""
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        return status_code in (429, 500, 502, 503)

    lower = str(exc).lower()
    if any(k in lower for k in ["429", "rate", "503", "502", "500", "overloaded", "timeout", "connection"]):
        return True
    if "401" in lower or "403" in lower or ("invalid" in lower and "key" in lower):
        return False
    return False


def _is_placeholder_key(api_key: str) -> bool:
    """Check if an API key is a placeholder value."""
    if not api_key or not api_key.strip():
        return True
    placeholders = ["sk-your-", "your-", "change-me", "placeholder", "xxx"]
    return any(p in api_key.lower() for p in placeholders)


async def llm_chat(
    *,
    model: str = "mimo2.5",
    system_prompt: str | None = None,
    user_message: str,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    response_format: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Single entry point for all LLM chat calls.

    Returns a dict with keys: content, model, usage, latency_ms, finish_reason.
    Automatically retries with exponential backoff and falls back to alternate models.
    """
    cfg = get_model_config(model)

    # Build fallback chain, skipping models with placeholder keys
    models_to_try: list[ModelConfig] = []
    for fallback_name in [model] + cfg.fallback:
        try:
            fcfg = get_model_config(fallback_name)
        except ValueError:
            continue
        if fcfg.name in [m.name for m in models_to_try]:
            continue  # deduplicate
        if _is_placeholder_key(fcfg.api_key):
            logger.warning("llm.skip_placeholder", extra={"model": fcfg.name})
            continue
        models_to_try.append(fcfg)

    if not models_to_try:
        raise LLMUnavailableError([model])

    last_error: Exception | None = None
    for attempt_cfg in models_to_try:
        try:
            return await _call_with_retry(
                attempt_cfg, system_prompt, user_message,
                temperature, max_tokens, response_format,
            )
        except LLMError as exc:
            last_error = exc
            logger.warning("llm.fallback", extra={
                "from_model": attempt_cfg.name,
                "to_model": "next" if attempt_cfg != models_to_try[-1] else "none",
                "error": str(exc)[:300],
                "retryable": exc.retryable,
            })
            continue

    raise LLMUnavailableError([m.name for m in models_to_try]) from last_error


async def _call_with_retry(
    cfg: ModelConfig,
    system_prompt: str | None,
    user_message: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, Any] | None,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Call a single model with exponential backoff retry."""
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await _call_provider(
                cfg, system_prompt, user_message,
                temperature, max_tokens, response_format,
            )
        except Exception as exc:
            last_error = exc
            classified = _classify_error(exc, cfg.name)

            if classified.retryable and attempt < max_retries:
                wait = 2 ** (attempt + 1)
                logger.warning("llm.retry", extra={
                    "model": cfg.name,
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "wait_seconds": wait,
                    "error": str(classified)[:300],
                })
                await asyncio.sleep(wait)
            else:
                # Non-retryable or retries exhausted
                raise classified from exc

    raise last_error or LLMError("max retries exceeded", model=cfg.name)


async def _call_provider(
    cfg: ModelConfig,
    system_prompt: str | None,
    user_message: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, Any] | None,
) -> dict[str, Any]:
    """Route to the correct provider based on config."""
    if cfg.provider == "anthropic":
        return await _call_anthropic(cfg, system_prompt, user_message, temperature, max_tokens)
    else:
        return await _call_openai(cfg, system_prompt, user_message, temperature, max_tokens, response_format)


async def _call_anthropic(
    cfg: ModelConfig,
    system_prompt: str | None,
    user_message: str,
    temperature: float,
    max_tokens: int,
) -> dict[str, Any]:
    """Call via Anthropic Messages API (for MiMo 2.5 Pro)."""
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
    )

    kwargs: dict[str, Any] = {
        "model": cfg.model_id,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_message}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    start = time.monotonic()
    response = await client.messages.create(**kwargs)
    latency_ms = int((time.monotonic() - start) * 1000)

    # Extract text content from response
    content = ""
    for block in response.content:
        if block.type == "text":
            content += block.text

    usage = response.usage

    logger.info("llm.call", extra={
        "model": cfg.name,
        "model_id": cfg.model_id,
        "provider": "anthropic",
        "prompt_tokens": usage.input_tokens,
        "completion_tokens": usage.output_tokens,
        "latency_ms": latency_ms,
        "stop_reason": response.stop_reason,
        "content_length": len(content),
    })

    return {
        "content": content,
        "model": cfg.model_id,
        "usage": {
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
        },
        "latency_ms": latency_ms,
        "finish_reason": response.stop_reason or "end_turn",
    }


async def _call_openai(
    cfg: ModelConfig,
    system_prompt: str | None,
    user_message: str,
    temperature: float,
    max_tokens: int,
    response_format: dict[str, Any] | None,
) -> dict[str, Any]:
    """Call via OpenAI Chat Completions API (for DeepSeek)."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=cfg.api_key,
        base_url=cfg.base_url,
        timeout=cfg.timeout,
    )

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    kwargs: dict[str, Any] = {
        "model": cfg.model_id,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    start = time.monotonic()
    response = await client.chat.completions.create(**kwargs)
    latency_ms = int((time.monotonic() - start) * 1000)

    choice = response.choices[0]
    content = choice.message.content or ""
    usage = response.usage

    logger.info("llm.call", extra={
        "model": cfg.name,
        "model_id": cfg.model_id,
        "provider": "openai",
        "prompt_tokens": usage.prompt_tokens if usage else 0,
        "completion_tokens": usage.completion_tokens if usage else 0,
        "latency_ms": latency_ms,
        "finish_reason": choice.finish_reason,
        "content_length": len(content),
    })

    return {
        "content": content,
        "model": cfg.model_id,
        "usage": {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
        },
        "latency_ms": latency_ms,
        "finish_reason": choice.finish_reason or "stop",
    }
