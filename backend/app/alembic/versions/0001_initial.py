"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from app.db.base import GUID

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="USER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "questions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("request_id", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("mode", sa.String(16), nullable=False, server_default="EVALUATE"),
        sa.Column("created_by", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_questions_request_id", "questions", ["request_id"])

    op.create_table(
        "evidence",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("question_id", GUID(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "answers",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("question_id", GUID(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False, server_default="EXTERNAL"),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("perplexity", sa.Float(), nullable=True),
        sa.Column("perplexity_available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "claims",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("answer_id", GUID(), sa.ForeignKey("answers.id"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_critical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supported", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("semantic_support", sa.Float(), nullable=False, server_default="0"),
        sa.Column("evidence_support", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contradicted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("best_evidence_ordinal", sa.Integer(), nullable=True),
    )

    op.create_table(
        "reliability_scores",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("answer_id", GUID(), sa.ForeignKey("answers.id"), nullable=False, unique=True),
        sa.Column("evidence_score", sa.Float(), nullable=False),
        sa.Column("semantic_score", sa.Float(), nullable=False),
        sa.Column("uncertainty_score", sa.Float(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(24), nullable=False, server_default="NEEDS_VERIFICATION"),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "reviews",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("answer_id", GUID(), sa.ForeignKey("answers.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("request_id", sa.String(32), nullable=False),
        sa.Column("actor_id", GUID(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", GUID(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reviews")
    op.drop_table("reliability_scores")
    op.drop_table("claims")
    op.drop_table("answers")
    op.drop_table("evidence")
    op.drop_table("questions")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
