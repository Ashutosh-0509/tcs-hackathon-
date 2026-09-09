"""RetrievalService — fetches real, citable sources for a question.

Trusted sources (no API key, stable, real URLs, transparent editorial process):
  - Wikipedia  (en.wikipedia.org)  — general encyclopedia
  - Wikidata   (www.wikidata.org)  — structured knowledge graph; authoritative
                                     for entity facts (founder, inception, HQ...)
  - Wikinews   (en.wikinews.org)   — journalism / current events

Each source is queried independently and failures are isolated: one source being
down never breaks retrieval. The interface stays provider-shaped so a web-search
backend (Tavily / Brave / Google CSE) can be added later behind `search()`.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import httpx

from app.core.config import get_settings

logger = logging.getLogger("trustlens.retrieval")

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_WS_RE = re.compile(r"[ \t\f\v]+")
_BLANKS_RE = re.compile(r"\n\s*\n+")

# Wikimedia User-Agent policy requires a client name + a contact (a URL counts).
_UA = "TrustLens/0.1 (https://github.com/Ashutosh-0509/tcs-hackathon-; TCS Hackathon project)"

# MediaWiki sites share one REST/API surface — only the host changes.
_MW_SITES: dict[str, tuple[str, str]] = {
    "wikipedia": ("en.wikipedia.org", "Wikipedia"),
    "wikinews": ("en.wikinews.org", "Wikinews"),
}
_WIKI_API = "https://en.wikipedia.org/w/api.php"  # for pasted-URL extract only
_WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Wikidata properties worth rendering as a verification snippet, in a sensible order.
_WD_PROPS: list[tuple[str, str]] = [
    ("P112", "Founder"),
    ("P170", "Creator"),
    ("P571", "Inception"),
    ("P169", "CEO"),
    ("P159", "Headquarters"),
    ("P17", "Country"),
    ("P452", "Industry"),
    ("P1454", "Legal form"),
    ("P138", "Named after"),
    ("P361", "Part of"),
    ("P69", "Educated at"),
    ("P106", "Occupation"),
    ("P19", "Place of birth"),
    ("P569", "Date of birth"),
]
_ALL_SOURCES = ("wikipedia", "wikidata", "wikinews")


def is_url(text: str) -> bool:
    """True when the whole string is a single http(s) URL (a pasted link)."""
    return bool(_URL_RE.fullmatch(text.strip()))


@dataclass
class RetrievedDoc:
    title: str
    url: str
    snippet: str
    source: str = "wikipedia"  # "wikipedia" | "wikidata" | "wikinews"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def _wiki_title_from_url(url: str) -> str | None:
    p = urlparse(url)
    if not p.netloc.endswith("wikipedia.org"):
        return None
    m = re.match(r"/wiki/([^?#]+)", p.path)
    return unquote(m.group(1)) if m else None


def _html_to_text(raw: str) -> tuple[str, str]:
    """Very small readability pass: drop non-content elements, keep block text."""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    title = html.unescape(_WS_RE.sub(" ", title_m.group(1)).strip()) if title_m else ""
    body = re.sub(r"(?is)<(script|style|noscript|head|nav|footer|header|form|svg)[^>]*>.*?</\1>", " ", raw)
    body = re.sub(r"(?is)<(br|/p|/div|/li|/h[1-6]|/tr)\s*>", "\n", body)
    body = re.sub(r"(?s)<[^>]+>", " ", body)
    body = html.unescape(body)
    body = _WS_RE.sub(" ", body)
    body = _BLANKS_RE.sub("\n\n", body).strip()
    return title, body


def _chunk(text: str, *, max_chunks: int, chunk_chars: int) -> list[str]:
    paras = [p.strip() for p in text.split("\n") if len(p.strip()) > 40]
    chunks: list[str] = []
    buf = ""
    for para in paras:
        if buf and len(buf) + len(para) + 1 > chunk_chars:
            chunks.append(buf)
            buf = ""
            if len(chunks) >= max_chunks:
                break
        buf = f"{buf} {para}".strip()
    if buf and len(chunks) < max_chunks:
        chunks.append(buf)
    return chunks or ([text[:chunk_chars]] if text.strip() else [])


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


def _split_entities(phrases: list[str]) -> list[str]:
    """Break "Larry Page and Sergey Brin" / "A, B" into individual names."""
    out: list[str] = []
    for p in phrases:
        for part in re.split(r"\s+and\s+|\s*,\s*", p):
            part = part.strip()
            if len(part.split()) >= 2 and part not in out:
                out.append(part)
    return out


_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if len(w) > 2 and w not in _QUERY_STOP}


def _rank(
    docs: list[RetrievedDoc], subject_terms: set[str], other_terms: set[str], k: int
) -> list[RetrievedDoc]:
    """Rank by real topical overlap, deduped by URL. A title match on a term from
    the *question itself* (the subject, e.g. "google") counts most — that's the
    page we actually need. Sources compete on relevance, so an off-topic hit from
    a source with no real coverage drops out instead of taking a slot."""
    all_terms = subject_terms | other_terms
    scored: list[tuple[float, int, RetrievedDoc]] = []
    seen: set[str] = set()
    for i, d in enumerate(docs):
        if d.url in seen:
            continue
        seen.add(d.url)
        title_terms = _terms(d.title)
        body_terms = _terms(d.snippet)
        title_subj = subject_terms & title_terms
        title_other = other_terms & title_terms
        body_hits = all_terms & body_terms
        matched = title_subj | title_other | body_hits
        if len(matched) < 2:  # need real overlap, not one stray shared word
            continue
        score = (
            len(title_subj) * 5
            + len(title_other) * 2
            + len(body_hits)
            + (1.0 if d.source == "wikidata" else 0.0)
        )
        scored.append((score, -i, d))
    scored.sort(reverse=True)
    return [d for _, _, d in scored[:k]]


class RetrievalService:
    def __init__(
        self,
        provider: str | None = None,
        timeout: float | None = None,
        sources: list[str] | None = None,
    ) -> None:
        settings = get_settings()
        self.provider = provider or settings.retrieval_provider
        self.timeout = timeout or settings.llm_timeout_seconds
        # per-HTTP-call budget — keep fan-out snappy even on a slow source
        self.call_timeout = min(self.timeout, 8.0)
        self.sources = sources or settings.retrieval_sources_list or list(_ALL_SOURCES)

    # ---- public API ----
    def search(self, query: str, k: int = 4) -> list[RetrievedDoc]:
        """Query every configured trusted source, interleave, dedupe by URL."""
        if self.provider == "none" or not query.strip():
            return []
        pool: list[RetrievedDoc] = []
        with self._client() as client:
            for name in self.sources:
                if name == "wikidata":
                    pool += self._safe(self._wikidata, client, query, k)
                elif name in _MW_SITES:
                    host, label = _MW_SITES[name]
                    pool += self._safe(self._mediawiki, client, host, name, label, query, k)
        return _rank(pool, _terms(query), set(), k)

    def search_for_answer(self, question: str, answer: str, k: int = 6) -> list[RetrievedDoc]:
        """Retrieve for the Ask flow: hit the trusted sources with the question's
        proper nouns and keywords so we pull the pages that can actually confirm
        or refute the specific claims. Interleave so all sources are represented."""
        if self.provider == "none":
            return []

        q_entities = _split_entities(_entities(question))
        a_entities = _split_entities(_entities(answer))
        entities = q_entities + [e for e in a_entities if e not in q_entities]
        keyword = _keyword_query(question) or question

        pool: list[RetrievedDoc] = []
        with self._client() as client:
            if "wikidata" in self.sources:
                # the question subject first (e.g. "google"), then the named people
                pool += self._safe(self._wikidata, client, keyword, 2)
                for e in entities[:2]:
                    pool += self._safe(self._wikidata, client, e, 1)

            # keyword query first — it carries the question's actual subject
            mw_queries = [(keyword, 3)] + [(e, 2) for e in entities[:3]]
            for name in ("wikipedia", "wikinews"):
                if name not in self.sources:
                    continue
                host, label = _MW_SITES[name]
                for q, n in mw_queries:
                    if q.strip():
                        pool += self._safe(self._mediawiki, client, host, name, label, q, n)

        # rank by the question terms (the subject) vs. the named entities separately,
        # and NOT the answer body — retrieval must not be biased toward confirming
        # whatever the answer happens to claim
        return _rank(pool, _terms(question), _terms(" ".join(entities)), k)

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.call_timeout, headers={"User-Agent": _UA}, follow_redirects=True
        )

    @staticmethod
    def _safe(fn, *args) -> list[RetrievedDoc]:
        try:
            return fn(*args)
        except Exception:  # noqa: BLE001 - one source failing must not break retrieval
            logger.exception("retrieval call %s failed", getattr(fn, "__name__", fn))
            return []

    # ---- MediaWiki (Wikipedia, Wikinews) ----
    def _mediawiki(
        self, client: httpx.Client, host: str, source: str, label: str, query: str, k: int
    ) -> list[RetrievedDoc]:
        resp = client.get(
            f"https://{host}/w/rest.php/v1/search/page",
            params={"q": query, "limit": max(k, 3)},
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        pages = resp.json().get("pages", [])[:k]
        if not pages:
            return []
        titles = [p["title"] for p in pages if p.get("title")]
        extracts = self._extracts(client, host, titles)
        docs: list[RetrievedDoc] = []
        for page in pages:
            title = page.get("title", "")
            key = page.get("key") or title.replace(" ", "_")
            snippet = extracts.get(title) or _strip_html(page.get("excerpt", ""))
            if not snippet:
                continue
            docs.append(
                RetrievedDoc(
                    title=f"{title} ({label})",
                    url=f"https://{host}/wiki/{key}",
                    snippet=snippet[:2500],
                    source=source,
                )
            )
        return docs

    @staticmethod
    def _extracts(client: httpx.Client, host: str, titles: list[str]) -> dict[str, str]:
        """Intro-paragraph plain text for several articles in one call."""
        try:
            r = client.get(
                f"https://{host}/w/api.php",
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

    # ---- Wikidata (structured facts) ----
    def _wikidata(self, client: httpx.Client, query: str, k: int) -> list[RetrievedDoc]:
        r = client.get(
            _WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "type": "item",
                "limit": max(k, 2),
                "format": "json",
            },
        )
        r.raise_for_status()
        hits = r.json().get("search", [])[:k]
        ids = [h["id"] for h in hits if h.get("id")]
        if not ids:
            return []

        ent = client.get(
            _WIKIDATA_API,
            params={
                "action": "wbgetentities",
                "ids": "|".join(ids),
                "props": "labels|descriptions|claims",
                "languages": "en",
                "format": "json",
            },
        )
        ent.raise_for_status()
        entities = ent.json().get("entities", {})

        # collect referenced item ids so we can resolve their labels in one call
        referenced: set[str] = set()
        for eid in ids:
            for pid, _ in _WD_PROPS:
                for claim in entities.get(eid, {}).get("claims", {}).get(pid, []):
                    dv = claim.get("mainsnak", {}).get("datavalue", {})
                    if dv.get("type") == "wikibase-entityid":
                        referenced.add(dv["value"]["id"])
        labels = self._wikidata_labels(client, sorted(referenced))

        docs: list[RetrievedDoc] = []
        for eid in ids:
            e = entities.get(eid, {})
            name = e.get("labels", {}).get("en", {}).get("value") or eid
            desc = e.get("descriptions", {}).get("en", {}).get("value", "")
            facts: list[str] = []
            for pid, plabel in _WD_PROPS:
                vals = [
                    v
                    for v in (
                        _wd_value(c.get("mainsnak", {}), labels)
                        for c in e.get("claims", {}).get(pid, [])
                    )
                    if v
                ]
                if vals:
                    facts.append(f"{plabel}: {', '.join(vals[:4])}")
            snippet = name + (f" — {desc}." if desc else ".")
            if facts:
                snippet += " " + " ".join(f"{f}." for f in facts)
            docs.append(
                RetrievedDoc(
                    title=f"{name} (Wikidata)",
                    url=f"https://www.wikidata.org/wiki/{eid}",
                    snippet=snippet,
                    source="wikidata",
                )
            )
        return docs

    @staticmethod
    def _wikidata_labels(client: httpx.Client, ids: list[str]) -> dict[str, str]:
        out: dict[str, str] = {}
        for i in range(0, len(ids), 50):  # API caps ids per call
            batch = ids[i : i + 50]
            try:
                r = client.get(
                    _WIKIDATA_API,
                    params={
                        "action": "wbgetentities",
                        "ids": "|".join(batch),
                        "props": "labels",
                        "languages": "en",
                        "format": "json",
                    },
                )
                r.raise_for_status()
                for eid, e in r.json().get("entities", {}).items():
                    label = e.get("labels", {}).get("en", {}).get("value")
                    if label:
                        out[eid] = label
            except httpx.HTTPError:
                continue
        return out

    # ---- fetch a URL the user pasted as a source ----
    def fetch_page(self, url: str, max_chunks: int = 16, chunk_chars: int = 1500) -> list[RetrievedDoc]:
        """Fetch a web page the user gave as a source and return its readable
        text, split into paragraph-sized chunks so the per-claim checks have
        something granular to match. Returns [] on any failure (caller falls
        back to treating the raw string as evidence)."""
        if self.provider == "none":
            return []
        url = url.strip()
        try:
            title, text = self._read_url(url)
        except Exception:  # noqa: BLE001 - a bad link must not break the request
            logger.exception("failed to fetch source URL %r", url[:200])
            return []
        chunks = _chunk(text, max_chunks=max_chunks, chunk_chars=chunk_chars)
        return [RetrievedDoc(title=title, url=url, snippet=c, source="url") for c in chunks]

    def _read_url(self, url: str) -> tuple[str, str]:
        headers = {"User-Agent": _UA, "Api-User-Agent": _UA, "Accept": "*/*"}
        with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as client:
            wiki_title = _wiki_title_from_url(url)
            if wiki_title:
                extract = self._full_extract(client, wiki_title)
                if extract:
                    return wiki_title.replace("_", " "), extract
            resp = client.get(url)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype and ctype:
                raise ValueError(f"unsupported content-type {ctype!r}")
            title, body = _html_to_text(resp.text)
            return (title or urlparse(url).netloc), body

    @staticmethod
    def _full_extract(client: httpx.Client, title: str) -> str:
        """Whole-article plain text for one Wikipedia title (not just the intro)."""
        try:
            r = client.get(
                _WIKI_API,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "explaintext": 1,
                    "redirects": 1,
                    "format": "json",
                    "titles": title.replace("_", " "),
                },
            )
            if r.status_code != 200:
                return ""
            for page in r.json().get("query", {}).get("pages", {}).values():
                if page.get("extract"):
                    return page["extract"].strip()
            return ""
        except httpx.HTTPError:
            return ""


def _wd_value(snak: dict, labels: dict[str, str]) -> str:
    """Render one Wikidata statement value as plain text."""
    dv = snak.get("datavalue", {})
    t, val = dv.get("type"), dv.get("value")
    if t == "wikibase-entityid":
        return labels.get(val["id"], val["id"])
    if t == "time":
        # "+1998-00-00T00:00:00Z" -> "1998"
        m = re.match(r"[+-](\d{4})", str(val.get("time", "")))
        return m.group(1) if m else ""
    if t == "quantity":
        return str(val.get("amount", "")).lstrip("+")
    if t == "monolingualtext":
        return val.get("text", "")
    if t == "string":
        return str(val)
    return ""


_default: RetrievalService | None = None


def get_retrieval_service() -> RetrievalService:
    global _default
    if _default is None:
        _default = RetrievalService()
    return _default
