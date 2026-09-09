"""Structured logging with request-id injection and a secret/PII redaction filter."""
from __future__ import annotations

import logging
import re
import sys

from app.core.request_context import get_request_id

_SECRET_PATTERNS = [
    re.compile(r"(api[_-]?key\"?\s*[:=]\s*\"?)([A-Za-z0-9\-_]{8,})", re.I),
    re.compile(r"(bearer\s+)([A-Za-z0-9\-_\.]{12,})", re.I),
    re.compile(r"(password\"?\s*[:=]\s*\"?)([^\s\"']+)", re.I),
    # Raw Indian identifiers must never reach the log stream.
    re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),          # PAN
    re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),           # Aadhaar
]


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        for pat in _SECRET_PATTERNS:
            if pat.groups >= 2:
                msg = pat.sub(r"\1[REDACTED]", msg)
            else:
                msg = pat.sub("[REDACTED]", msg)
        record.msg = msg
        record.args = ()
        return True


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    for noisy in ("httpx", "httpcore", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
