"""
Pytest configuration and shared fixtures.

Uses SQLite in-memory for speed; rate limiting disabled in TestingConfig.

KEY DESIGN DECISIONS
--------------------
* The `app` fixture is session-scoped: one in-memory DB for the entire run.
* `clean_tables` is function-scoped and runs after every test, deleting all
  non-badge rows in FK-safe order so each test starts clean.
* Helper functions (create_free_course, create_premium_course, make_admin)
  do NOT open a nested app_context.  They are always called from inside a
  test that already has an active context via the session-scoped `app` fixture.
"""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient


# ── App + DB fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def app() -> Flask:
    from stemquest import create_app

    flask_app = create_app("testing")

    ctx = flask_app.app_context()
    ctx.push()

    from stemquest.extensions import db
    db.create_all()
    _seed_badges()

    yield flask_app

    db.session.remove()
    db.drop_all()
    ctx.pop()


def _seed_badges() -> None:
    """Minimal badge seed required by the gamification service."""
    from stemquest.extensions import db
    from stemquest.models.gamification import Badge
    from stemquest.utils.helpers import new_id

    # slug is the canonical machine-readable field (not "criteria")
    badges = [
        dict(slug="signup",          title="Early Adopter",  description="", points_required=None),
        dict(slug="first_lesson",    title="First Steps",    description="", points_required=None),
        dict(slug="quiz_passes",     title="Quiz Whiz",      description="", points_required=None),
        dict(slug="perfect_score",   title="Perfectionist",  description="", points_required=None),
        dict(slug="streak_7",        title="Week Warrior",   description="", points_required=None),
        dict(slug="xp_100",          title="Century Club",   description="", points_required=100),
        dict(slug="xp_500",          title="High Achiever",  description="", points_required=500),
        dict(slug="course_complete", title="Graduate",       description="", points_required=None),
    ]
    for bd in badges:
        if not Badge.query.filter_by(slug=bd["slug"]).first():
            db.session.add(Badge(id=new_id(), **bd))
    db.session.commit()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_tables(app: Flask):
    """Delete all non-badge rows between tests to keep isolation."""
    from stemquest.extensions import db
    from stemquest.models.user         import User
    from stemquest.models.course       import Course
    from stemquest.models.module       import Module
    from stemquest.models.lesson       import Lesson
    from stemquest.models.enrollment   import Enrollment
    from stemquest.models.progress     import LessonProgress
    from stemquest.models.quiz         import Quiz, QuizQuestion, QuizOption, QuizAttempt
    from stemquest.models.gamification import PointsTransaction, UserBadge, UserStreak
    from stemquest.models.billing      import Purchase, PendingOrder, WebhookEvent

    yield  # run the test

    # Teardown in FK-safe reverse-dependency order
    for model in (
        WebhookEvent, PendingOrder, Purchase,
        UserStreak, UserBadge, PointsTransaction,
        QuizAttempt, QuizOption, QuizQuestion, Quiz,
        LessonProgress, Lesson, Module,
        Enrollment, Course, User,
    ):
        db.session.query(model).delete()
    db.session.commit()


# ── Shared helpers (called inside tests that already have an app context) ──────

def register_and_login(client: FlaskClient, email: str, name: str, password: str) -> None:
    """Register a student account and set the JWT cookie on the test client."""
    resp = client.post("/api/auth/register", json={"email": email, "name": name, "password": password})
    assert resp.status_code == 201, resp.json


