from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import (
    ClaimResult,
    MetricsBlock,
    ReliabilityBlock,
    SecurityBlock,
)


class AnswerRequest(BaseModel):
    """Mode A — TrustLens generates the answer, then evaluates it."""

    question: str = Field(min_length=3, max_length=4000)
    source_snippets: list[str] = Field(default_factory=list, max_length=50)
    include_perplexity: bool = True
    include_explanation: bool = True


class EvaluateRequest(BaseModel):
    """Mode B — evaluate an answer produced by another system."""

    question: str = Field(min_length=3, max_length=4000)
    answer: str = Field(min_length=1, max_length=8000)
    evidence: list[str] = Field(default_factory=list, max_length=50)
    model: str | None = Field(default=None, max_length=128)
    include_explanation: bool = True


class AnswerResponse(BaseModel):
    request_id: str
    answer_id: str
    question_id: str
    answer: str
    claims: list[ClaimResult]
    metrics: MetricsBlock
    reliability: ReliabilityBlock
    security: SecurityBlock
    explanation: str | None = None
    review_required: bool
