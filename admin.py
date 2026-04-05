"""
STEMQuest — Admin Service

Content authoring, analytics, user management, and platform metrics.
Admin absorbs all instructor responsibilities — there is no teacher role.

FIELD MAPPING (service → model)
--------------------------------
Course     : is_premium (not is_free), published (not is_published)
Module     : sort_order (not order), func.max(Module.sort_order)
Lesson     : content_body (not content), difficulty_level (not difficulty),
             sort_order (not order), func.max(Lesson.sort_order)
QuizQuestion : prompt (not text), sort_order (not order)
QuizOption   : option_text (not text), sort_order (not order)
Enrollment   : created_at (not enrolled_at)
"""
from __future__ import annotations

import logging
from sqlalchemy import func

from ..extensions import db
from ..models.user import User, UserRole
from ..models.course import Course, Difficulty
from ..models.module import Module
from ..models.lesson import Lesson
from ..models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt
from ..models.enrollment import Enrollment
from ..models.progress import LessonProgress
from ..models.gamification import PointsTransaction, UserBadge
from ..models.billing import Purchase, PurchaseStatus, WebhookEvent
from ..utils.helpers import new_id, utcnow, paginate_query
from ..utils.errors import NotFoundError, ConflictError, ValidationError

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Content Authoring
# ─────────────────────────────────────────────────────────────────────────────

