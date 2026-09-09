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
_ENTITY = re.compile(r"\b([A-Z][a-z]+(?:\s+(?:of|the|de|van|von|and|[A-Z][a-z]+))+)\b")
_MONTHS = {
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
}
_ENTITY_STOP = _MONTHS | {
    "The", "A", "An", "It", "This", "That", "There", "In", "On", "According",
    "British", "American", "French", "German", "Indian", "Chinese", "European",
}


def _entities(text: str, limit: int = 3) -> list[str]:
    out: list[str] = []
    for m in _ENTITY.finditer(text):
        phrase = " ".join(w for w in m.group(1).split())
        first = phrase.split()[0]
        if first in _ENTITY_STOP or len(phrase.split()) < 2:
            continue
        if phrase not in out:
            out.append(phrase)
        if len(out) >= limit:
            break
    return out


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
        """Retrieve for the Ask flow: search the question, then the proper nouns
        named in the answer (people, places, works) so we actually pull the pages
        that can confirm or refute the specific claims. Merge and dedupe."""
        if self.provider == "none":
            return []
        seen: dict[str, RetrievedDoc] = {}
        for d in self.search(question, 3):
            seen.setdefault(d.url, d)
        for entity in _entities(answer):
            for d in self.search(entity, 1):
                seen.setdefault(d.url, d)
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
                        snippet=snippet[:1000],
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
