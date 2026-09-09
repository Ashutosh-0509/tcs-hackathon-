from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep, EngineDep, LLMDep, OptionalUser, PIIDep
from app.schemas.answer import AnswerRequest, AnswerResponse
from app.services.answer_service import AnswerService

router = APIRouter()


@router.post("/answer", response_model=AnswerResponse)
def generate_answer(
    payload: AnswerRequest,
    db: DbDep,
    llm: LLMDep,
    engine: EngineDep,
    pii: PIIDep,
    user: OptionalUser,
) -> AnswerResponse:
    """Mode A — TrustLens generates an answer from the supplied sources, then
    evaluates it. Auth is optional for the demo."""
    service = AnswerService(db=db, llm=llm, engine=engine, pii=pii)
    return service.generate_and_evaluate(
        question=payload.question,
        source_snippets=payload.source_snippets,
        include_explanation=payload.include_explanation,
        actor_id=user.id if user else None,
    )
