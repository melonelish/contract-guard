from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    app_name: str = "ContractGuard"
    app_env: str = "development"
    app_debug: bool = True
    secret_key: str = "change-me"
    database_url: str = "postgresql+asyncpg://contractguard:changeme@localhost:5432/contractguard"
    database_sync_url: str = "postgresql://contractguard:changeme@localhost:5432/contractguard"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "contractguard-uploads"
    minio_secure: bool = False
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]
    local_storage_path: str = "backend/.data/uploads"

    # LLM — MiMo 2.5 Pro (primary, Anthropic-compatible)
    mimo_api_key: str = ""
    # WebSocket (Phase 4)
    ws_ticket_ttl: int = 60
    ws_max_duration: int = 1800  # 30 minutes
    mimo_base_url: str = "https://token-plan-cn.xiaomimimo.com/anthropic"
    mimo_model: str = "mimo-v2.5"

    # LLM — DeepSeek V4-Flash (backup, OpenAI-compatible)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-v4-flash"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
