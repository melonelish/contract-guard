from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api import deps as deps_module
from app.api.v1 import contracts as contracts_module


@pytest.mark.asyncio
async def test_upload_and_list_contracts(client, monkeypatch):
    fake_user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        email="uploader@example.com",
        name="Uploader",
        role="owner",
        created_at=datetime.now(UTC),
    )
    fake_contract = SimpleNamespace(
        id=uuid4(),
        tenant_id=fake_user.tenant_id,
        user_id=fake_user.id,
        title="采购合同",
        file_url="s3://fake/sample.pdf",
        file_type="pdf",
        file_size=128,
        contract_type=None,
        status="uploaded",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        page_count=None,
    )

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    async def fake_create_contract(**_kwargs):
        return fake_contract

    async def fake_list_contracts(*_args, **_kwargs):
        return [fake_contract], 1

    async def fake_get_contract(*_args, **_kwargs):
        return fake_contract

    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(contracts_module, "create_contract", fake_create_contract)
    monkeypatch.setattr(contracts_module, "list_contracts", fake_list_contracts)
    monkeypatch.setattr(contracts_module, "get_contract", fake_get_contract)

    token = "test-token"

    upload_response = await client.post(
        "/api/v1/contracts/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("sample.pdf", b"%PDF-1.4 test content", "application/pdf")},
        data={"title": "采购合同"},
    )
    assert upload_response.status_code == 201
    contract_id = upload_response.json()["data"]["id"]

    list_response = await client.get(
        "/api/v1/contracts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    items = list_response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["id"] == contract_id

    detail_response = await client.get(
        f"/api/v1/contracts/{contract_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["title"] == "采购合同"
