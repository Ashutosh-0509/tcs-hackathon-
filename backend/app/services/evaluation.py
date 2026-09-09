"""EvaluationEngine — turns (answer, claims, evidence) into deterministic signals,
then applies the ReliabilityPolicy.

Signals (ARCHITECTURE.md §3.3):
  - evidence_support : fraction of claims whose best evidence cosine >= threshold,
                       weighted so critical claims count double
  - semantic_support : mean best-match cosine across claims
  - answer_relevance : cosine(question, answer)
  - uncertainty      : 1 - normalized(perplexity); neutral 0.5 when unavailable
  - flags            : evidence_available, contradictory_evidence,
                       critical_unsupported_claim, evaluation_failed
"""
from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.policies.reliability import (
    ReliabilityPolicy,
    ReliabilityResult,
    ReliabilitySignals,
)
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm.base import ExtractedClaim

logger = logging.getLogger("trustlens.evaluation")

_NEGATIONS = {
    "not", "no", "never", "none", "cannot", "can't", "didn't", "doesn't", "isn't",
    "wasn't", "aren't", "weren't", "without", "nor", "neither", "false", "incorrect",
}
_WORD = re.compile(r"[a-z0-9']+")

# Perplexity normalization band: ppl<=PPL_LOW -> confident(1), ppl>=PPL_HIGH -> unsure(0)
_PPL_LOW = 1.5
_PPL_HIGH = 20.0


@dataclass
class ClaimAssessment:
    text: str
    is_critical: bool
    semantic_support: float
    evidence_support: float
    supported: bool
    contradicted: bool
    best_evidence_ordinal: int | None


@dataclass
class EvaluationOutcome:
    claims: list[ClaimAssessment] = field(default_factory=list)
    semantic_support: float = 0.0
    evidence_support: float = 0.0
    answer_relevance: float = 0.0
    uncertainty: float = 0.5
    perplexity: float | None = None
    perplexity_available: bool = False
    evidence_count: int = 0
    reliability: ReliabilityResult | None = None
    evaluation_failed: bool = False


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _has_negation_mismatch(claim: str, evidence: str) -> bool:
    ct, et = _tokens(claim), _tokens(evidence)
    overlap = ct & et
    if len(overlap) < 3:
        return False
    claim_neg = bool(ct & _NEGATIONS)
    ev_neg = bool(et & _NEGATIONS)
    return claim_neg != ev_neg


def _normalized_uncertainty(perplexity: float) -> float:
    if perplexity <= _PPL_LOW:
        return 1.0
    if perplexity >= _PPL_HIGH:
        return 0.0
    return 1.0 - (math.log(perplexity) - math.log(_PPL_LOW)) / (
        math.log(_PPL_HIGH) - math.log(_PPL_LOW)
    )


