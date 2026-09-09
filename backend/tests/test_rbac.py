"""RBAC is enforced on the backend; body-supplied role is ignored (TECH_STACK.md §38, §78)."""
from __future__ import annotations


def test_user_cannot_access_review_queue(client, register):
    token = register("user@example.com", role="USER")
    resp = client.get("/api/v1/reviews", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_user_cannot_access_audit(client, register):
    token = register("user2@example.com", role="USER")
    resp = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_editor_can_access_review_queue(client, register):
    token = register("editor@example.com", role="EDITOR")
    resp = client.get("/api/v1/reviews", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_can_access_audit(client, register):
    token = register("admin@example.com", role="ADMIN")
    resp = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_missing_token_is_401(client):
    assert client.get("/api/v1/reviews").status_code == 401


def test_garbage_token_is_401(client):
    resp = client.get("/api/v1/reviews", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
