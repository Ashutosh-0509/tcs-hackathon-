"""retrieved-evidence source (title + url)

Revision ID: 0004_evidence_source
Revises: 0003_claim_provenance
Create Date: 2026-09-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_evidence_source"
down_revision: str | None = "0003_claim_provenance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("title", sa.String(400), nullable=True))
    op.add_column("evidence", sa.Column("url", sa.String(1000), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "url")
    op.drop_column("evidence", "title")
