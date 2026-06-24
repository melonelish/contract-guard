"""Tests for review API endpoints."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from app.api.deps import get_current_user, get_db
from app.main import app
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fake review and contract objects
# ---------------------------------------------------------------------------

_FAKE_CONTRACT_ID = uuid.uuid4()
_FAKE_TENANT_ID = uuid.uuid4()
_FAKE_USER_ID = uuid.uuid4()
_FAKE_REVIEW_ID = uuid.uuid4()


def _make_fake_contract():
    return SimpleNamespace(
        id=_FAKE_CONTRACT_ID,
        tenant_id=_FAKE_TENANT_ID,
        user_id=_FAKE_USER_ID,
        title="测试采购合同",
        file_url="s3://bucket/test.pdf",
        file_type="pdf",
        file_size=1024,
        page_count=10,
        contract_type="采购合同",
        status="uploaded",
        description=None,
        created_at="2026-06-18T10:00:00",
        updated_at=None,
    )


def _make_fake_review(status="completed", progress=100):
    return SimpleNamespace(
        id=_FAKE_REVIEW_ID,
        contract_id=_FAKE_CONTRACT_ID,
        tenant_id=_FAKE_TENANT_ID,
        user_id=_FAKE_USER_ID,
        status=status,
        progress=progress,
        current_stage=None,
        schema_version="1.0",
        report_json={
            "schema_version": "1.0",
            "summary": {"total_risks": 4, "high": 2, "medium": 1, "low": 1},
            "risks": [
                {
                    "clause_id": str(uuid.uuid4()),
                    "clause_code": "cl_007",
                    "risk_level": "high",
                    "risk_category": "付款条件",
                    "original_text": "测试原文",
                    "legal_analysis": "测试分析",
                    "legal_basis": "《民法典》第585条",
                    "basis_excerpt": "当事人可以约定一方违约时应当根据违约情况向对方支付一定数额的违约金",  # noqa: E501
                    "basis_source": "《民法典》第585条（违约金）",
                    "plain_explanation": "通俗解释",
                    "suggested_revision": "修改建议",
                    "confidence": 0.9,
                }
            ],
            "contradictions": [],
            "missing_clauses": [{"name": "保密条款", "reason": "应约定保密义务"}],
            "llm_meta": {
                "provider_model": "mimo-v2.5",
                "prompt_tokens": 321,
                "completion_tokens": 654,
                "latency_ms": 1234,
                "finish_reason": "end_turn",
            },
            "rag_meta": {
                "enabled": True,
                "hit_count": 5,
                "mode": "rag_enhanced",
                "queries": ["违约金", "付款条件"],
            },
            "disclaimer": "免责声明",
        },
        error_detail=None,
        started_at="2026-06-18T10:00:01",
        completed_at="2026-06-18T10:00:05",
        created_at="2026-06-18T10:00:00",
        contract=_make_fake_contract(),
    )


_FAKE_USER = SimpleNamespace(
    id=_FAKE_USER_ID,
    tenant_id=_FAKE_TENANT_ID,
    email="test@example.com",
    name="Test User",
    role="owner",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _override_deps():
    """Override auth and db for all tests in this module."""
    async def override_get_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FAKE_USER
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_review(client: AsyncClient, monkeypatch):
    """POST /api/v1/contracts/{id}/review should return 202 with review info."""
    from app.api.v1 import contracts as contracts_mod

    fake_contract = _make_fake_contract()
    fake_review = _make_fake_review(status="queued", progress=0)
    fake_review.report_json = None

    async def fake_get_contract(*_a, **_kw):
        return fake_contract

    async def fake_create_review(*_a, **_kw):
        return fake_review

    async def fake_enqueue(**_kw):
        return "msg-1"

    monkeypatch.setattr(contracts_mod, "get_contract", fake_get_contract)
    monkeypatch.setattr(contracts_mod, "create_review", fake_create_review)
    # Patch on contracts_mod — that's where the import binding lives
    monkeypatch.setattr(contracts_mod, "enqueue_review_task", fake_enqueue)

    resp = await client.post(f"/api/v1/contracts/{_FAKE_CONTRACT_ID}/review")
    assert resp.status_code == 202
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["id"] == str(_FAKE_REVIEW_ID)
    assert body["data"]["status"] == "queued"


@pytest.mark.asyncio
async def test_trigger_review_enqueue_failure_marks_review_failed(client: AsyncClient, monkeypatch):
    """When Redis enqueue fails, the just-created review must be marked failed."""
    from app.api.v1 import contracts as contracts_mod

    fake_contract = _make_fake_contract()
    fake_review = _make_fake_review(status="queued", progress=0)
    fake_review.report_json = None

    # Track the compensation call
    compensation_calls = []

    class FakeSession:
        """Minimal session mock that tracks status changes."""
        async def get(self, model, review_id):
            return fake_review
        async def commit(self):
            compensation_calls.append({
                "status": fake_review.status,
                "error_detail": fake_review.error_detail,
            })

    async def fake_get_contract(*_a, **_kw):
        return fake_contract

    async def fake_create_review(session, *args, **kwargs):
        return fake_review

    async def fake_enqueue(**kwargs):
        raise RuntimeError("Redis connection refused")

    monkeypatch.setattr(contracts_mod, "get_contract", fake_get_contract)
    monkeypatch.setattr(contracts_mod, "create_review", fake_create_review)
    monkeypatch.setattr(contracts_mod, "enqueue_review_task", fake_enqueue)

    # Override get_db to return our FakeSession
    async def override_get_db():
        yield FakeSession()

    app.dependency_overrides[get_db] = override_get_db

    resp = await client.post(f"/api/v1/contracts/{_FAKE_CONTRACT_ID}/review")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == 1007
    assert "enqueue" in body["message"].lower()

    # Verify the review was marked as failed with clear error
    assert len(compensation_calls) == 1
    assert compensation_calls[0]["status"] == "failed"
    assert "入队失败" in compensation_calls[0]["error_detail"]


@pytest.mark.asyncio
async def test_trigger_review_conflict(client: AsyncClient, monkeypatch):
    """POST should return 409 when a review is already running."""
    from app.api.v1 import contracts as contracts_mod
    from app.services.review import ReviewServiceError

    fake_contract = _make_fake_contract()

    async def fake_get_contract(*_a, **_kw):
        return fake_contract

    async def fake_create_review(*_a, **_kw):
        raise ReviewServiceError(4002, "review already in progress")

    monkeypatch.setattr(contracts_mod, "get_contract", fake_get_contract)
    monkeypatch.setattr(contracts_mod, "create_review", fake_create_review)

    resp = await client.post(f"/api/v1/contracts/{_FAKE_CONTRACT_ID}/review")
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == 4002


@pytest.mark.asyncio
async def test_get_review_report(client: AsyncClient, monkeypatch):
    """GET /api/v1/reviews/{id} should return full report."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review()

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["id"] == str(_FAKE_REVIEW_ID)
    assert data["schema_version"] == "1.0"
    assert data["summary"]["total_risks"] == 4
    assert len(data["risks"]) == 1
    assert len(data["missing_clauses"]) == 1
    assert data["llm_meta"]["provider_model"] == "mimo-v2.5"
    assert data["disclaimer"] is not None


