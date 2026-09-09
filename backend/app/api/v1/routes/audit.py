from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import DbDep, EditorUser
from app.models import AuditLog
from app.schemas.audit import AuditEntry, AuditPage

router = APIRouter()


@router.get("", response_model=AuditPage)
def audit_timeline(
    db: DbDep,
    _: EditorUser,
    request_id: str | None = None,
    action: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AuditPage:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    count_stmt = select(func.count()).select_from(AuditLog)
    if request_id:
        stmt = stmt.where(AuditLog.request_id == request_id)
        count_stmt = count_stmt.where(AuditLog.request_id == request_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.limit(limit).offset(offset)).all()
    return AuditPage(
        items=[
            AuditEntry(
                id=str(r.id),
                request_id=r.request_id,
                actor_id=str(r.actor_id) if r.actor_id else None,
                action=r.action,
                entity_type=r.entity_type,
                entity_id=str(r.entity_id) if r.entity_id else None,
                metadata=r.audit_metadata,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
