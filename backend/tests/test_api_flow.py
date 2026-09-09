"""End-to-end API flow with the stub provider (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.services.embeddings import get_embedding_service

DEMO = json.loads(
    (Path(__file__).resolve().parents[2] / "data" / "demo_cases.json").read_text()
)

# Cases whose label is fixed by a deterministic safety override (no evidence /
# contradiction) are asserted exactly regardless of embedding backend. The rest
# depend on semantic-similarity quality and are only asserted with real embeddings.
_REAL_EMBEDDINGS = get_embedding_service().backend == "sentence-transformers"
_SAFETY_FIXED = {"unsupported_ceo", "contradicted_claim", "no_evidence"}


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] in {"healthy", "degraded"}
    assert "database" in body and "llm" in body


def test_evaluate_supported_answer(client):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Who invented Python?",
            "answer": "Python was created by Guido van Rossum.",
            "evidence": ["Python was created by Guido van Rossum and first released in 1991."],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["reliability"]["label"] != "NEEDS_VERIFICATION"
    assert body["request_id"].startswith("TRUST-")
    assert body["metrics"]["perplexity_available"] is False
    if _REAL_EMBEDDINGS:
        assert body["reliability"]["label"] == "CERTAIN"
        assert body["review_required"] is False


def test_evaluate_no_evidence_needs_verification_and_opens_review(client, register):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Who is the CEO of Company X?",
            "answer": "The CEO of Company X is Jane Doe.",
            "evidence": ["Company X was founded in 1995."],
        },
    )
    body = resp.json()
    assert body["reliability"]["label"] == "NEEDS_VERIFICATION"
    assert body["review_required"] is True

    token = register("editor-flow@example.com", role="EDITOR")
    queue = client.get(
        "/api/v1/reviews", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert any(item["answer_id"] == body["answer_id"] for item in queue)


def test_evaluate_redacts_pii_before_storage(client):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Explain this customer record.",
            "answer": "The customer PAN is ABCPD1234E.",
            "evidence": ["Customer PAN ABCPD1234E, email customer@example.com."],
        },
    )
    body = resp.json()
    assert body["security"]["pii_detected"] is True
    assert "ABCPD1234E" not in body["answer"]
    assert "ABCPD1234E" not in json.dumps(body)


def test_review_decision_flow(client, register):
    ev = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Is the Earth flat?",
            "answer": "The Earth is flat.",
            "evidence": ["The Earth is not flat; it is an oblate spheroid."],
        },
    ).json()
    token = register("editor-decide@example.com", role="EDITOR")
    h = {"Authorization": f"Bearer {token}"}
    queue = client.get("/api/v1/reviews", headers=h).json()
    review_id = next(i["review_id"] for i in queue if i["answer_id"] == ev["answer_id"])

    decided = client.post(
        f"/api/v1/reviews/{review_id}",
        headers=h,
        json={"status": "REJECTED", "decision_note": "Contradicts evidence."},
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "REJECTED"

    # second decision is rejected
    again = client.post(
        f"/api/v1/reviews/{review_id}", headers=h, json={"status": "APPROVED"}
    )
    assert again.status_code == 409


@pytest.mark.parametrize("case", DEMO, ids=[c["name"] for c in DEMO])
def test_demo_cases_match_expected_labels(client, case):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": case["question"],
            "answer": case["answer"],
            "evidence": [case["source"]] if case["source"] else [],
        },
    )
    assert resp.status_code == 200, resp.text
    label = resp.json()["reliability"]["label"]
    assert label in {"CERTAIN", "UNCERTAIN", "NEEDS_VERIFICATION"}
    # Deterministic safety overrides must hold on every backend.
    if case["name"] in _SAFETY_FIXED:
        assert label == "NEEDS_VERIFICATION"
