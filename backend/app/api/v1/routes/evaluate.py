from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep, EngineDep, LLMDep, OptionalUser, PIIDep
from app.schemas.answer import AnswerResponse, EvaluateRequest
from app.services.answer_service import AnswerService

router = APIRouter()


@router.post("/evaluate", response_model=AnswerResponse)
def evaluate_answer(
    payload: EvaluateRequest,
    db: DbDep,
    llm: LLMDep,
    engine: EngineDep,
    pii: PIIDep,
    user: OptionalUser,
) -> AnswerResponse:
    """Mode B — evaluate an answer produced by another AI system against the
    supplied evidence. This is the enterprise integration path."""
    service = AnswerService(db=db, llm=llm, engine=engine, pii=pii)
    return service.evaluate_external(
        question=payload.question,
        answer=payload.answer,
        evidence=payload.evidence,
        model=payload.model,
        include_explanation=payload.include_explanation,
        actor_id=user.id if user else None,
    )
