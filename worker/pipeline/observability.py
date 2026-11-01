"""Langfuse tracing. Each agent's model call is recorded in Langfuse as a generation,
and its trace id is saved on the `agent_runs` row. If Langfuse fails, the error is
logged but the case continues, so a real decision is never lost because of tracing.
"""
from __future__ import annotations

import structlog

from pipeline.settings import get_settings

log = structlog.get_logger()
_lf = None


def lf():
    global _lf
    if _lf is None:
        from langfuse import Langfuse

        s = get_settings()
        _lf = Langfuse(
            public_key=s.langfuse_public_key,
            secret_key=s.langfuse_secret_key,
            host=s.langfuse_host,
        )
    return _lf


def record_generation(
    *, agent: str, model: str, prompt: str, output: str,
    return_id: str, graph_run_id: str,
    tokens_in: int, tokens_out: int, cost: float,
    langfuse_prompt=None,
) -> str | None:
    try:
        kw = {"prompt": langfuse_prompt} if langfuse_prompt is not None else {}
        gen = lf().start_generation(
            name=agent,
            model=model,
            input=prompt,
            metadata={"return_id": return_id, "graph_run_id": graph_run_id},
            **kw,
        )
        gen.update(
            output=output,
            usage_details={"input": tokens_in, "output": tokens_out},
            cost_details={"total": cost},
        )
        gen.update_trace(session_id=graph_run_id, tags=[f"return:{return_id}"])
        gen.end()
        return gen.trace_id
    except Exception as e:  # noqa: BLE001
        log.warning("langfuse.record_failed", agent=agent, error=f"{type(e).__name__}: {e}")
        return None


def flush() -> None:
    try:
        if _lf is not None:
            _lf.flush()
    except Exception as e:  # noqa: BLE001
        log.warning("langfuse.flush_failed", error=str(e))
