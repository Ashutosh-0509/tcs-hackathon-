"""Read-side queries for answers (history + detail)."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.models import Answer, Question
from app.models.enums import ReliabilityLabel
from app.schemas.answer import AnswerDetail, AnswerSummary, ReviewSummary
from app.schemas.common import ClaimResult, MetricsBlock, ReliabilityBlock
from app.services.review_service import effective_label


def _summary(answer: Answer) -> AnswerSummary:
    q = answer.question
    rel = answer.reliability
    machine = rel.label if rel else ReliabilityLabel.NEEDS_VERIFICATION
    return AnswerSummary(
        answer_id=str(answer.id),
        question_id=str(q.id),
        request_id=q.request_id,
        question=q.text,
        answer=answer.text,
        mode=q.mode,
        source=answer.source,
        model=answer.model,
        label=machine,
        effective_label=effective_label(answer.review, machine),
        final_score=rel.final_score if rel else 0,
        review_status=answer.review.status if answer.review else None,
        created_at=answer.created_at,
    )


def list_answers(
    db: Session, *, actor_id: uuid.UUID | None, mine: bool, limit: int, offset: int
) -> list[AnswerSummary]:
    stmt = (
        select(Answer)
        .join(Question, Answer.question_id == Question.id)
        .options(
            selectinload(Answer.question),
            selectinload(Answer.reliability),
            selectinload(Answer.review),
        )
        .order_by(Answer.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if mine and actor_id is not None:
        stmt = stmt.where(Question.created_by == actor_id)
    return [_summary(a) for a in db.scalars(stmt)]


def get_answer(db: Session, answer_id: uuid.UUID) -> AnswerDetail:
    answer = db.scalar(
        select(Answer)
        .where(Answer.id == answer_id)
        .options(
            selectinload(Answer.question).selectinload(Question.evidence),
            selectinload(Answer.reliability),
            selectinload(Answer.review),
            selectinload(Answer.claims),
        )
    )
    if not answer:
        raise NotFoundError("Answer not found")
    rel = answer.reliability
    base = _summary(answer)
    review = answer.review
    return AnswerDetail(
        **base.model_dump(),
        claims=[
            ClaimResult(
                text=c.text,
                is_critical=c.is_critical,
                supported=c.supported,
                semantic_support=round(c.semantic_support, 4),
                evidence_support=round(c.evidence_support, 4),
                contradicted=c.contradicted,
                best_evidence_ordinal=c.best_evidence_ordinal,
                support_source=c.support_source,
                rationale=c.rationale,
            )
            for c in answer.claims
        ],
        metrics=MetricsBlock(
            semantic_support=rel.semantic_score if rel else 0.0,
            evidence_support=rel.evidence_score if rel else 0.0,
            answer_relevance=rel.relevance_score if rel else 0.0,
            uncertainty=rel.uncertainty_score if rel else 0.0,
            perplexity=round(answer.perplexity, 4) if answer.perplexity is not None else None,
            perplexity_available=answer.perplexity_available,
            evidence_count=len(answer.question.evidence),
        ),
        reliability=ReliabilityBlock(
            final_score=rel.final_score if rel else 0,
            label=rel.label if rel else ReliabilityLabel.NEEDS_VERIFICATION,
            reasons=list(rel.reasons) if rel else [],
            weights={k: round(v, 4) for k, v in (rel.weights if rel else {}).items()},
            thresholds=rel.thresholds if rel else {},
            evidence_score=round(rel.evidence_score, 4) if rel else 0.0,
            semantic_score=round(rel.semantic_score, 4) if rel else 0.0,
            uncertainty_score=round(rel.uncertainty_score, 4) if rel else 0.0,
            relevance_score=round(rel.relevance_score, 4) if rel else 0.0,
        ),
        evidence=[e.snippet for e in answer.question.evidence],
        explanation=answer.explanation,
        review=(
            ReviewSummary(
                review_id=str(review.id),
                status=review.status,
                overridden_label=review.overridden_label,
                decision_note=review.decision_note,
                decided_at=review.decided_at,
            )
            if review
            else None
        ),
    )
