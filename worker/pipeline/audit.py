"""Append-only, hash-chained audit log (worker side).

Each row is turned into compact JSON with sorted keys, from (ts_iso, actor_type,
actor_id, action, entity_type, entity_id, data). Then
`row_hash = sha256(prev_hash + that JSON)`, so every row depends on the one before it.
A database trigger blocks UPDATE and DELETE, and `scripts/verify_audit_chain.py`
recalculates the chain with the same rule.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json

from pipeline import db

GENESIS = "0" * 64


def _canonical(ts_iso, actor_type, actor_id, action, entity_type, entity_id, data) -> str:
    return json.dumps(
        {"ts": ts_iso, "actor_type": actor_type, "actor_id": actor_id, "action": action,
         "entity_type": entity_type, "entity_id": entity_id, "data": data},
        sort_keys=True, separators=(",", ":"), default=str,
    )


async def append(*, actor_type: str, actor_id: str, action: str,
                 entity_type: str, entity_id: str, data: dict) -> str:
    async with db.pool.connection() as conn:
        async with conn.transaction():
            # make all audit writes (API and worker) happen one at a time, using one
            # transaction-level advisory lock. Locking only the last row is not enough:
            # two writers can both read the same last row and split the chain.
            await conn.execute("SELECT pg_advisory_xact_lock(742042)")
            cur = await conn.execute(
                "SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1"
            )
            last = await cur.fetchone()
            prev = last[0] if last else GENESIS
            ts_iso = dt.datetime.now(dt.UTC).isoformat()
            canonical = _canonical(ts_iso, actor_type, actor_id, action,
                                   entity_type, entity_id, data)
            row_hash = hashlib.sha256((prev + canonical).encode()).hexdigest()
            await conn.execute(
                "INSERT INTO audit_log "
                "(ts, actor_type, actor_id, action, entity_type, entity_id, data, prev_hash, row_hash) "
                "VALUES (%(ts)s,%(at)s,%(ai)s,%(ac)s,%(et)s,%(ei)s,%(d)s,%(ph)s,%(rh)s)",
                {"ts": ts_iso, "at": actor_type, "ai": actor_id, "ac": action,
                 "et": entity_type, "ei": entity_id, "d": json.dumps(data, default=str),
                 "ph": prev, "rh": row_hash},
            )
    return row_hash
