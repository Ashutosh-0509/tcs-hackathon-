"""Audit log writer. Adds a row to the current unit of work (caller commits)."""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.models import AuditLog


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    actor_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        request_id=get_request_id(),
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        audit_metadata=metadata or {},
    )
    db.add(entry)
    return entry
