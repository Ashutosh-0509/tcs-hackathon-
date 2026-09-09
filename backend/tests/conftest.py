from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("LLM_PROVIDER", "stub")
os.environ.setdefault("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
# Keep the test run hermetic: never block on a HuggingFace download. If the
# sentence-transformers model is already cached locally it is used; otherwise the
# EmbeddingService falls back to its deterministic hashed vectors.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import app.models  # noqa: F401  (register tables)
import pytest
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Shared in-memory SQLite across connections for the whole test session.
_engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture()
def db():
    session = _TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    def _override_get_db():
        session = _TestSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def register(client):
    def _register(email: str, password: str = "password123", role: str = "USER") -> str:
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "role": role},
        )
        assert resp.status_code == 201, resp.text
        return resp.json()["access_token"]

    return _register
