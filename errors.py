"""
STEMQuest — Structured JSON error responses and global error handler registration.
All API errors return:  {"error": "<message>", "detail": <optional>}
"""
from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Base class for all intentional API errors."""
    status_code: int = 400

    def __init__(self, message: str, status_code: int | None = None, detail: object = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
        if status_code is not None:
            self.status_code = status_code

    def to_response(self):
        body: dict = {"error": self.message}
        if self.detail is not None:
            body["detail"] = self.detail
        return jsonify(body), self.status_code


class ValidationError(APIError):
    status_code = 422


class NotFoundError(APIError):
    status_code = 404


class ForbiddenError(APIError):
    status_code = 403


class UnauthorizedError(APIError):
    status_code = 401


class ConflictError(APIError):
    status_code = 409


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(APIError)
    def handle_api_error(exc: APIError):
        return exc.to_response()

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        return jsonify({"error": exc.name, "detail": exc.description}), exc.code

    @app.errorhandler(404)
    def handle_404(_exc):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(405)
    def handle_405(_exc):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def handle_500(exc):
        app.logger.exception("Unhandled server error: %s", exc)
        return jsonify({"error": "Internal server error"}), 500
