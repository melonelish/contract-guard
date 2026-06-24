from __future__ import annotations

import pytest
from app.llm import client as client_module
from app.llm.client import _classify_error, _is_placeholder_key
from app.llm.config import ModelConfig
from app.llm.exceptions import LLMError, LLMTimeoutError, LLMUnavailableError


@pytest.mark.asyncio
async def test_llm_chat_falls_back_to_secondary_model(monkeypatch):
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="primary-key",
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="backup-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    async def fake_call_with_retry(cfg, *_args, **_kwargs):
        if cfg.name == "mimo2.5":
            raise LLMError("primary failed", model=cfg.name, retryable=False)
        return {
            "content": "{}",
            "model": cfg.model_id,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            "latency_ms": 12,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(client_module, "_call_with_retry", fake_call_with_retry)

    result = await client_module.llm_chat(user_message="hello")

    assert result["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_llm_chat_raises_when_all_models_fail(monkeypatch):
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="primary-key",
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="backup-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    async def always_fail(cfg, *_args, **_kwargs):
        raise LLMError(f"{cfg.name} failed", model=cfg.name, retryable=True)

    monkeypatch.setattr(client_module, "_call_with_retry", always_fail)

    with pytest.raises(LLMUnavailableError):
        await client_module.llm_chat(user_message="hello")


@pytest.mark.asyncio
async def test_llm_chat_skips_placeholder_keys(monkeypatch):
    """Models with placeholder keys should be skipped entirely."""
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="sk-your-mimo-api-key",  # placeholder
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="sk-real-deepseek-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    called_models: list[str] = []

    async def fake_call_with_retry(cfg, *_args, **_kwargs):
        called_models.append(cfg.name)
        return {
            "content": "{}",
            "model": cfg.model_id,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            "latency_ms": 12,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(client_module, "_call_with_retry", fake_call_with_retry)

    result = await client_module.llm_chat(user_message="hello")

    assert called_models == ["deepseek-v4-flash"]
    assert result["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_llm_chat_all_placeholder_raises(monkeypatch):
    """When all models have placeholder keys, LLMUnavailableError should be raised."""
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="sk-your-mimo-api-key",
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="sk-your-deepseek-api-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    with pytest.raises(LLMUnavailableError):
        await client_module.llm_chat(user_message="hello")


@pytest.mark.asyncio
async def test_llm_chat_403_primary_falls_back(monkeypatch):
    """403 on primary should trigger fallback, not abort."""
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="real-mimo-key",
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="real-deepseek-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    call_count = {"mimo": 0, "deepseek": 0}

    async def fake_call_with_retry(cfg, *_args, **_kwargs):
        if cfg.name == "mimo2.5":
            call_count["mimo"] += 1
            raise LLMError("无访问权限", model=cfg.name, retryable=False)
        call_count["deepseek"] += 1
        return {
            "content": '{"summary": {"total_risks": 0, "high": 0, "medium": 0, "low": 0}, "risks": []}',  # noqa: E501
            "model": cfg.model_id,
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            "latency_ms": 100,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(client_module, "_call_with_retry", fake_call_with_retry)

    result = await client_module.llm_chat(user_message="test contract")

    assert call_count["mimo"] == 1
    assert call_count["deepseek"] == 1
    assert result["model"] == "deepseek-v4-flash"


@pytest.mark.asyncio
async def test_llm_chat_429_retries_then_falls_back(monkeypatch):
    """429 should retry on same model, then fall back if retries exhausted."""
    configs = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url="https://example.com/anthropic",
            api_key="real-mimo-key",
            model_id="mimo-v2.5",
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url="https://example.com/openai",
            api_key="real-deepseek-key",
            model_id="deepseek-v4-flash",
            fallback=[],
        ),
    }

    monkeypatch.setattr(client_module, "get_model_config", lambda model_name: configs[model_name])

    async def fake_call_with_retry(cfg, *_args, **_kwargs):
        if cfg.name == "mimo2.5":
            raise LLMError("速率限制", model=cfg.name, retryable=True)
        return {
            "content": "{}",
            "model": cfg.model_id,
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            "latency_ms": 50,
            "finish_reason": "stop",
        }

    monkeypatch.setattr(client_module, "_call_with_retry", fake_call_with_retry)

    result = await client_module.llm_chat(user_message="test")
    assert result["model"] == "deepseek-v4-flash"


class TestClassifyError:
    """Verify _classify_error produces clear, accurate messages."""

    def test_403_no_access(self):
        exc = Exception("You don't have access to this resource")
        exc.status_code = 403  # type: ignore[attr-defined]
        result = _classify_error(exc, "mimo2.5")
        assert "无访问权限" in str(result)
        assert result.model == "mimo2.5"
        assert result.retryable is False

    def test_429_rate_limit(self):
        exc = Exception("Rate limit reached for model mimo-v2.5")
        exc.status_code = 429  # type: ignore[attr-defined]
        result = _classify_error(exc, "mimo2.5")
        assert "速率限制" in str(result)
        assert result.retryable is True

    def test_401_invalid_key(self):
        exc = Exception("Invalid API Key")
        exc.status_code = 401  # type: ignore[attr-defined]
        result = _classify_error(exc, "deepseek-v4-flash")
        assert "无效" in str(result)
        assert result.retryable is False

    def test_500_server_error(self):
        exc = Exception("Internal server error")
        exc.status_code = 500  # type: ignore[attr-defined]
        result = _classify_error(exc, "mimo2.5")
        assert "服务端异常" in str(result)
        assert result.retryable is True

    def test_503_overloaded(self):
        exc = Exception("Model overloaded")
        exc.status_code = 503  # type: ignore[attr-defined]
        result = _classify_error(exc, "mimo2.5")
        assert "服务端异常" in str(result)
        assert result.retryable is True

    def test_timeout(self):
        exc = Exception("Connection timed out")
        result = _classify_error(exc, "mimo2.5")
        # _classify_error returns LLMTimeoutError with English message
        assert isinstance(result, LLMTimeoutError)
        assert result.retryable is True

    def test_connection_error(self):
        exc = Exception("Connection refused")
        result = _classify_error(exc, "mimo2.5")
        assert "连接" in str(result)
        assert result.retryable is True

    def test_unknown_error(self):
        exc = Exception("Something weird happened")
        result = _classify_error(exc, "mimo2.5")
        assert "调用失败" in str(result)
        assert result.model == "mimo2.5"


class TestPlaceholderKeyDetection:
    """Verify placeholder API keys are detected."""

    def test_empty_key(self):
        assert _is_placeholder_key("") is True

    def test_placeholder_sk(self):
        assert _is_placeholder_key("sk-your-deepseek-api-key") is True

    def test_placeholder_generic(self):
        assert _is_placeholder_key("your-key-here") is True

    def test_real_mimo_key(self):
        assert _is_placeholder_key("tp-cul8qredd5isnarcppxkm7rf5ovniwoorgq1fe47s3vaz0f7") is False

    def test_real_deepseek_key(self):
        assert _is_placeholder_key("sk-39983afbd2434d74a9d89d044c6874fa") is False

    def test_change_me(self):
        assert _is_placeholder_key("change-me") is True


class TestLLMExceptions:
    """Verify exception types have correct attributes."""

    def test_llm_error(self):
        exc = LLMError("test message", model="mimo2.5", retryable=False)
        assert str(exc) == "test message"
        assert exc.model == "mimo2.5"
        assert exc.retryable is False

    def test_timeout_error(self):
        exc = LLMTimeoutError(model="mimo2.5", timeout=120)
        assert "timed out" in str(exc)
        assert exc.model == "mimo2.5"
        assert exc.retryable is True

    def test_unavailable_error(self):
        exc = LLMUnavailableError(["mimo2.5", "deepseek-v4-flash"])
        assert "mimo2.5" in str(exc)
        assert "deepseek-v4-flash" in str(exc)
        assert exc.retryable is True
