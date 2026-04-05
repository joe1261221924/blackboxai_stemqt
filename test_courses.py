"""
Course, lesson, and quiz tests.

Covers:
  - Public course catalog
  - Free course access and enrollment
  - Premium course blocked without purchase / accessible after purchase
  - Lesson completion (XP, idempotency)
  - Quiz submission (pass, fail, auth guard)
  - Admin content creation (course -> module -> lesson -> quiz)

FIELD NAME CONTRACT (must match SQLAlchemy models exactly)
----------------------------------------------------------
Course       : is_premium, published          (NOT is_free / is_published)
Lesson       : content_body, difficulty_level, sort_order  (NOT content / difficulty / order)
QuizQuestion : prompt, sort_order              (NOT text / order)
QuizOption   : option_text, sort_order         (NOT text / order)
Purchase     : provider_payment_id             (NOT paypal_order_id)
"""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from tests.conftest import (
    get_or_create_admin,
    create_free_course,
    create_premium_course,
)


# ── Test helpers ───────────────────────────────────────────────────────────────

def _register_login(client: FlaskClient, suffix: str = "") -> str:
    """Register a fresh student and return their email."""
    email = f"student{suffix}@test.com"
    client.post("/api/auth/register", json={
        "email": email, "name": f"Student {suffix}", "password": "securepass123",
    })
    client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
    return email


def _create_quiz_lesson(app: Flask, course_id: str, module_id: str) -> dict:
    """
    Create an extra lesson + quiz inside an existing course/module.

    Uses canonical model field names:
      Lesson       : content_body, difficulty_level, sort_order
      QuizQuestion : prompt, sort_order
      QuizOption   : option_text, sort_order
    """
    from stemquest.extensions import db
    from stemquest.models.lesson import Lesson
    from stemquest.models.course import Difficulty
    from stemquest.models.quiz import Quiz, QuizQuestion, QuizOption
    from stemquest.utils.helpers import new_id, utcnow

    lesson = Lesson(
        id=new_id(),
        module_id=module_id,
        course_id=course_id,
        title="Quiz Lesson",
        summary="",
        content_body="Content.",          # canonical: content_body (not content)
        difficulty_level=Difficulty.beginner,  # canonical: difficulty_level (not difficulty)
        xp_reward=20,
        sort_order=99,                    # canonical: sort_order (not order)
        published=True,
        created_at=utcnow(),
    )
    db.session.add(lesson)
    db.session.flush()

    quiz = Quiz(
        id=new_id(),
        lesson_id=lesson.id,
        title="Test Quiz",
        passing_score=70,
        xp_reward=30,
        created_at=utcnow(),
    )
    db.session.add(quiz)
    db.session.flush()

    q = QuizQuestion(
        id=new_id(),
        quiz_id=quiz.id,
        prompt="1 + 1 = ?",              # canonical: prompt (not text)
        sort_order=1,                     # canonical: sort_order (not order)
        created_at=utcnow(),
    )
    db.session.add(q)
    db.session.flush()

    opt_correct = QuizOption(
        id=new_id(),
        question_id=q.id,
        option_text="2",                  # canonical: option_text (not text)
        is_correct=True,
        sort_order=1,                     # canonical: sort_order (not order)
        created_at=utcnow(),
    )
    opt_wrong = QuizOption(
        id=new_id(),
        question_id=q.id,
        option_text="3",                  # canonical: option_text (not text)
        is_correct=False,
        sort_order=2,                     # canonical: sort_order (not order)
        created_at=utcnow(),
    )
    db.session.add_all([opt_correct, opt_wrong])
    db.session.commit()

    return {
        "lesson_id":      lesson.id,
        "quiz_id":        quiz.id,
        "question_id":    q.id,
        "correct_opt_id": opt_correct.id,
        "wrong_opt_id":   opt_wrong.id,
    }


# ── Course catalog ─────────────────────────────────────────────────────────────

