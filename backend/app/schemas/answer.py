from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AnswerSource, QuestionMode, ReliabilityLabel, ReviewStatus
from app.schemas.common import (
    ClaimResult,
    MetricsBlock,
    ReliabilityBlock,
    SecurityBlock,
    SourceRef,
)


class AskRequest(BaseModel):
    """Primary flow — the user asks a question and nothing else. TrustLens gets
    the model's answer, retrieves real sources, and verifies the answer against
    them."""

    question: str = Field(min_length=3, max_length=2000)
    include_explanation: bool = True


class AnswerRequest(BaseModel):
    """Mode A — TrustLens generates the answer from user-supplied sources."""

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
    question: str
    answer: str
    mode: QuestionMode
    evidence: list[str]
    sources: list[SourceRef]
    claims: list[ClaimResult]
    metrics: MetricsBlock
    reliability: ReliabilityBlock
    security: SecurityBlock
    explanation: str | None = None
    review_required: bool


class ReviewSummary(BaseModel):
    review_id: str
    status: ReviewStatus
    overridden_label: ReliabilityLabel | None = None
    decision_note: str | None = None
    decided_at: datetime | None = None


class AnswerSummary(BaseModel):
    answer_id: str
    question_id: str
    request_id: str
    question: str
    answer: str
    mode: QuestionMode
    source: AnswerSource
    model: str | None = None
    label: ReliabilityLabel
    effective_label: ReliabilityLabel
    final_score: int
    review_status: ReviewStatus | None = None
    created_at: datetime


class AnswerDetail(AnswerSummary):
    claims: list[ClaimResult]
    metrics: MetricsBlock
    reliability: ReliabilityBlock
    evidence: list[str]
    sources: list[SourceRef] = []
    explanation: str | None = None
    review: ReviewSummary | None = None
