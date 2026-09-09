from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ReliabilityLabel, ReviewStatus


class ReviewQueueItem(BaseModel):
    review_id: str
    answer_id: str
    question_id: str
    request_id: str
    question: str
    answer: str
    label: ReliabilityLabel  # machine label
    effective_label: ReliabilityLabel  # machine label, or human override if set
    overridden_label: ReliabilityLabel | None = None
    final_score: int
    status: ReviewStatus
    created_at: datetime


class ReviewDetail(ReviewQueueItem):
    reasons: list[str]
    claims: list[dict]
    evidence: list[str]
    explanation: str | None = None
    decision_note: str | None = None
    reviewed_by: str | None = None
    decided_at: datetime | None = None


class ReviewDecisionRequest(BaseModel):
    status: ReviewStatus = Field(
        description="APPROVED | REJECTED | ESCALATED (PENDING is not a decision)"
    )
    decision_note: str | None = Field(default=None, max_length=2000)
    override_label: ReliabilityLabel | None = Field(
        default=None,
        description="Optional human override of the machine reliability label.",
    )
