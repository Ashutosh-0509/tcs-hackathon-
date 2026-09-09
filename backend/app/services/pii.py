"""PIIService — deterministic PII detection + masking.

Regex recognizers for common Indian identifiers plus email / credit card, with an
optional Microsoft Presidio pass (TECH_STACK.md §24-28). PII is redacted BEFORE
any LLM call and before persistence. Presidio is not treated as a complete
guarantee.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.core.config import get_settings

logger = logging.getLogger("trustlens.pii")


@dataclass(frozen=True)
class PIISpan:
    type: str
    start: int
    end: int


@dataclass
class PIIResult:
    original: str
    redacted: str
    spans: list[PIISpan]

    @property
    def detected(self) -> bool:
        return bool(self.spans)

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for s in self.spans:
            out[s.type] = out.get(s.type, 0) + 1
        return out


def _luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if len(d) < 12:
        return False
    checksum = 0
    parity = len(d) % 2
    for i, n in enumerate(d):
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        checksum += n
    return checksum % 10 == 0


# order matters: longer / more specific patterns first so they claim spans before
# shorter ones (a 16-digit card must win over the 12-digit Aadhaar pattern).
_RECOGNIZERS: list[tuple[str, re.Pattern]] = [
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("CREDIT_CARD", re.compile(r"(?<!\d)(?:\d[ \-]?){13,19}(?<![ \-])(?!\d)")),
    ("AADHAAR", re.compile(r"(?<!\d)[2-9]\d{3}\s?\d{4}\s?\d{4}(?!\d)")),
    ("PHONE_IN", re.compile(r"(?<!\d)(?:\+?91[\-\s]?|0)?[6-9]\d{9}(?!\d)")),
    ("BANK_ACCOUNT", re.compile(r"(?<!\d)\d{9,18}(?!\d)")),
]

_MASK = {
    "PAN": "[REDACTED_PAN]",
    "AADHAAR": "[REDACTED_AADHAAR]",
    "EMAIL": "[REDACTED_EMAIL]",
    "PHONE_IN": "[REDACTED_PHONE]",
    "CREDIT_CARD": "[REDACTED_CARD]",
    "BANK_ACCOUNT": "[REDACTED_ACCOUNT]",
    "PERSON": "[REDACTED_NAME]",
    "LOCATION": "[REDACTED_LOCATION]",
    "DEFAULT": "[REDACTED]",
}


class PIIService:
    def __init__(self, use_presidio: bool | None = None) -> None:
        self.use_presidio = (
            get_settings().pii_use_presidio if use_presidio is None else use_presidio
        )
        self._analyzer = None
        if self.use_presidio:
            self._try_load_presidio()

    def _try_load_presidio(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine

            self._analyzer = AnalyzerEngine()
            logger.info("PII: Presidio analyzer enabled")
        except Exception as exc:  # noqa: BLE001
            logger.warning("PII: Presidio requested but unavailable (%s); regex-only", exc)
            self._analyzer = None

    # ---- detection ----
    def scan(self, text: str) -> list[PIISpan]:
        spans: list[PIISpan] = []
        claimed: list[tuple[int, int]] = []

        def overlaps(a: int, b: int) -> bool:
            return any(not (b <= s or a >= e) for s, e in claimed)

        for label, pattern in _RECOGNIZERS:
            for m in pattern.finditer(text):
                s, e = m.start(), m.end()
                if overlaps(s, e):
                    continue
                value = m.group()
                if label == "CREDIT_CARD" and not _luhn_ok(value):
                    continue
                if label == "BANK_ACCOUNT" and (len(re.sub(r"\D", "", value)) < 9):
                    continue
                spans.append(PIISpan(type=label, start=s, end=e))
                claimed.append((s, e))

        if self._analyzer is not None:
            try:
                for r in self._analyzer.analyze(text=text, language="en"):
                    if not overlaps(r.start, r.end):
                        spans.append(PIISpan(type=r.entity_type, start=r.start, end=r.end))
                        claimed.append((r.start, r.end))
            except Exception as exc:  # noqa: BLE001
                logger.warning("PII: Presidio analyze failed (%s)", exc)

        spans.sort(key=lambda s: s.start)
        return spans

    def redact(self, text: str) -> PIIResult:
        spans = self.scan(text)
        if not spans:
            return PIIResult(original=text, redacted=text, spans=[])
        out = []
        cursor = 0
        for span in spans:
            out.append(text[cursor : span.start])
            out.append(_MASK.get(span.type, _MASK["DEFAULT"]))
            cursor = span.end
        out.append(text[cursor:])
        return PIIResult(original=text, redacted="".join(out), spans=spans)

    def redact_many(self, texts: list[str]) -> tuple[list[str], list[PIISpan]]:
        redacted: list[str] = []
        all_spans: list[PIISpan] = []
        for t in texts:
            r = self.redact(t)
            redacted.append(r.redacted)
            all_spans.extend(r.spans)
        return redacted, all_spans


_default: PIIService | None = None


def get_pii_service() -> PIIService:
    global _default
    if _default is None:
        _default = PIIService()
    return _default
