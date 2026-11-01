"""Puts a submitted return on the arq job queue right away, so review starts quickly.
This is only a shortcut: the outbox row is what guarantees the case is processed,
and the worker's `dispatch_outbox` job picks up anything this step missed.
"""
from __future__ import annotations

from arq import create_pool
from arq.connections import RedisSettings

from app.logging import log
from app.settings import get_settings

_pool = None


async def enqueue_review(return_id: str) -> None:
    global _pool
    try:
        if _pool is None:
            _pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
        await _pool.enqueue_job("review_return", return_id)
        log.info("queue.enqueued", return_id=return_id)
    except Exception as e:  # noqa: BLE001 — outbox + cron will catch it
        log.warning("queue.enqueue_failed", return_id=return_id, error=str(e))
