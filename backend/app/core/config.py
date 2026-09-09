"""Application configuration (pydantic-settings).

Single source of runtime config. Nothing else in the codebase reads os.environ
directly. Secrets are never logged.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = "postgresql+psycopg://trustlens:trustlens@postgres:5432/trustlens"

    # --- Auth ---
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # --- LLM provider ---
    llm_provider: str = "stub"  # "stub" | "openai_compatible"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    # --- Embeddings ---
    embedding_model: str = "all-MiniLM-L6-v2"

    # --- Reliability policy ---
    certain_threshold: int = 80
    uncertain_threshold: int = 50
    weight_evidence: float = 0.50
    weight_semantic: float = 0.25
    weight_uncertainty: float = 0.15
    weight_relevance: float = 0.10
    evidence_support_threshold: float = 0.55

    # --- Security ---
    pii_use_presidio: bool = False
    cors_allow_origins: str = "http://localhost:3000"
    rate_limit_per_minute: int = 60

    @field_validator("cors_allow_origins")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def effective_llm_provider(self) -> str:
        """openai_compatible with no key falls back to the offline stub."""
        if self.llm_provider == "openai_compatible" and not self.llm_api_key:
            return "stub"
        return self.llm_provider

    @property
    def reliability_weights(self) -> dict[str, float]:
        return {
            "evidence": self.weight_evidence,
            "semantic": self.weight_semantic,
            "uncertainty": self.weight_uncertainty,
            "relevance": self.weight_relevance,
        }

    @property
    def reliability_thresholds(self) -> dict[str, int]:
        return {
            "certain": self.certain_threshold,
            "uncertain": self.uncertain_threshold,
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
