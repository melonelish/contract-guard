from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Contract, User

settings = get_settings()
SUPPORTED_FILE_TYPES = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 50 * 1024 * 1024


class ContractServiceError(Exception):
    pass


def detect_file_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix not in SUPPORTED_FILE_TYPES:
        raise ContractServiceError("unsupported file type")
    return suffix


def ensure_file_size(file_size: int) -> None:
    if file_size > MAX_FILE_SIZE:
        raise ContractServiceError("file too large")


def build_object_name(user: User, filename: str) -> str:
    extension = detect_file_extension(filename)
    return f"{user.tenant_id}/{user.id}/{uuid.uuid4()}.{extension}"


def upload_bytes_to_storage(filename: str, content: bytes, content_type: str) -> str:
    from minio import Minio
    from minio.error import S3Error

    client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        object_name = filename
        from io import BytesIO

        client.put_object(
            settings.minio_bucket,
            object_name,
            BytesIO(content),
            len(content),
            content_type=content_type,
        )
        return f"s3://{settings.minio_bucket}/{object_name}"
    except S3Error as exc:
        raise ContractServiceError("storage error") from exc


async def create_contract(
    session: AsyncSession,
    user: User,
    title: str | None,
    filename: str,
    content: bytes,
    content_type: str,
) -> Contract:
    ensure_file_size(len(content))
    extension = detect_file_extension(filename)
    object_name = build_object_name(user, filename)
    file_url = upload_bytes_to_storage(object_name, content, content_type)
    contract = Contract(
        tenant_id=user.tenant_id,
        user_id=user.id,
        title=title or Path(filename).stem,
        file_url=file_url,
        file_type=extension,
        file_size=len(content),
        status="uploaded",
    )
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


async def list_contracts(
    session: AsyncSession,
    user: User,
    page: int,
    page_size: int,
) -> tuple[list[Contract], int]:
    stmt = (
        select(Contract)
        .where(Contract.tenant_id == user.tenant_id)
        .order_by(Contract.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await session.scalars(stmt)).all())
    total = await session.scalar(
        select(func.count()).select_from(Contract).where(Contract.tenant_id == user.tenant_id)
    )
    return items, int(total or 0)


async def get_contract(session: AsyncSession, user: User, contract_id: uuid.UUID) -> Contract | None:
    contract = await session.get(Contract, contract_id)
    if not contract or contract.tenant_id != user.tenant_id:
        return None
    return contract
