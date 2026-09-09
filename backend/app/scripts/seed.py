"""Seed demo users and demo cases so the product is runnable without manual setup.

    python -m app.scripts.seed          # idempotent
    python -m app.scripts.seed --reset  # wipe answers/questions/reviews first

Demo accounts (password: trustlens):
    user@trustlens.dev    USER
    editor@trustlens.dev  EDITOR
    admin@trustlens.dev   ADMIN
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func, select

from app.core.request_context import new_request_id, set_request_id
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import (
    Answer,
    AuditLog,
    Claim,
    Evidence,
    Question,
    ReliabilityScore,
    Review,
    User,
)
from app.models.enums import UserRole
from app.services.answer_service import AnswerService
from app.services.auth_service import register_user
from app.services.embeddings import get_embedding_service
from app.services.evaluation import EvaluationEngine
from app.services.llm import get_llm_provider
from app.services.pii import get_pii_service

DEMO_PASSWORD = "trustlens"  # noqa: S105 - demo only
DEMO_USERS = [
    ("user@trustlens.dev", UserRole.USER),
    ("editor@trustlens.dev", UserRole.EDITOR),
    ("admin@trustlens.dev", UserRole.ADMIN),
]
_CASES_PATH = Path(__file__).resolve().parents[3] / "data" / "demo_cases.json"


def _ensure_schema() -> None:
    Base.metadata.create_all(engine)


def _seed_users(db) -> dict[str, User]:
    users: dict[str, User] = {}
    for email, role in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            users[role.value] = existing
            continue
        users[role.value] = register_user(db, email, DEMO_PASSWORD, role)
        print(f"  + user {email} ({role.value})")
    return users


def _reset(db) -> None:
    for model in (AuditLog, Review, ReliabilityScore, Claim, Evidence, Answer, Question):
        db.execute(delete(model))
    db.commit()
    print("  reset: cleared answers / questions / claims / reviews / audit")


def _seed_cases(db, actor_id) -> None:
    if db.scalar(select(func.count()).select_from(Answer)):
        print("  cases already present — skipping (use --reset to reseed)")
        return
    cases = json.loads(_CASES_PATH.read_text())
    service = AnswerService(
        db=db,
        llm=get_llm_provider(),
        engine=EvaluationEngine(embedding_service=get_embedding_service()),
        pii=get_pii_service(),
    )
    print(f"  running {len(cases)} demo cases through the pipeline "
          f"(embeddings: {get_embedding_service().backend})")
    for case in cases:
        set_request_id(new_request_id())
        resp = service.evaluate_external(
            question=case["question"],
            answer=case["answer"],
            evidence=case.get("evidence", []),
            model="demo-seed",
            include_explanation=True,
            actor_id=actor_id,
        )
        got = resp.reliability.label.value
        exp = case.get("expected_label", "-")
        flag = "ok " if got == exp else "~! "
        print(f"    {flag}{case['name']:30} score={resp.reliability.final_score:3}  "
              f"got={got:18} expected={exp}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed TrustLens demo data")
    parser.add_argument("--reset", action="store_true", help="wipe demo answers first")
    parser.add_argument(
        "--users-only", action="store_true", help="create the demo accounts, no example cases"
    )
    args = parser.parse_args()

    _ensure_schema()
    set_request_id(new_request_id())
    with SessionLocal() as db:
        print("seeding users…")
        users = _seed_users(db)
        if args.reset:
            _reset(db)
        if args.users_only:
            print("done (users only).")
            return 0
        print("seeding demo cases…")
        _seed_cases(db, actor_id=users["ADMIN"].id)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
