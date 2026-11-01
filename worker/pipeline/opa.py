"""A small client for OPA (Open Policy Agent), which runs as its own container.

OPA makes these decisions:
  * the Governance Gate route      `data.returnguard.governance.decision`
  * per-agent tool permissions     `data.returnguard.authz.allow_tool`
  * per-agent model permissions    `data.returnguard.authz.allow_model`

The policies are in `infra/opa/*.rego`. Callers **fail closed**: if OPA cannot be
reached, `query()` returns None and the caller escalates or refuses
(`mcp_client` and `models_config` keep a copy of the permission rules for this case).
"""
from __future__ import annotations

import os

import httpx
import structlog

log = structlog.get_logger()

_URL = os.getenv("RG_OPA_URL", "http://opa:8181").rstrip("/")


def query(path: str, input_doc: dict):
    """POST to /v1/data/<path> with {"input": ...}; return the `result` value.

    Returns None on any transport / HTTP error — callers must fail closed.
    """
    try:
        r = httpx.post(f"{_URL}/v1/data/{path}",
                       json={"input": input_doc}, timeout=5)
        r.raise_for_status()
        return r.json().get("result")
    except Exception as e:  # noqa: BLE001 — policy must degrade, not crash
        log.warning("opa.unreachable", path=path, error=f"{type(e).__name__}: {e}")
        return None


def allowed(path: str, input_doc: dict, *, offline: bool) -> bool:
    """Boolean OPA query. On OPA failure, return the `offline` fallback verdict."""
    res = query(path, input_doc)
    return offline if res is None else bool(res)
