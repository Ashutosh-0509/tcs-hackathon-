"""per-claim entailment provenance

Revision ID: 0003_claim_provenance
Revises: 0002_explanation_and_override
Create Date: 2026-09-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_claim_provenance"
down_revision: str | None = "0002_explanation_and_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "claims",
        sa.Column("support_source", sa.String(16), nullable=False, server_default="heuristic"),
    )
    op.add_column("claims", sa.Column("rationale", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "rationale")
    op.drop_column("claims", "support_source")
