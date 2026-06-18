from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api import deps as deps_module
from app.api.v1 import auth as auth_module


@pytest.mark.asyncio
async def test_register_login_and_me(client, monkeypatch):
    fake_user = SimpleNamespace(
        id=uuid4(),
        tenant_id=uuid4(),
        email="owner@example.com",
        name="Owner",
        role="owner",
        created_at=datetime.now(UTC),
    )

    async def fake_register_user(**_kwargs):
        return fake_user

    async def fake_authenticate_user(*_args, **_kwargs):
        return fake_user

    async def fake_get_user_by_id(*_args, **_kwargs):
        return fake_user

    monkeypatch.setattr(auth_module, "register_user", fake_register_user)
    monkeypatch.setattr(auth_module, "authenticate_user", fake_authenticate_user)
    monkeypatch.setattr(auth_module, "create_access_token", lambda user: ("test-token", 3600))
    monkeypatch.setattr(deps_module, "decode_access_token", lambda token: {"sub": str(fake_user.id)})
    monkeypatch.setattr(deps_module, "get_user_by_id", fake_get_user_by_id)

    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecret123",
            "name": "Owner",
            "tenant_name": "Alpha Team",
        },
    )
    assert register_response.status_code == 201
    register_payload = register_response.json()["data"]
    assert register_payload["user"]["email"] == "owner@example.com"
    assert register_payload["access_token"] == "test-token"

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "owner@example.com",
            "password": "supersecret123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["data"]["access_token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["data"]["name"] == "Owner"