def test_course_list_is_public(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_free_course(admin_id)
    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert isinstance(resp.json["courses"], list)
    assert any(c["slug"] == "test-free-course" for c in resp.json["courses"])


def test_course_list_excludes_unpublished(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    from stemquest.extensions import db
    from stemquest.models.course import Course, Difficulty
    from stemquest.utils.helpers import new_id, utcnow

    c = Course(
        id=new_id(),
        slug="hidden-course",
        title="Hidden",
        description=".",
        instructor_id=admin_id,
        is_premium=False,           # canonical: is_premium (not is_free)
        price=None,
        currency="USD",
        published=False,            # canonical: published (not is_published)
        category="Test",
        difficulty=Difficulty.beginner,
        tags=[],
        total_lessons=0,
        estimated_hours=0,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.session.add(c)
    db.session.commit()

    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert all(course["slug"] != "hidden-course" for course in resp.json["courses"])


def test_course_detail_is_public(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_free_course(admin_id)
    resp = client.get("/api/courses/test-free-course")
    assert resp.status_code == 200
    assert resp.json["course"]["slug"] == "test-free-course"
    assert "modules" in resp.json["course"]


def test_course_detail_404_for_unknown_slug(client: FlaskClient):
    resp = client.get("/api/courses/does-not-exist")
    assert resp.status_code == 404


# ── Free course enrollment ─────────────────────────────────────────────────────

def test_free_course_enroll_success(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_free_course(admin_id)
    _register_login(client, "free1")
    resp = client.post("/api/courses/test-free-course/enroll")
    assert resp.status_code == 201
    assert resp.json["enrollment"]["course_id"] is not None


def test_free_course_enroll_requires_auth(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_free_course(admin_id)
    fresh = client.application.test_client()
    resp  = fresh.post("/api/courses/test-free-course/enroll")
    assert resp.status_code == 401


def test_free_course_enroll_idempotent_returns_409(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_free_course(admin_id)
    _register_login(client, "free2")
    client.post("/api/courses/test-free-course/enroll")
    resp2 = client.post("/api/courses/test-free-course/enroll")
    assert resp2.status_code == 409


def test_free_course_lesson_accessible_after_enroll(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    _register_login(client, "free3")
    client.post("/api/courses/test-free-course/enroll")
    resp = client.get(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}"
    )
    assert resp.status_code == 200
    assert resp.json["lesson"]["title"] == "Lesson 1"


# ── Premium course access ──────────────────────────────────────────────────────

def test_premium_lesson_blocked_without_purchase(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_premium_course(admin_id)
    _register_login(client, "prem1")
    resp = client.get(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}"
    )
    assert resp.status_code == 403


def test_premium_enroll_blocked_without_purchase(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    create_premium_course(admin_id)
    _register_login(client, "prem2")
    resp = client.post("/api/courses/test-premium-course/enroll")
    assert resp.status_code == 403


def test_premium_course_accessible_after_completed_purchase(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_premium_course(admin_id)
    _register_login(client, "prem3")

    me = client.get("/api/auth/me")
    user_id = me.json["user"]["id"]

    # Simulate a completed PayPal capture directly in the DB
    from stemquest.extensions import db
    from stemquest.models.billing import Purchase, PurchaseStatus
    from stemquest.utils.helpers import new_id, utcnow

    db.session.add(Purchase(
        id=new_id(),
        user_id=user_id,
        course_id=data["course_id"],
        amount=29.99,
        currency="USD",
        provider="paypal",
        provider_payment_id=f"SIMULATED-{new_id()}",  # canonical (not paypal_order_id)
        status=PurchaseStatus.completed,
        created_at=utcnow(),
        completed_at=utcnow(),
    ))
    db.session.commit()

    resp = client.get(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}"
    )
    assert resp.status_code == 200


# ── Lesson completion ──────────────────────────────────────────────────────────

def test_lesson_complete_awards_xp(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    _register_login(client, "lc1")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.post(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}/complete"
    )
    assert resp.status_code == 200
    assert resp.json["xp_awarded"] > 0
    assert resp.json["already_completed"] is False


def test_lesson_complete_is_idempotent(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    _register_login(client, "lc2")
    client.post("/api/courses/test-free-course/enroll")

    url = f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}/complete"
    resp1 = client.post(url)
    resp2 = client.post(url)

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp2.json["already_completed"] is True
    assert resp2.json["xp_awarded"] == 0


def test_lesson_complete_requires_auth(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    fresh = client.application.test_client()
    resp  = fresh.post(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}/complete"
    )
    assert resp.status_code == 401


def test_lesson_complete_returns_streak(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    _register_login(client, "lc3")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.post(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}/complete"
    )
    assert resp.status_code == 200
    assert resp.json["streak"] is not None
    assert "current_streak" in resp.json["streak"]


# ── Quiz ───────────────────────────────────────────────────────────────────────

def test_quiz_submit_pass_100(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    qd   = _create_quiz_lesson(app, data["course_id"], data["module_id"])
    _register_login(client, "qz1")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.post(
        f"/api/courses/{data['course_id']}/lessons/{qd['lesson_id']}/quiz/submit",
        json={"answers": {qd["question_id"]: qd["correct_opt_id"]}},
    )
    assert resp.status_code == 200
    body = resp.json
    assert body["passed"]        is True
    assert body["score"]         == 100
    assert body["perfect_score"] is True
    assert body["xp_awarded"]    > 0
    assert body["recommendation"] == "advanced"


def test_quiz_submit_fail_returns_review(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    qd   = _create_quiz_lesson(app, data["course_id"], data["module_id"])
    _register_login(client, "qz2")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.post(
        f"/api/courses/{data['course_id']}/lessons/{qd['lesson_id']}/quiz/submit",
        json={"answers": {qd["question_id"]: qd["wrong_opt_id"]}},
    )
    assert resp.status_code == 200
    body = resp.json
    assert body["passed"]        is False
    assert body["score"]         == 0
    assert body["recommendation"] == "review"


def test_quiz_submit_requires_auth(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    qd   = _create_quiz_lesson(app, data["course_id"], data["module_id"])
    fresh = client.application.test_client()
    resp  = fresh.post(
        f"/api/courses/{data['course_id']}/lessons/{qd['lesson_id']}/quiz/submit",
        json={"answers": {qd["question_id"]: qd["correct_opt_id"]}},
    )
    assert resp.status_code == 401


def test_quiz_get_hides_correct_answers(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    qd   = _create_quiz_lesson(app, data["course_id"], data["module_id"])
    _register_login(client, "qz3")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.get(
        f"/api/courses/{data['course_id']}/lessons/{qd['lesson_id']}/quiz"
    )
    assert resp.status_code == 200
    quiz = resp.json["quiz"]
    for question in quiz["questions"]:
        for option in question["options"]:
            assert "is_correct" not in option, "Correct answers must not be exposed to students"


def test_quiz_get_no_quiz_returns_404(client: FlaskClient, app: Flask):
    """Lesson 1 of the free course has no quiz in the test fixture."""
    admin_id = get_or_create_admin()
    data = create_free_course(admin_id)
    _register_login(client, "qz4")
    client.post("/api/courses/test-free-course/enroll")

    resp = client.get(
        f"/api/courses/{data['course_id']}/lessons/{data['lesson_id']}/quiz"
    )
    assert resp.status_code == 404


# ── Admin content creation ─────────────────────────────────────────────────────

def _login_as_admin(client: FlaskClient, app: Flask) -> str:
    """Create an admin, log in, return admin user_id."""
    from stemquest.extensions import db, bcrypt
    from stemquest.models.user import User, UserRole
    from stemquest.utils.helpers import new_id, make_initials, utcnow

    email = "contentadmin@test.com"
    u = User.query.filter_by(email=email).first()
    if not u:
        pw = bcrypt.generate_password_hash("adminpass123").decode()
        u  = User(
            id=new_id(), email=email, name="Content Admin", password_hash=pw,
            role=UserRole.admin, avatar="CA", is_active=True, email_verified=True,
            created_at=utcnow(), updated_at=utcnow(),
        )
        db.session.add(u)
        db.session.commit()
    client.post("/api/auth/login", json={"email": email, "password": "adminpass123"})
    return u.id


def test_admin_create_course_module_lesson_quiz(client: FlaskClient, app: Flask):
    """Full content authoring flow: course -> module -> lesson -> quiz."""
    _login_as_admin(client, app)

    # Create course — use canonical is_premium (not is_free)
    cr = client.post("/api/admin/courses", json={
        "title":       "Test Admin Course",
        "slug":        "admin-test-course",
        "description": "A course created by admin.",
        "is_premium":  False,            # canonical field (not is_free)
        "price":       0,
        "difficulty":  "beginner",
    })
    assert cr.status_code == 201, cr.json
    course_id = cr.json["course"]["id"]

    # Create module
    mr = client.post(f"/api/admin/courses/{course_id}/modules", json={"title": "Module Alpha"})
    assert mr.status_code == 201
    module_id = mr.json["module"]["id"]

    # Create lesson — use canonical content_body (not content)
    lr = client.post(f"/api/admin/modules/{module_id}/lessons", json={
        "title":        "Lesson One",
        "content_body": "Lesson body text here.",  # canonical (not content)
        "xp_reward":    25,
    })
    assert lr.status_code == 201
    lesson_id = lr.json["lesson"]["id"]

    # Create quiz — use canonical prompt / option_text (not text)
    qr = client.post(f"/api/admin/lessons/{lesson_id}/quiz", json={
        "title":         "Lesson One Quiz",
        "passing_score": 70,
        "questions": [
            {
                "prompt": "What is 2 + 2?",    # canonical (not text)
                "options": [
                    {"option_text": "4", "is_correct": True},   # canonical (not text)
                    {"option_text": "3", "is_correct": False},
                ],
            }
        ],
    })
    assert qr.status_code == 201
    quiz = qr.json["quiz"]
    assert len(quiz["questions"]) == 1
    # Admin response must include correct flags
    for option in quiz["questions"][0]["options"]:
        assert "is_correct" in option


def test_admin_publish_course(client: FlaskClient, app: Flask):
    _login_as_admin(client, app)

    cr = client.post("/api/admin/courses", json={
        "title":       "Publish Test",
        "slug":        "publish-test",
        "description": "desc",
        "is_premium":  False,        # canonical (not is_free)
        "price":       0,
    })
    assert cr.status_code == 201
    course_id = cr.json["course"]["id"]
    # Admin-created courses start as draft (published=False in admin_svc.create_course)
    assert cr.json["course"]["published"] is False  # canonical key (not is_published)

    pr = client.post(f"/api/admin/courses/{course_id}/publish")
    assert pr.status_code == 200
    assert pr.json["course"]["published"] is True   # canonical key (not is_published)

    # Toggle again -> unpublish
    pr2 = client.post(f"/api/admin/courses/{course_id}/publish")
    assert pr2.status_code == 200
    assert pr2.json["course"]["published"] is False  # canonical key


def test_admin_routes_forbidden_for_student(client: FlaskClient, app: Flask):
    client.post("/api/auth/register", json={
        "email": "student_block@test.com", "name": "S", "password": "securepass123",
    })
    client.post("/api/auth/login", json={
        "email": "student_block@test.com", "password": "securepass123",
    })
    resp = client.get("/api/admin/metrics")
    assert resp.status_code == 403


def test_admin_quiz_requires_at_least_one_question(client: FlaskClient, app: Flask):
    admin_id = _login_as_admin(client, app)

    cr = client.post("/api/admin/courses", json={
        "title":      "NoQ",
        "slug":       "noq-course",
        "description": ".",
        "is_premium": False,      # canonical
        "price":      0,
    })
    course_id = cr.json["course"]["id"]
    mr = client.post(f"/api/admin/courses/{course_id}/modules", json={"title": "M"})
    module_id = mr.json["module"]["id"]
    lr = client.post(f"/api/admin/modules/{module_id}/lessons", json={
        "title":        "L",
        "content_body": "Body.",  # canonical
    })
    lesson_id = lr.json["lesson"]["id"]

    resp = client.post(f"/api/admin/lessons/{lesson_id}/quiz", json={
        "title": "Empty Quiz", "questions": [],
    })
    assert resp.status_code == 422


def test_admin_create_quiz_without_correct_option_returns_422(client: FlaskClient, app: Flask):
    _login_as_admin(client, app)

    cr = client.post("/api/admin/courses", json={
        "title":      "BadQ",
        "slug":       "badq-course",
        "description": ".",
        "is_premium": False,      # canonical
        "price":      0,
    })
    course_id = cr.json["course"]["id"]
    mr = client.post(f"/api/admin/courses/{course_id}/modules", json={"title": "M"})
    module_id = mr.json["module"]["id"]
    lr = client.post(f"/api/admin/modules/{module_id}/lessons", json={
        "title":        "L",
        "content_body": "Body.",  # canonical
    })
    lesson_id = lr.json["lesson"]["id"]

    resp = client.post(f"/api/admin/lessons/{lesson_id}/quiz", json={
        "questions": [
            {
                "prompt": "No correct?",   # canonical (not text)
                "options": [
                    {"option_text": "A", "is_correct": False},  # canonical (not text)
                    {"option_text": "B", "is_correct": False},
                ],
            },
        ],
    })
    assert resp.status_code == 422
