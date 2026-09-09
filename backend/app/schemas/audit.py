from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AuditEntry(BaseModel):
    id: str
    request_id: str
    actor_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    metadata: dict
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditEntry]
    total: int
    limit: int
    offset: int
