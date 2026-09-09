"""LLM provider abstraction.

Business logic depends ONLY on this interface, never on a concrete provider or a
model name (TECH_STACK.md §13, §83-84).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_logprobs: bool = False
    supports_embeddings: bool = False
    supports_structured_output: bool = False
    supports_streaming: bool = False


@dataclass
class LLMResult:
    text: str
    model: str
    # Mean token log-probability, if the provider exposes it. None => not available.
    avg_logprob: float | None = None
    logprob_available: bool = False


@dataclass
class ExtractedClaim:
    text: str
    is_critical: bool = False


@dataclass
class ClaimExtraction:
    claims: list[ExtractedClaim] = field(default_factory=list)
    model: str = ""


class LLMProvider(ABC):
    """One configured provider per deployment."""

    name: str = "abstract"

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities: ...

    @abstractmethod
    def generate_answer(self, question: str, sources: list[str]) -> LLMResult: ...

    @abstractmethod
    def extract_claims(self, question: str, answer: str) -> ClaimExtraction: ...

    @abstractmethod
    def generate_explanation(
        self, label: str, score: int, reasons: list[str], claim_summary: str
    ) -> str: ...

    def health(self) -> str:
        return "available"