def login_user(client: FlaskClient, email: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.json


def make_admin(email: str) -> None:
    """
    Promote an existing user to admin.
    Must be called while an app context is already active (it always is inside tests).
    """
    from stemquest.extensions import db
    from stemquest.models.user import User, UserRole

    u = User.query.filter_by(email=email).first()
    if u:
        u.role = UserRole.admin
        db.session.commit()


def create_free_course(admin_id: str) -> dict:
    """
    Create and publish a minimal free course with one module and one lesson.
    Returns {"course_id", "course_slug", "lesson_id", "module_id"}.

    Must be called while an app context is already active.
    """
    from stemquest.extensions import db
    from stemquest.models.course  import Course, Difficulty
    from stemquest.models.module  import Module
    from stemquest.models.lesson  import Lesson
    from stemquest.utils.helpers  import new_id, utcnow

    course = Course(
        id=new_id(), slug="test-free-course", title="Test Free Course",
        description="A free test course.", instructor_id=admin_id,
        is_premium=False, price=0, currency="USD", published=True,
        category="Test", difficulty=Difficulty.beginner, tags=[],
        total_lessons=1, estimated_hours=1,
        created_at=utcnow(), updated_at=utcnow(),
    )
    db.session.add(course)
    module = Module(
        id=new_id(), course_id=course.id, title="Module 1",
        description="", sort_order=1, created_at=utcnow(),
    )
    db.session.add(module)
    db.session.flush()
    lesson = Lesson(
        id=new_id(), module_id=module.id, course_id=course.id,
        title="Lesson 1", summary="", content_body="Test content.",
        difficulty_level=Difficulty.beginner, xp_reward=20, sort_order=1,
        published=True, created_at=utcnow(),
    )
    db.session.add(lesson)
    db.session.commit()
    return {
        "course_id":   course.id,
        "course_slug": course.slug,
        "lesson_id":   lesson.id,
        "module_id":   module.id,
    }


def create_premium_course(admin_id: str) -> dict:
    """
    Create and publish a minimal premium course with one module and one lesson.
    Returns {"course_id", "course_slug", "lesson_id", "module_id"}.

    Must be called while an app context is already active.
    """
    from stemquest.extensions import db
    from stemquest.models.course  import Course, Difficulty
    from stemquest.models.module  import Module
    from stemquest.models.lesson  import Lesson
    from stemquest.utils.helpers  import new_id, utcnow

    course = Course(
        id=new_id(), slug="test-premium-course", title="Test Premium Course",
        description="A premium test course.", instructor_id=admin_id,
        is_premium=True, price=29.99, currency="USD", published=True,
        category="Test", difficulty=Difficulty.intermediate, tags=[],
        total_lessons=1, estimated_hours=2,
        created_at=utcnow(), updated_at=utcnow(),
    )
    db.session.add(course)
    module = Module(
        id=new_id(), course_id=course.id, title="Module 1",
        description="", sort_order=1, created_at=utcnow(),
    )
    db.session.add(module)
    db.session.flush()
    lesson = Lesson(
        id=new_id(), module_id=module.id, course_id=course.id,
        title="Lesson 1", summary="", content_body="Test content.",
        difficulty_level=Difficulty.intermediate, xp_reward=30, sort_order=1,
        published=True, created_at=utcnow(),
    )
    db.session.add(lesson)
    db.session.commit()
    return {
        "course_id":   course.id,
        "course_slug": course.slug,
        "lesson_id":   lesson.id,
        "module_id":   module.id,
    }


def get_or_create_admin(email: str = "admin@fixture.test", name: str = "Fixture Admin") -> str:
    """
    Return the ID of an admin user, creating one if needed.
    Must be called while an app context is already active.
    """
    from stemquest.extensions import db, bcrypt
    from stemquest.models.user import User, UserRole
    from stemquest.utils.helpers import new_id, make_initials, utcnow

    u = User.query.filter_by(email=email).first()
    if u:
        if u.role != UserRole.admin:
            u.role = UserRole.admin
            db.session.commit()
        return u.id

    pw = bcrypt.generate_password_hash("adminpass123").decode("utf-8")
    u = User(
        id=new_id(), email=email, name=name, password_hash=pw,
        role=UserRole.admin, avatar=make_initials(name),
        is_active=True, email_verified=True,
        created_at=utcnow(), updated_at=utcnow(),
    )
    db.session.add(u)
    db.session.commit()
    return u.id
