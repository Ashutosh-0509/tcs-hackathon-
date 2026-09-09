"""persist answer explanation + reviewer label override

Revision ID: 0002_explanation_and_override
Revises: 0001_initial
Create Date: 2026-09-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_explanation_and_override"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("answers", sa.Column("explanation", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("overridden_label", sa.String(24), nullable=True))


def downgrade() -> None:
    op.drop_column("reviews", "overridden_label")
    op.drop_column("answers", "explanation")
