"""Per-request context: a request ID that threads through logs, LLM calls, audit."""
from __future__ import annotations

import itertools
from contextvars import ContextVar
from datetime import UTC, datetime

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_counter = itertools.count(1)


def new_request_id() -> str:
    """e.g. TRUST-2026-000123. Monotonic within a process; good enough for a demo."""
    year = datetime.now(UTC).year
    seq = next(_counter)
    return f"TRUST-{year}-{seq:06d}"


def set_request_id(value: str) -> None:
    _request_id.set(value)


def get_request_id() -> str:
    return _request_id.get() or "TRUST-0000-000000"