class EvaluationEngine:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        policy: ReliabilityPolicy | None = None,
    ) -> None:
        settings = get_settings()
        self.embeddings = embedding_service or get_embedding_service()
        self._base_weights = settings.reliability_weights
        self._thresholds = settings.reliability_thresholds
        self.policy = policy or ReliabilityPolicy(
            weights=self._base_weights, thresholds=self._thresholds
        )
        self._policy_overridden = policy is not None
        self.support_threshold = settings.evidence_support_threshold

    def _policy_for(self, *, perplexity_available: bool) -> ReliabilityPolicy:
        """When perplexity is unavailable we do not fabricate an uncertainty value
        (TECH_STACK.md §22): the uncertainty weight is redistributed across the
        signals we actually measured."""
        if self._policy_overridden or perplexity_available:
            return self.policy
        w = dict(self._base_weights)
        freed = w.pop("uncertainty", 0.0)
        remaining = sum(w.values()) or 1.0
        redistributed = {k: v + freed * (v / remaining) for k, v in w.items()}
        redistributed["uncertainty"] = 0.0
        return ReliabilityPolicy(weights=redistributed, thresholds=self._thresholds)

    def evaluate(
        self,
        *,
        question: str,
        answer: str,
        claims: list[ExtractedClaim],
        evidence: list[str],
        avg_logprob: float | None = None,
        logprob_available: bool = False,
    ) -> EvaluationOutcome:
        try:
            return self._evaluate(
                question, answer, claims, evidence, avg_logprob, logprob_available
            )
        except Exception:  # noqa: BLE001 - any failure must fail safe, never crash the request
            logger.exception("evaluation failed; forcing NEEDS_VERIFICATION")
            signals = ReliabilitySignals(
                evidence_support=0.0,
                semantic_support=0.0,
                uncertainty_score=0.0,
                answer_relevance=0.0,
                evidence_available=bool(evidence),
                evaluation_failed=True,
            )
            return EvaluationOutcome(
                reliability=self.policy.evaluate(signals),
                evaluation_failed=True,
                evidence_count=len(evidence),
            )

    def _evaluate(
        self,
        question: str,
        answer: str,
        claims: list[ExtractedClaim],
        evidence: list[str],
        avg_logprob: float | None,
        logprob_available: bool,
    ) -> EvaluationOutcome:
        evidence = [e for e in evidence if e and e.strip()]
        evidence_available = len(evidence) > 0

        # ---- answer relevance ----
        if question.strip() and answer.strip():
            rel = float(self.embeddings.similarity_matrix([question], [answer])[0, 0])
            answer_relevance = max(0.0, rel)
        else:
            answer_relevance = 0.0

        # ---- perplexity / uncertainty ----
        perplexity: float | None = None
        perplexity_available = False
        uncertainty = 0.5  # neutral prior when not available
        if logprob_available and avg_logprob is not None:
            perplexity = math.exp(-avg_logprob)
            perplexity_available = True
            uncertainty = _normalized_uncertainty(perplexity)

        # ---- per-claim support ----
        assessments: list[ClaimAssessment] = []
        if claims and evidence_available:
            sim = self.embeddings.similarity_matrix([c.text for c in claims], evidence)
            for i, claim in enumerate(claims):
                row = sim[i]
                best_j = int(row.argmax())
                best_sim = float(row[best_j])
                supported = best_sim >= self.support_threshold
                contradicted = _has_negation_mismatch(claim.text, evidence[best_j])
                assessments.append(
                    ClaimAssessment(
                        text=claim.text,
                        is_critical=claim.is_critical,
                        semantic_support=max(0.0, best_sim),
                        evidence_support=1.0 if supported else max(0.0, best_sim),
                        supported=supported and not contradicted,
                        contradicted=contradicted,
                        best_evidence_ordinal=best_j,
                    )
                )
        else:
            for claim in claims:
                assessments.append(
                    ClaimAssessment(
                        text=claim.text,
                        is_critical=claim.is_critical,
                        semantic_support=0.0,
                        evidence_support=0.0,
                        supported=False,
                        contradicted=False,
                        best_evidence_ordinal=None,
                    )
                )

        # ---- aggregate signals ----
        if assessments:
            weights = [2.0 if a.is_critical else 1.0 for a in assessments]
            wsum = sum(weights)
            evidence_support = sum(
                w * (1.0 if a.supported else 0.0) for a, w in zip(assessments, weights, strict=False)
            ) / wsum
            semantic_support = sum(a.semantic_support for a in assessments) / len(assessments)
        else:
            evidence_support = 0.0
            semantic_support = 0.0

        contradictory = any(a.contradicted for a in assessments)
        critical_unsupported = any(
            a.is_critical and not a.supported for a in assessments
        ) or (not assessments and evidence_available is False)

        signals = ReliabilitySignals(
            evidence_support=evidence_support,
            semantic_support=semantic_support,
            uncertainty_score=uncertainty,
            answer_relevance=answer_relevance,
            evidence_available=evidence_available,
            contradictory_evidence=contradictory,
            critical_unsupported_claim=critical_unsupported,
            evaluation_failed=False,
        )
        reliability = self._policy_for(perplexity_available=perplexity_available).evaluate(signals)

        return EvaluationOutcome(
            claims=assessments,
            semantic_support=semantic_support,
            evidence_support=evidence_support,
            answer_relevance=answer_relevance,
            uncertainty=uncertainty,
            perplexity=perplexity,
            perplexity_available=perplexity_available,
            evidence_count=len(evidence),
            reliability=reliability,
            evaluation_failed=False,
        )
