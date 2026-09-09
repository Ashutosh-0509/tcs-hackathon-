"""Multi-source retrieval: Wikipedia + Wikidata + Wikinews, ranked by relevance."""
from __future__ import annotations

from app.services.retrieval import (
    RetrievedDoc,
    RetrievalService,
    _rank,
    _split_entities,
    _terms,
    _wd_value,
)


def test_split_entities_breaks_conjunctions():
    assert _split_entities(["Larry Page and Sergey Brin"]) == ["Larry Page", "Sergey Brin"]
    assert _split_entities(["Barack Obama, Joe Biden"]) == ["Barack Obama", "Joe Biden"]
    assert _split_entities(["Stanford University"]) == ["Stanford University"]


def test_rank_drops_offtopic_and_prefers_subject_title():
    subject = _terms("who is the founder of google")
    other = _terms("Larry Page Sergey Brin")
    docs = [
        RetrievedDoc("U.S. Senator Larry Craig to resign (Wikinews)", "u1",
                     "Senator Larry Craig announced he will resign.", "wikinews"),
        RetrievedDoc("Larry Page (Wikipedia)", "u2",
                     "Larry Page co-founded Google with Sergey Brin.", "wikipedia"),
        RetrievedDoc("Google (Wikipedia)", "u3",
                     "Google was founded in 1998 by Larry Page and Sergey Brin.", "wikipedia"),
    ]
    ranked = _rank(docs, subject, other, k=5)
    urls = [d.url for d in ranked]
    assert "u1" not in urls  # off-topic Wikinews hit dropped
    assert urls[0] == "u3"  # title matches the question subject ("google")


def test_rank_dedupes_by_url():
    subject = _terms("python guido rossum")
    d = RetrievedDoc("Python (Wikipedia)", "same", "Python was created by Guido van Rossum.", "wikipedia")
    assert len(_rank([d, d, d], subject, set(), k=5)) == 1


def test_wd_value_renders_types():
    labels = {"Q504": "Larry Page"}
    assert _wd_value({"datavalue": {"type": "wikibase-entityid", "value": {"id": "Q504"}}}, labels) == "Larry Page"
    assert _wd_value({"datavalue": {"type": "time", "value": {"time": "+1998-00-00T00:00:00Z"}}}, labels) == "1998"
    assert _wd_value({"datavalue": {"type": "string", "value": "BackRub"}}, labels) == "BackRub"


def test_search_for_answer_interleaves_sources(monkeypatch):
    svc = RetrievalService(provider="wikipedia", sources=["wikipedia", "wikidata", "wikinews"])

    def fake_wikidata(client, query, k):
        return [RetrievedDoc(f"{query} (Wikidata)", f"wd:{query}",
                             f"{query} — founder of Google. Google Larry Page Sergey Brin.", "wikidata")]

    def fake_mediawiki(client, host, source, label, query, k):
        return [RetrievedDoc(f"{query} ({label})", f"{source}:{query}",
                             f"{query} Google founder Larry Page Sergey Brin.", source)]

    monkeypatch.setattr(svc, "_wikidata", fake_wikidata)
    monkeypatch.setattr(svc, "_mediawiki", fake_mediawiki)

    docs = svc.search_for_answer(
        "who is the founder of google?",
        "Google was founded by Larry Page and Sergey Brin.",
        k=6,
    )
    assert {d.source for d in docs} >= {"wikipedia", "wikidata"}


def test_retrieval_disabled_returns_nothing():
    svc = RetrievalService(provider="none")
    assert svc.search("anything", 4) == []
    assert svc.search_for_answer("q", "a", 4) == []
    assert svc.fetch_page("https://en.wikipedia.org/wiki/Google") == []
