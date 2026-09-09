"""Request-id assignment, latency logging, and a simple in-process rate limiter."""
from __future__ import annotations

import logging
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.request_context import get_request_id, new_request_id, set_request_id

logger = logging.getLogger("trustlens.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or new_request_id()
        set_request_id(rid)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "%s %s failed after %.0fms", request.method, request.url.path, latency_ms
            )
            raise
        latency_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        logger.info(
            "%s %s -> %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket-ish fixed-window limiter keyed by client IP. MVP-grade."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = {}
        self._limit = get_settings().rate_limit_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(("/api/docs", "/api/redoc", "/openapi.json")):
            return await call_next(request)
        key = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits.setdefault(key, deque())
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self._limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limited",
                    "detail": "Too many requests.",
                    "request_id": get_request_id(),
                },
            )
        window.append(now)
        return await call_next(request)
