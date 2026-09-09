"""The ONLY place a concrete LLM provider is selected."""
from __future__ import annotations

import logging
from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.llm.base import LLMProvider

logger = logging.getLogger("trustlens.llm")


def _build(settings: Settings) -> LLMProvider:
    provider = settings.effective_llm_provider
    if provider == "openai_compatible":
        from app.services.llm.openai_compatible import OpenAICompatibleProvider

        logger.info("LLM provider: openai_compatible model=%s", settings.llm_model)
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    from app.services.llm.stub import StubProvider

    if settings.llm_provider != "stub":
        logger.warning("falling back to stub LLM provider (no API key configured)")
    else:
        logger.info("LLM provider: stub (offline)")
    return StubProvider()


@lru_cache
def get_llm_provider() -> LLMProvider:
    return _build(get_settings())
