from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON as SA_JSON
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin, uuid_pk
from app.models.enums import ReliabilityLabel

if TYPE_CHECKING:
    from app.models.qa import Answer


class ReliabilityScore(Base, TimestampMixin):
    __tablename__ = "reliability_scores"

    id: Mapped[uuid.UUID] = uuid_pk()
    answer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("answers.id"), unique=True, nullable=False
    )
    evidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    uncertainty_score: Mapped[float] = mapped_column(Float, nullable=False)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(
        String(24), default=ReliabilityLabel.NEEDS_VERIFICATION, nullable=False
    )
    reasons: Mapped[list] = mapped_column(SA_JSON, default=list, nullable=False)
    weights: Mapped[dict] = mapped_column(SA_JSON, default=dict, nullable=False)
    thresholds: Mapped[dict] = mapped_column(SA_JSON, default=dict, nullable=False)

    answer: Mapped[Answer] = relationship(back_populates="reliability")
