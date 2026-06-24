"""Redis-driven task queue and event pub/sub for review execution.

Phase 4: Decouples review trigger from execution via Redis Streams,
and publishes real-time progress events via Redis Pub/Sub.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger("contractguard.queue")

_REDIS_CLIENT: aioredis.Redis | None = None
REDIS_STREAM_KEY = "review:tasks"
REDIS_STREAM_GROUP = "review-workers"
REDIS_CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:8]}"

# ---------------------------------------------------------------------------
# Redis connection management
# ---------------------------------------------------------------------------


async def get_redis() -> aioredis.Redis:
    """Return the shared async Redis client, creating it lazily."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT is None:
        settings = get_settings()
        _REDIS_CLIENT = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _REDIS_CLIENT


async def close_redis() -> None:
    """Close the shared Redis client on shutdown."""
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        await _REDIS_CLIENT.close()
        _REDIS_CLIENT = None


async def ensure_stream_group() -> None:
    """Create the consumer group if it doesn't exist yet."""
    try:
        r = await get_redis()
        await r.xgroup_create(
            REDIS_STREAM_KEY, REDIS_STREAM_GROUP, id="0", mkstream=True,
        )
        logger.info("queue.stream_group_created", extra={"stream": REDIS_STREAM_KEY})
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" in str(exc):
            pass  # group already exists
        else:
            raise


# ---------------------------------------------------------------------------
# Task publishing (contracts.py calls this)
# ---------------------------------------------------------------------------


async def enqueue_review_task(
    review_id: uuid.UUID,
    contract_title: str | None,
    contract_file_url: str,
    contract_file_type: str,
    use_draft_content: bool = False,
    contract_id: uuid.UUID | None = None,
) -> str:
    """Push a review task onto the Redis Stream. Returns the stream message ID.

    Phase v12: Added use_draft_content and contract_id for draft review support.
    """
    r = await get_redis()
    payload = {
        "review_id": str(review_id),
        "contract_title": contract_title or "",
        "contract_file_url": contract_file_url,
        "contract_file_type": contract_file_type,
        "use_draft_content": "true" if use_draft_content else "false",
    }
    if contract_id:
        payload["contract_id"] = str(contract_id)

    msg_id = await r.xadd(
        REDIS_STREAM_KEY,
        payload,
        maxlen=10000,
    )
    logger.info(
        "queue.task_enqueued",
        extra={
            "review_id": str(review_id),
            "msg_id": msg_id,
            "use_draft": use_draft_content,
        },
    )
    return msg_id


# ---------------------------------------------------------------------------
# Progress event publishing (review.py calls these)
# ---------------------------------------------------------------------------


async def publish_review_event(review_id: uuid.UUID, event: dict[str, Any]) -> None:
    """Publish a progress event to the review's Pub/Sub channel."""
    r = await get_redis()
    channel = f"review:{review_id}:events"
    await r.publish(channel, json.dumps(event, ensure_ascii=False))
    logger.debug(
        "queue.event_published",
        extra={"review_id": str(review_id), "event": event.get("event")},
    )


async def publish_stage_event(
    review_id: uuid.UUID,
    task_id: str,
    stage: str,
    progress: int,
    detail: str,
    clause_current: int | None = None,
    clause_total: int | None = None,
    eta_sec: int | None = None,
) -> None:
    """Publish a stage progress event matching the API contract."""
    evt: dict[str, Any] = {
        "event": "stage",
        "review_id": str(review_id),
        "task_id": task_id,
        "stage": stage,
        "progress": progress,
        "detail": detail,
    }
    if clause_current is not None:
        evt["clause_current"] = clause_current
    if clause_total is not None:
        evt["clause_total"] = clause_total
    if eta_sec is not None:
        evt["eta_sec"] = eta_sec
    await publish_review_event(review_id, evt)


async def publish_complete_event(
    review_id: uuid.UUID,
    task_id: str,
    summary: dict[str, Any],
    duration_sec: int,
) -> None:
    """Publish a completion event matching the API contract."""
    await publish_review_event(review_id, {
        "event": "complete",
        "review_id": str(review_id),
        "task_id": task_id,
        "summary": summary,
        "duration_sec": duration_sec,
    })


async def publish_failed_event(
    review_id: uuid.UUID,
    task_id: str,
    code: int,
    message: str,
    detail: str,
    retryable: bool = True,
) -> None:
    """Publish a failure event matching the API contract."""
    await publish_review_event(review_id, {
        "event": "failed",
        "review_id": str(review_id),
        "task_id": task_id,
        "code": code,
        "message": message,
        "detail": detail,
        "retryable": retryable,
    })
