"""RetrievalService — fetches real, citable sources for a question.

MVP source: Wikipedia (no API key, stable, real article URLs). The interface is
provider-shaped so a web-search backend (Tavily / Brave) can be dropped in later
behind the same `search()` call.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger("trustlens.retrieval")

# Wikimedia REST API — designed for third-party use, more permissive than w/api.php
_WIKI_SEARCH = "https://en.wikipedia.org/w/rest.php/v1/search/page"
_WIKI_API = "https://en.wikipedia.org/w/api.php"
# Wikimedia User-Agent policy requires a client name + a contact (a URL counts).
_UA = "TrustLens/0.1 (https://github.com/Ashutosh-0509/tcs-hackathon-; TCS Hackathon project)"


@dataclass
class RetrievedDoc:
    title: str
    url: str
    snippet: str


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


# multi-word Capitalised sequences — proper-noun phrases (people, places, works)
_TOKEN_RE = r"(?:[A-Z][a-z]+|of|the|de|van|von|and)"
_ENTITY = re.compile(rf"\b({_TOKEN_RE}(?:\s+{_TOKEN_RE})+)\b")
_MONTHS = {
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
}
_LEAD_STOP = _MONTHS | {
    "the", "a", "an", "it", "this", "that", "there", "in", "on", "according",
    "and", "of", "de", "does", "do", "did", "is", "are", "was", "were", "who",
    "what", "when", "where", "why", "how", "which", "has", "have", "had", "can",
    "could", "would", "should", "will",
}
_QUERY_STOP = _LEAD_STOP | {
    "is", "are", "was", "were", "did", "do", "does", "has", "have", "had", "who",
    "what", "when", "where", "why", "how", "which", "whom", "to", "for", "from",
    "over", "about", "into", "than", "with", "as", "by", "at", "or", "not", "be",
    "its", "their", "his", "her", "any", "many", "much", "very", "also", "can",
    "could", "would", "should", "may", "might", "will", "shall", "km", "years",
}


def _entities(text: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for m in _ENTITY.finditer(text):
        words = m.group(1).split()
        while words and words[0].lower() in _LEAD_STOP:
            words = words[1:]
        while words and words[-1].lower() in _LEAD_STOP:
            words = words[:-1]
        if len(words) < 2 or not any(w[:1].isupper() for w in words):
            continue
        phrase = " ".join(words)
        if phrase not in out:
            out.append(phrase)
        if len(out) >= limit:
            break
    return out


def _keyword_query(text: str) -> str:
    """Reduce a natural-language question to its content words for keyword search."""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", text)
    kept = [w for w in words if w.lower() not in _QUERY_STOP and len(w) > 1]
    return " ".join(kept[:12])


class RetrievalService:
    def __init__(self, provider: str | None = None, timeout: float | None = None) -> None:
        settings = get_settings()
        self.provider = provider or settings.retrieval_provider
        self.timeout = timeout or settings.llm_timeout_seconds

    def search(self, query: str, k: int = 4) -> list[RetrievedDoc]:
        if self.provider == "none":
            return []
        try:
            return self._wikipedia(query, k)
        except Exception:  # noqa: BLE001 - retrieval failure must not break the request
            logger.exception("retrieval failed for %r", query[:120])
            return []

    def search_for_answer(self, question: str, answer: str, k: int = 6) -> list[RetrievedDoc]:
        """Retrieve for the Ask flow: search the question's keywords and the proper
        nouns named in the question and answer, so we actually pull the pages that
        can confirm or refute the specific claims. Merge and dedupe."""
        if self.provider == "none":
            return []
        seen: dict[str, RetrievedDoc] = {}

        q_entities = _entities(question)
        entities = q_entities + [e for e in _entities(answer) if e not in q_entities]

        # entities are precise -> search them first; keyword query is the fallback
        queries: list[tuple[str, int]] = [(e, 2) for e in entities[:4]]
        queries.append((_keyword_query(question) or question, 3))

        for q, n in queries:
            if not q.strip():
                continue
            for d in self.search(q, n):
                seen.setdefault(d.url, d)
            if len(seen) >= k + 2:
                break
        return list(seen.values())[:k]

    # ---- Wikipedia ----
    def _wikipedia(self, query: str, k: int) -> list[RetrievedDoc]:
        headers = {
            "User-Agent": _UA,
            "Api-User-Agent": _UA,
            "Accept": "application/json",
        }
        with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            resp = client.get(_WIKI_SEARCH, params={"q": query, "limit": max(k, 3)})
            resp.raise_for_status()
            pages = resp.json().get("pages", [])[:k]
            if not pages:
                return []

            titles = [p["title"] for p in pages if p.get("title")]
            extracts = self._extracts(client, titles)

            docs: list[RetrievedDoc] = []
            for page in pages:
                title = page.get("title", "")
                key = page.get("key") or title.replace(" ", "_")
                snippet = extracts.get(title) or _strip_html(page.get("excerpt", ""))
                if not snippet:
                    continue
                docs.append(
                    RetrievedDoc(
                        title=title,
                        url=f"https://en.wikipedia.org/wiki/{key}",
                        snippet=snippet[:2500],
                    )
                )
        return docs

    @staticmethod
    def _extracts(client: httpx.Client, titles: list[str]) -> dict[str, str]:
        """Intro-paragraph plain text for several articles in one call."""
        try:
            r = client.get(
                _WIKI_API,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "exintro": 1,
                    "explaintext": 1,
                    "redirects": 1,
                    "format": "json",
                    "titles": "|".join(titles),
                },
            )
            if r.status_code != 200:
                return {}
            out: dict[str, str] = {}
            for page in r.json().get("query", {}).get("pages", {}).values():
                if page.get("title") and page.get("extract"):
                    out[page["title"]] = page["extract"].strip()
            return out
        except httpx.HTTPError:
            return {}


_default: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _default
    if _default is None:
        _default = RetrievalService()
    return _default
