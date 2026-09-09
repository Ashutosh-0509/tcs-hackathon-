"""Password hashing (Argon2, bcrypt fallback) and JWT encode/decode."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# Argon2 preferred; bcrypt kept as a verify-only fallback for older hashes.
_pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
