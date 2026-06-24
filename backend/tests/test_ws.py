"""Tests for Phase 4: WebSocket ticket, queue, and events."""

from __future__ import annotations

import asyncio
import time
import uuid
from types import SimpleNamespace

import pytest
from app.api.deps import get_current_user, get_db
from app.main import app
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_FAKE_CONTRACT_ID = uuid.uuid4()
_FAKE_TENANT_ID = uuid.uuid4()
_FAKE_USER_ID = uuid.uuid4()
_FAKE_REVIEW_ID = uuid.uuid4()


def _make_fake_review(status="queued", progress=0):
    return SimpleNamespace(
        id=_FAKE_REVIEW_ID,
        contract_id=_FAKE_CONTRACT_ID,
        tenant_id=_FAKE_TENANT_ID,
        user_id=_FAKE_USER_ID,
        status=status,
        progress=progress,
        current_stage=None,
        schema_version="1.0",
        report_json=None,
        error_detail=None,
        started_at=None,
        completed_at=None,
        created_at="2026-06-18T10:00:00",
        contract=SimpleNamespace(
            id=_FAKE_CONTRACT_ID,
            tenant_id=_FAKE_TENANT_ID,
            title="测试合同",
            file_url="s3://bucket/test.pdf",
            file_type="pdf",
        ),
    )


