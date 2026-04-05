"""
STEMQuest — Async webhook processing task (RQ job).

Triggered by billing_svc.handle_webhook() after the WebhookEvent row is created.
Designed for exactly-once processing via WebhookEvent.processed boolean flag.

FIELD MAPPING (task → model)
------------------------------
WebhookEvent : processed    (boolean, not a status enum)
               raw_payload  (Text; use json.loads() — NOT event.payload)
               event_id     (not provider_event_id)
Purchase     : provider_payment_id  (not paypal_order_id)
PendingOrder : provider_order_id    (not paypal_order_id)
Enrollment   : created_at           (not enrolled_at)

IMPORT NOTE
-----------
All imports inside _run(), _dispatch(), _fulfill_payment_capture(), and
_ensure_enrollment() use ABSOLUTE package paths (stemquest.models…) rather than
relative imports (..models…).  This is required because RQ loads this module as a
top-level script in the worker process, where relative imports are not resolvable.
process_webhook_event() re-creates the Flask app and pushes an app context before
calling _run(), so all Flask-SQLAlchemy operations work normally.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)


def process_webhook_event(event_id: str) -> None:
    """
    RQ job entry-point.

    Creates a Flask app context (the worker process has none by default) and
    delegates to _run().
    """
    import os
    from stemquest import create_app

    app = create_app(os.environ.get("FLASK_ENV", "production"))
    with app.app_context():
        _run(event_id)


def _run(event_id: str) -> None:
    """
    Main processing logic.  Runs inside the Flask app context.

    Uses WebhookEvent.processed (boolean) — NOT a status enum.
    Uses WebhookEvent.raw_payload (Text) — NOT event.payload.
    """
    from stemquest.extensions import db
    from stemquest.models.billing import WebhookEvent

    event = WebhookEvent.query.get(event_id)
    if event is None:
        log.warning("Webhook task: event %s not found", event_id)
        return

    # already processed — exactly-once guard
    if event.processed:                   # processed boolean (not status enum)
        log.info("Webhook task: event %s already processed — skipping", event_id)
        return

    try:
        _dispatch(event)
        event.processed = True            # processed boolean (not status transition)
    except Exception as exc:              # noqa: BLE001
        # Keep processed=False so admin replay can retry
        log.exception("Webhook task failed for event %s: %s", event_id, exc)
    finally:
        db.session.commit()


def _dispatch(event) -> None:
    """
    Route the webhook event to the appropriate handler.

    raw_payload is stored as Text — parse it with json.loads().
    The event_type lives inside the JSON body under "event_type".
    """
    try:
        # raw_payload is db.Text — must be parsed (not accessed as event.payload)
        payload_dict = json.loads(event.raw_payload)
    except (json.JSONDecodeError, TypeError) as exc:
        log.error(
            "Webhook task: could not parse raw_payload for event %s: %s",
            event.id, exc,
        )
        return

    event_type = payload_dict.get("event_type", "")
    log.info("Webhook task: dispatching event_type=%s (id=%s)", event_type, event.id)

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        # PayPal nests the order ID deep inside the resource object
        order_id = (
            payload_dict
            .get("resource", {})
            .get("supplementary_data", {})
            .get("related_ids", {})
            .get("order_id")
        )
        if order_id:
            _fulfill_payment_capture(order_id)
        else:
            log.warning(
                "PAYMENT.CAPTURE.COMPLETED event %s missing order_id in payload",
                event.id,
            )
    else:
        log.info(
            "Webhook task: unhandled event_type=%s (event_id=%s)",
            event_type, event.id,
        )


def _fulfill_payment_capture(provider_order_id: str) -> None:
    """
    Idempotent post-capture fulfillment.

    Ensures a completed Purchase row exists and that the corresponding
    Enrollment is active.  Safe to call multiple times for the same order.

    FIELD MAPPING:
      Purchase     : provider_payment_id  (not paypal_order_id)
      PendingOrder : provider_order_id    (not paypal_order_id)
      Enrollment   : created_at           (not enrolled_at)
    """
    from stemquest.extensions import db
    from stemquest.models.billing import Purchase, PurchaseStatus, PendingOrder, PendingOrderStatus
    from stemquest.utils.helpers import new_id, utcnow

    # Fast-path: already fulfilled — just ensure enrollment is active
    existing_purchase = Purchase.query.filter_by(
        provider_payment_id=provider_order_id,   # provider_payment_id (not paypal_order_id)
        status=PurchaseStatus.completed,
    ).first()
    if existing_purchase:
        log.info(
            "Webhook fulfill: purchase already completed for order %s", provider_order_id
        )
        _ensure_enrollment(existing_purchase.user_id, existing_purchase.course_id)
        return

    # Locate the pending order using canonical field name
    pending = PendingOrder.query.filter_by(
        provider_order_id=provider_order_id     # provider_order_id (not paypal_order_id)
    ).first()
    if not pending:
        log.warning(
            "Webhook fulfill: no pending order found for %s — may have been captured already",
            provider_order_id,
        )
        return

    now = utcnow()

    purchase = Purchase(
        id=new_id(),
        user_id=pending.user_id,
        course_id=pending.course_id,
        amount=pending.amount,
        currency=pending.currency,
        provider=pending.provider,
        provider_payment_id=provider_order_id,   # provider_payment_id (not paypal_order_id)
        status=PurchaseStatus.completed,
        created_at=now,
        completed_at=now,
    )
    db.session.add(purchase)

    # Mark pending order as captured
    pending.status = PendingOrderStatus.captured

    _ensure_enrollment(pending.user_id, pending.course_id)
    db.session.flush()

    log.info(
        "Webhook fulfill: completed purchase for order %s (user=%s course=%s)",
        provider_order_id, pending.user_id, pending.course_id,
    )


def _ensure_enrollment(user_id: str, course_id: str) -> None:
    """
    Upsert an active Enrollment row.
    If one already exists but is inactive, re-activate it.
    Uses ``created_at`` (not ``enrolled_at``).
    """
    from stemquest.extensions import db
    from stemquest.models.enrollment import Enrollment
    from stemquest.utils.helpers import new_id, utcnow

    existing = Enrollment.query.filter_by(user_id=user_id, course_id=course_id).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.source    = "purchase"
        return

    enrollment = Enrollment(
        id=new_id(),
        user_id=user_id,
        course_id=course_id,
        source="purchase",
        is_active=True,
        created_at=utcnow(),    # created_at (not enrolled_at)
    )
    db.session.add(enrollment)
