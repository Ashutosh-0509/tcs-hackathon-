"""Enum values shared by models and schemas. Stored as plain strings in the DB."""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "USER"
    EDITOR = "EDITOR"
    ADMIN = "ADMIN"


class QuestionMode(StrEnum):
    ASK = "ASK"  # question only; TrustLens answers + retrieves sources + verifies
    GENERATE = "GENERATE"  # user supplies sources; TrustLens answers from them
    EVALUATE = "EVALUATE"  # user supplies answer + evidence; TrustLens scores it


class AnswerSource(StrEnum):
    TRUSTLENS_LLM = "TRUSTLENS_LLM"
    EXTERNAL = "EXTERNAL"


class ReliabilityLabel(StrEnum):
    CERTAIN = "CERTAIN"
    UNCERTAIN = "UNCERTAIN"
    NEEDS_VERIFICATION = "NEEDS_VERIFICATION"


class ReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


class AuditAction(StrEnum):
    LOGIN = "LOGIN"
    REGISTER = "REGISTER"
    ANSWER_GENERATED = "ANSWER_GENERATED"
    ANSWER_EVALUATED = "ANSWER_EVALUATED"
    REVIEW_DECIDED = "REVIEW_DECIDED"


_ROLE_RANK = {UserRole.USER: 1, UserRole.EDITOR: 2, UserRole.ADMIN: 3}


def role_at_least(role: str, minimum: str) -> bool:
    return _ROLE_RANK.get(UserRole(role), 0) >= _ROLE_RANK.get(UserRole(minimum), 99)
