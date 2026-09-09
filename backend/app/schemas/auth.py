from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    # role is accepted only for the demo bootstrap; in production this is admin-gated.
    role: UserRole = UserRole.USER


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