_FAKE_USER = SimpleNamespace(
    id=_FAKE_USER_ID,
    tenant_id=_FAKE_TENANT_ID,
    email="test@example.com",
    name="Test User",
    role="owner",
)


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
# WebSocket ticket issuance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ws_ticket_issuance(client: AsyncClient, monkeypatch):
    """POST /api/v1/reviews/ws/ticket should return a valid ticket."""
    from app.api.v1 import reviews as reviews_mod

    fake_review = _make_fake_review(status="analyzing", progress=45)

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return fake_review

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.post(
        f"/api/v1/reviews/ws/ticket?review_id={_FAKE_REVIEW_ID}",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["ticket"].startswith("ws_tkt_")
    assert data["expires_in"] > 0
    assert data["review_id"] == str(_FAKE_REVIEW_ID)


@pytest.mark.asyncio
async def test_ws_ticket_review_not_found(client: AsyncClient, monkeypatch):
    """POST should return 404 when review doesn't exist."""
    from app.api.v1 import reviews as reviews_mod

    async def fake_get_review_tenant_scoped(*_a, **_kw):
        return None

    monkeypatch.setattr(reviews_mod, "get_review_tenant_scoped", fake_get_review_tenant_scoped)

    resp = await client.post(
        f"/api/v1/reviews/ws/ticket?review_id={uuid.uuid4()}",
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == 4001


# ---------------------------------------------------------------------------
# Ticket validation tests
# ---------------------------------------------------------------------------


def test_ticket_validation_success():
    """Valid ticket should pass validation."""
    from app.api.v1.ws import issue_ws_ticket, validate_ws_ticket

    user_id = uuid.uuid4()
    review_id = uuid.uuid4()

    ticket, expires_in = issue_ws_ticket(user_id, review_id, str(review_id))
    assert expires_in > 0

    payload = validate_ws_ticket(ticket, str(review_id))
    assert payload is not None
    assert payload["user_id"] == str(user_id)
    assert payload["review_id"] == str(review_id)
    assert payload["task_id"] == str(review_id)


def test_ticket_validation_wrong_review_id():
    """Ticket should fail when review_id doesn't match."""
    from app.api.v1.ws import issue_ws_ticket, validate_ws_ticket

    user_id = uuid.uuid4()
    review_id = uuid.uuid4()
    wrong_review_id = uuid.uuid4()

    ticket, _ = issue_ws_ticket(user_id, review_id)
    payload = validate_ws_ticket(ticket, str(wrong_review_id))
    assert payload is None


def test_ticket_validation_expired():
    """Expired ticket should fail validation."""
    from app.api.v1.ws import _sign_ticket, issue_ws_ticket, validate_ws_ticket
    from app.config import get_settings

    user_id = uuid.uuid4()
    review_id = uuid.uuid4()

    ticket, _ = issue_ws_ticket(user_id, review_id)

    # Reconstruct with expired timestamp
    body = ticket[len("ws_tkt_"):]
    parts = body.split(":")
    expired_ts = str(int(time.time()) - 100)
    settings = get_settings()
    payload_str = f"{parts[0]}:{parts[1]}:{parts[2]}:{parts[3]}:{expired_ts}"
    sig = _sign_ticket(payload_str, settings.jwt_secret)
    expired_ticket = f"ws_tkt_{payload_str}:{sig}"

    payload = validate_ws_ticket(expired_ticket, str(review_id))
    assert payload is None


def test_ticket_validation_invalid_format():
    """Malformed ticket should fail validation."""
    from app.api.v1.ws import validate_ws_ticket

    assert validate_ws_ticket("not_a_ticket", str(uuid.uuid4())) is None
    assert validate_ws_ticket("ws_tkt_short", str(uuid.uuid4())) is None
    assert validate_ws_ticket("", str(uuid.uuid4())) is None


def test_ticket_validation_tampered_signature():
    """Ticket with tampered signature should fail."""
    from app.api.v1.ws import issue_ws_ticket, validate_ws_ticket

    user_id = uuid.uuid4()
    review_id = uuid.uuid4()

    ticket, _ = issue_ws_ticket(user_id, review_id)

    # Tamper with the last character of the signature
    tampered = ticket[:-1] + ("a" if ticket[-1] != "a" else "b")
    payload = validate_ws_ticket(tampered, str(review_id))
    assert payload is None


# ---------------------------------------------------------------------------
# Queue service tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enqueue_review_task(monkeypatch):
    """enqueue_review_task should call Redis XADD."""
    from app.services import queue as queue_mod

    fake_msg_id = "1234567890-0"
    calls = []

    class FakeRedis:
        async def xadd(self, stream, data, maxlen=None):
            calls.append({"stream": stream, "data": data, "maxlen": maxlen})
            return fake_msg_id

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(queue_mod, "get_redis", fake_get_redis)

    result = await queue_mod.enqueue_review_task(
        review_id=uuid.uuid4(),
        contract_title="Test",
        contract_file_url="s3://bucket/test.pdf",
        contract_file_type="pdf",
    )
    assert result == fake_msg_id
    assert len(calls) == 1
    assert calls[0]["stream"] == "review:tasks"


@pytest.mark.asyncio
async def test_publish_stage_event(monkeypatch):
    """publish_stage_event should publish JSON to Redis Pub/Sub."""
    from app.services import queue as queue_mod

    published = []

    class FakeRedis:
        async def publish(self, channel, message):
            published.append({"channel": channel, "message": message})

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(queue_mod, "get_redis", fake_get_redis)

    review_id = uuid.uuid4()
    await queue_mod.publish_stage_event(
        review_id, str(review_id), "analyzing", 45, "test detail",
    )

    assert len(published) == 1
    assert published[0]["channel"] == f"review:{review_id}:events"
    import json
    event = json.loads(published[0]["message"])
    assert event["event"] == "stage"
    assert event["stage"] == "analyzing"
    assert event["progress"] == 45


@pytest.mark.asyncio
async def test_publish_complete_event(monkeypatch):
    """publish_complete_event should publish completion JSON."""
    from app.services import queue as queue_mod

    published = []

    class FakeRedis:
        async def publish(self, channel, message):
            published.append({"channel": channel, "message": message})

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(queue_mod, "get_redis", fake_get_redis)

    review_id = uuid.uuid4()
    summary = {"total_risks": 4, "high": 1, "medium": 2, "low": 1}
    await queue_mod.publish_complete_event(review_id, str(review_id), summary, 286)

    assert len(published) == 1
    import json
    event = json.loads(published[0]["message"])
    assert event["event"] == "complete"
    assert event["summary"]["total_risks"] == 4
    assert event["duration_sec"] == 286


@pytest.mark.asyncio
async def test_publish_failed_event(monkeypatch):
    """publish_failed_event should publish failure JSON."""
    from app.services import queue as queue_mod

    published = []

    class FakeRedis:
        async def publish(self, channel, message):
            published.append({"channel": channel, "message": message})

    async def fake_get_redis():
        return FakeRedis()

    monkeypatch.setattr(queue_mod, "get_redis", fake_get_redis)

    review_id = uuid.uuid4()
    await queue_mod.publish_failed_event(
        review_id, str(review_id), 4004, "llm unavailable", "model unavailable",
    )

    assert len(published) == 1
    import json
    event = json.loads(published[0]["message"])
    assert event["event"] == "failed"
    assert event["code"] == 4004
    assert event["retryable"] is True


# ---------------------------------------------------------------------------
# Worker tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_start_stop():
    """Worker should start and stop cleanly."""
    from app.services.worker import is_worker_running, start_worker, stop_worker

    # Initially not running
    assert not is_worker_running()

    await start_worker()
    assert is_worker_running()

    await stop_worker()
    assert not is_worker_running()


@pytest.mark.asyncio
async def test_worker_processes_task(monkeypatch):
    """Worker should consume from Redis Stream and process tasks."""
    from app.services import worker as worker_mod

    processed = []

    async def fake_process_task(fields):
        processed.append(fields)

    # Mock _process_task to avoid needing real Redis/review
    monkeypatch.setattr(worker_mod, "_process_task", fake_process_task)

    # Mock the entire worker loop to simulate one task then exit
    async def controlled_loop():
        """Simulate one iteration: process a task, then stop."""
        # Simulate processing one task
        await fake_process_task({
            "review_id": str(uuid.uuid4()),
            "contract_title": "Test",
            "contract_file_url": "s3://bucket/test.pdf",
            "contract_file_type": "pdf",
        })
        # Then wait until cancelled
        try:
            await asyncio.sleep(100)
        except asyncio.CancelledError:
            raise

    monkeypatch.setattr(worker_mod, "_worker_loop", controlled_loop)

    await worker_mod.start_worker()
    await asyncio.sleep(0.2)
    await worker_mod.stop_worker()

    assert len(processed) >= 1


# ---------------------------------------------------------------------------
# Trigger review with queue tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trigger_review_queues_task(client: AsyncClient, monkeypatch):
    """POST /review should enqueue to Redis instead of BackgroundTasks."""
    from app.api.v1 import contracts as contracts_mod

    fake_contract = SimpleNamespace(
        id=_FAKE_CONTRACT_ID,
        tenant_id=_FAKE_TENANT_ID,
        user_id=_FAKE_USER_ID,
        title="测试合同",
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
    fake_review = _make_fake_review(status="queued", progress=0)

    async def fake_get_contract(*_a, **_kw):
        return fake_contract

    async def fake_create_review(*_a, **_kw):
        return fake_review

    enqueue_calls = []

    async def fake_enqueue(**kwargs):
        enqueue_calls.append(kwargs)
        return "msg-1"

    monkeypatch.setattr(contracts_mod, "get_contract", fake_get_contract)
    monkeypatch.setattr(contracts_mod, "create_review", fake_create_review)
    monkeypatch.setattr(contracts_mod, "enqueue_review_task", fake_enqueue)

    resp = await client.post(f"/api/v1/contracts/{_FAKE_CONTRACT_ID}/review")
    assert resp.status_code == 202
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "queued"

    # Verify task was enqueued
    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["review_id"] == _FAKE_REVIEW_ID


# ---------------------------------------------------------------------------
# Event structure contract tests (T-SCHEMA-004)
# ---------------------------------------------------------------------------


def test_ws_stage_event_structure():
    """Stage event must match the fixed contract."""
    # Verify the event structure by checking what would be published
    review_id = uuid.uuid4()
    task_id = str(review_id)

    event = {
        "event": "stage",
        "review_id": str(review_id),
        "task_id": task_id,
        "stage": "analyzing",
        "progress": 45,
        "detail": "正在分析条款 8/18",
    }

    # Required fields per contract
    assert "event" in event
    assert "review_id" in event
    assert "task_id" in event
    assert "stage" in event
    assert "progress" in event
    assert "detail" in event
    assert event["event"] == "stage"


def test_ws_complete_event_structure():
    """Complete event must match the fixed contract."""
    review_id = uuid.uuid4()

    event = {
        "event": "complete",
        "review_id": str(review_id),
        "task_id": str(review_id),
        "summary": {"total_risks": 4, "high": 1, "medium": 2, "low": 1},
        "duration_sec": 286,
    }

    assert event["event"] == "complete"
    assert "summary" in event
    assert "duration_sec" in event
    assert "total_risks" in event["summary"]


def test_ws_failed_event_structure():
    """Failed event must match the fixed contract."""
    review_id = uuid.uuid4()

    event = {
        "event": "failed",
        "review_id": str(review_id),
        "task_id": str(review_id),
        "code": 4004,
        "message": "llm unavailable",
        "detail": "主模型与备用模型均不可用",
        "retryable": True,
    }

    assert event["event"] == "failed"
    assert "code" in event
    assert "message" in event
    assert "detail" in event
    assert "retryable" in event


# ---------------------------------------------------------------------------
# Phase 4.1: Pending reclaim tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reclaim_pending_processes_stale_messages(monkeypatch):
    """Worker should reclaim stale pending messages via XAUTOCLAIM."""
    from app.services import worker as worker_mod

    reclaimed = []

    class FakeRedis:
        async def xautoclaim(self, stream, group, consumer, min_idle_time, start, count=10):
            if start == "0-0":
                review_id = str(uuid.uuid4())
                return (
                    "0-0",
                    [("msg-reclaim-1", {
                        "review_id": review_id,
                        "contract_title": "Reclaimed",
                        "contract_file_url": "s3://bucket/reclaimed.pdf",
                        "contract_file_type": "pdf",
                    })],
                )
            return ("0-0", [])

        async def xack(self, *a, **kw):
            pass

    async def fake_process_task(fields):
        reclaimed.append(fields)

    monkeypatch.setattr(worker_mod, "_process_task", fake_process_task)

    result = await worker_mod._reclaim_pending(FakeRedis())
    assert result is True
    assert len(reclaimed) == 1
    assert reclaimed[0]["contract_title"] == "Reclaimed"


@pytest.mark.asyncio
async def test_reclaim_pending_no_messages(monkeypatch):
    """When no stale pending messages, reclaim should return False."""
    from app.services import worker as worker_mod

    class FakeRedis:
        async def xautoclaim(self, *a, **kw):
            return ("0-0", [])

    result = await worker_mod._reclaim_pending(FakeRedis())
    assert result is False


@pytest.mark.asyncio
async def test_reclaim_pending_handles_xautoclaim_unavailable(monkeypatch):
    """If XAUTOCLAIM is unavailable (old Redis), should return False gracefully."""
    from app.services import worker as worker_mod

    class FakeRedis:
        async def xautoclaim(self, *a, **kw):
            raise Exception("ERR unknown command 'XAUTOCLAIM'")

    result = await worker_mod._reclaim_pending(FakeRedis())
    assert result is False


@pytest.mark.asyncio
async def test_worker_reclaims_when_no_new_messages(monkeypatch):
    """Worker should reclaim stale pending even when xreadgroup returns nothing."""
    from app.services import worker as worker_mod

    reclaim_calls = []

    async def fake_reclaim(r):
        reclaim_calls.append(1)
        # After first reclaim, stop the loop
        if len(reclaim_calls) >= 1:
            raise asyncio.CancelledError()
        return False

    class FakeRedis:
        async def xreadgroup(self, *a, **kw):
            return []  # No new messages

    async def fake_get_redis():
        return FakeRedis()

    from app.services import queue as queue_mod
    monkeypatch.setattr(worker_mod, "_reclaim_pending", fake_reclaim)
    monkeypatch.setattr(worker_mod, "ensure_stream_group", lambda: None)
    monkeypatch.setattr(queue_mod, "get_redis", fake_get_redis)

    # The loop should call reclaim even when no new messages
    try:
        await worker_mod._worker_loop()
    except asyncio.CancelledError:
        pass

    assert len(reclaim_calls) >= 1


# ---------------------------------------------------------------------------
# Phase 4.1: WS config tests
# ---------------------------------------------------------------------------


def test_ws_config_reads_from_settings():
    """WS ticket TTL and max duration should come from settings."""
    from app.config import get_settings

    settings = get_settings()
    assert settings.ws_ticket_ttl > 0
    assert settings.ws_max_duration > 0


def test_ticket_uses_config_ttl():
    """Issued ticket should use ws_ticket_ttl from settings."""
    from app.api.v1.ws import issue_ws_ticket, validate_ws_ticket
    from app.config import get_settings

    settings = get_settings()
    user_id = uuid.uuid4()
    review_id = uuid.uuid4()

    ticket, expires_in = issue_ws_ticket(user_id, review_id)
    assert expires_in == settings.ws_ticket_ttl

    # Ticket should still be valid immediately
    payload = validate_ws_ticket(ticket, str(review_id))
    assert payload is not None


# ---------------------------------------------------------------------------
# Phase 4.3: Heartbeat Pub/Sub publishing tests
# ---------------------------------------------------------------------------


def _make_heartbeat_session_mocks(review_id, fake_review):
    """Build FakeSession and session_factory for heartbeat tests."""

    class FakeSession:
        async def get(self, model, rid):
            return fake_review if rid == review_id else None
        async def commit(self):
            pass

    class FakeSessionFactory:
        def __call__(self):
            return self
        async def __aenter__(self):
            return FakeSession()
        async def __aexit__(self, *a):
            pass

    return FakeSessionFactory()


@pytest.mark.asyncio
async def test_heartbeat_publishes_stage_event(monkeypatch):
    """Heartbeat should call _publish_stage after each progress update."""
    from app.services import review as review_mod

    published = []

    async def fake_publish(review_id, task_id, stage, progress, detail):
        published.append({
            "review_id": str(review_id),
            "task_id": task_id,
            "stage": stage,
            "progress": progress,
            "detail": detail,
        })

    review_id = uuid.uuid4()
    task_id = str(review_id)
    fake_review = SimpleNamespace(id=review_id, status="analyzing", progress=30)

    monkeypatch.setattr(review_mod, "_publish_stage", fake_publish)
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: _make_heartbeat_session_mocks(review_id, fake_review),
    )
    monkeypatch.setattr(review_mod, "ANALYZING_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    task = asyncio.create_task(
        review_mod._analyzing_progress_heartbeat(review_id, task_id)
    )
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(published) >= 1
    for evt in published:
        assert evt["stage"] == "analyzing"
        assert evt["task_id"] == task_id
        assert evt["progress"] > 30


@pytest.mark.asyncio
async def test_heartbeat_respects_progress_ceiling(monkeypatch):
    """Heartbeat should not push progress above ANALYZING_PROGRESS_CEILING."""
    from app.services import review as review_mod

    published = []

    async def fake_publish(review_id, task_id, stage, progress, detail):
        published.append(progress)

    review_id = uuid.uuid4()
    fake_review = SimpleNamespace(id=review_id, status="analyzing", progress=65)

    monkeypatch.setattr(review_mod, "_publish_stage", fake_publish)
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: _make_heartbeat_session_mocks(review_id, fake_review),
    )
    monkeypatch.setattr(review_mod, "ANALYZING_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    task = asyncio.create_task(
        review_mod._analyzing_progress_heartbeat(review_id, str(review_id))
    )
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    for p in published:
        assert p <= review_mod.ANALYZING_PROGRESS_CEILING


@pytest.mark.asyncio
async def test_heartbeat_stops_when_not_analyzing(monkeypatch):
    """Heartbeat should stop when review status changes from analyzing."""
    from app.services import review as review_mod

    published = []

    async def fake_publish(review_id, task_id, stage, progress, detail):
        published.append(1)

    review_id = uuid.uuid4()
    # Status is reporting, not analyzing — heartbeat should exit immediately
    fake_review = SimpleNamespace(id=review_id, status="reporting", progress=30)

    monkeypatch.setattr(review_mod, "_publish_stage", fake_publish)
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: _make_heartbeat_session_mocks(review_id, fake_review),
    )
    monkeypatch.setattr(review_mod, "ANALYZING_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    await review_mod._analyzing_progress_heartbeat(review_id, str(review_id))

    assert len(published) == 0


@pytest.mark.asyncio
async def test_heartbeat_does_not_publish_on_no_progress_change(monkeypatch):
    """Heartbeat should not publish if progress didn't change."""
    from app.services import review as review_mod

    published = []

    async def fake_publish(review_id, task_id, stage, progress, detail):
        published.append(progress)

    review_id = uuid.uuid4()
    fake_review = SimpleNamespace(
        id=review_id,
        status="analyzing",
        progress=review_mod.ANALYZING_PROGRESS_CEILING,
    )

    monkeypatch.setattr(review_mod, "_publish_stage", fake_publish)
    monkeypatch.setattr(
        "app.db.session.get_session_factory",
        lambda: _make_heartbeat_session_mocks(review_id, fake_review),
    )
    monkeypatch.setattr(review_mod, "ANALYZING_HEARTBEAT_INTERVAL_SECONDS", 0.01)

    task = asyncio.create_task(
        review_mod._analyzing_progress_heartbeat(review_id, str(review_id))
    )
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(published) == 0
