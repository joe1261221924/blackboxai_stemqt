"""
Auth endpoint tests.

Covers:
  - Registration always produces student role
  - Duplicate email / validation errors
  - Login success and failure
  - /me with gamification summary
  - Logout clears cookie
"""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register(client: FlaskClient, email: str, name: str = "Test User",
              password: str = "securepass123") -> dict:
    resp = client.post("/api/auth/register", json={
        "email": email, "name": name, "password": password,
    })
    return resp


def _login(client: FlaskClient, email: str, password: str = "securepass123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ── Registration ───────────────────────────────────────────────────────────────

def test_register_returns_201(client: FlaskClient):
    resp = _register(client, "newuser@test.com")
    assert resp.status_code == 201
    assert resp.json["user"]["email"] == "newuser@test.com"


def test_register_always_creates_student(client: FlaskClient):
    """role=admin in the request body must be ignored."""
    resp = client.post("/api/auth/register", json={
        "email": "hacker@test.com",
        "name":  "Hacker",
        "password": "securepass123",
        "role": "admin",          # attempted privilege escalation
    })
    assert resp.status_code == 201
    assert resp.json["user"]["role"] == "student"


def test_register_sets_jwt_cookie(client: FlaskClient):
    _register(client, "cookie@test.com")
    cookie_names = [c.name for c in client.cookie_jar]
    assert "sq_access_token" in cookie_names


def test_register_duplicate_email_returns_409(client: FlaskClient):
    payload = {"email": "dup@test.com", "name": "Dup", "password": "securepass123"}
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_weak_password_returns_422(client: FlaskClient):
    resp = _register(client, "weak@test.com", password="short")
    assert resp.status_code == 422
    assert "password" in resp.json.get("detail", {})


def test_register_missing_name_returns_422(client: FlaskClient):
    resp = client.post("/api/auth/register", json={
        "email": "noname@test.com", "password": "securepass123",
    })
    assert resp.status_code == 422
    assert "name" in resp.json.get("detail", {})


def test_register_invalid_email_returns_422(client: FlaskClient):
    resp = _register(client, "notanemail")
    assert resp.status_code == 422
    assert "email" in resp.json.get("detail", {})


def test_register_awards_signup_xp(client: FlaskClient):
    """Registration should trigger the signup bonus; /me reflects it."""
    _register(client, "xptest@test.com")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.json["gamification"]["total_xp"] >= 10


# ── Login ──────────────────────────────────────────────────────────────────────

def test_login_success_sets_cookie(client: FlaskClient):
    _register(client, "login@test.com")
    # Use a fresh client so the registration cookie is not present
    fresh = client.application.test_client()
    resp  = _login(fresh, "login@test.com")
    assert resp.status_code == 200
    assert resp.json["user"]["email"] == "login@test.com"
    assert "sq_access_token" in [c.name for c in fresh.cookie_jar]


def test_login_wrong_password_returns_401(client: FlaskClient):
    _register(client, "login2@test.com")
    resp = _login(client, "login2@test.com", password="wrongpassword")
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client: FlaskClient):
    resp = _login(client, "ghost@test.com")
    assert resp.status_code == 401


def test_login_missing_fields_returns_422(client: FlaskClient):
    resp = client.post("/api/auth/login", json={"email": "a@b.com"})
    assert resp.status_code == 422


# ── /me ───────────────────────────────────────────────────────────────────────

def test_me_returns_user_data(client: FlaskClient):
    _register(client, "me@test.com", name="Me User")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    data = resp.json
    assert data["user"]["email"] == "me@test.com"
    assert data["user"]["name"]  == "Me User"


def test_me_includes_gamification_summary_for_student(client: FlaskClient):
    _register(client, "gami@test.com")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    g = resp.json["gamification"]
    assert g is not None
    for key in ("total_xp", "rank", "current_streak", "badges", "enrollments"):
        assert key in g, f"Missing key: {key}"


def test_me_returns_401_without_token(client: FlaskClient):
    # fresh client has no cookies
    fresh = client.application.test_client()
    resp  = fresh.get("/api/auth/me")
    assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

def test_logout_clears_cookie_and_invalidates_session(client: FlaskClient):
    _register(client, "logout@test.com")
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    # After logout /me must return 401
    resp2 = client.get("/api/auth/me")
    assert resp2.status_code == 401


def test_logout_without_token_returns_401(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.post("/api/auth/logout")
    assert resp.status_code == 401
