"""Domain error types and a structured exception handler."""
from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id

logger = logging.getLogger("trustlens.errors")


class TrustLensError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, detail: str, *, status_code: int | None = None, code: str | None = None):
        super().__init__(detail)
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class NotFoundError(TrustLensError):
    status_code = 404
    code = "not_found"


class AuthError(TrustLensError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(TrustLensError):
    status_code = 403
    code = "forbidden"


class LLMUnavailableError(TrustLensError):
    status_code = 503
    code = "llm_unavailable"


async def trustlens_error_handler(request: Request, exc: TrustLensError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "detail": exc.detail, "request_id": get_request_id()},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": "An unexpected error occurred.",
            "request_id": get_request_id(),
        },
    )