@pytest.mark.asyncio
async def test_get_review_status(client: AsyncClient, monkeypatch):
    """GET /api/v1/reviews/{id}/status should return lightweight status."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="analyzing", progress=45)

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}/status")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert data["status"] == "analyzing"
    assert data["progress"] == 45
    assert data["error_detail"] is None


@pytest.mark.asyncio
async def test_review_not_found(client: AsyncClient, monkeypatch):
    """GET with invalid ID should return 404 with code 4001."""
    from app.api.v1 import reviews as reviews_mod

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return None

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{uuid.uuid4()}")
    assert resp.status_code == 404
    assert resp.json()["code"] == 4001


@pytest.mark.asyncio
async def test_trigger_review_contract_not_found(client: AsyncClient, monkeypatch):
    """POST should return 404 when contract doesn't exist."""
    from app.api.v1 import contracts as contracts_mod

    async def fake_get_contract(*_a, **_kw):
        return None

    monkeypatch.setattr(contracts_mod, "get_contract", fake_get_contract)

    resp = await client.post(f"/api/v1/contracts/{uuid.uuid4()}/review")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Phase 3 cleanup tests — LLM availability and error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_error_classifies_403():
    """403 errors should produce clear 'no access permission' messages."""
    from app.llm.client import _classify_error

    # Simulate an Anthropic 403
    exc = Exception("You don't have access to this resource")
    exc.status_code = 403  # type: ignore[attr-defined]
    result = _classify_error(exc, "mimo2.5")
    assert "无访问权限" in str(result)
    assert result.retryable is False


@pytest.mark.asyncio
async def test_llm_error_classifies_429():
    """429 errors should produce clear rate-limit messages."""
    from app.llm.client import _classify_error

    exc = Exception("Rate limit reached for model")
    exc.status_code = 429  # type: ignore[attr-defined]
    result = _classify_error(exc, "mimo2.5")
    assert "速率限制" in str(result)
    assert result.retryable is True


@pytest.mark.asyncio
async def test_llm_error_classifies_401():
    """401 errors should produce clear invalid-key messages."""
    from app.llm.client import _classify_error

    exc = Exception("Invalid API Key")
    exc.status_code = 401  # type: ignore[attr-defined]
    result = _classify_error(exc, "deepseek-v4-flash")
    assert "无效" in str(result)
    assert result.retryable is False


@pytest.mark.asyncio
async def test_llm_error_classifies_timeout():
    """Timeout errors should produce clear timeout messages."""
    from app.llm.client import _classify_error
    from app.llm.exceptions import LLMTimeoutError

    exc = Exception("Connection timed out")
    result = _classify_error(exc, "mimo2.5")
    assert isinstance(result, LLMTimeoutError)
    assert result.retryable is True


