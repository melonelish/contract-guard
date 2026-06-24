import asyncio

from fastapi import APIRouter
from redis.asyncio import Redis
from sqlalchemy import text

from app.config import get_settings
from app.db.session import get_engine
from app.schemas.api import APIResponse, HealthPayload

router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=APIResponse[HealthPayload])
async def health_check() -> APIResponse[HealthPayload]:
    checks = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
        "minio": await check_minio(),
        "environment": settings.app_env,
    }
    return APIResponse(
        data=HealthPayload(
            status="healthy",
            version="0.1.0",
            checks=checks,
        )
    )


async def check_postgres() -> str:
    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


async def check_redis() -> str:
    client = Redis.from_url(settings.redis_url)
    try:
        result = await client.ping()
        return "ok" if result else "error"
    except Exception:
        return "error"
    finally:
        await client.aclose()


async def check_minio() -> str:
    try:
        from minio import Minio
    except Exception:
        return "error"

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    try:
        await asyncio.to_thread(client.bucket_exists, settings.minio_bucket)
        return "ok"
    except Exception:
        return "error"
