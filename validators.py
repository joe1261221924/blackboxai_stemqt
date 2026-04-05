"""
STEMQuest — Request body validators.
Each function raises ValidationError on failure or returns the cleaned data.

Field naming rules (aligned to final SQLAlchemy models):
  Course  : is_premium (not is_free), published (not is_published)
  Module  : sort_order (not order)
  Lesson  : content_body (not content), difficulty_level (not difficulty),
            sort_order (not order)
  Quiz    : xp_reward field exists on Quiz; QuizQuestion.prompt (not text);
            QuizOption.option_text (not text); sort_order (not order) for both
"""
from __future__ import annotations

import re
from flask import request

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def require_json() -> dict:
    """Return parsed JSON body or raise ValidationError."""
    data = request.get_json(silent=True)
    if data is None:
        raise ValidationError("Request body must be JSON.")
    return data


def validate_register(data: dict) -> dict:
    errors: dict[str, str] = {}

    email = (data.get("email") or "").strip().lower()
    if not email:
        errors["email"] = "Email is required."
    elif not EMAIL_RE.match(email):
        errors["email"] = "Invalid email address."

    name = (data.get("name") or "").strip()
    if not name:
        errors["name"] = "Full name is required."
    elif len(name) > 150:
        errors["name"] = "Name must be 150 characters or fewer."

    password = data.get("password") or ""
    if not password:
        errors["password"] = "Password is required."
    elif len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    elif len(password) > 128:
        errors["password"] = "Password must be 128 characters or fewer."

    if errors:
        raise ValidationError("Validation failed.", detail=errors)

    return {"email": email, "name": name, "password": password}


def validate_login(data: dict) -> dict:
    errors: dict[str, str] = {}

    email = (data.get("email") or "").strip().lower()
    if not email:
        errors["email"] = "Email is required."

    password = data.get("password") or ""
    if not password:
        errors["password"] = "Password is required."

    if errors:
        raise ValidationError("Validation failed.", detail=errors)

    return {"email": email, "password": password}


def validate_create_course(data: dict) -> dict:
    """
    Validates and normalises course creation input.

    The API accepts ``is_premium`` (preferred) or ``is_free`` (legacy alias).
    The returned dict always uses ``is_premium`` to match the Course model.
    """
    errors: dict[str, str] = {}

    title = (data.get("title") or "").strip()
    if not title:
        errors["title"] = "Title is required."

    slug = (data.get("slug") or "").strip().lower()
    if not slug:
        errors["slug"] = "Slug is required."
    elif not re.match(r"^[a-z0-9-]+$", slug):
        errors["slug"] = "Slug may only contain lowercase letters, numbers, and hyphens."

    description = (data.get("description") or "").strip()

    # Accept is_premium (preferred) or is_free (inverted legacy alias)
    if "is_premium" in data:
        raw_premium = data["is_premium"]
        if not isinstance(raw_premium, bool):
            errors["is_premium"] = "is_premium must be a boolean."
        is_premium: bool = bool(raw_premium)
    elif "is_free" in data:
        raw_free = data["is_free"]
        if not isinstance(raw_free, bool):
            errors["is_free"] = "is_free must be a boolean."
        is_premium = not bool(raw_free)
    else:
        is_premium = False   # default: free

    price_raw = data.get("price", 0)
    try:
        price = float(price_raw)
        if price < 0:
            errors["price"] = "Price must be non-negative."
    except (TypeError, ValueError):
        price = 0.0
        errors["price"] = "Price must be a number."

    if is_premium and price == 0.0:
        errors["price"] = "Premium courses must have a price greater than 0."

    allowed_difficulties = {"beginner", "intermediate", "advanced"}
    difficulty = data.get("difficulty", "beginner")
    if difficulty not in allowed_difficulties:
        errors["difficulty"] = (
            f"Difficulty must be one of: {', '.join(sorted(allowed_difficulties))}."
        )

    if errors:
        raise ValidationError("Validation failed.", detail=errors)

    return {
        "title":           title,
        "slug":            slug,
        "description":     description,
        "is_premium":      is_premium,                        # canonical model field name
        "price":           price if is_premium else None,     # None for free courses
        "difficulty":      difficulty,
        "category":        (data.get("category") or "").strip(),
        "tags":            data.get("tags") or [],
        "image_url":       (data.get("image_url") or "").strip() or None,
        "estimated_hours": float(data.get("estimated_hours") or 0),
    }


def validate_create_module(data: dict) -> dict:
    """
    Returns dict with canonical field names for the Module model.
    ``sort_order`` replaces the old ``order`` key.
    """
    title = (data.get("title") or "").strip()
    if not title:
        raise ValidationError("Validation failed.", detail={"title": "Title is required."})

    # Accept ``sort_order`` (preferred) or ``order`` (legacy alias).
    sort_order_raw = data.get("sort_order") or data.get("order") or 1
    try:
        sort_order = int(sort_order_raw)
    except (TypeError, ValueError):
        sort_order = 1

    return {
        "title":       title,
        "description": (data.get("description") or "").strip(),
        "sort_order":  sort_order,    # canonical Module.sort_order field name
    }


def validate_create_lesson(data: dict) -> dict:
    """
    Returns dict with canonical field names for the Lesson model.
    ``content_body``     replaces ``content``
    ``difficulty_level`` replaces ``difficulty``
    ``sort_order``       replaces ``order``
    """
    errors: dict[str, str] = {}

    title = (data.get("title") or "").strip()
    if not title:
        errors["title"] = "Title is required."

    # Accept ``content_body`` (preferred) or ``content`` (legacy alias).
    content_body = (
        data.get("content_body") or data.get("content") or ""
    ).strip()
    if not content_body:
        errors["content_body"] = "Content body is required."

    allowed_levels = {"beginner", "intermediate", "advanced"}
    # Accept ``difficulty_level`` (preferred) or ``difficulty`` (legacy alias).
    difficulty_level = (
        data.get("difficulty_level") or data.get("difficulty") or "beginner"
    )
    if difficulty_level not in allowed_levels:
        errors["difficulty_level"] = (
            f"Difficulty level must be one of: {', '.join(sorted(allowed_levels))}."
        )

    # Accept ``sort_order`` (preferred) or ``order`` (legacy alias).
    sort_order_raw = data.get("sort_order") or data.get("order") or 1
    try:
        sort_order = int(sort_order_raw)
    except (TypeError, ValueError):
        sort_order = 1

    xp_reward_raw = data.get("xp_reward", 20)
    try:
        xp_reward = int(xp_reward_raw)
    except (TypeError, ValueError):
        xp_reward = 20

    if errors:
        raise ValidationError("Validation failed.", detail=errors)

    return {
        "title":           title,
        "summary":         (data.get("summary") or "").strip(),
        "content_body":    content_body,      # canonical Lesson.content_body field name
        "video_url":       (data.get("video_url") or "").strip() or None,
        "difficulty_level": difficulty_level, # canonical Lesson.difficulty_level field name
        "xp_reward":       xp_reward,
        "sort_order":      sort_order,        # canonical Lesson.sort_order field name
        "published":       bool(data.get("published", True)),
    }


def validate_quiz_answers(data: dict) -> dict[str, str]:
    """Validate and return the answers map {questionId: optionId}."""
    answers = data.get("answers")
    if not isinstance(answers, dict):
        raise ValidationError("answers must be an object mapping question IDs to option IDs.")
    if not answers:
        raise ValidationError("At least one answer is required.")
    return {str(k): str(v) for k, v in answers.items()}
