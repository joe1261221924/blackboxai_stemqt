"""
Gamification tests.

Covers:
  - /gamification/me summary
  - Leaderboard (admin exclusion, limit param)
  - /gamification/my-badges (signup badge auto-awarded)
  - Admin grant-points (success, student forbidden, unauthenticated)
  - Admin-only route protection
  - Role update validation (teacher role rejected)

FIELD NAME CONTRACT (must match SQLAlchemy models exactly)
----------------------------------------------------------
UserBadge.to_dict() : awarded_at   (NOT earned_at)
Badge.to_dict()     : title        (NOT name)
                      slug, description, points_required
                      (no icon / category / color fields)
"""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from tests.conftest import make_admin


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_login(client: FlaskClient, suffix: str = "") -> str:
    email = f"gami{suffix}@test.com"
    client.post("/api/auth/register", json={
        "email": email, "name": f"GamiUser {suffix}", "password": "securepass123",
    })
    client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
    return email


def _setup_admin(client: FlaskClient, suffix: str = "a") -> str:
    """Register a user, promote to admin, log in — return email."""
    email = f"admin_{suffix}@admintest.com"
    client.post("/api/auth/register", json={
        "email": email, "name": f"Admin {suffix}", "password": "securepass123",
    })
    make_admin(email)
    client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
    return email


# ── Summary ────────────────────────────────────────────────────────────────────

def test_gamification_me_returns_summary(client: FlaskClient):
    _register_login(client, "sum1")
    resp = client.get("/api/gamification/me")
    assert resp.status_code == 200
    data = resp.json
    for key in ("total_xp", "rank", "current_streak", "longest_streak",
                "badge_count", "badges", "enrollments"):
        assert key in data, f"Missing key: {key}"
    # Signup bonus (10 XP) should be present
    assert data["total_xp"] >= 10


