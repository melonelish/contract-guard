"""Draft service — save and retrieve contract draft content."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contract, User


async def get_draft(
    session: AsyncSession,
    user: User,
    contract_id: uuid.UUID,
) -> tuple[str | None, datetime | None]:
    """Get draft content for a contract.

    Returns (content, updated_at) tuple.
    Raises ValueError if contract not found or access denied.
    """
    contract = await session.get(Contract, contract_id)
    if not contract or contract.tenant_id != user.tenant_id:
        raise ValueError("Contract not found or access denied")

    return contract.draft_content, contract.draft_updated_at


async def save_draft(
    session: AsyncSession,
    user: User,
    contract_id: uuid.UUID,
    content: str,
) -> tuple[str, datetime]:
    """Save draft content for a contract.

    Returns (content, updated_at) tuple.
    """
    contract = await session.get(Contract, contract_id)
    if not contract or contract.tenant_id != user.tenant_id:
        raise ValueError("Contract not found or access denied")

    contract.draft_content = content
    contract.draft_updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(contract)

    return contract.draft_content or "", contract.draft_updated_at or datetime.utcnow()
