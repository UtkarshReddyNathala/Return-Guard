"""Creates the FastAPI app. It connects all the routers and adds rate limiting,
correlation ids, Prometheus metrics, security headers and a clean 404 for malformed
ids.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import DataError

from app import telemetry
from app.logging import configure, log
from app.ratelimit import limiter
from app.routers import health

configure()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("backend.start")
    yield
    log.info("backend.stop")


app = FastAPI(title="ReturnGuard API", version="0.1.0", lifespan=lifespan)

# rate limiting (slowapi): one global limit for every request, plus stricter limits
# on some routes with @limiter.limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError) -> JSONResponse:
    # every {id} route passes the id straight to Postgres as a UUID. A malformed id (a
    # typo, a bad link, a bot) must return 404, not a 500 error that shows SQL details.
    # Real ids never reach this handler.
    log.warning("request.malformed_id", path=request.url.path)
    return JSONResponse(status_code=404, content={"detail": "not found"})

# correlation ids and Prometheus metrics (served at /metrics)
telemetry.setup(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


app.include_router(health.router)

from app.routers import analytics, appeals, dashboard, orders, returns, shop, ws

app.include_router(shop.router)
app.include_router(orders.router)
app.include_router(returns.router)
app.include_router(ws.router)
app.include_router(dashboard.router)
app.include_router(analytics.router)
app.include_router(appeals.router)
