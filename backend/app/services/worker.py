"""Background worker that consumes review tasks from Redis Stream.

Phase 4: Decouples task execution from HTTP request lifecycle.
The worker runs as an asyncio task started on app startup.
Phase 4.1: Adds pending message reclaim via XAUTOCLAIM on startup.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.services.queue import (
    REDIS_CONSUMER_NAME,
    REDIS_STREAM_GROUP,
    REDIS_STREAM_KEY,
    ensure_stream_group,
    get_redis,
    publish_failed_event,
    publish_stage_event,
)

logger = logging.getLogger("contractguard.worker")

_worker_task: asyncio.Task[None] | None = None

# Pending messages older than this are considered stale and reclaimable
PENDING_MIN_IDLE_MS = 30_000  # 30 seconds

# ---------------------------------------------------------------------------
# Worker main loop
# ---------------------------------------------------------------------------


async def start_worker() -> None:
    """Start the background review worker. Called on app startup."""
    global _worker_task
    if _worker_task is not None and not _worker_task.done():
        return
    _worker_task = asyncio.create_task(_worker_loop())
    logger.info("worker.started", extra={"consumer": REDIS_CONSUMER_NAME})


async def stop_worker() -> None:
    """Stop the background worker. Called on app shutdown."""
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
        logger.info("worker.stopped")


async def _reclaim_pending(r) -> bool:
    """Attempt to reclaim stale pending messages from this consumer group.

    Uses XAUTOCLAIM (Redis 6.2+) to take ownership of messages that have
    been idle for PENDING_MIN_IDLE_MS. Returns True if any were reclaimed.
    """
    try:
        # XAUTOCLAIM returns (next_start_id, claimed_entries)
        # Use "0-0" to scan from the beginning
        start = "0-0"
        reclaimed_any = False
        while True:
            result = await r.xautoclaim(
                REDIS_STREAM_KEY,
                REDIS_STREAM_GROUP,
                REDIS_CONSUMER_NAME,
                min_idle_time=PENDING_MIN_IDLE_MS,
                start=start,
                count=10,
            )
            # Result: (next_start, entries, deleted)
            # entries is list of (msg_id, fields)
            if not result or len(result) < 2:
                break
            next_start, entries = result[0], result[1]
            if not entries:
                break
            for msg_id, fields in entries:
                logger.info(
                    "worker.reclaiming_pending",
                    extra={"msg_id": msg_id, "review_id": fields.get("review_id")},
                )
                try:
                    await _process_task(fields)
                    await r.xack(REDIS_STREAM_KEY, REDIS_STREAM_GROUP, msg_id)
                    logger.info(
                        "worker.reclaimed_acked",
                        extra={"msg_id": msg_id},
                    )
                    reclaimed_any = True
                except Exception as exc:
                    logger.error(
                        "worker.reclaim_failed",
                        extra={"msg_id": msg_id, "error": str(exc)},
                    )
                    # Ack to prevent infinite loop — review already marked failed
                    await r.xack(REDIS_STREAM_KEY, REDIS_STREAM_GROUP, msg_id)
            # Move to next batch if next_start is not "0-0"
            if next_start == start or not next_start:
                break
            start = next_start
        return reclaimed_any
    except Exception as exc:
        logger.warning(
            "worker.xautoclaim_unavailable",
            extra={"error": str(exc)},
        )
        return False


async def _worker_loop() -> None:
    """Main loop: reclaim stale pending messages, then read new ones."""
    try:
        await ensure_stream_group()
    except Exception as exc:
        logger.error("worker.stream_group_init_failed", extra={"error": str(exc)})

    # Phase 4.1: On startup, first reclaim any stale pending messages
    try:
        r = await get_redis()
        reclaimed = await _reclaim_pending(r)
        if reclaimed:
            logger.info("worker.startup_reclaim_done")
    except Exception as exc:
        logger.warning("worker.startup_reclaim_failed", extra={"error": str(exc)})

    while True:
        try:
            r = await get_redis()
            # Read new messages (">" means only un-delivered messages)
            messages = await r.xreadgroup(
                REDIS_STREAM_GROUP,
                REDIS_CONSUMER_NAME,
                streams={REDIS_STREAM_KEY: ">"},
                count=1,
                block=5000,  # 5 second block
            )

            if not messages:
                # Phase 4.2: Even with no new messages, try reclaiming
                # stale pending from crashed consumers
                try:
                    await _reclaim_pending(r)
                except Exception:
                    pass
                continue

            for _stream_name, entries in messages:
                for msg_id, fields in entries:
                    try:
                        await _process_task(fields)
                        # Acknowledge successful processing
                        await r.xack(REDIS_STREAM_KEY, REDIS_STREAM_GROUP, msg_id)
                        logger.info(
                            "worker.task_acked",
                            extra={"msg_id": msg_id, "review_id": fields.get("review_id")},
                        )
                    except Exception as exc:
                        logger.error(
                            "worker.task_failed",
                            extra={
                                "msg_id": msg_id,
                                "review_id": fields.get("review_id"),
                                "error": str(exc),
                            },
                        )
                        # Acknowledge even on failure to prevent re-delivery loops
                        # The review is already marked as failed in DB
                        await r.xack(REDIS_STREAM_KEY, REDIS_STREAM_GROUP, msg_id)

            # Also reclaim after processing new messages
            try:
                await _reclaim_pending(r)
            except Exception:
                pass

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("worker.loop_error", extra={"error": str(exc)})
            await asyncio.sleep(5)  # Back off on errors


async def _process_task(fields: dict[str, str]) -> None:
    """Process a single review task from the queue."""
    review_id_str = fields.get("review_id")
    contract_title = fields.get("contract_title") or None
    contract_file_url = fields.get("contract_file_url")
    contract_file_type = fields.get("contract_file_type")
    contract_id_str = fields.get("contract_id")
    use_draft_str = fields.get("use_draft_content", "false")

    if not review_id_str or not contract_file_url:
        logger.error("worker.invalid_task", extra={"fields": fields})
        return

    review_id = uuid.UUID(review_id_str)
    contract_id = uuid.UUID(contract_id_str) if contract_id_str else None
    use_draft_content = use_draft_str.lower() in ("true", "1", "yes")
    task_id = review_id_str  # MVP: task_id == review_id

    logger.info(
        "worker.task_started",
        extra={
            "review_id": review_id_str,
            "use_draft_content": use_draft_content,
        },
    )

    # Publish initial queued → parsing event
    await publish_stage_event(
        review_id, task_id, "parsing", 5, "开始文档解析",
    )

    try:
        from app.services.review import run_real_review

        await run_real_review(
            review_id=review_id,
            contract_title=contract_title,
            contract_file_url=contract_file_url,
            contract_file_type=contract_file_type,
            contract_id=contract_id,
            use_draft_content=use_draft_content,
        )
    except Exception as exc:
        logger.error(
            "worker.review_execution_failed",
            extra={"review_id": review_id_str, "error": str(exc)},
        )
        # Try to publish failure event
        try:
            await publish_failed_event(
                review_id, task_id,
                code=4003,
                message="review execution failed",
                detail=str(exc)[:500],
                retryable=False,
            )
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def is_worker_running() -> bool:
    """Check if the worker task is alive."""
    return _worker_task is not None and not _worker_task.done()