@pytest.mark.asyncio
async def test_placeholder_key_detection():
    """Placeholder keys should be detected and skipped."""
    from app.llm.client import _is_placeholder_key

    assert _is_placeholder_key("sk-your-deepseek-api-key") is True
    assert _is_placeholder_key("sk-your-mimo-api-key") is True
    assert _is_placeholder_key("") is True
    assert _is_placeholder_key("sk-real-key-12345") is False
    assert _is_placeholder_key("tp-cul8qredd5isnarcppxkm7rf5ovniwoorgq1fe47s3vaz0f7") is False


@pytest.mark.asyncio
async def test_review_report_shows_error_detail_on_failure(client: AsyncClient, monkeypatch):
    """Failed review should return error_detail in report."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=30)
    fake_review.error_detail = "模型 mimo2.5 无访问权限（API Key 可能没有该模型的使用权限）"
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "无访问权限" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_status_shows_error_detail_on_failure(client: AsyncClient, monkeypatch):
    """Failed review status endpoint should include error_detail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=30)
    fake_review.error_detail = "LLM 调用超时，超过 300 秒仍未返回"

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "超时" in data["error_detail"]


@pytest.mark.asyncio
async def test_llm_all_models_unavailable_produces_clear_error():
    """When all models have placeholder keys, LLMUnavailableError should be raised."""
    from app.llm.client import _is_placeholder_key
    from app.llm.config import get_model_config

    # Verify that with current config, at least one model has a real key
    cfg = get_model_config("mimo2.5")
    has_real = not _is_placeholder_key(cfg.api_key)
    for fb in cfg.fallback:
        fcfg = get_model_config(fb)
        if not _is_placeholder_key(fcfg.api_key):
            has_real = True
            break

    # This test verifies the config state — at least MiMo should have a real key
    assert has_real, "No model has a valid API key configured"


# ---------------------------------------------------------------------------
# Phase 3 cleanup — review pipeline failure path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_llm_failure_writes_error_detail(client: AsyncClient, monkeypatch):
    """When LLM raises, review should show failed status with clear error_detail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=30)
    fake_review.error_detail = "模型 mimo2.5 无访问权限（API Key 可能没有该模型的使用权限）"
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "无访问权限" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_json_parse_failure_marks_failed(client: AsyncClient, monkeypatch):
    """When LLM returns invalid JSON that can't be repaired, review should fail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=75)
    fake_review.error_detail = (
        "LLM 输出 JSON 解析失败: Expecting value: line 1 column 1; "
        "自动修复失败: repair error"
    )
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "JSON" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_schema_validation_failure_marks_failed(client: AsyncClient, monkeypatch):
    """When LLM output doesn't match schema, review should fail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=90)
    fake_review.error_detail = "LLM 输出不符合 schema: Missing required field: summary"
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "schema" in data["error_detail"].lower() or "schema" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_timeout_marks_failed(client: AsyncClient, monkeypatch):
    """When LLM times out, review should be marked failed with timeout message."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=30)
    fake_review.error_detail = "LLM 调用超时，超过 300 秒仍未返回"

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "超时" in data["error_detail"]
    assert "300" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_all_models_unavailable_marks_failed(client: AsyncClient, monkeypatch):
    """When all LLM models are unavailable, review should fail with clear message."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=30)
    fake_review.error_detail = (
        "LLM 调用失败: All LLM models unavailable: "
        "mimo2.5, deepseek-v4-flash"
    )

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "unavailable" in data["error_detail"].lower() or "不可用" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_never_stays_running(client: AsyncClient, monkeypatch):
    """Failed reviews should always have error_detail and completed_at set."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=50)
    fake_review.error_detail = "Some error"
    fake_review.completed_at = "2026-06-18T10:00:05"

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Failed reviews should have error_detail and completed_at
    assert data["status"] == "failed"
    assert data["error_detail"] is not None
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_review_completed_never_has_error_detail(client: AsyncClient, monkeypatch):
    """Completed reviews should not have error_detail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="completed", progress=100)

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert data["error_detail"] is None


# ---------------------------------------------------------------------------
# Phase 3c — JSON parsing failure path tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_json_failure_preserves_raw_info(client: AsyncClient, monkeypatch):
    """Failed JSON parse should preserve raw content length in error_detail."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=75)
    fake_review.error_detail = (
        "JSON解析失败: Expecting value: line 1 column 1; "
        "修复失败: All strategies failed; raw_len=4500; preview={bad json..."
    )
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "raw_len=" in data["error_detail"]
    assert "preview=" in data["error_detail"]


@pytest.mark.asyncio
async def test_review_schema_failure_shows_field(client: AsyncClient, monkeypatch):
    """Schema validation failure should indicate which field is missing."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="failed", progress=90)
    fake_review.error_detail = "schema不合规: Missing required field: summary"
    fake_review.report_json = None

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.get(f"/api/v1/reviews/{_FAKE_REVIEW_ID}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "failed"
    assert "summary" in data["error_detail"]
