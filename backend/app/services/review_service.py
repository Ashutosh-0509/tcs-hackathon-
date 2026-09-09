"""Human review queue. EDITOR/ADMIN only (enforced at the API layer).

A review records a human decision. It never rewrites the machine reliability score;
if the editor disagrees with the label they set `overridden_label`, and the
*effective* label surfaced to consumers becomes the override.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, TrustLensError
from app.models import Answer, Question, Review
from app.models.enums import AuditAction, ReliabilityLabel, ReviewStatus
from app.schemas.common import SourceRef
from app.schemas.review import ReviewDecisionRequest, ReviewDetail, ReviewQueueItem
from app.services import audit

_DECISION_STATUSES = {ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.ESCALATED}


def effective_label(review: Review | None, machine_label: str) -> str:
    if review and review.overridden_label:
        return review.overridden_label
    return machine_label


def _queue_item(review: Review) -> ReviewQueueItem:
    answer = review.answer
    question = answer.question
    rel = answer.reliability
    machine = rel.label if rel else ReliabilityLabel.NEEDS_VERIFICATION
    return ReviewQueueItem(
        review_id=str(review.id),
        answer_id=str(answer.id),
        question_id=str(question.id),
        request_id=question.request_id,
        question=question.text,
        answer=answer.text,
        label=machine,
        effective_label=effective_label(review, machine),
        overridden_label=review.overridden_label,
        final_score=rel.final_score if rel else 0,
        status=review.status,
        created_at=review.created_at,
    )


def list_queue(
    db: Session, *, status: str | None, limit: int, offset: int
) -> list[ReviewQueueItem]:
    stmt = (
        select(Review)
        .options(
            selectinload(Review.answer).selectinload(Answer.question),
            selectinload(Review.answer).selectinload(Answer.reliability),
        )
        .order_by(Review.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status:
        stmt = stmt.where(Review.status == status)
    return [_queue_item(r) for r in db.scalars(stmt)]


def get_detail(db: Session, review_id: uuid.UUID) -> ReviewDetail:
    review = db.scalar(
        select(Review)
        .where(Review.id == review_id)
        .options(
            selectinload(Review.answer)
            .selectinload(Answer.question)
            .selectinload(Question.evidence),
            selectinload(Review.answer).selectinload(Answer.reliability),
            selectinload(Review.answer).selectinload(Answer.claims),
        )
    )
    if not review:
        raise NotFoundError("Review not found")
    answer = review.answer
    question = answer.question
    rel = answer.reliability
    base = _queue_item(review)
    return ReviewDetail(
        **base.model_dump(),
        reasons=list(rel.reasons) if rel else [],
        explanation=answer.explanation,
        claims=[
            {
                "text": c.text,
                "is_critical": c.is_critical,
                "supported": c.supported,
                "semantic_support": round(c.semantic_support, 4),
                "evidence_support": round(c.evidence_support, 4),
                "contradicted": c.contradicted,
                "best_evidence_ordinal": c.best_evidence_ordinal,
                "support_source": c.support_source,
                "rationale": c.rationale,
            }
            for c in answer.claims
        ],
        evidence=[e.snippet for e in question.evidence],
        sources=[
            SourceRef(ordinal=e.ordinal, snippet=e.snippet, title=e.title, url=e.url)
            for e in sorted(question.evidence, key=lambda e: e.ordinal)
        ],
        decision_note=review.decision_note,
        reviewed_by=str(review.reviewed_by) if review.reviewed_by else None,
        decided_at=review.decided_at,
    )


def decide(
    db: Session,
    review_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    reviewer_id: uuid.UUID,
) -> ReviewDetail:
    review = db.scalar(select(Review).where(Review.id == review_id))
    if not review:
        raise NotFoundError("Review not found")
    if ReviewStatus(payload.status) not in _DECISION_STATUSES:
        raise TrustLensError("status must be APPROVED, REJECTED or ESCALATED")
    if review.status != ReviewStatus.PENDING:
        raise TrustLensError(
            f"Review already decided ({review.status})", status_code=409, code="already_decided"
        )

    review.status = payload.status
    review.decision_note = payload.decision_note
    review.overridden_label = (
        payload.override_label.value if payload.override_label else None
    )
    review.reviewed_by = reviewer_id
    review.decided_at = datetime.now(UTC)

    audit.record(
        db,
        action=AuditAction.REVIEW_DECIDED,
        entity_type="review",
        entity_id=review.id,
        actor_id=reviewer_id,
        metadata={
            "status": payload.status,
            "answer_id": str(review.answer_id),
            "overridden_label": review.overridden_label,
        },
    )
    db.commit()
    return get_detail(db, review_id)
