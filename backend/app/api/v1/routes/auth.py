from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbDep
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: DbDep) -> TokenResponse:
    user = auth_service.register_user(db, payload.email, payload.password, payload.role)
    _, token = auth_service.authenticate(db, payload.email, payload.password)
    return TokenResponse(access_token=token, role=user.role)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbDep) -> TokenResponse:
    user, token = auth_service.authenticate(db, payload.email, payload.password)
    return TokenResponse(access_token=token, role=user.role)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserOut:
    return UserOut(id=str(user.id), email=user.email, role=user.role)
