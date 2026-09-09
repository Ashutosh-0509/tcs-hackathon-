"""Orchestrates the three entry flows:

  ask(question)            — retrieve sources, get the model's answer, verify it
  generate_and_evaluate    — user supplies sources; model answers from them
  evaluate_external        — user supplies answer + evidence; just score it

Common pipeline (`_run`):
  redact PII -> extract claims -> per-claim entailment -> reliability policy
  -> persist (ONE transaction) -> open a review row if label != CERTAIN
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.models import Answer, Claim, Evidence, Question, ReliabilityScore, Review
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
    SourceRef,
)
from app.services import audit
from app.services.evaluation import EvaluationEngine
from app.services.llm.base import ExtractedClaim, LLMProvider
from app.services.pii import PIIService
from app.services.retrieval import RetrievalService, get_retrieval_service

logger = logging.getLogger("trustlens.answer")


@dataclass
class Source:
    snippet: str
    title: str | None = None
    url: str | None = None


class AnswerService:
    def __init__(
        self,
        db: Session,
        llm: LLMProvider,
        engine: EvaluationEngine,
        pii: PIIService,
        retrieval: RetrievalService | None = None,
    ) -> None:
        self.db = db
        self.llm = llm
        self.engine = engine
        self.pii = pii
        self.retrieval = retrieval or get_retrieval_service()

    # ---- public entry points ----
    def ask(
        self, *, question: str, include_explanation: bool, actor_id: uuid.UUID | None
    ) -> AnswerResponse:
        red_q = self.pii.redact(question)

        # 1. the model answers from its own knowledge
        answer_result = self.llm.answer_question(red_q.redacted)

        # 2. retrieve independent, citable sources (for the question and the answer)
        docs = self.retrieval.search_for_answer(red_q.redacted, answer_result.text, k=5)
        red_sources: list[Source] = []
        source_spans = []
        for d in docs:
            r = self.pii.redact(d.snippet)
            source_spans.extend(r.spans)
            red_sources.append(Source(snippet=r.redacted, title=d.title, url=d.url))

        security = self._security_block(red_q.spans + source_spans, ["question", "sources"])
        return self._run(
            mode=QuestionMode.ASK,
            answer_source=AnswerSource.TRUSTLENS_LLM,
            question=red_q.redacted,
            sources=red_sources,
            answer_text=answer_result.text,
            model=answer_result.model,
            avg_logprob=answer_result.avg_logprob,
            logprob_available=answer_result.logprob_available,
            security=security,
            include_explanation=include_explanation,
            actor_id=actor_id,
            audit_action=AuditAction.ANSWER_GENERATED,
        )

    def generate_and_evaluate(
        self,
        *,
        question: str,
        source_snippets: list[str],
        include_explanation: bool,
        actor_id: uuid.UUID | None,
    ) -> AnswerResponse:
        red_q = self.pii.redact(question)
        red_snips, snip_spans = self.pii.redact_many(source_snippets)
        sources = [Source(snippet=s) for s in red_snips]
        security = self._security_block(
            red_q.spans + snip_spans, ["question", "source_snippets"]
        )
        result = self.llm.generate_answer(red_q.redacted, [s.snippet for s in sources])
        return self._run(
            mode=QuestionMode.GENERATE,
            answer_source=AnswerSource.TRUSTLENS_LLM,
            question=red_q.redacted,
            sources=sources,
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
            question=red_question,
            sources=[Source(snippet=s) for s in red_evidence],
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
        question: str,
        sources: list[Source],
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
        snippets = [s.snippet for s in sources]

        try:
            extraction = self.llm.extract_claims(question, answer_text)
            claims: list[ExtractedClaim] = extraction.claims
        except Exception:  # noqa: BLE001
            logger.exception("claim extraction failed; continuing with zero claims")
            claims = []

        judgements = None
        if claims and snippets:
            try:
                judgements = self.llm.judge_claims([c.text for c in claims], snippets)
            except Exception:  # noqa: BLE001
                logger.exception("claim entailment check failed; falling back to heuristic")

        outcome = self.engine.evaluate(
            question=question,
            answer=answer_text,
            claims=claims,
            evidence=snippets,
            avg_logprob=avg_logprob,
            logprob_available=logprob_available,
            judgements=judgements,
        )
        reliability = outcome.reliability
        assert reliability is not None

        # For retrieved sources, drop any that no claim actually used (keep a couple
        # for context) and reindex, so the UI shows a tidy, relevant source list.
        if mode == QuestionMode.ASK and sources:
            used = {
                a.best_evidence_ordinal
                for a in outcome.claims
                if a.best_evidence_ordinal is not None
            }
            keep = sorted(set(range(min(2, len(sources)))) | used)
            remap = {old: new for new, old in enumerate(keep)}
            sources = [sources[i] for i in keep]
            snippets = [s.snippet for s in sources]
            for a in outcome.claims:
                a.best_evidence_ordinal = remap.get(a.best_evidence_ordinal)

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

        # ---- persist: one transaction ----
        question_row = Question(
            request_id=get_request_id(), text=question, mode=mode.value, created_by=actor_id
        )
        self.db.add(question_row)
        self.db.flush()

        for i, src in enumerate(sources):
            self.db.add(
                Evidence(
                    question_id=question_row.id,
                    snippet=src.snippet,
                    ordinal=i,
                    title=src.title,
                    url=src.url,
                )
            )

        answer_row = Answer(
            question_id=question_row.id,
            text=answer_text,
            source=answer_source.value,
            model=model,
            perplexity=outcome.perplexity,
            perplexity_available=outcome.perplexity_available,
            explanation=explanation,
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
                    support_source=a.support_source,
                    rationale=a.rationale or None,
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
            self.db.add(Review(answer_id=answer_row.id, status=ReviewStatus.PENDING.value))

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
            question=question,
            answer=answer_text,
            mode=mode,
            evidence=snippets,
            sources=[
                SourceRef(ordinal=i, snippet=s.snippet, title=s.title, url=s.url)
                for i, s in enumerate(sources)
            ],
            claims=[
                ClaimResult(
                    text=a.text,
                    is_critical=a.is_critical,
                    supported=a.supported,
                    semantic_support=round(a.semantic_support, 4),
                    evidence_support=round(a.evidence_support, 4),
                    contradicted=a.contradicted,
                    best_evidence_ordinal=a.best_evidence_ordinal,
                    support_source=a.support_source,
                    rationale=a.rationale or None,
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
