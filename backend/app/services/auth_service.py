"""User registration + authentication."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AuthError, TrustLensError
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.models.enums import AuditAction, UserRole
from app.services import audit


def register_user(db: Session, email: str, password: str, role: UserRole = UserRole.USER) -> User:
    email = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise TrustLensError("Email already registered", status_code=409, code="email_taken")
    user = User(email=email, password_hash=hash_password(password), role=role.value)
    db.add(user)
    db.flush()
    audit.record(db, action=AuditAction.REGISTER, entity_type="user", entity_id=user.id,
                 actor_id=user.id, metadata={"role": user.role})
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> tuple[User, str]:
    email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    token = create_access_token(subject=str(user.id), role=user.role)
    audit.record(db, action=AuditAction.LOGIN, entity_type="user", entity_id=user.id,
                 actor_id=user.id, metadata={})
    db.commit()
    return user, token