def test_gamification_me_requires_auth(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.get("/api/gamification/me")
    assert resp.status_code == 401


def test_gamification_me_rank_is_positive(client: FlaskClient):
    _register_login(client, "rank1")
    resp = client.get("/api/gamification/me")
    assert resp.json["rank"] >= 1


# ── Leaderboard ────────────────────────────────────────────────────────────────

def test_leaderboard_returns_list(client: FlaskClient):
    _register_login(client, "lb1")
    resp = client.get("/api/gamification/leaderboard")
    assert resp.status_code == 200
    body = resp.json
    assert "leaderboard" in body
    assert isinstance(body["leaderboard"], list)
    assert "count" in body


def test_leaderboard_excludes_admins(client: FlaskClient):
    admin_email = _setup_admin(client, "lbex")
    resp = client.get("/api/gamification/leaderboard")
    assert resp.status_code == 200
    names = [entry["name"] for entry in resp.json["leaderboard"]]
    assert "Admin lbex" not in names


def test_leaderboard_requires_auth(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.get("/api/gamification/leaderboard")
    assert resp.status_code == 401


def test_leaderboard_limit_param_respected(client: FlaskClient):
    _register_login(client, "lb2")
    resp = client.get("/api/gamification/leaderboard?limit=1")
    assert resp.status_code == 200
    assert len(resp.json["leaderboard"]) <= 1


def test_leaderboard_entries_have_required_fields(client: FlaskClient):
    _register_login(client, "lb3")
    resp = client.get("/api/gamification/leaderboard")
    assert resp.status_code == 200
    for entry in resp.json["leaderboard"]:
        for field in ("rank", "user_id", "name", "avatar", "total_xp", "badge_count", "streak"):
            assert field in entry, f"Missing field '{field}' in leaderboard entry"


# ── My Badges ──────────────────────────────────────────────────────────────────

def test_my_badges_includes_signup_badge(client: FlaskClient):
    _register_login(client, "badge1")
    resp = client.get("/api/gamification/my-badges")
    assert resp.status_code == 200
    body = resp.json
    assert "badges" in body
    # Badge.to_dict() uses "title" (not "name")
    badge_titles = [b["badge"]["title"] for b in body["badges"]]
    assert "Early Adopter" in badge_titles


def test_my_badges_requires_auth(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.get("/api/gamification/my-badges")
    assert resp.status_code == 401


def test_my_badges_response_structure(client: FlaskClient):
    _register_login(client, "badge2")
    resp = client.get("/api/gamification/my-badges")
    assert resp.status_code == 200
    for ub in resp.json["badges"]:
        # UserBadge.to_dict() fields
        assert "badge_id"   in ub
        assert "awarded_at" in ub    # canonical field (not earned_at)
        assert "badge"      in ub
        badge = ub["badge"]
        # Badge.to_dict() fields — only what the model actually serialises
        for field in ("id", "slug", "title", "description", "points_required"):
            assert field in badge, f"Missing badge field: {field}"


# ── Admin grant-points ─────────────────────────────────────────────────────────

def test_admin_grant_points_success(client: FlaskClient, app: Flask):
    student_email = _register_login(client, "gp1")
    me_resp       = client.get("/api/auth/me")
    student_id    = me_resp.json["user"]["id"]

    _setup_admin(client, "gpadmin")

    resp = client.post("/api/gamification/grant-points", json={
        "user_id": student_id, "points": 50, "reason": "Bonus XP",
    })
    assert resp.status_code == 200
    assert "Awarded 50 XP" in resp.json["message"]


def test_admin_grant_points_forbidden_for_student(client: FlaskClient, app: Flask):
    _register_login(client, "gp2")
    me_resp    = client.get("/api/auth/me")
    student_id = me_resp.json["user"]["id"]

    resp = client.post("/api/gamification/grant-points", json={
        "user_id": student_id, "points": 50, "reason": "Exploit attempt",
    })
    assert resp.status_code == 403


def test_admin_grant_points_requires_auth(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.post("/api/gamification/grant-points", json={
        "user_id": "some-id", "points": 50, "reason": "Test",
    })
    assert resp.status_code == 401


def test_admin_grant_points_validates_positive_integer(client: FlaskClient, app: Flask):
    _setup_admin(client, "gpval")
    resp = client.post("/api/gamification/grant-points", json={
        "user_id": "some-id", "points": -10, "reason": "Negative",
    })
    assert resp.status_code == 422


# ── Admin Users + Role Management ─────────────────────────────────────────────

def test_admin_users_list_requires_admin(client: FlaskClient):
    _register_login(client, "userprot1")
    resp = client.get("/api/admin/users")
    assert resp.status_code == 403


def test_admin_users_list_accessible_by_admin(client: FlaskClient):
    _setup_admin(client, "userlist")
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    body = resp.json
    assert "items" in body
    assert "total" in body
    assert "page"  in body


def test_admin_metrics_requires_admin(client: FlaskClient):
    _register_login(client, "metprot")
    resp = client.get("/api/admin/metrics")
    assert resp.status_code == 403


def test_admin_metrics_accessible_by_admin(client: FlaskClient):
    _setup_admin(client, "metadmin")
    resp = client.get("/api/admin/metrics")
    assert resp.status_code == 200
    body = resp.json
    for key in ("users", "courses", "enrollments", "revenue", "quizzes"):
        assert key in body, f"Missing metrics key: {key}"
    assert "total"    in body["users"]
    assert "students" in body["users"]
    assert "admins"   in body["users"]


def test_admin_analytics_accessible_by_admin(client: FlaskClient):
    _setup_admin(client, "analytadmin")
    resp = client.get("/api/admin/analytics")
    assert resp.status_code == 200
    assert "courses" in resp.json


def test_admin_role_update_to_admin_works(client: FlaskClient, app: Flask):
    """A student can be promoted to admin by an existing admin."""
    target_client = app.test_client()
    target_client.post("/api/auth/register", json={
        "email": "target@roletest.com", "name": "Target", "password": "securepass123",
    })
    me        = target_client.get("/api/auth/me")
    target_id = me.json["user"]["id"]

    _setup_admin(client, "roleadmin1")
    resp = client.put(f"/api/admin/users/{target_id}/role", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json["user"]["role"] == "admin"


def test_admin_role_update_to_student_works(client: FlaskClient, app: Flask):
    target_client = app.test_client()
    target_client.post("/api/auth/register", json={
        "email": "target2@roletest.com", "name": "Target2", "password": "securepass123",
    })
    me        = target_client.get("/api/auth/me")
    target_id = me.json["user"]["id"]

    _setup_admin(client, "roleadmin2")
    # First promote
    client.put(f"/api/admin/users/{target_id}/role", json={"role": "admin"})
    # Then demote
    resp = client.put(f"/api/admin/users/{target_id}/role", json={"role": "student"})
    assert resp.status_code == 200
    assert resp.json["user"]["role"] == "student"


def test_admin_role_update_rejects_teacher(client: FlaskClient, app: Flask):
    """
    There is no teacher role. Setting role=teacher must return 422.
    This is a critical guard — the system has only student and admin.
    """
    target_client = app.test_client()
    target_client.post("/api/auth/register", json={
        "email": "target3@roletest.com", "name": "Target3", "password": "securepass123",
    })
    me        = target_client.get("/api/auth/me")
    target_id = me.json["user"]["id"]

    _setup_admin(client, "roleadmin3")
    resp = client.put(f"/api/admin/users/{target_id}/role", json={"role": "teacher"})
    assert resp.status_code == 422
    assert "role" in str(resp.json).lower()


def test_admin_grant_enrollment(client: FlaskClient, app: Flask):
    """Admin can grant enrollment in a premium course to any student."""
    from tests.conftest import get_or_create_admin, create_premium_course

    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)

    # Register a student
    target_client = app.test_client()
    target_client.post("/api/auth/register", json={
        "email": "grantee@test.com", "name": "Grantee", "password": "securepass123",
    })
    me_resp    = target_client.get("/api/auth/me")
    student_id = me_resp.json["user"]["id"]

    # Log in as admin and grant enrollment
    _setup_admin(client, "grantenroll")
    resp = client.post(f"/api/admin/users/{student_id}/enroll", json={
        "course_id": data["course_id"],
    })
    assert resp.status_code == 201
    assert resp.json["enrollment"]["user_id"] == student_id
