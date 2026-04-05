"""
STEMQuest — Course Service

Handles access control, progress tracking, lesson completion, and quiz scoring.

FIELD MAPPING (service → model)
--------------------------------
Course     : is_premium (not is_free, inverted), published (not is_published)
Module     : sort_order (not order)
Lesson     : sort_order (not order), content_body (not content)
Enrollment : created_at (not enrolled_at), source field added
LessonProgress : completed=True must be set explicitly
QuizAttempt    : perfect (not perfect_score), created_at (not completed_at)
"""
from __future__ import annotations

import logging

from ..extensions import db
from ..models.course import Course
from ..models.module import Module
from ..models.lesson import Lesson
from ..models.enrollment import Enrollment
from ..models.progress import LessonProgress
from ..models.quiz import Quiz, QuizAttempt, Recommendation
from ..models.billing import Purchase, PurchaseStatus
from ..utils.helpers import new_id, utcnow
from ..utils.errors import NotFoundError, ForbiddenError, ConflictError
from . import gamification as gami

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Access helpers
# ─────────────────────────────────────────────────────────────────────────────

def user_has_access(user_id: str, course: Course) -> bool:
    """
    A user has access to a course if:
      - the course is NOT premium (i.e. is_premium=False), OR
      - they have an active enrollment, OR
      - they have a completed purchase.

    NOTE: the field is ``is_premium`` (True = requires payment).
    The old ``is_free`` field does not exist on the model.
    """
    if not course.is_premium:          # is_premium=False → free course, always accessible
        return True
    enrolled = Enrollment.query.filter_by(
        user_id=user_id, course_id=course.id, is_active=True
    ).first()
    if enrolled:
        return True
    purchased = Purchase.query.filter_by(
        user_id=user_id, course_id=course.id, status=PurchaseStatus.completed
    ).first()
    return purchased is not None


def get_enrollment(user_id: str, course_id: str) -> Enrollment | None:
    return Enrollment.query.filter_by(
        user_id=user_id, course_id=course_id, is_active=True
    ).first()


def enroll_student(user_id: str, course: Course) -> Enrollment:
    """
    Enroll a student in a course.
    Free courses: enroll immediately.
    Premium courses: require a completed purchase.
    """
    existing = get_enrollment(user_id, course.id)
    if existing:
        raise ConflictError("You are already enrolled in this course.")

    if course.is_premium:              # is_premium (not is_free)
        purchased = Purchase.query.filter_by(
            user_id=user_id, course_id=course.id, status=PurchaseStatus.completed
        ).first()
        if not purchased:
            raise ForbiddenError("This course requires purchase before enrollment.")

    enrollment = Enrollment(
        id=new_id(),
        user_id=user_id,
        course_id=course.id,
        source="free" if not course.is_premium else "purchase",
        is_active=True,
        created_at=utcnow(),           # created_at (not enrolled_at)
    )
    db.session.add(enrollment)
    db.session.commit()
    return enrollment


# ─────────────────────────────────────────────────────────────────────────────
# Course catalog
# ─────────────────────────────────────────────────────────────────────────────

def get_published_courses(user_id: str | None = None) -> list[dict]:
    """Return all published courses with per-user progress metadata."""
    # ``published`` is the correct column name (not ``is_published``)
    courses = Course.query.filter_by(published=True).order_by(Course.title).all()
    result = []
    for course in courses:
        data = course.to_dict()
        if user_id:
            enrollment = get_enrollment(user_id, course.id)
            data["is_enrolled"] = enrollment is not None
            data["has_access"]  = user_has_access(user_id, course)
            data["progress"]    = (
                _course_progress(user_id, course.id, course.total_lessons)
                if enrollment else None
            )
        else:
            data["is_enrolled"] = False
            data["has_access"]  = not course.is_premium   # free = no payment needed
            data["progress"]    = None
        result.append(data)
    return result


