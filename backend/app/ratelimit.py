"""Rate limiting with slowapi, keyed by the caller's IP address.

- A global limit (`SlowAPIMiddleware` in `app.main`) applies to every request before
  it reaches a route, so a flood of unauthenticated requests is slowed down early.
- Stricter limits on single routes: add `@limiter.limit("12/minute")` to the endpoint
  and give it a `request: Request` parameter.

The counts are kept in memory, which is enough for a single API container.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1200/minute"],
)
