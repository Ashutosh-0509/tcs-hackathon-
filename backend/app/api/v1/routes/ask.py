from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbDep, EngineDep, LLMDep, OptionalUser, PIIDep
from app.schemas.answer import AnswerResponse, AskRequest
from app.services.answer_service import AnswerService

router = APIRouter()


@router.post("/ask", response_model=AnswerResponse)
def ask(
    payload: AskRequest,
    db: DbDep,
    llm: LLMDep,
    engine: EngineDep,
    pii: PIIDep,
    user: OptionalUser,
) -> AnswerResponse:
    """Primary flow — the user asks a question. TrustLens gets the model's answer,
    retrieves real sources, and verifies the answer against them."""
    service = AnswerService(db=db, llm=llm, engine=engine, pii=pii)
    return service.ask(
        question=payload.question,
        include_explanation=payload.include_explanation,
        actor_id=user.id if user else None,
    )
