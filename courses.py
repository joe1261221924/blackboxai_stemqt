"""
STEMQuest — Course/Lesson/Quiz routes

GET  /api/courses                         — public (with per-user metadata if authed)
GET  /api/courses/<slug>                  — public (with enrollment check)
POST /api/courses/<slug>/enroll           — student
GET  /api/courses/<course_id>/lessons/<lesson_id>  — student
POST /api/courses/<course_id>/lessons/<lesson_id>/complete — student
GET  /api/courses/<course_id>/lessons/<lesson_id>/quiz     — student
POST /api/courses/<course_id>/lessons/<lesson_id>/quiz/submit — student
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

from ..services import course as course_svc
from ..utils.validators import require_json, validate_quiz_answers
from ..utils.auth import jwt_required_custom, get_current_user
from ..utils.errors import UnauthorizedError
from ..models.user import User

bp = Blueprint("courses", __name__)


def _optional_user_id() -> str | None:
    """Return the JWT identity if a valid token is present, otherwise None."""
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        return uid
    except Exception:  # noqa: BLE001
        return None


# ── Course catalog ─────────────────────────────────────────────────────────

@bp.get("")
def list_courses():
    user_id = _optional_user_id()
    courses = course_svc.get_published_courses(user_id=user_id)
    return jsonify({"courses": courses, "total": len(courses)}), 200


@bp.get("/<slug>")
def get_course(slug: str):
    user_id = _optional_user_id()
    data = course_svc.get_course_detail(slug, user_id=user_id)
    return jsonify({"course": data}), 200


@bp.post("/<slug>/enroll")
@jwt_required_custom
def enroll(slug: str):
    user = get_current_user()
    from ..models.course import Course
    from ..utils.errors import NotFoundError
    course = Course.query.filter_by(slug=slug, published=True).first()
    if not course:
        raise NotFoundError("Course not found.")
    enrollment = course_svc.enroll_student(user.id, course)
    return jsonify({"message": "Enrolled successfully.", "enrollment": enrollment.to_dict()}), 201


# ── Lesson ─────────────────────────────────────────────────────────────────

@bp.get("/<course_id>/lessons/<lesson_id>")
@jwt_required_custom
def get_lesson(course_id: str, lesson_id: str):
    user = get_current_user()
    data = course_svc.get_lesson(lesson_id, user.id)
    return jsonify({"lesson": data}), 200


@bp.post("/<course_id>/lessons/<lesson_id>/complete")
@jwt_required_custom
def complete_lesson(course_id: str, lesson_id: str):
    user = get_current_user()
    result = course_svc.complete_lesson(user.id, lesson_id)
    return jsonify(result), 200


# ── Quiz ───────────────────────────────────────────────────────────────────

@bp.get("/<course_id>/lessons/<lesson_id>/quiz")
@jwt_required_custom
def get_quiz(course_id: str, lesson_id: str):
    user = get_current_user()
    data = course_svc.get_quiz(lesson_id, user.id)
    return jsonify({"quiz": data}), 200


@bp.post("/<course_id>/lessons/<lesson_id>/quiz/submit")
@jwt_required_custom
def submit_quiz(course_id: str, lesson_id: str):
    user    = get_current_user()
    body    = require_json()

    # Resolve quiz_id from lesson
    from ..models.lesson import Lesson
    from ..utils.errors import NotFoundError
    lesson = Lesson.query.get(lesson_id)
    if not lesson or not lesson.quiz:
        raise NotFoundError("Quiz not found for this lesson.")

    answers = validate_quiz_answers(body)
    result  = course_svc.submit_quiz(user.id, lesson.quiz.id, answers)
    return jsonify(result), 200
