"""
STEMQuest — Billing Service
============================
Handles PayPal Sandbox order creation, capture, and idempotent fulfillment.
Demo mode (PAYPAL_DEMO_MODE=true) bypasses real PayPal calls.

Field mapping (service → model)
--------------------------------
PendingOrder   : provider_order_id  (was paypal_order_id)
Purchase       : provider_payment_id (was paypal_order_id; nullable until capture)
                 provider            (always "paypal")
                 status              (PurchaseStatus enum)
WebhookEvent   : event_id           (was provider_event_id)
                 raw_payload         (Text; was payload JSON)
                 processed           (boolean; was status enum / WebhookStatus)
Course         : is_premium          (was is_free, inverted)
                 price               (nullable Numeric; was always present)
Enrollment     : source              (was enrolled_at / no source)
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta

import requests
from flask import current_app

from ..extensions import db
from ..models.billing import (
    Purchase,
    PurchaseStatus,
    PendingOrder,
    PendingOrderStatus,
    WebhookEvent,
)
from ..models.enrollment import Enrollment
from ..models.course import Course
from ..utils.helpers import new_id, utcnow
from ..utils.errors import NotFoundError, ConflictError, ForbiddenError

log = logging.getLogger(__name__)

ORDER_EXPIRY_MINUTES = 60


# ─────────────────────────────────────────────────────────────────────────────
# PayPal REST helpers
# ─────────────────────────────────────────────────────────────────────────────

def _paypal_token() -> str:
    resp = requests.post(
        f"{current_app.config['PAYPAL_BASE_URL']}/v1/oauth2/token",
        auth=(
            current_app.config["PAYPAL_CLIENT_ID"],
            current_app.config["PAYPAL_CLIENT_SECRET"],
        ),
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _paypal_create_order(amount: float, currency: str, return_url: str, cancel_url: str) -> dict:
    token = _paypal_token()
    resp = requests.post(
        f"{current_app.config['PAYPAL_BASE_URL']}/v2/checkout/orders",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "intent": "CAPTURE",
            "purchase_units": [
                {"amount": {"currency_code": currency, "value": f"{amount:.2f}"}}
            ],
            "application_context": {
                "return_url": return_url,
                "cancel_url": cancel_url,
            },
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _paypal_capture_order(provider_order_id: str) -> dict:
    token = _paypal_token()
    resp = requests.post(
        f"{current_app.config['PAYPAL_BASE_URL']}/v2/checkout/orders"
        f"/{provider_order_id}/capture",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def create_order(
    user_id: str,
    course_id: str,
    frontend_base: str,
) -> dict:
    """
    Create a PayPal order for a premium course.

    Returns
    -------
    dict with keys: approval_url, provider_order_id, course_id.

    In demo mode generates a fake order ID and an immediate approval URL.
    """
    course = Course.query.get(course_id)
    if not course:
        raise NotFoundError("Course not found.")
    # is_premium=False means free — no payment required.
    if not course.is_premium:
        raise ConflictError("This course is free and does not require purchase.")

    # Idempotency: already has a completed purchase.
    existing = Purchase.query.filter_by(
        user_id=user_id, course_id=course_id, status=PurchaseStatus.completed
    ).first()
    if existing:
        raise ConflictError("You have already purchased this course.")

    amount   = float(course.price) if course.price is not None else 0.0
    currency = course.currency

    return_url = f"{frontend_base}/billing/success"
    cancel_url  = f"{frontend_base}/billing/cancel"

    demo_mode: bool = current_app.config["PAYPAL_DEMO_MODE"]

    if demo_mode:
        provider_order_id = f"DEMO-{new_id()}"
        approval_url      = f"{return_url}?token={provider_order_id}&courseId={course_id}"
    else:
        order_data        = _paypal_create_order(amount, currency, return_url, cancel_url)
        provider_order_id = order_data["id"]
        approval_url      = next(
            link["href"] for link in order_data["links"] if link["rel"] == "approve"
        )

    # Persist the pre-capture pending order.
    expires_at = utcnow() + timedelta(minutes=ORDER_EXPIRY_MINUTES)
    pending = PendingOrder(
        id=new_id(),
        user_id=user_id,
        course_id=course_id,
        provider_order_id=provider_order_id,   # canonical model field name
        amount=amount,
        currency=currency,
        provider="paypal",
        status=PendingOrderStatus.pending,
        created_at=utcnow(),
        expires_at=expires_at,
    )
    db.session.add(pending)
    db.session.commit()

    return {
        "approval_url":      approval_url,
        "provider_order_id": provider_order_id,
        "course_id":         course_id,
    }


def capture_order(user_id: str, provider_order_id: str) -> dict:
    """
    Capture a PayPal order and fulfill the purchase.

    Fully idempotent: a second call for the same order returns the existing
    purchase record without re-charging.

    Returns
    -------
    dict with keys: course_id, course_slug, course_title, purchase_id.
    """
    # Fast-path: already fulfilled — return existing data.
    existing_purchase = Purchase.query.filter_by(
        provider_payment_id=provider_order_id,
        status=PurchaseStatus.completed,
    ).first()
    if existing_purchase:
        course = existing_purchase.course
        return {
            "course_id":    existing_purchase.course_id,
            "course_slug":  course.slug  if course else "",
            "course_title": course.title if course else "",
            "purchase_id":  existing_purchase.id,
        }

    # Retrieve pending order.
    pending = PendingOrder.query.filter_by(provider_order_id=provider_order_id).first()
    if not pending:
        raise NotFoundError("Order not found. It may have expired.")
    if pending.user_id != user_id:
        raise ForbiddenError("This order does not belong to your account.")
    if pending.expires_at < utcnow():
        raise ConflictError("This order has expired. Please start a new purchase.")

    course = Course.query.get(pending.course_id)
    if not course:
        raise NotFoundError("The purchased course no longer exists.")

    # Capture with PayPal (skipped in demo mode).
    capture_id: str | None = None
    if not current_app.config["PAYPAL_DEMO_MODE"]:
        try:
            capture_data = _paypal_capture_order(provider_order_id)
            # Extract the capture ID from the PayPal response.
            capture_id = (
                capture_data
                .get("purchase_units", [{}])[0]
                .get("payments", {})
                .get("captures", [{}])[0]
                .get("id")
            )
        except Exception as exc:
            log.error("PayPal capture failed for order %s: %s", provider_order_id, exc)
            raise ConflictError("Payment capture failed. Please contact support.")
    else:
        # Demo mode: use the provider_order_id as a synthetic capture ID.
        capture_id = f"DEMO-CAPTURE-{new_id()}"

    now = utcnow()

    # Create the fulfilled Purchase record.
    purchase = Purchase(
        id=new_id(),
        user_id=user_id,
        course_id=pending.course_id,
        amount=pending.amount,
        currency=pending.currency,
        provider="paypal",
        # provider_payment_id is the gateway capture ID (spec: nullable until capture).
        provider_payment_id=capture_id,
        status=PurchaseStatus.completed,
        created_at=now,
        completed_at=now,
    )
    db.session.add(purchase)

    # Mark pending order as captured.
    pending.status = PendingOrderStatus.captured

    # Grant course enrollment.
    existing_enroll = Enrollment.query.filter_by(
        user_id=user_id, course_id=pending.course_id
    ).first()
    if not existing_enroll:
        enroll = Enrollment(
            id=new_id(),
            user_id=user_id,
            course_id=pending.course_id,
            source="purchase",   # spec field: tracks how enrollment was granted
            is_active=True,
            created_at=now,
        )
        db.session.add(enroll)
    else:
        existing_enroll.is_active = True
        existing_enroll.source    = "purchase"

    db.session.commit()

    log.info(
        "Purchase completed: user=%s course=%s purchase=%s",
        user_id, pending.course_id, purchase.id,
    )

    return {
        "course_id":    pending.course_id,
        "course_slug":  course.slug,
        "course_title": course.title,
        "purchase_id":  purchase.id,
    }


def handle_webhook(payload: bytes, headers: dict) -> None:
    """
    Receive and store a PayPal webhook event payload.

    Stores the raw bytes as text (verbatim) for auditability and HMAC replay.
    Deduplicates on event_id.  Processing is dispatched to the RQ worker.
    """
    # PayPal transmits a unique ID per event delivery attempt.
    event_id = headers.get("PAYPAL-TRANSMISSION-ID", "") or None

    try:
        payload_text = payload.decode("utf-8")
    except Exception:
        payload_text = payload.decode("latin-1")

    # Deduplicate by event_id.
    if event_id:
        existing = WebhookEvent.query.filter_by(event_id=event_id).first()
        if existing:
            log.info("Webhook: duplicate event %s, skipping", event_id)
            return

    event = WebhookEvent(
        id=new_id(),
        provider="paypal",
        event_id=event_id or new_id(),   # generate synthetic ID if header absent
        raw_payload=payload_text,        # stored as Text per spec, not JSON
        processed=False,
        created_at=utcnow(),
    )
    db.session.add(event)
    db.session.commit()

    # Dispatch to RQ worker for async processing.
    try:
        from ..tasks.webhook import process_webhook_event
        from ..extensions import get_task_queue
        q = get_task_queue()
        q.enqueue(process_webhook_event, event.id)
    except Exception as exc:
        log.warning("Could not enqueue webhook processing: %s — falling back to sync", exc)
        _process_webhook_sync(event)


def _process_webhook_sync(event: WebhookEvent) -> None:
    """Synchronous fallback webhook processor (used when Redis is unavailable)."""
    from ..tasks.webhook import _fulfill_payment_capture
    try:
        payload_dict = json.loads(event.raw_payload)
        event_type   = payload_dict.get("event_type", "")
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            order_id = (
                payload_dict
                .get("resource", {})
                .get("supplementary_data", {})
                .get("related_ids", {})
                .get("order_id")
            )
            if order_id:
                _fulfill_payment_capture(order_id)
        event.processed = True
    except Exception as exc:
        log.error("Synchronous webhook processing failed: %s", exc)
    db.session.commit()
