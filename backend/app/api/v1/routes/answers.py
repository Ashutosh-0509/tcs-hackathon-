from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbDep, OptionalUser
from app.schemas.answer import AnswerDetail, AnswerSummary
from app.services import answer_query

router = APIRouter()


@router.get("/answers", response_model=list[AnswerSummary])
def list_answers(
    db: DbDep,
    user: OptionalUser,
    mine: bool = Query(False, description="Only answers created by the authenticated user"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AnswerSummary]:
    return answer_query.list_answers(
        db, actor_id=user.id if user else None, mine=mine, limit=limit, offset=offset
    )


@router.get("/answers/{answer_id}", response_model=AnswerDetail)
def get_answer(answer_id: uuid.UUID, db: DbDep) -> AnswerDetail:
    return answer_query.get_answer(db, answer_id)
