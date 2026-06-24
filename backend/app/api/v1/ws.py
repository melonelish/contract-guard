"""WebSocket ticket validation and real-time review progress endpoint.

Phase 4: Implements the ticket-in-query authentication scheme from 安全设计.md §7,
and Redis Pub/Sub-based real-time progress push.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.services.queue import get_redis

logger = logging.getLogger("contractguard.ws")

router = APIRouter()

# ---------------------------------------------------------------------------
# Ticket constants (static ones only; TTL/duration read from settings)
# ---------------------------------------------------------------------------

TICKET_USED_PREFIX = "ws:ticket:used:"
TICKET_MAX_PER_USER = 3

# ---------------------------------------------------------------------------
# Ticket HMAC helpers
# ---------------------------------------------------------------------------


def _sign_ticket(payload_str: str, secret: str) -> str:
    """HMAC-SHA256 signature for ticket payload."""
    return hmac.new(
        secret.encode(), payload_str.encode(), hashlib.sha256,
    ).hexdigest()


def issue_ws_ticket(
    user_id: uuid.UUID,
    review_id: uuid.UUID,
    task_id: str | None = None,
) -> tuple[str, int]:
    """Create a one-time WebSocket ticket.

    Returns (ticket_string, expires_in_seconds).
    Ticket format: base64(payload).signature
    """
    settings = get_settings()
    expires_at = int(time.time()) + settings.ws_ticket_ttl
    tid = uuid.uuid4().hex[:16]
    payload_str = f"{tid}:{user_id}:{review_id}:{task_id or ''}:{expires_at}"
    sig = _sign_ticket(payload_str, settings.jwt_secret)
    ticket = f"ws_tkt_{tid}:{user_id}:{review_id}:{task_id or ''}:{expires_at}:{sig}"
    return ticket, settings.ws_ticket_ttl


def validate_ws_ticket(
    ticket: str,
    expected_review_id: str,
) -> dict[str, str] | None:
    """Validate a WebSocket ticket synchronously.

    Returns payload dict with user_id, review_id, task_id on success, None on failure.
    Does NOT check one-time-use (that requires Redis, done async in the WS handler).
    """
    settings = get_settings()

    if not ticket.startswith("ws_tkt_"):
        return None

    body = ticket[len("ws_tkt_"):]
    parts = body.split(":")
    if len(parts) != 6:
        return None

    tid, user_id, review_id, task_id, expires_at_str, sig = parts

    # Verify signature
    payload_str = f"{tid}:{user_id}:{review_id}:{task_id}:{expires_at_str}"
    expected_sig = _sign_ticket(payload_str, settings.jwt_secret)
    if not hmac.compare_digest(sig, expected_sig):
        return None

    # Check expiry
    try:
        expires_at = int(expires_at_str)
    except ValueError:
        return None
    if int(time.time()) > expires_at:
        return None

    # Check review_id matches
    if review_id != expected_review_id:
        return None

    return {
        "tid": tid,
        "user_id": user_id,
        "review_id": review_id,
        "task_id": task_id,
    }


# ---------------------------------------------------------------------------
# WebSocket endpoint: real-time review progress
# ---------------------------------------------------------------------------


@router.websocket("/review/{review_id}")
async def review_progress_ws(
    websocket: WebSocket,
    review_id: uuid.UUID,
    ticket: str = Query(...),
) -> None:
    """WebSocket endpoint for real-time review progress.

    Authenticates via one-time ticket, then subscribes to Redis Pub/Sub
    for the review's event channel.
    """
    # Step 1: Validate ticket synchronously
    payload = validate_ws_ticket(ticket, str(review_id))
    if not payload:
        await websocket.close(code=4001, reason="ticket invalid or expired")
        return

    tid = payload["tid"]
    user_id = payload["user_id"]

    # Step 2: Check one-time use via Redis SET NX
    settings = get_settings()
    r = await get_redis()
    used_key = f"{TICKET_USED_PREFIX}{tid}"
    was_set = await r.set(used_key, "1", ex=settings.ws_ticket_ttl + 5, nx=True)
    if not was_set:
        await websocket.close(code=4001, reason="ticket already used")
        return

    # Step 3: Accept connection
    await websocket.accept()
    logger.info(
        "ws.connected",
        extra={"review_id": str(review_id), "user_id": user_id},
    )

    # Step 4: Check if review is already completed/failed — send final event immediately
    from app.db.models import Review
    from app.db.session import get_session_factory

    async with get_session_factory()() as session:
        review = await session.get(Review, review_id)
        if review:
            if review.status == "completed":
                summary = {}
                if review.report_json and review.report_json.get("summary"):
                    summary = review.report_json["summary"]
                await websocket.send_json({
                    "event": "complete",
                    "review_id": str(review_id),
                    "task_id": str(review_id),
                    "summary": summary,
                    "duration_sec": 0,
                })
                await websocket.close(code=1000, reason="review already completed")
                return
            elif review.status == "failed":
                await websocket.send_json({
                    "event": "failed",
                    "review_id": str(review_id),
                    "task_id": str(review_id),
                    "code": 4003,
                    "message": "review failed",
                    "detail": review.error_detail or "unknown error",
                    "retryable": False,
                })
                await websocket.close(code=1000, reason="review already failed")
                return

    # Step 5: Subscribe to Redis Pub/Sub channel
    channel = f"review:{review_id}:events"
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    try:
        # Absolute connection start time for max duration enforcement
        connection_start = asyncio.get_event_loop().time()
        ws_max_duration = settings.ws_max_duration

        async def _heartbeat_loop() -> None:
            """Send periodic pings to keep connection alive."""
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"event": "ping"})
                except Exception:
                    return

        heartbeat_task = asyncio.create_task(_heartbeat_loop())

        try:
            while True:
                # Phase 4.1: Check max duration from connection start (absolute)
                elapsed = asyncio.get_event_loop().time() - connection_start
                if elapsed > ws_max_duration:
                    await websocket.close(code=4002, reason="connection timeout")
                    break

                # Read from Pub/Sub with timeout
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(
                            ignore_subscribe_messages=True,
                            timeout=1.0,
                        ),
                        timeout=5.0,
                    )
                except TimeoutError:
                    # No message, check if websocket has incoming data (close frame)
                    try:
                        # Non-blocking check for client disconnect
                        data = await asyncio.wait_for(
                            websocket.receive_text(), timeout=0.1,
                        )
                        # Client sent a text message — ignore or handle ping
                        if data == "ping":
                            await websocket.send_json({"event": "pong"})
                    except TimeoutError:
                        continue
                    except WebSocketDisconnect:
                        break
                    continue

                if message is None:
                    continue

                if message["type"] != "message":
                    continue

                # Forward event to WebSocket client
                try:
                    event_data = json.loads(message["data"])
                    await websocket.send_json(event_data)

                    # If this is a terminal event, close the connection
                    if event_data.get("event") in ("complete", "failed"):
                        await websocket.close(code=1000, reason="review finished")
                        break
                except WebSocketDisconnect:
                    break
                except Exception as exc:
                    logger.error(
                        "ws.send_failed",
                        extra={"review_id": str(review_id), "error": str(exc)},
                    )
                    break
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    except WebSocketDisconnect:
        logger.info(
            "ws.disconnected",
            extra={"review_id": str(review_id), "user_id": user_id},
        )
    except Exception as exc:
        logger.error(
            "ws.error",
            extra={"review_id": str(review_id), "error": str(exc)},
        )
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
