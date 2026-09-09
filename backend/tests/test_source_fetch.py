"""The 'sources' box on the Check page accepts a pasted link, not just text.

A line that is a bare URL is fetched server-side and its readable text becomes
the evidence (split into chunks); any other line stays literal. A search term
like "wikipedia" is literal text and — correctly — supports nothing.
"""
from __future__ import annotations

from app.services.answer_service import AnswerService
from app.services.evaluation import EvaluationEngine
from app.services.llm import get_llm_provider
from app.services.pii import PIIService
from app.services.retrieval import RetrievedDoc, _chunk, _html_to_text, is_url


def test_is_url():
    assert is_url("https://en.wikipedia.org/wiki/Linux_kernel")
    assert is_url("  http://example.com/a?b=c  ")
    assert not is_url("wikipedia")
    assert not is_url("see https://example.com for details")


def test_html_to_text_drops_chrome_and_keeps_body():
    title, body = _html_to_text(
        "<html><head><title>Cats &amp; Dogs</title><style>.x{}</style></head>"
        "<body><nav>menu</nav><p>Cats are small carnivorous mammals.</p>"
        "<script>evil()</script><p>They were domesticated long ago.</p></body></html>"
    )
    assert title == "Cats & Dogs"
    assert "carnivorous mammals" in body
    assert "evil()" not in body and "menu" not in body


def test_chunk_splits_long_text():
    text = "\n".join(f"Paragraph number {i} with enough words to be kept here." for i in range(20))
    chunks = _chunk(text, max_chunks=3, chunk_chars=120)
    assert 1 <= len(chunks) <= 3
    assert all(c.strip() for c in chunks)


class _FakeRetrieval:
    def __init__(self, docs: list[RetrievedDoc] | None = None):
        self._docs = docs or []
        self.fetched: list[str] = []

    def fetch_page(self, url: str, **_):
        self.fetched.append(url)
        return list(self._docs)


def _service(db, retrieval):
    return AnswerService(
        db=db,
        llm=get_llm_provider(),
        engine=EvaluationEngine(),
        pii=PIIService(use_presidio=False),
        retrieval=retrieval,
    )


def test_prepare_sources_fetches_a_pasted_url(db):
    docs = [
        RetrievedDoc(title="Linux kernel", url="https://en.wikipedia.org/wiki/Linux_kernel",
                     snippet="The Linux kernel was created by Linus Torvalds in 1991."),
        RetrievedDoc(title="Linux kernel", url="https://en.wikipedia.org/wiki/Linux_kernel",
                     snippet="It is released under the GNU GPL version 2."),
    ]
    fake = _FakeRetrieval(docs)
    sources, _spans = _service(db, fake)._prepare_sources(
        ["https://en.wikipedia.org/wiki/Linux_kernel", "A hand-written note."]
    )
    assert fake.fetched == ["https://en.wikipedia.org/wiki/Linux_kernel"]
    assert [s.snippet for s in sources] == [
        "The Linux kernel was created by Linus Torvalds in 1991.",
        "It is released under the GNU GPL version 2.",
        "A hand-written note.",
    ]
    assert sources[0].url == "https://en.wikipedia.org/wiki/Linux_kernel"
    assert sources[2].url is None


def test_prepare_sources_keeps_url_literal_when_fetch_fails(db):
    fake = _FakeRetrieval([])  # fetch returns nothing
    sources, _ = _service(db, fake)._prepare_sources(["https://en.wikipedia.org/wiki/Nope"])
    assert len(sources) == 1
    assert sources[0].snippet == "https://en.wikipedia.org/wiki/Nope"


def test_evaluate_with_fetched_url_shows_page_as_source(client, monkeypatch):
    """End-to-end: pasting a link surfaces the fetched page text as the source."""
    from app.services import answer_service

    doc = RetrievedDoc(
        title="Linus Torvalds",
        url="https://en.wikipedia.org/wiki/Linus_Torvalds",
        snippet="Linus Benedict Torvalds is the creator of the Linux kernel, first released in 1991.",
    )
    monkeypatch.setattr(
        answer_service, "get_retrieval_service", lambda: _FakeRetrieval([doc])
    )

    resp = client.post(
        "/api/v1/evaluate",
        json={
            "question": "Who created the Linux kernel?",
            "answer": "Linus Torvalds created the Linux kernel.",
            "evidence": ["https://en.wikipedia.org/wiki/Linus_Torvalds"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sources"], "the fetched page should appear as a source"
    assert body["sources"][0]["url"] == "https://en.wikipedia.org/wiki/Linus_Torvalds"
