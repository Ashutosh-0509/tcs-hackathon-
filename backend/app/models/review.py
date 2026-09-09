from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import GUID, Base, TimestampMixin, uuid_pk
from app.models.enums import ReviewStatus

if TYPE_CHECKING:
    from app.models.qa import Answer


class Review(Base, TimestampMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = uuid_pk()
    answer_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("answers.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), default=ReviewStatus.PENDING, nullable=False)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Human override of the machine reliability label (nullable = not overridden).
    overridden_label: Mapped[str | None] = mapped_column(String(24), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(GUID(), ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    answer: Mapped[Answer] = relationship(back_populates="review")
