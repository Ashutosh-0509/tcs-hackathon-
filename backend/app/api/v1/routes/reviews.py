from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbDep, EditorUser
from app.models.enums import ReviewStatus
from app.schemas.review import ReviewDecisionRequest, ReviewDetail, ReviewQueueItem
from app.services import review_service

router = APIRouter()


@router.get("", response_model=list[ReviewQueueItem])
def review_queue(
    db: DbDep,
    _: EditorUser,
    status: ReviewStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ReviewQueueItem]:
    return review_service.list_queue(
        db, status=status.value if status else None, limit=limit, offset=offset
    )


@router.get("/{review_id}", response_model=ReviewDetail)
def review_detail(review_id: uuid.UUID, db: DbDep, _: EditorUser) -> ReviewDetail:
    return review_service.get_detail(db, review_id)


@router.post("/{review_id}", response_model=ReviewDetail)
def decide_review(
    review_id: uuid.UUID,
    payload: ReviewDecisionRequest,
    db: DbDep,
    reviewer: EditorUser,
) -> ReviewDetail:
    return review_service.decide(db, review_id, payload, reviewer.id)
