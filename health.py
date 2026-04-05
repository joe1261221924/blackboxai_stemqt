"""Health-check endpoint."""
from __future__ import annotations

from flask import Blueprint, jsonify, current_app

from ..extensions import db

bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    """
    Returns DB and Redis connectivity.
    Always returns 200 if the app is reachable;
    individual service status is in the body.
    """
    status: dict = {"status": "ok", "services": {}}

    # Database
    try:
        db.session.execute(db.text("SELECT 1"))
        status["services"]["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["services"]["database"] = f"error: {exc}"
        status["status"] = "degraded"

    # Redis
    try:
        current_app.redis.ping()
        status["services"]["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        status["services"]["redis"] = f"error: {exc}"
        status["status"] = "degraded"

    return jsonify(status), 200
