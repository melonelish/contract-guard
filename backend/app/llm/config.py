"""LLM model registry and configuration."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import get_settings


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""

    name: str
    provider: str  # "anthropic" or "openai"
    base_url: str
    api_key: str
    model_id: str
    max_tokens: int = 8192
    timeout: int = 120
    temperature: float = 0.1
    fallback: list[str] = field(default_factory=list)


def get_model_config(model_name: str) -> ModelConfig:
    """Get configuration for a named model from environment settings."""
    settings = get_settings()

    models = {
        "mimo2.5": ModelConfig(
            name="mimo2.5",
            provider="anthropic",
            base_url=settings.mimo_base_url,
            api_key=settings.mimo_api_key,
            model_id=settings.mimo_model,
            max_tokens=8192,
            timeout=120,
            temperature=0.1,
            fallback=["deepseek-v4-flash"],
        ),
        "deepseek-v4-flash": ModelConfig(
            name="deepseek-v4-flash",
            provider="openai",
            base_url=settings.deepseek_base_url,
            api_key=settings.deepseek_api_key,
            model_id=settings.deepseek_model,
            max_tokens=8192,
            timeout=90,
            temperature=0.1,
            fallback=["mimo2.5"],
        ),
    }

    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}")
    return models[model_name]


def get_primary_model() -> ModelConfig:
    """Get the primary analysis model (MiMo 2.5)."""
    return get_model_config("mimo2.5")
