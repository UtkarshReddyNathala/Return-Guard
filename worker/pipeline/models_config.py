"""Model settings and per-agent model permissions.

Every model call names a **role** (for example "fast" or "reason"), never a real model
name. This file maps each role to a model id, so changing a model is a config change.
Each agent is allowed certain roles, and `assert_grant()` refuses a call for a role
the agent does not have. The permission check is done by **OPA**
(`data.returnguard.authz.allow_model` in `infra/opa/authz.rego`); `AGENT_MODEL_GRANTS`
below is a copy of the same rules, used when OPA cannot be reached (it fails closed).
The per-agent Bifrost virtual keys from `scripts/bifrost_setup.py` hold the same
lists, plus spending and rate limits.

Groq's mid-2026 catalog dropped the llama-3.x models; the replacements are the
gpt-oss models.
"""
from __future__ import annotations

import os

from pipeline import opa

_DEFAULTS = {
    "fast": "groq/openai/gpt-oss-20b",      # intake, data-quality, planner
    "reason": "groq/openai/gpt-oss-120b",   # policy, behaviour, decision
    "deep": "openai/gpt-4o-mini",           # critic, explanation
    "vision": "openai/gpt-4o",              # borderline image checks (image only)
    "embed": "openai/text-embedding-3-small",
}

_FALLBACKS = {
    "fast": ["openai/gpt-4o-mini"],
    "reason": ["openai/gpt-4o-mini"],
    "deep": ["openai/gpt-4o"],
    "vision": ["openai/gpt-4o-mini"],
    "embed": [],
}

# Copy of `model_grants` in infra/opa/authz.rego, used when OPA cannot be reached (fails closed).
AGENT_MODEL_GRANTS: dict[str, set[str]] = {
    "planner": {"fast"},
    "intake": {"fast"},
    "policy": {"reason", "embed"},
    "image": {"vision"},
    "behavior": {"reason"},
    "decision": {"reason", "deep"},
    "critic": {"deep"},
    "explanation": {"deep"},
}


def model(role: str) -> str:
    return os.getenv(f"RG_MODEL_{role.upper()}", _DEFAULTS[role])


def fallbacks(role: str) -> list[str]:
    return _FALLBACKS.get(role, [])


def is_granted(agent: str | None, role: str) -> bool:
    """Ask OPA; if OPA cannot be reached, use the copy of the rules in this file.
    `agent=None` (helper jobs such as the policy re-embed) has no limits.
    """
    if agent is None:
        return True
    return opa.allowed(
        "returnguard/authz/allow_model", {"agent": agent, "role": role},
        offline=role in AGENT_MODEL_GRANTS.get(agent, set()),
    )


def assert_grant(agent: str | None, role: str) -> None:
    """Raise if `agent` is not permitted to use `role`."""
    if agent is None:
        return
    if not is_granted(agent, role):
        raise PermissionError(
            f"agent '{agent}' is not granted the '{role}' model role "
            f"(granted: {sorted(AGENT_MODEL_GRANTS.get(agent, set())) or 'none'})"
        )
