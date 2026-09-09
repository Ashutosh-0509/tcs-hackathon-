"""TrustLens FastAPI application entrypoint."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    TrustLensError,
    trustlens_error_handler,
    unhandled_error_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("trustlens")


def create_app() -> FastAPI:
    app = FastAPI(
        title="TrustLens API",
        version=__version__,
        description="A reliability layer for AI answers. The LLM never decides the label.",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.add_exception_handler(TrustLensError, trustlens_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"service": "TrustLens", "version": __version__, "docs": "/api/docs"}

    logger.info(
        "TrustLens %s started (env=%s, llm=%s)",
        __version__,
        settings.environment,
        settings.effective_llm_provider,
    )
    return app


app = create_app()
