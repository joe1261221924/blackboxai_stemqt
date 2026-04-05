"""
STEMQuest — Webhook receiver

POST /api/webhooks/paypal  — PayPal event delivery endpoint
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from ..services import billing as billing_svc

bp = Blueprint("webhooks", __name__)


@bp.post("/paypal")
def paypal_webhook():
    """
    Receives raw PayPal webhook events.
    Stores in DB and enqueues for async processing.
    Always returns 200 immediately to prevent PayPal retry storms.
    """
    payload = request.get_data()
    headers = {k: v for k, v in request.headers}
    try:
        billing_svc.handle_webhook(payload, headers)
    except Exception:  # noqa: BLE001
        # Swallow errors to avoid retry loops; errors are logged inside the service
        pass
    return jsonify({"received": True}), 200
