"""Orchestrates Mode A (generate + evaluate) and Mode B (evaluate external answer).

Flow (ARCHITECTURE.md §5):
  redact PII -> [generate answer] -> extract claims -> evaluate -> policy
  -> persist (ONE transaction) -> open review row if label != CERTAIN
"""
from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.models import (
    Answer,
    Claim,
    Evidence,
    Question,
    ReliabilityScore,
    Review,
)
from app.models.enums import (
    AnswerSource,
    AuditAction,
    QuestionMode,
    ReliabilityLabel,
    ReviewStatus,
)
from app.schemas.answer import AnswerResponse
from app.schemas.common import (
    ClaimResult,
    MetricsBlock,
    PIIFinding,
    ReliabilityBlock,
    SecurityBlock,
)
from app.services import audit
from app.services.evaluation import EvaluationEngine
from app.services.llm.base import ExtractedClaim, LLMProvider
from app.services.pii import PIIService

logger = logging.getLogger("trustlens.answer")


class AnswerService:
    def __init__(
        self,
        db: Session,
        llm: LLMProvider,
        engine: EvaluationEngine,
        pii: PIIService,
    ) -> None:
        self.db = db
        self.llm = llm
        self.engine = engine
        self.pii = pii

    # ---- public entry points ----
    def generate_and_evaluate(
        self,
        *,
        question: str,
        source_snippets: list[str],
        include_explanation: bool,
        actor_id: uuid.UUID | None,
    ) -> AnswerResponse:
        red_question, red_sources, security = self._redact(question, source_snippets)
        result = self.llm.generate_answer(red_question, red_sources)
        return self._run(
            mode=QuestionMode.GENERATE,
            answer_source=AnswerSource.TRUSTLENS_LLM,
            red_question=red_question,
            red_sources=red_sources,
            answer_text=result.text,
            model=result.model,
            avg_logprob=result.avg_logprob,
            logprob_available=result.logprob_available,
            security=security,
            include_explanation=include_explanation,
            actor_id=actor_id,
            audit_action=AuditAction.ANSWER_GENERATED,
        )

    def evaluate_external(
        self,
        *,
        question: str,
        answer: str,
        evidence: list[str],
        model: str | None,
        include_explanation: bool,
        actor_id: uuid.UUID | None,
    ) -> AnswerResponse:
        (red_question, red_answer), _ = self.pii.redact_many([question, answer])
        red_evidence, ev_spans = self.pii.redact_many(evidence)
        q_spans = self.pii.scan(question) + self.pii.scan(answer)
        security = self._security_block(q_spans + ev_spans, ["question", "answer", "evidence"])
        return self._run(
            mode=QuestionMode.EVALUATE,
            answer_source=AnswerSource.EXTERNAL,
            red_question=red_question,
            red_sources=red_evidence,
            answer_text=red_answer,
            model=model,
            avg_logprob=None,
            logprob_available=False,
            security=security,
            include_explanation=include_explanation,
            actor_id=actor_id,
            audit_action=AuditAction.ANSWER_EVALUATED,
        )

    # ---- internals ----
    def _redact(
        self, question: str, snippets: list[str]
    ) -> tuple[str, list[str], SecurityBlock]:
        red_q = self.pii.redact(question)
        red_snips, snip_spans = self.pii.redact_many(snippets)
        security = self._security_block(
            red_q.spans + snip_spans, ["question", "source_snippets"]
        )
        return red_q.redacted, red_snips, security

    @staticmethod
    def _security_block(spans, fields: list[str]) -> SecurityBlock:
        counts: dict[str, int] = {}
        for s in spans:
            counts[s.type] = counts.get(s.type, 0) + 1
        findings = [PIIFinding(type=k, count=v) for k, v in sorted(counts.items())]
        return SecurityBlock(
            pii_detected=bool(spans),
            pii_findings=findings,
            redaction_applied=bool(spans),
            redacted_fields=fields if spans else [],
        )

    def _run(
        self,
        *,
        mode: QuestionMode,
        answer_source: AnswerSource,
        red_question: str,
        red_sources: list[str],
        answer_text: str,
        model: str | None,
        avg_logprob: float | None,
        logprob_available: bool,
        security: SecurityBlock,
        include_explanation: bool,
        actor_id: uuid.UUID | None,
        audit_action: AuditAction,
    ) -> AnswerResponse:
        started = time.perf_counter()

        # claim extraction
        try:
            extraction = self.llm.extract_claims(red_question, answer_text)
            claims: list[ExtractedClaim] = extraction.claims
        except Exception:  # noqa: BLE001
            logger.exception("claim extraction failed; continuing with zero claims")
            claims = []

        outcome = self.engine.evaluate(
            question=red_question,
            answer=answer_text,
            claims=claims,
            evidence=red_sources,
            avg_logprob=avg_logprob,
            logprob_available=logprob_available,
        )
        reliability = outcome.reliability
        assert reliability is not None

        explanation = None
        if include_explanation:
            claim_summary = "; ".join(
                f"{c.text[:80]} -> {'supported' if c.supported else 'unsupported'}"
                f"{' (contradicted)' if c.contradicted else ''}"
                for c in outcome.claims
            )
            try:
                explanation = self.llm.generate_explanation(
                    reliability.label.value,
                    reliability.final_score,
                    reliability.reasons,
                    claim_summary,
                )
            except Exception:  # noqa: BLE001
                logger.exception("explanation generation failed")
                explanation = None

        # ---- persist: one transaction ----
        question_row = Question(
            request_id=get_request_id(),
            text=red_question,
            mode=mode.value,
            created_by=actor_id,
        )
        self.db.add(question_row)
        self.db.flush()

        for i, snip in enumerate(red_sources):
            self.db.add(Evidence(question_id=question_row.id, snippet=snip, ordinal=i))

        answer_row = Answer(
            question_id=question_row.id,
            text=answer_text,
            source=answer_source.value,
            model=model,
            perplexity=outcome.perplexity,
            perplexity_available=outcome.perplexity_available,
        )
        self.db.add(answer_row)
        self.db.flush()

        for a in outcome.claims:
            self.db.add(
                Claim(
                    answer_id=answer_row.id,
                    text=a.text,
                    is_critical=a.is_critical,
                    supported=a.supported,
                    semantic_support=a.semantic_support,
                    evidence_support=a.evidence_support,
                    contradicted=a.contradicted,
                    best_evidence_ordinal=a.best_evidence_ordinal,
                )
            )

        self.db.add(
            ReliabilityScore(
                answer_id=answer_row.id,
                evidence_score=reliability.components["evidence_score"],
                semantic_score=reliability.components["semantic_score"],
                uncertainty_score=reliability.components["uncertainty_score"],
                relevance_score=reliability.components["relevance_score"],
                final_score=reliability.final_score,
                label=reliability.label.value,
                reasons=list(reliability.reasons),
                weights=reliability.weights,
                thresholds=reliability.thresholds,
            )
        )

        review_required = reliability.label != ReliabilityLabel.CERTAIN
        if review_required:
            self.db.add(
                Review(answer_id=answer_row.id, status=ReviewStatus.PENDING.value)
            )

        latency_ms = round((time.perf_counter() - started) * 1000)
        audit.record(
            self.db,
            action=audit_action,
            entity_type="answer",
            entity_id=answer_row.id,
            actor_id=actor_id,
            metadata={
                "label": reliability.label.value,
                "score": reliability.final_score,
                "model": model,
                "latency_ms": latency_ms,
                "pii_findings": sum(f.count for f in security.pii_findings),
                "evidence_count": outcome.evidence_count,
                "evaluation_failed": outcome.evaluation_failed,
                "review_required": review_required,
            },
        )

        self.db.commit()
        self.db.refresh(answer_row)

        return AnswerResponse(
            request_id=get_request_id(),
            answer_id=str(answer_row.id),
            question_id=str(question_row.id),
            answer=answer_text,
            claims=[
                ClaimResult(
                    text=a.text,
                    is_critical=a.is_critical,
                    supported=a.supported,
                    semantic_support=round(a.semantic_support, 4),
                    evidence_support=round(a.evidence_support, 4),
                    contradicted=a.contradicted,
                    best_evidence_ordinal=a.best_evidence_ordinal,
                )
                for a in outcome.claims
            ],
            metrics=MetricsBlock(
                semantic_support=round(outcome.semantic_support, 4),
                evidence_support=round(outcome.evidence_support, 4),
                answer_relevance=round(outcome.answer_relevance, 4),
                uncertainty=round(outcome.uncertainty, 4),
                perplexity=round(outcome.perplexity, 4) if outcome.perplexity is not None else None,
                perplexity_available=outcome.perplexity_available,
                evidence_count=outcome.evidence_count,
            ),
            reliability=ReliabilityBlock(
                final_score=reliability.final_score,
                label=reliability.label,
                reasons=reliability.reasons,
                weights={k: round(v, 4) for k, v in reliability.weights.items()},
                thresholds=reliability.thresholds,
                evidence_score=round(reliability.components["evidence_score"], 4),
                semantic_score=round(reliability.components["semantic_score"], 4),
                uncertainty_score=round(reliability.components["uncertainty_score"], 4),
                relevance_score=round(reliability.components["relevance_score"], 4),
            ),
            security=security,
            explanation=explanation,
            review_required=review_required,
        )
