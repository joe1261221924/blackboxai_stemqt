"""
STEMQuest — Authentication and authorization decorators.

Roles:
  student — default for all registered users
  admin   — content authoring, analytics, user management

There is NO teacher role. Any teacher reference is an error.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable

from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import g

from ..models.user import User, UserRole
from .errors import UnauthorizedError, ForbiddenError


def _load_current_user() -> User:
    """Load the User record from the identity stored in the JWT."""
    user_id: str = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        raise UnauthorizedError("User account not found.")
    if not user.is_active:
        raise UnauthorizedError("Your account has been deactivated.")
    g.current_user = user
    return user


def jwt_required_custom(fn: Callable) -> Callable:
    """
    Require a valid JWT (cookie or Bearer header).
    Stores the User object in flask.g.current_user.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        _load_current_user()
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn: Callable) -> Callable:
    """Require a valid JWT AND admin role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _load_current_user()
        if user.role != UserRole.admin:
            raise ForbiddenError("Admin access required.")
        return fn(*args, **kwargs)
    return wrapper


def student_required(fn: Callable) -> Callable:
    """Require a valid JWT AND student role."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _load_current_user()
        if user.role != UserRole.student:
            raise ForbiddenError("Student access required.")
        return fn(*args, **kwargs)
    return wrapper


def get_current_user() -> User:
    """
    Return the user previously loaded by a decorator.
    Must only be called inside a route that used one of the decorators above.
    """
    user: User | None = getattr(g, "current_user", None)
    if user is None:
        raise UnauthorizedError("No authenticated user in request context.")
    return user
