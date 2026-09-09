"""Deterministic reliability policy.

PURE. No I/O, no DB, no LLM, no network. This module is the audit-critical core:
given a set of numeric signals and boolean flags it returns a score and a label.

Rules (ARCHITECTURE.md §3.4, TECH_STACK.md §30-33):

    final_score = 100 * ( evidence*w_e + semantic*w_s + uncertainty*w_u + relevance*w_r )

    score >= CERTAIN_THRESHOLD            -> CERTAIN
    UNCERTAIN_THRESHOLD <= score < ...    -> UNCERTAIN
    score < UNCERTAIN_THRESHOLD           -> NEEDS_VERIFICATION

Safety overrides (win over the number):
    evaluation_failed            -> NEEDS_VERIFICATION
    no_evidence_available        -> NEEDS_VERIFICATION
    critical_unsupported_claim   -> NEEDS_VERIFICATION
    contradictory_evidence       -> at most UNCERTAIN

Fail-safe: never emit CERTAIN when evidence is absent or the evaluator errored.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.enums import ReliabilityLabel

DEFAULT_WEIGHTS: dict[str, float] = {
    "evidence": 0.50,
    "semantic": 0.25,
    "uncertainty": 0.15,
    "relevance": 0.10,
}
DEFAULT_THRESHOLDS: dict[str, int] = {"certain": 80, "uncertain": 50}


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


@dataclass(frozen=True)
class ReliabilitySignals:
    evidence_support: float  # [0,1] fraction / strength of claims backed by evidence
    semantic_support: float  # [0,1] mean cosine(claim, best evidence)
    uncertainty_score: float  # [0,1] higher = more confident (1 - normalized ppl)
    answer_relevance: float  # [0,1] cosine(question, answer)

    # flags
    evidence_available: bool = True
    contradictory_evidence: bool = False
    critical_unsupported_claim: bool = False
    evaluation_failed: bool = False

    def normalized(self) -> ReliabilitySignals:
        return ReliabilitySignals(
            evidence_support=_clamp01(self.evidence_support),
            semantic_support=_clamp01(self.semantic_support),
            uncertainty_score=_clamp01(self.uncertainty_score),
            answer_relevance=_clamp01(self.answer_relevance),
            evidence_available=self.evidence_available,
            contradictory_evidence=self.contradictory_evidence,
            critical_unsupported_claim=self.critical_unsupported_claim,
            evaluation_failed=self.evaluation_failed,
        )


@dataclass(frozen=True)
class ReliabilityResult:
    final_score: int
    label: ReliabilityLabel
    reasons: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, int] = field(default_factory=dict)
    components: dict[str, float] = field(default_factory=dict)


class ReliabilityPolicy:
    def __init__(
        self,
        weights: dict[str, float] | None = None,
        thresholds: dict[str, int] | None = None,
    ) -> None:
        w = {**DEFAULT_WEIGHTS, **(weights or {})}
        total = sum(w.values())
        # Normalize so weights always sum to 1.0 regardless of config drift.
        self.weights = {k: (v / total if total else 0.0) for k, v in w.items()}
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    def score(self, signals: ReliabilitySignals) -> float:
        s = signals.normalized()
        raw = (
            s.evidence_support * self.weights["evidence"]
            + s.semantic_support * self.weights["semantic"]
            + s.uncertainty_score * self.weights["uncertainty"]
            + s.answer_relevance * self.weights["relevance"]
        )
        return round(raw * 100)

    def label(self, score: float, signals: ReliabilitySignals) -> tuple[ReliabilityLabel, list[str]]:
        reasons: list[str] = []
        certain_t = self.thresholds["certain"]
        uncertain_t = self.thresholds["uncertain"]

        # ---- safety overrides (highest priority) ----
        if signals.evaluation_failed:
            return ReliabilityLabel.NEEDS_VERIFICATION, ["evaluation_failed: forced fail-safe"]
        if not signals.evidence_available:
            return ReliabilityLabel.NEEDS_VERIFICATION, ["no_evidence_available: cannot verify"]
        if signals.critical_unsupported_claim:
            return ReliabilityLabel.NEEDS_VERIFICATION, [
                "critical_unsupported_claim: a critical claim is not backed by evidence"
            ]

        # ---- numeric band ----
        if score >= certain_t:
            label = ReliabilityLabel.CERTAIN
            reasons.append(f"score {score} >= certain_threshold {certain_t}")
        elif score >= uncertain_t:
            label = ReliabilityLabel.UNCERTAIN
            reasons.append(f"uncertain_threshold {uncertain_t} <= score {score} < {certain_t}")
        else:
            label = ReliabilityLabel.NEEDS_VERIFICATION
            reasons.append(f"score {score} < uncertain_threshold {uncertain_t}")

        # ---- contradiction cap: never better than UNCERTAIN ----
        if signals.contradictory_evidence and label == ReliabilityLabel.CERTAIN:
            label = ReliabilityLabel.UNCERTAIN
            reasons.append("contradictory_evidence: capped at UNCERTAIN")

        return label, reasons

    def evaluate(self, signals: ReliabilitySignals) -> ReliabilityResult:
        s = signals.normalized()
        score = self.score(s)
        label, reasons = self.label(score, s)
        return ReliabilityResult(
            final_score=int(score),
            label=label,
            reasons=reasons,
            weights=self.weights,
            thresholds=self.thresholds,
            components={
                "evidence_score": s.evidence_support,
                "semantic_score": s.semantic_support,
                "uncertainty_score": s.uncertainty_score,
                "relevance_score": s.answer_relevance,
            },
        )
