"""FastAPI dependencies: DB session, current user, RBAC.

user_id / role ALWAYS come from the verified JWT here — never from the request
body (TECH_STACK.md §78).
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AuthError, ForbiddenError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole, role_at_least
from app.services.embeddings import get_embedding_service
from app.services.evaluation import EvaluationEngine
from app.services.llm import get_llm_provider
from app.services.pii import get_pii_service

DbDep = Annotated[Session, Depends(get_db)]


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = _bearer_token(authorization)
    if not token:
        raise AuthError("Missing bearer token")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise AuthError("Invalid or expired token")
    try:
        user = db.get(User, uuid.UUID(str(payload["sub"])))
    except ValueError:
        user = None
    if not user:
        raise AuthError("User no longer exists")
    return user


def get_optional_user(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> User | None:
    if not _bearer_token(authorization):
        return None
    try:
        return get_current_user(db, authorization)
    except AuthError:
        return None


def require_role(minimum: UserRole):
    def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not role_at_least(user.role, minimum):
            raise ForbiddenError(f"Requires {minimum} role or higher")
        return user

    return _dep


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
EditorUser = Annotated[User, Depends(require_role(UserRole.EDITOR))]
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


# ---- service providers ----
def get_evaluation_engine() -> EvaluationEngine:
    return EvaluationEngine(embedding_service=get_embedding_service())


LLMDep = Annotated[object, Depends(get_llm_provider)]
EngineDep = Annotated[EvaluationEngine, Depends(get_evaluation_engine)]
PIIDep = Annotated[object, Depends(get_pii_service)]
