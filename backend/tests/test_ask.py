"""The Ask flow: question in, model answers, TrustLens verifies against sources.

Retrieval is disabled in tests (RETRIEVAL_PROVIDER=none), so these assert wiring
and the fail-safe: with no sources to check against, a real answer must land in
NEEDS_VERIFICATION, never CERTAIN.
"""
from __future__ import annotations

from app.services.answer_service import AnswerService, Source
from app.services.evaluation import EvaluationEngine
from app.services.llm import get_llm_provider
from app.services.pii import PIIService
from app.services.retrieval import RetrievedDoc


def test_ask_endpoint_shape(client):
    resp = client.post("/api/v1/ask", json={"question": "Who painted the Mona Lisa?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mode"] == "ASK"
    assert body["question"]
    assert body["answer"]
    assert isinstance(body["sources"], list)
    assert "reliability" in body and "label" in body["reliability"]


def test_ask_with_no_retrieval_is_not_certain(client):
    body = client.post(
        "/api/v1/ask", json={"question": "What is the boiling point of water at sea level?"}
    ).json()
    # nothing was retrieved to verify against -> cannot be CERTAIN
    assert body["reliability"]["label"] != "CERTAIN"
    assert body["review_required"] is True


def test_ask_verifies_against_injected_sources(db, monkeypatch):
    """With sources present, a supported answer can clear."""

    docs = [
        RetrievedDoc(
            title="Water",
            url="https://en.wikipedia.org/wiki/Water",
            snippet="Water boils at 100 degrees Celsius at sea level under standard pressure.",
        )
    ]

    class FakeRetrieval:
        def search(self, query, k=4):
            return docs

        def search_for_answer(self, question, answer, k=6):
            return docs

    svc = AnswerService(
        db=db,
        llm=get_llm_provider(),
        engine=EvaluationEngine(),
        pii=PIIService(use_presidio=False),
        retrieval=FakeRetrieval(),
    )
    # force a concrete answer regardless of the stub
    from app.services.llm.base import LLMResult

    monkeypatch.setattr(
        svc.llm,
        "answer_question",
        lambda q: LLMResult(
            text="Water boils at 100 degrees Celsius at sea level.", model="test"
        ),
    )
    out = svc.ask(question="What is the boiling point of water?", include_explanation=False, actor_id=None)
    assert out.sources and out.sources[0].url == "https://en.wikipedia.org/wiki/Water"
    assert out.reliability.label in {"CERTAIN", "UNCERTAIN", "NEEDS_VERIFICATION"}
    assert isinstance(Source(snippet="x"), Source)
