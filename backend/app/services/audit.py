"""Append-only, hash-chained audit log (API side). Each row stores a hash of its own
content plus the previous row's hash, so any later change breaks the chain. Uses
exactly the same hashing rule as `worker/pipeline/audit.py`.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

GENESIS = "0" * 64


def _canonical(ts_iso, actor_type, actor_id, action, entity_type, entity_id, data) -> str:
    return json.dumps(
        {"ts": ts_iso, "actor_type": actor_type, "actor_id": actor_id, "action": action,
         "entity_type": entity_type, "entity_id": entity_id, "data": data},
        sort_keys=True, separators=(",", ":"), default=str,
    )


async def append(
    session: AsyncSession, *, actor_type: str, actor_id: str, action: str,
    entity_type: str, entity_id: str, data: dict,
) -> str:
    """Add one audit row inside the caller's transaction, so the change and its audit
    row are saved together. One database lock (a transaction-level advisory lock) makes
    all audit writes from the API and the worker happen one at a time. Locking only the
    last row is not enough: two writers can both read the same last row and split the
    chain.
    """
    await session.execute(text("SELECT pg_advisory_xact_lock(742042)"))
    last = (
        await session.execute(
            text("SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1")
        )
    ).scalar_one_or_none()
    prev = last or GENESIS
    ts_iso = dt.datetime.now(dt.UTC).isoformat()
    canonical = _canonical(ts_iso, actor_type, actor_id, action, entity_type, entity_id, data)
    row_hash = hashlib.sha256((prev + canonical).encode()).hexdigest()
    await session.execute(
        text(
            "INSERT INTO audit_log "
            "(ts, actor_type, actor_id, action, entity_type, entity_id, data, prev_hash, row_hash) "
            "VALUES (:ts,:at,:ai,:ac,:et,:ei,CAST(:d AS jsonb),:ph,:rh)"
        ),
        {"ts": ts_iso, "at": actor_type, "ai": actor_id, "ac": action, "et": entity_type,
         "ei": entity_id, "d": json.dumps(data, default=str), "ph": prev, "rh": row_hash},
    )
    return row_hash