def create_course(admin_id: str, data: dict) -> Course:
    """
    Create a new course in draft state (published=False).

    ``data`` must use canonical field names from validate_create_course():
      - is_premium (bool)       — True = paid course
      - price (float|None)      — None for free courses
      - published is always set to False on creation (draft)
    """
    if Course.query.filter_by(slug=data["slug"]).first():
        raise ConflictError(f"A course with slug '{data['slug']}' already exists.")

    course = Course(
        id=new_id(),
        slug=data["slug"],
        title=data["title"],
        description=data.get("description", ""),
        image_url=data.get("image_url") or None,
        instructor_id=admin_id,
        is_premium=data["is_premium"],                   # is_premium (not is_free)
        price=data.get("price"),                          # None for free, decimal for premium
        currency="USD",
        published=False,                                  # published (not is_published); always draft
        category=data.get("category", ""),
        difficulty=Difficulty(data.get("difficulty", "beginner")),
        tags=data.get("tags", []),
        total_lessons=0,
        estimated_hours=data.get("estimated_hours", 0),
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.session.add(course)
    db.session.commit()
    return course


def update_course(course_id: str, data: dict) -> Course:
    course = Course.query.get(course_id)
    if not course:
        raise NotFoundError("Course not found.")

    # Canonical field names only — reject stale names silently by not mapping them
    if "title" in data:
        course.title = (data["title"] or "").strip()
    if "description" in data:
        course.description = data["description"]
    if "image_url" in data:
        course.image_url = data["image_url"] or None
    if "published" in data:                              # published (not is_published)
        course.published = bool(data["published"])
    if "is_premium" in data:                             # is_premium (not is_free)
        course.is_premium = bool(data["is_premium"])
    if "price" in data:
        course.price = float(data["price"]) if data["price"] is not None else None
    if "category" in data:
        course.category = (data["category"] or "").strip()
    if "difficulty" in data:
        try:
            course.difficulty = Difficulty(data["difficulty"])
        except ValueError:
            raise ValidationError(
                "Validation failed.",
                detail={"difficulty": f"Must be one of: {', '.join(d.value for d in Difficulty)}."},
            )
    if "tags" in data:
        course.tags = data["tags"] or []
    if "estimated_hours" in data:
        course.estimated_hours = float(data["estimated_hours"] or 0)

    # If set to free, clear the price
    if not course.is_premium:
        course.price = None

    course.updated_at = utcnow()
    db.session.commit()
    return course


def publish_course(course_id: str) -> Course:
    """Toggle the published flag (draft ↔ published)."""
    course = Course.query.get(course_id)
    if not course:
        raise NotFoundError("Course not found.")
    course.published  = not course.published    # published (not is_published)
    course.updated_at = utcnow()
    db.session.commit()
    return course


def create_module(course_id: str, data: dict) -> Module:
    """
    ``data`` uses canonical field names from validate_create_module():
      - sort_order (int)  — canonical (not ``order``)
    """
    course = Course.query.get(course_id)
    if not course:
        raise NotFoundError("Course not found.")

    # Auto-assign next sort_order if not supplied
    sort_order = data.get("sort_order") or (
        (
            db.session.query(func.max(Module.sort_order))   # sort_order (not order)
            .filter(Module.course_id == course_id)
            .scalar() or 0
        ) + 1
    )
    module = Module(
        id=new_id(),
        course_id=course_id,
        title=data["title"],
        description=data.get("description", ""),
        sort_order=int(sort_order),                         # sort_order (not order)
        created_at=utcnow(),
    )
    db.session.add(module)
    db.session.commit()
    return module


def create_lesson(module_id: str, data: dict) -> Lesson:
    """
    ``data`` uses canonical field names from validate_create_lesson():
      - content_body (str)      — canonical (not ``content``)
      - difficulty_level (str)  — canonical (not ``difficulty``)
      - sort_order (int)        — canonical (not ``order``)
    """
    module = Module.query.get(module_id)
    if not module:
        raise NotFoundError("Module not found.")

    difficulty_str = data.get("difficulty_level", "beginner")   # difficulty_level (not difficulty)
    try:
        difficulty = Difficulty(difficulty_str)
    except ValueError:
        raise ValidationError(
            "Validation failed.",
            detail={"difficulty_level": f"Must be one of: {', '.join(d.value for d in Difficulty)}."},
        )

    sort_order = data.get("sort_order") or (        # sort_order (not order)
        (
            db.session.query(func.max(Lesson.sort_order))    # sort_order (not order)
            .filter(Lesson.module_id == module_id)
            .scalar() or 0
        ) + 1
    )
    lesson = Lesson(
        id=new_id(),
        module_id=module_id,
        course_id=module.course_id,
        title=data["title"],
        summary=data.get("summary", ""),
        content_body=data["content_body"],              # content_body (not content)
        video_url=data.get("video_url") or None,
        difficulty_level=difficulty,                    # difficulty_level (not difficulty)
        xp_reward=int(data.get("xp_reward", 20)),
        sort_order=int(sort_order),                     # sort_order (not order)
        published=bool(data.get("published", True)),
        created_at=utcnow(),
    )
    db.session.add(lesson)
    db.session.flush()   # flush so lesson.id exists and COUNT below is accurate

    # Recount total lessons from DB (includes the just-flushed new row)
    course = module.course
    if course:
        course.total_lessons = (
            db.session.query(func.count(Lesson.id))
            .filter(Lesson.course_id == course.id)
            .scalar() or 0
        )
        course.updated_at = utcnow()

    db.session.commit()
    return lesson


def create_quiz(lesson_id: str, data: dict) -> Quiz:
    """
    Create a quiz with questions and options.

    Expected body shape::

        {
            "title": str,               # optional — defaults to "Quiz: <lesson title>"
            "passing_score": int,       # 0-100, default 70
            "xp_reward": int,           # default 30
            "questions": [
                {
                    "prompt": str,          # canonical field (not "text")
                    "explanation": str,     # optional
                    "sort_order": int,      # optional
                    "options": [
                        {
                            "option_text": str,   # canonical field (not "text")
                            "is_correct": bool,
                            "sort_order": int     # optional
                        }
                    ]
                }
            ]
        }
    """
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        raise NotFoundError("Lesson not found.")
    if lesson.quiz:
        raise ConflictError("This lesson already has a quiz.")

    questions_data = data.get("questions") or []
    if not questions_data:
        raise ValidationError(
            "At least one question is required.",
            detail={"questions": "Required."},
        )

    quiz = Quiz(
        id=new_id(),
        lesson_id=lesson_id,
        title=data.get("title") or f"Quiz: {lesson.title}",
        passing_score=int(data.get("passing_score", 70)),
        xp_reward=int(data.get("xp_reward", 30)),
        created_at=utcnow(),
    )
    db.session.add(quiz)
    db.session.flush()   # need quiz.id for child rows

    for q_idx, q_data in enumerate(questions_data):
        # Accept ``prompt`` (canonical) or ``text`` (legacy alias)
        prompt_text = (
            q_data.get("prompt") or q_data.get("text") or ""
        ).strip()
        if not prompt_text:
            raise ValidationError(
                "Validation failed.",
                detail={"questions": f"Question {q_idx + 1} is missing prompt text."},
            )

        # sort_order: accept ``sort_order`` (canonical) or ``order`` (legacy)
        q_sort = q_data.get("sort_order") or q_data.get("order") or (q_idx + 1)

        question = QuizQuestion(
            id=new_id(),
            quiz_id=quiz.id,
            prompt=prompt_text,           # prompt (not text)
            explanation=q_data.get("explanation") or None,
            sort_order=int(q_sort),       # sort_order (not order)
            created_at=utcnow(),
        )
        db.session.add(question)
        db.session.flush()

        options_data = q_data.get("options") or []
        if not any(o.get("is_correct") for o in options_data):
            raise ValidationError(
                f"Question '{prompt_text[:60]}' must have at least one correct option.",
                detail={"questions": "Each question needs exactly one correct option marked."},
            )

        for o_idx, o_data in enumerate(options_data):
            # Accept ``option_text`` (canonical) or ``text`` (legacy alias)
            option_text = (
                o_data.get("option_text") or o_data.get("text") or ""
            ).strip()

            # sort_order: accept ``sort_order`` (canonical) or ``order`` (legacy)
            o_sort = o_data.get("sort_order") or o_data.get("order") or (o_idx + 1)

            option = QuizOption(
                id=new_id(),
                question_id=question.id,
                option_text=option_text,        # option_text (not text)
                is_correct=bool(o_data.get("is_correct", False)),
                sort_order=int(o_sort),         # sort_order (not order)
                created_at=utcnow(),
            )
            db.session.add(option)

    db.session.commit()
    return quiz


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────

def list_users(page: int = 1, per_page: int = 50) -> dict:
    q = User.query.order_by(User.created_at.desc())
    paginated = paginate_query(q, page=page, per_page=per_page)
    paginated["items"] = [u.to_dict() for u in paginated["items"]]
    return paginated


def update_user_role(target_user_id: str, new_role: str) -> User:
    """
    Transition a user between 'admin' and 'student'.
    Any other value — including 'teacher' — is rejected with 422.
    """
    if new_role not in ("admin", "student"):
        raise ValidationError(
            "Role must be 'admin' or 'student'.",
            detail={"role": "Allowed values: 'admin', 'student'."},
        )
    user = User.query.get(target_user_id)
    if not user:
        raise NotFoundError("User not found.")
    user.role       = UserRole(new_role)
    user.updated_at = utcnow()
    db.session.commit()
    return user


def grant_enrollment(admin_id: str, user_id: str, course_id: str) -> Enrollment:
    """
    Admin grants course access to any student.
    Uses ``source="admin"`` to distinguish from self-enrollment and purchases.
    Uses ``created_at`` (not ``enrolled_at``).
    """
    user = User.query.get(user_id)
    if not user:
        raise NotFoundError("User not found.")
    course = Course.query.get(course_id)
    if not course:
        raise NotFoundError("Course not found.")

    existing = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            db.session.commit()
        return existing

    enrollment = Enrollment(
        id=new_id(),
        user_id=user_id,
        course_id=course_id,
        source="admin",              # tracks how enrollment was granted
        is_active=True,
        created_at=utcnow(),         # created_at (not enrolled_at)
    )
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


# ─────────────────────────────────────────────────────────────────────────────
# Analytics & Metrics
# ─────────────────────────────────────────────────────────────────────────────

def get_metrics() -> dict:
    total_users    = User.query.count()
    total_students = User.query.filter_by(role=UserRole.student).count()
    total_admins   = User.query.filter_by(role=UserRole.admin).count()
    total_courses  = Course.query.count()
    published      = Course.query.filter_by(published=True).count()     # published (not is_published)
    enrollments    = Enrollment.query.filter_by(is_active=True).count()
    completions    = Enrollment.query.filter(Enrollment.completed_at.isnot(None)).count()
    total_revenue  = float(
        db.session.query(func.coalesce(func.sum(Purchase.amount), 0))
        .filter(Purchase.status == PurchaseStatus.completed)
        .scalar()
    )
    lesson_completions = LessonProgress.query.filter_by(completed=True).count()
    quiz_attempts      = QuizAttempt.query.count()
    quiz_passes        = QuizAttempt.query.filter_by(passed=True).count()
    pass_rate          = round(
        (quiz_passes / quiz_attempts * 100) if quiz_attempts > 0 else 0, 1
    )
    total_xp_awarded = int(
        db.session.query(func.coalesce(func.sum(PointsTransaction.amount), 0)).scalar()
    )

    return {
        "users": {
            "total":    total_users,
            "students": total_students,
            "admins":   total_admins,
        },
        "courses": {
            "total":     total_courses,
            "published": published,
            "draft":     total_courses - published,
        },
        "enrollments": {
            "total":              enrollments,
            "completions":        completions,
            "lesson_completions": lesson_completions,
        },
        "revenue": {
            "total_usd": total_revenue,
        },
        "quizzes": {
            "total_attempts": quiz_attempts,
            "pass_rate_pct":  pass_rate,
        },
        "gamification": {
            "total_xp_awarded": total_xp_awarded,
        },
    }


def get_analytics() -> dict:
    """Per-course enrollment, completion, lesson, quiz, and revenue breakdown."""
    courses = Course.query.order_by(Course.title).all()
    rows = []
    for course in courses:
        enrolled  = Enrollment.query.filter_by(course_id=course.id, is_active=True).count()
        completed = Enrollment.query.filter(
            Enrollment.course_id == course.id,
            Enrollment.completed_at.isnot(None),
        ).count()
        lesson_completions = LessonProgress.query.filter_by(
            course_id=course.id, completed=True
        ).count()
        # Count quiz attempts for all lessons in this course (denormalised lesson_id)
        from ..models.lesson import Lesson as _Lesson
        course_lesson_ids = db.session.query(_Lesson.id).filter_by(course_id=course.id)
        quiz_attempts = (
            QuizAttempt.query
            .filter(QuizAttempt.lesson_id.in_(course_lesson_ids))
            .count()
        )
        revenue = float(
            db.session.query(func.coalesce(func.sum(Purchase.amount), 0))
            .filter(
                Purchase.course_id == course.id,
                Purchase.status    == PurchaseStatus.completed,
            )
            .scalar()
        )
        rows.append({
            "course_id":          course.id,
            "course_title":       course.title,
            "published":          course.published,    # published (not is_published)
            "is_premium":         course.is_premium,   # is_premium (not is_free)
            "enrolled":           enrolled,
            "completed":          completed,
            "lesson_completions": lesson_completions,
            "revenue_usd":        revenue,
        })
    return {"courses": rows}


# ─────────────────────────────────────────────────────────────────────────────
# Billing admin views
# ─────────────────────────────────────────────────────────────────────────────

def list_purchases(page: int = 1, per_page: int = 50) -> dict:
    q = Purchase.query.order_by(Purchase.created_at.desc())
    paginated = paginate_query(q, page=page, per_page=per_page)
    paginated["items"] = [p.to_dict() for p in paginated["items"]]
    return paginated


def list_webhook_events(page: int = 1, per_page: int = 50) -> dict:
    q = WebhookEvent.query.order_by(WebhookEvent.created_at.desc())
    paginated = paginate_query(q, page=page, per_page=per_page)
    paginated["items"] = [e.to_dict() for e in paginated["items"]]
    return paginated
