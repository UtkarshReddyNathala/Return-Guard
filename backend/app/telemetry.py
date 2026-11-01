"""Request monitoring for the API, using two standard libraries.

- `asgi-correlation-id` reads or creates an `X-Correlation-ID` for every request and
  stores it so `app.logging` can add it to every log line.
- `prometheus-fastapi-instrumentator` measures time, count and size per route and
  serves them at `/metrics`.

Traces of the AI agent calls are sent to Langfuse by the worker, where those calls
happen.
"""
from __future__ import annotations

import uuid

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup(app: FastAPI) -> None:
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Correlation-ID",
        generator=lambda: uuid.uuid4().hex,
    )
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, include_in_schema=False)
