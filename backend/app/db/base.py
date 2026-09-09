"""Declarative base + shared column types.

Uses a portable GUID type so the same models run on PostgreSQL (native UUID)
and on SQLite (CHAR(32)) for tests.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import CHAR, DateTime, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """Platform-independent UUID: PG UUID, otherwise CHAR(32) hex."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "postgresql":
            return value
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


def uuid_pk():
    """Usage:  id: Mapped[uuid.UUID] = uuid_pk()"""
    return mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
