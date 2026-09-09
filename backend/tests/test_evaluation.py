"""Evaluation engine behaviour on the mandatory scenarios (TECH_STACK.md §47)."""
from __future__ import annotations

from app.models.enums import ReliabilityLabel
from app.services.embeddings import get_embedding_service
from app.services.evaluation import EvaluationEngine, _token_coverage
from app.services.llm.base import (
    ClaimJudgement,
    ClaimJudgementResult,
    Entailment,
    ExtractedClaim,
)

engine = EvaluationEngine()

# The hashed-embedding fallback (no sentence-transformers / no model download) gives
# only approximate semantic scores, so the exact CERTAIN/UNCERTAIN boundary for the
# positive path is not asserted there. Safety-critical labels are always asserted.
_REAL_EMBEDDINGS = get_embedding_service().backend == "sentence-transformers"


def test_no_evidence_yields_needs_verification():
    outcome = engine.evaluate(
        question="What is the capital of Atlantis?",
        answer="The capital of Atlantis is Poseidonis.",
        claims=[ExtractedClaim(text="The capital of Atlantis is Poseidonis.", is_critical=True)],
        evidence=[],
    )
    assert outcome.reliability.label == ReliabilityLabel.NEEDS_VERIFICATION


def test_well_supported_answer_scores_high():
    outcome = engine.evaluate(
        question="Who invented Python?",
        answer="Python was created by Guido van Rossum.",
        claims=[ExtractedClaim(text="Python was created by Guido van Rossum.", is_critical=True)],
        evidence=["Python was created by Guido van Rossum and first released in 1991."],
    )
    assert outcome.reliability.label != ReliabilityLabel.NEEDS_VERIFICATION
    assert outcome.reliability.final_score >= 70
    if _REAL_EMBEDDINGS:
        assert outcome.reliability.label == ReliabilityLabel.CERTAIN


def test_contradiction_is_capped_at_uncertain_or_lower():
    outcome = engine.evaluate(
        question="Is the Earth flat?",
        answer="The Earth is flat.",
        claims=[ExtractedClaim(text="The Earth is flat.", is_critical=True)],
        evidence=["The Earth is not flat; it is an oblate spheroid."],
    )
    assert outcome.reliability.label != ReliabilityLabel.CERTAIN


def test_perplexity_not_fabricated_when_unavailable():
    outcome = engine.evaluate(
        question="Who invented Python?",
        answer="Guido van Rossum.",
        claims=[ExtractedClaim(text="Guido van Rossum invented Python.")],
        evidence=["Python was created by Guido van Rossum."],
        avg_logprob=None,
        logprob_available=False,
    )
    assert outcome.perplexity is None
    assert outcome.perplexity_available is False


def _all_supported(n: int) -> ClaimJudgementResult:
    return ClaimJudgementResult(
        judgements=[ClaimJudgement(verdict=Entailment.SUPPORTED, evidence_ordinal=0) for _ in range(n)],
        model="test",
        available=True,
    )


def test_fully_entailed_answer_scores_certain_even_with_hashed_embeddings():
    """The bug report: every claim confirmed by the cited source, yet the score
    stuck at ~70. With an authoritative LLM verdict the fuzzy cosine must not tax
    the score — a fully-supported answer clears CERTAIN."""
    claims = [
        ExtractedClaim(text="Google was founded in 1998.", is_critical=True),
        ExtractedClaim(text="Larry Page co-founded Google."),
        ExtractedClaim(text="Sergey Brin co-founded Google."),
    ]
    outcome = engine.evaluate(
        question="who is the founder of google?",
        answer="Google was founded in 1998 by Larry Page and Sergey Brin.",
        claims=claims,
        evidence=["Google was founded in 1998 by Larry Page and Sergey Brin."],
        judgements=_all_supported(len(claims)),
        logprob_available=False,
    )
    assert outcome.reliability.label == ReliabilityLabel.CERTAIN
    assert outcome.reliability.final_score >= 90


def test_one_unsupported_noncritical_claim_still_drops_below_certain():
    claims = [
        ExtractedClaim(text="Google was founded by Larry Page and Sergey Brin.", is_critical=True),
        ExtractedClaim(text="They were PhD students at Stanford."),
    ]
    judgements = ClaimJudgementResult(
        judgements=[
            ClaimJudgement(verdict=Entailment.SUPPORTED, evidence_ordinal=0),
            ClaimJudgement(verdict=Entailment.NOT_STATED),
        ],
        model="test",
        available=True,
    )
    outcome = engine.evaluate(
        question="who founded google?",
        answer="...",
        claims=claims,
        evidence=["Google was founded by Larry Page and Sergey Brin."],
        judgements=judgements,
        logprob_available=False,
    )
    assert outcome.reliability.label != ReliabilityLabel.CERTAIN


def test_token_coverage_heuristic_supports_a_covered_claim():
    assert _token_coverage("Guido van Rossum created Python", "Python was created by Guido van Rossum in 1991") >= 0.7
    outcome = engine.evaluate(
        question="Who created Python?",
        answer="Guido van Rossum created Python.",
        claims=[ExtractedClaim(text="Guido van Rossum created Python.", is_critical=True)],
        evidence=["The Python programming language was created by Guido van Rossum."],
    )
    assert outcome.reliability.label != ReliabilityLabel.NEEDS_VERIFICATION


def test_evaluation_never_crashes_the_caller(monkeypatch):
    bad = EvaluationEngine()

    def boom(*a, **k):
        raise RuntimeError("embedding backend exploded")

    monkeypatch.setattr(bad.embeddings, "similarity_matrix", boom)
    outcome = bad.evaluate(
        question="q", answer="a", claims=[ExtractedClaim(text="a")], evidence=["e"]
    )
    assert outcome.evaluation_failed is True
    assert outcome.reliability.label == ReliabilityLabel.NEEDS_VERIFICATION