def get_course_detail(slug: str, user_id: str | None = None) -> dict:
    """Return full course detail including modules, lessons, and per-user progress."""
    # ``published`` (not ``is_published``)
    course = Course.query.filter_by(slug=slug, published=True).first()
    if not course:
        raise NotFoundError("Course not found.")

    data = course.to_dict()

    # Modules ordered by sort_order (not ``order``)
    modules = (
        Module.query
        .filter_by(course_id=course.id)
        .order_by(Module.sort_order)    # sort_order, not order
        .all()
    )
    modules_data = []
    for mod in modules:
        mod_dict = mod.to_dict()
        # Lessons ordered by sort_order (not ``order``)
        lessons = (
            Lesson.query
            .filter_by(module_id=mod.id, published=True)
            .order_by(Lesson.sort_order)    # sort_order, not order
            .all()
        )
        lessons_data = []
        for lesson in lessons:
            l_dict = lesson.to_dict()
            l_dict["has_quiz"] = lesson.quiz is not None
            if user_id:
                prog = LessonProgress.query.filter_by(
                    user_id=user_id, lesson_id=lesson.id
                ).first()
                l_dict["completed"]    = prog.completed if prog else False
                l_dict["completed_at"] = (
                    prog.completed_at.isoformat() if prog and prog.completed_at else None
                )
            else:
                l_dict["completed"]    = False
                l_dict["completed_at"] = None
            lessons_data.append(l_dict)
        mod_dict["lessons"] = lessons_data
        modules_data.append(mod_dict)
    data["modules"] = modules_data

    if user_id:
        enrollment = get_enrollment(user_id, course.id)
        data["is_enrolled"] = enrollment is not None
        data["has_access"]  = user_has_access(user_id, course)
        data["progress"]    = (
            _course_progress(user_id, course.id, course.total_lessons)
            if enrollment else None
        )
    else:
        data["is_enrolled"] = False
        data["has_access"]  = not course.is_premium
        data["progress"]    = None

    return data


