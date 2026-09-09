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
# contradiction / unsupported critical claim) are asserted exactly regardless of the
# embedding backend. The rest depend on semantic-similarity quality.
_REAL_EMBEDDINGS = get_embedding_service().backend == "sentence-transformers"
_SAFETY_FIXED = {
    "acme_market_share_unsupported",
    "merger_contradiction",
    "library_contradiction",
    "no_evidence_capital",
}


def test_health(client):
    body = client.get("/api/v1/health").json()
    assert body["status"] in {"healthy", "degraded"}
    assert "database" in body and "llm" in body


def test_evaluate_supported_answer(client):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Who created the Linux kernel?",
            "answer": "The Linux kernel was created by Linus Torvalds in 1991.",
            "evidence": ["The Linux kernel was first released by Linus Torvalds in 1991."],
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
            "question": "What was Acme Corp's market share in 2024?",
            "answer": "Acme Corp held a 37% market share in 2024.",
            "evidence": ["Acme Corp was founded in 2009."],
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
            "question": "Summarise this customer record.",
            "answer": "The customer PAN is ABCPD1234E.",
            "evidence": ["Customer PAN ABCPD1234E, email customer@example.com."],
        },
    )
    body = resp.json()
    assert body["security"]["pii_detected"] is True
    assert "ABCPD1234E" not in body["answer"]
    assert "ABCPD1234E" not in json.dumps(body)


def test_history_and_detail_endpoints(client, register):
    token = register("hist@example.com", role="USER")
    h = {"Authorization": f"Bearer {token}"}
    ev = client.post(
        "/api/v1/evaluate",
        headers=h,
        json={
            "question": "Who created the Linux kernel?",
            "answer": "Linus Torvalds created the Linux kernel.",
            "evidence": ["The Linux kernel was created by Linus Torvalds."],
        },
    ).json()

    mine = client.get("/api/v1/answers?mine=true", headers=h).json()
    assert any(a["answer_id"] == ev["answer_id"] for a in mine)

    detail = client.get(f"/api/v1/answers/{ev['answer_id']}").json()
    assert detail["answer_id"] == ev["answer_id"]
    assert detail["effective_label"] == detail["label"]
    assert "claims" in detail and "evidence" in detail and "reliability" in detail


def test_review_decision_and_label_override(client, register):
    ev = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Was the merger approved by regulators in March?",
            "answer": "The merger was approved by regulators in March.",
            "evidence": [
                "Regulators did not approve the merger in March; the proposal was rejected."
            ],
        },
    ).json()
    assert ev["reliability"]["label"] == "NEEDS_VERIFICATION"

    token = register("editor-decide@example.com", role="EDITOR")
    h = {"Authorization": f"Bearer {token}"}
    queue = client.get("/api/v1/reviews", headers=h).json()
    review_id = next(i["review_id"] for i in queue if i["answer_id"] == ev["answer_id"])

    decided = client.post(
        f"/api/v1/reviews/{review_id}",
        headers=h,
        json={
            "status": "REJECTED",
            "decision_note": "Evidence contradicts the claim.",
            "override_label": "NEEDS_VERIFICATION",
        },
    )
    assert decided.status_code == 200
    assert decided.json()["status"] == "REJECTED"
    assert decided.json()["effective_label"] == "NEEDS_VERIFICATION"

    # override surfaces on the answer detail
    detail = client.get(f"/api/v1/answers/{ev['answer_id']}").json()
    assert detail["review"]["status"] == "REJECTED"

    again = client.post(
        f"/api/v1/reviews/{review_id}", headers=h, json={"status": "APPROVED"}
    )
    assert again.status_code == 409


@pytest.mark.parametrize("case", DEMO, ids=[c["name"] for c in DEMO])
def test_demo_cases(client, case):
    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": case["question"],
            "answer": case["answer"],
            "evidence": case.get("evidence", []),
        },
    )
    assert resp.status_code == 200, resp.text
    label = resp.json()["reliability"]["label"]
    assert label in {"CERTAIN", "UNCERTAIN", "NEEDS_VERIFICATION"}
    # Deterministic safety overrides hold on every backend. The exact
    # CERTAIN/UNCERTAIN boundary for the rest depends on embedding quality, so it
    # is only asserted when a real semantic model is loaded.
    if case["name"] in _SAFETY_FIXED:
        assert label == "NEEDS_VERIFICATION", case["name"]
    elif _REAL_EMBEDDINGS:
        assert label == case["expected_label"], case["name"]
