from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin, uuid_pk
from app.models.enums import AnswerSource, QuestionMode


class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = uuid_pk()
    request_id: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)  # redacted
    mode: Mapped[str] = mapped_column(String(16), default=QuestionMode.EVALUATE, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )

    answers: Mapped[list[Answer]] = relationship(back_populates="question", cascade="all, delete-orphan")
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="Evidence.ordinal"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("questions.id"), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False)  # redacted
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # populated when the snippet was retrieved (not user-supplied)
    title: Mapped[str | None] = mapped_column(String(400), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    question: Mapped[Question] = relationship(back_populates="evidence")


class Answer(Base, TimestampMixin):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = uuid_pk()
    question_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("questions.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)  # redacted
    source: Mapped[str] = mapped_column(String(16), default=AnswerSource.EXTERNAL, nullable=False)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    perplexity: Mapped[float | None] = mapped_column(Float, nullable=True)
    perplexity_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped[Question] = relationship(back_populates="answers")
    claims: Mapped[list[Claim]] = relationship(back_populates="answer", cascade="all, delete-orphan")
    reliability: Mapped[ReliabilityScore | None] = relationship(
        back_populates="answer", cascade="all, delete-orphan", uselist=False
    )
    review: Mapped[Review | None] = relationship(
        back_populates="answer", cascade="all, delete-orphan", uselist=False
    )


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = uuid_pk()
    answer_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("answers.id"), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    semantic_support: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evidence_support: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    contradicted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    best_evidence_ordinal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    support_source: Mapped[str] = mapped_column(String(16), default="heuristic", nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    answer: Mapped[Answer] = relationship(back_populates="claims")


# late imports for type checkers / relationship strings
from app.models.reliability import ReliabilityScore  # noqa: E402
from app.models.review import Review  # noqa: E402