def _course_progress(user_id: str, course_id: str, total_lessons: int) -> dict:
    completed_count = LessonProgress.query.filter_by(
        user_id=user_id, course_id=course_id, completed=True
    ).count()
    pct = round((completed_count / total_lessons * 100) if total_lessons > 0 else 0, 1)
    return {
        "completed_lessons": completed_count,
        "total_lessons":     total_lessons,
        "percentage":        pct,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lesson
# ─────────────────────────────────────────────────────────────────────────────

def get_lesson(lesson_id: str, user_id: str) -> dict:
    """Return lesson detail. Requires enrollment (or free course access)."""
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        raise NotFoundError("Lesson not found.")

    course = lesson.course
    # ``published`` (not ``is_published``)
    if not course or not course.published:
        raise NotFoundError("Course not found.")

    if not user_has_access(user_id, course):
        raise ForbiddenError("Enroll in or purchase this course to access lessons.")

    data = lesson.to_dict()
    prog = LessonProgress.query.filter_by(user_id=user_id, lesson_id=lesson_id).first()
    data["completed"]    = prog.completed if prog else False
    data["completed_at"] = (
        prog.completed_at.isoformat() if prog and prog.completed_at else None
    )
    data["has_quiz"] = lesson.quiz is not None
    data["quiz_id"]  = lesson.quiz.id if lesson.quiz else None
    return data


def complete_lesson(user_id: str, lesson_id: str) -> dict:
    """
    Mark a lesson as completed (idempotent).
    Awards XP, updates streak, checks for course completion.
    Returns gamification payload.
    """
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        raise NotFoundError("Lesson not found.")
    course = lesson.course
    if not course or not course.published:   # published (not is_published)
        raise NotFoundError("Course not found.")
    if not user_has_access(user_id, course):
        raise ForbiddenError("Access denied.")

    # Idempotent: return existing if already completed
    existing = LessonProgress.query.filter_by(
        user_id=user_id, lesson_id=lesson_id
    ).first()
    if existing and existing.completed:
        return {
            "already_completed": True,
            "xp_awarded":        0,
            "new_badges":        [],
            "streak":            None,
            "course_complete":   False,
        }

    now = utcnow()

    if existing:
        # Progress row exists but not marked complete — update it
        existing.completed    = True      # spec: completed boolean must be set
        existing.completed_at = now
    else:
        # Create new progress row with completed=True
        progress = LessonProgress(
            id=new_id(),
            user_id=user_id,
            lesson_id=lesson_id,
            course_id=lesson.course_id,
            completed=True,           # spec: completed boolean field
            completed_at=now,
            created_at=now,
        )
        db.session.add(progress)

    db.session.flush()   # ensure row exists before gamification reads counts

    # Gamification
    gami_result = gami.reward_lesson_complete(
        user_id, lesson_id, lesson.course_id, lesson.xp_reward
    )

    # Check course completion
    course_complete = False
    completed_count = LessonProgress.query.filter_by(
        user_id=user_id, course_id=lesson.course_id, completed=True
    ).count()
    if course.total_lessons > 0 and completed_count >= course.total_lessons:
        enrollment = Enrollment.query.filter_by(
            user_id=user_id, course_id=lesson.course_id, is_active=True
        ).first()
        if enrollment and enrollment.completed_at is None:
            enrollment.completed_at = now
        course_reward = gami.reward_course_complete(user_id, lesson.course_id)
        gami_result["xp_awarded"] += course_reward["xp_awarded"]
        gami_result["new_badges"].extend(course_reward["new_badges"])
        course_complete = True

    db.session.commit()

    return {
        "already_completed": False,
        "xp_awarded":        gami_result["xp_awarded"],
        "new_badges":        gami_result["new_badges"],
        "streak":            gami_result["streak"],
        "course_complete":   course_complete,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Quiz
# ─────────────────────────────────────────────────────────────────────────────

def get_quiz(lesson_id: str, user_id: str) -> dict:
    """Return quiz for a lesson, without revealing correct answers."""
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        raise NotFoundError("Lesson not found.")
    if not user_has_access(user_id, lesson.course):
        raise ForbiddenError("Access denied.")

    quiz = lesson.quiz
    if not quiz:
        raise NotFoundError("No quiz found for this lesson.")

    data = quiz.to_dict(include_correct=False)
    best = (
        QuizAttempt.query
        .filter_by(quiz_id=quiz.id, user_id=user_id)
        .order_by(QuizAttempt.score.desc())
        .first()
    )
    data["best_attempt"] = best.to_dict() if best else None
    return data


def submit_quiz(user_id: str, quiz_id: str, answers: dict[str, str]) -> dict:
    """
    Score a quiz submission.
    answers: {question_id: option_id}

    Returns full attempt data plus gamification outcome.
    Rewards are idempotent (safe to call multiple times for same quiz).

    FIELD NOTE: QuizAttempt model uses:
      - ``perfect``    (not ``perfect_score``)
      - ``created_at`` (not ``completed_at``)
      - ``answers``    (JSON dict)
    """
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        raise NotFoundError("Quiz not found.")

    lesson = quiz.lesson
    if not lesson:
        raise NotFoundError("Associated lesson not found.")
    if not user_has_access(user_id, lesson.course):
        raise ForbiddenError("Access denied.")

    questions = quiz.questions   # loaded via selectin
    total = len(questions)
    if total == 0:
        raise ConflictError("This quiz has no questions.")

    correct = 0
    for question in questions:
        submitted_option_id = answers.get(question.id)
        if submitted_option_id:
            correct_option = next(
                (o for o in question.options if o.is_correct), None
            )
            if correct_option and correct_option.id == submitted_option_id:
                correct += 1

    score  = round((correct / total) * 100)
    passed = score >= quiz.passing_score
    perfect = score == 100

    rec, rec_text = gami.get_adaptive_recommendation(score)

    # Gamification rewards (idempotent per quiz+user)
    gami_result = gami.reward_quiz(user_id, quiz_id, score, passed, perfect)

    # Record attempt — ``perfect`` (not ``perfect_score``), ``created_at`` (not ``completed_at``)
    attempt = QuizAttempt(
        id=new_id(),
        quiz_id=quiz_id,
        lesson_id=lesson.id,
        user_id=user_id,
        score=score,
        passed=passed,
        perfect=perfect,               # model field: perfect (not perfect_score)
        answers=answers,
        recommendation=rec,
        xp_awarded=gami_result["xp_awarded"],
        created_at=utcnow(),           # model field: created_at (not completed_at)
    )
    db.session.add(attempt)
    db.session.commit()

    return {
        "attempt":             attempt.to_dict(),
        "score":               score,
        "passed":              passed,
        "perfect_score":       perfect,
        "correct":             correct,
        "total":               total,
        "xp_awarded":          gami_result["xp_awarded"],
        "new_badges":          gami_result["new_badges"],
        "recommendation":      rec.value,
        "recommendation_text": rec_text,
        "total_xp":            gami.get_summary(user_id)["total_xp"],
    }
