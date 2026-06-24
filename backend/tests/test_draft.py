"""Tests for draft service."""

from datetime import UTC, datetime
from types import SimpleNamespace
import uuid

import pytest
from httpx import AsyncClient

from app.api import deps as deps_module
from app.api.v1 import contracts as contracts_module


@pytest.mark.asyncio
async def test_get_empty_draft(client: AsyncClient, monkeypatch):
    """Test GET /contracts/{id}/draft returns empty draft initially."""
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        role="owner",
        created_at=datetime.now(UTC),
    )
    contract_id = uuid.uuid4()
    fake_contract = SimpleNamespace(
        id=contract_id,
        tenant_id=fake_user.tenant_id,
        draft_content=None,
        draft_updated_at=None,
    )

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    async def fake_get_draft(*_args, **_kwargs):
        return fake_contract.draft_content, fake_contract.draft_updated_at

    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)

    from app.services import draft as draft_module
    monkeypatch.setattr(draft_module, "get_draft", fake_get_draft)

    token = "test-token"
    response = await client.get(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["contract_id"] == str(contract_id)
    assert data["data"]["content"] is None
    assert data["data"]["updated_at"] is None


@pytest.mark.asyncio
async def test_save_and_get_draft(client: AsyncClient, monkeypatch):
    """Test POST and GET draft content."""
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        role="owner",
        created_at=datetime.now(UTC),
    )
    contract_id = uuid.uuid4()
    draft_content = "<h1>Test Draft</h1><p>This is a test draft content.</p>"

    fake_contract = SimpleNamespace(
        id=contract_id,
        tenant_id=fake_user.tenant_id,
        draft_content=None,
        draft_updated_at=None,
    )

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    async def fake_save_draft(session, user, contract_id, content):
        fake_contract.draft_content = draft_content
        fake_contract.draft_updated_at = datetime.now(UTC)
        return fake_contract.draft_content, fake_contract.draft_updated_at

    async def fake_get_draft(*_args, **_kwargs):
        return fake_contract.draft_content, fake_contract.draft_updated_at

    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)

    from app.services import draft as draft_module
    monkeypatch.setattr(draft_module, "save_draft", fake_save_draft)
    monkeypatch.setattr(draft_module, "get_draft", fake_get_draft)

    token = "test-token"

    # Save draft
    save_response = await client.post(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": draft_content},
    )
    assert save_response.status_code == 200
    save_data = save_response.json()
    assert save_data["code"] == 0
    assert save_data["data"]["content"] == draft_content
    assert save_data["data"]["updated_at"] is not None

    # Get draft
    get_response = await client.get(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["code"] == 0
    assert get_data["data"]["content"] == draft_content


@pytest.mark.asyncio
async def test_update_draft(client: AsyncClient, monkeypatch):
    """Test updating draft content overwrites previous version."""
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        role="owner",
        created_at=datetime.now(UTC),
    )
    contract_id = uuid.uuid4()
    draft_v1 = "<p>Version 1</p>"
    draft_v2 = "<p>Version 2</p>"

    fake_contract = SimpleNamespace(
        id=contract_id,
        tenant_id=fake_user.tenant_id,
        draft_content=None,
        draft_updated_at=None,
    )

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    async def fake_save_draft(session, user, contract_id, content):
        fake_contract.draft_content = content
        fake_contract.draft_updated_at = datetime.now(UTC)
        return fake_contract.draft_content, fake_contract.draft_updated_at

    async def fake_get_draft(*_args, **_kwargs):
        return fake_contract.draft_content, fake_contract.draft_updated_at

    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)

    from app.services import draft as draft_module
    monkeypatch.setattr(draft_module, "save_draft", fake_save_draft)
    monkeypatch.setattr(draft_module, "get_draft", fake_get_draft)

    token = "test-token"

    # Save v1
    await client.post(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": draft_v1},
    )

    # Save v2 (should overwrite)
    save_response = await client.post(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": draft_v2},
    )
    assert save_response.status_code == 200

    # Get draft should return v2
    get_response = await client.get(
        f"/api/v1/contracts/{contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    get_data = get_response.json()
    assert get_data["data"]["content"] == draft_v2


@pytest.mark.asyncio
async def test_draft_not_found(client: AsyncClient, monkeypatch):
    """Test draft for non-existent contract returns 404."""
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        role="owner",
        created_at=datetime.now(UTC),
    )
    fake_contract_id = uuid.uuid4()

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    async def fake_save_draft(*_args, **_kwargs):
        raise ValueError("Contract not found or access denied")

    async def fake_get_draft(*_args, **_kwargs):
        raise ValueError("Contract not found or access denied")

    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)

    from app.services import draft as draft_module
    monkeypatch.setattr(draft_module, "save_draft", fake_save_draft)
    monkeypatch.setattr(draft_module, "get_draft", fake_get_draft)

    token = "test-token"

    # Save should return 404
    save_response = await client.post(
        f"/api/v1/contracts/{fake_contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "test"},
    )
    assert save_response.status_code == 404

    # Get should also return 404
    get_response = await client.get(
        f"/api/v1/contracts/{fake_contract_id}/draft",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 404
