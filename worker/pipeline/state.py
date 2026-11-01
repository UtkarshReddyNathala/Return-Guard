"""The pipeline state: one dictionary passed through every step. Each step returns
only the fields it changes. Nothing here is final; only the Governance Gate decides.
"""
from __future__ import annotations

from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # identity / control
    return_id: str
    graph_run_id: str
    automation_level: str
    kill_switch: bool
    category: str
    context: dict[str, Any]          # db.get_review_context output
    seq: int                        # event sequence counter (list so nodes can bump it)

    # per-agent outputs
    data_quality: dict[str, Any]    # {ok, reason}
    plan: list[str]                 # agent names Planner selected
    intake: dict[str, Any]          # {complete, missing, reason}
    policy: dict[str, Any]          # {eligible, reason, policy_version, citations}
    image: dict[str, Any]           # {clip_similarity, ai_generated_score, verdict, reason, checked}
    behavior: dict[str, Any]        # {risk_score, model_version, ring_accounts, pattern, reason}
    decision: dict[str, Any]        # {decision, confidence, risk, reason, signals}
    critic: dict[str, Any]          # {veto, concern, agree}
    explanation: str

    # final (GovernanceGate only)
    final: dict[str, Any]           # {route, proposed, reason, auto}
    errors: list[str]
