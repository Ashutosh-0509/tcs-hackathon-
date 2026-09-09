"""Unit tests for the deterministic reliability policy (TECH_STACK.md §47)."""
from __future__ import annotations

from app.models.enums import ReliabilityLabel
from app.policies.reliability import ReliabilityPolicy, ReliabilitySignals


def _signals(**kw) -> ReliabilitySignals:
    base = dict(
        evidence_support=1.0,
        semantic_support=1.0,
        uncertainty_score=1.0,
        answer_relevance=1.0,
    )
    base.update(kw)
    return ReliabilitySignals(**base)


def test_score_formula_full_support_is_100():
    policy = ReliabilityPolicy()
    assert policy.score(_signals()) == 100


def test_score_formula_weighted_components():
    policy = ReliabilityPolicy()
    s = _signals(
        evidence_support=1.0, semantic_support=0.0, uncertainty_score=0.0, answer_relevance=0.0
    )
    assert policy.score(s) == 50  # evidence weight 0.50


def test_weights_are_normalized_when_misconfigured():
    policy = ReliabilityPolicy(weights={"evidence": 5, "semantic": 0, "uncertainty": 0, "relevance": 0})
    assert policy.score(_signals()) == 100
    assert abs(sum(policy.weights.values()) - 1.0) < 1e-9


def test_threshold_bands():
    policy = ReliabilityPolicy()
    assert policy.label(85, _signals())[0] == ReliabilityLabel.CERTAIN
    assert policy.label(65, _signals())[0] == ReliabilityLabel.UNCERTAIN
    assert policy.label(30, _signals())[0] == ReliabilityLabel.NEEDS_VERIFICATION


def test_thresholds_are_configurable():
    policy = ReliabilityPolicy(thresholds={"certain": 90, "uncertain": 40})
    assert policy.label(85, _signals())[0] == ReliabilityLabel.UNCERTAIN
    assert policy.label(35, _signals())[0] == ReliabilityLabel.NEEDS_VERIFICATION


def test_safety_override_no_evidence_forces_needs_verification():
    policy = ReliabilityPolicy()
    label, reasons = policy.label(100, _signals(evidence_available=False))
    assert label == ReliabilityLabel.NEEDS_VERIFICATION
    assert any("no_evidence" in r for r in reasons)


def test_safety_override_evaluation_failure_forces_needs_verification():
    policy = ReliabilityPolicy()
    label, _ = policy.label(100, _signals(evaluation_failed=True))
    assert label == ReliabilityLabel.NEEDS_VERIFICATION


def test_safety_override_critical_unsupported_claim():
    policy = ReliabilityPolicy()
    label, _ = policy.label(95, _signals(critical_unsupported_claim=True))
    assert label == ReliabilityLabel.NEEDS_VERIFICATION


def test_contradiction_caps_at_uncertain():
    policy = ReliabilityPolicy()
    label, reasons = policy.label(95, _signals(contradictory_evidence=True))
    assert label == ReliabilityLabel.UNCERTAIN
    assert any("contradict" in r for r in reasons)


def test_contradiction_does_not_upgrade_low_score():
    policy = ReliabilityPolicy()
    label, _ = policy.label(20, _signals(contradictory_evidence=True))
    assert label == ReliabilityLabel.NEEDS_VERIFICATION


def test_fail_safe_never_returns_certain_without_evidence():
    policy = ReliabilityPolicy()
    for score in (0, 50, 80, 100):
        label, _ = policy.label(score, _signals(evidence_available=False))
        assert label != ReliabilityLabel.CERTAIN


def test_evaluate_returns_snapshot_of_weights_and_thresholds():
    policy = ReliabilityPolicy()
    result = policy.evaluate(_signals())
    assert result.thresholds == {"certain": 80, "uncertain": 50}
    assert set(result.weights) == {"evidence", "semantic", "uncertainty", "relevance"}
    assert result.final_score == 100
    assert result.label == ReliabilityLabel.CERTAIN
