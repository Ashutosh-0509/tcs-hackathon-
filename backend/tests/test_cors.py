from __future__ import annotations

import app.main as main
import pytest
from app.core.config import Settings
from fastapi.testclient import TestClient

PREFLIGHT = {"Access-Control-Request-Method": "POST"}


@pytest.fixture()
def cors_client(monkeypatch):
    """A fresh app whose CORS is an explicit origin plus a preview-URL regex."""
    test_settings = Settings(
        cors_allow_origins="https://tcs-hackathon.vercel.app",
        cors_allow_origin_regex=r"https://tcs-hackathon(-[a-z0-9-]+)?\.vercel\.app",
    )
    monkeypatch.setattr(main, "settings", test_settings)
    return TestClient(main.create_app())


def test_preflight_allows_listed_origin(cors_client):
    resp = cors_client.options(
        "/api/v1/evaluate",
        headers={"Origin": "https://tcs-hackathon.vercel.app", **PREFLIGHT},
    )
    assert resp.status_code == 200
    assert (
        resp.headers["access-control-allow-origin"]
        == "https://tcs-hackathon.vercel.app"
    )


def test_preflight_allows_regex_origin(cors_client):
    origin = "https://tcs-hackathon-git-main-dhruvghanchi.vercel.app"
    resp = cors_client.options(
        "/api/v1/evaluate", headers={"Origin": origin, **PREFLIGHT}
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == origin


def test_preflight_rejects_unknown_origin(cors_client):
    resp = cors_client.options(
        "/api/v1/evaluate",
        headers={"Origin": "https://not-trustlens.example.net", **PREFLIGHT},
    )
    assert resp.status_code == 400
