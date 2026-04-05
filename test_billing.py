"""
Billing tests (PayPal demo mode).

Covers:
  - create-order for a premium course (demo mode)
  - Reject create-order for free course
  - Reject duplicate purchase
  - capture-order: idempotent fulfillment, creates enrollment
  - Expired/missing order returns 404/409
  - Auth guards on both endpoints
  - Admin purchases list
  - Admin webhook-events list

FIELD NAME CONTRACT (must match SQLAlchemy models exactly)
----------------------------------------------------------
Purchase     : provider_payment_id          (NOT paypal_order_id)
PendingOrder : provider_order_id            (NOT paypal_order_id)
WebhookEvent : event_id                     (NOT provider_event_id)
API response : provider_order_id            (billing service key name)
"""
from __future__ import annotations

from flask import Flask
from flask.testing import FlaskClient

from tests.conftest import get_or_create_admin, create_free_course, create_premium_course


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_login(client: FlaskClient, suffix: str = "") -> str:
    email = f"buyer{suffix}@test.com"
    client.post("/api/auth/register", json={
        "email": email, "name": f"Buyer {suffix}", "password": "securepass123",
    })
    client.post("/api/auth/login", json={"email": email, "password": "securepass123"})
    return email


def _setup_admin(client: FlaskClient, suffix: str = "a") -> None:
    from tests.conftest import make_admin
    email = f"billing_admin_{suffix}@test.com"
    client.post("/api/auth/register", json={
        "email": email, "name": "Billing Admin", "password": "securepass123",
    })
    make_admin(email)
    client.post("/api/auth/login", json={"email": email, "password": "securepass123"})


# ── create-order ───────────────────────────────────────────────────────────────

def test_create_order_demo_mode_returns_approval_url(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "co1")

    resp = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    assert resp.status_code == 201, resp.json
    body = resp.json
    assert "approval_url"      in body
    assert "provider_order_id" in body          # canonical response key (not paypal_order_id)
    assert body["provider_order_id"].startswith("DEMO-")
    assert "billing/success" in body["approval_url"]


def test_create_order_free_course_returns_409(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_free_course(admin_id)
    _register_login(client, "co2")

    resp = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    assert resp.status_code == 409


def test_create_order_requires_auth(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    fresh    = client.application.test_client()
    resp     = fresh.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    assert resp.status_code == 401


def test_create_order_missing_course_id_returns_422(client: FlaskClient):
    _register_login(client, "co3")
    resp = client.post("/api/billing/create-order", json={})
    assert resp.status_code == 422


def test_create_order_unknown_course_returns_404(client: FlaskClient):
    _register_login(client, "co4")
    resp = client.post("/api/billing/create-order", json={"course_id": "does-not-exist"})
    assert resp.status_code == 404


def test_create_order_duplicate_purchase_returns_409(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "co5")
    me        = client.get("/api/auth/me")
    user_id   = me.json["user"]["id"]

    # Simulate a completed purchase using canonical field names
    from stemquest.extensions import db
    from stemquest.models.billing import Purchase, PurchaseStatus
    from stemquest.utils.helpers import new_id, utcnow

    db.session.add(Purchase(
        id=new_id(),
        user_id=user_id,
        course_id=data["course_id"],
        amount=29.99,
        currency="USD",
        provider="paypal",
        provider_payment_id=f"EXISTING-{new_id()}",  # canonical (not paypal_order_id)
        status=PurchaseStatus.completed,
        created_at=utcnow(),
        completed_at=utcnow(),
    ))
    db.session.commit()

    resp = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    assert resp.status_code == 409


# ── capture-order ──────────────────────────────────────────────────────────────

def test_capture_order_demo_fulfills_and_returns_course(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "cap1")

    # Create order
    order_resp        = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    provider_order_id = order_resp.json["provider_order_id"]  # canonical response key

    # Capture using canonical request body key (route also accepts paypal_order_id as alias)
    cap_resp = client.post("/api/billing/capture", json={"provider_order_id": provider_order_id})
    assert cap_resp.status_code == 200, cap_resp.json
    body = cap_resp.json
    assert body["course_id"]   == data["course_id"]
    assert body["course_slug"] == "test-premium-course"
    assert body["purchase_id"] is not None


def test_capture_order_creates_enrollment(client: FlaskClient, app: Flask):
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "cap2")
    me       = client.get("/api/auth/me")
    user_id  = me.json["user"]["id"]

    order_resp        = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    provider_order_id = order_resp.json["provider_order_id"]
    client.post("/api/billing/capture", json={"provider_order_id": provider_order_id})

    # Verify enrollment was created
    from stemquest.models.enrollment import Enrollment
    enroll = Enrollment.query.filter_by(
        user_id=user_id, course_id=data["course_id"], is_active=True
    ).first()
    assert enroll is not None


def test_capture_order_is_idempotent(client: FlaskClient, app: Flask):
    """Calling capture twice for the same order must return the same purchase."""
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "cap3")

    order_resp        = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    provider_order_id = order_resp.json["provider_order_id"]

    resp1 = client.post("/api/billing/capture", json={"provider_order_id": provider_order_id})
    resp2 = client.post("/api/billing/capture", json={"provider_order_id": provider_order_id})

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json["purchase_id"] == resp2.json["purchase_id"]


def test_capture_order_unknown_order_id_returns_404(client: FlaskClient):
    _register_login(client, "cap4")
    resp = client.post("/api/billing/capture", json={"provider_order_id": "FAKE-ORDER-ID"})
    assert resp.status_code == 404


def test_capture_order_requires_auth(client: FlaskClient):
    fresh = client.application.test_client()
    resp  = fresh.post("/api/billing/capture", json={"provider_order_id": "ANY-ID"})
    assert resp.status_code == 401


def test_capture_order_wrong_user_returns_403(client: FlaskClient, app: Flask):
    """User B must not be able to capture an order that belongs to User A."""
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)

    # User A creates the order
    _register_login(client, "capA")
    order_resp        = client.post("/api/billing/create-order", json={"course_id": data["course_id"]})
    provider_order_id = order_resp.json["provider_order_id"]

    # User B tries to capture it
    client_b = app.test_client()
    client_b.post("/api/auth/register", json={
        "email": "capB@test.com", "name": "Buyer B", "password": "securepass123",
    })
    client_b.post("/api/auth/login", json={"email": "capB@test.com", "password": "securepass123"})

    resp = client_b.post("/api/billing/capture", json={"provider_order_id": provider_order_id})
    assert resp.status_code == 403


def test_capture_expired_order_returns_409(client: FlaskClient, app: Flask):
    """An order whose expires_at is in the past must be rejected."""
    admin_id = get_or_create_admin()
    data     = create_premium_course(admin_id)
    _register_login(client, "capexp")
    me       = client.get("/api/auth/me")
    user_id  = me.json["user"]["id"]

    # Insert an expired PendingOrder directly using canonical field names
    from stemquest.extensions import db
    from stemquest.models.billing import PendingOrder, PendingOrderStatus
    from stemquest.utils.helpers import new_id, utcnow
    from datetime import timedelta

    expired_order_id = f"EXPIRED-{new_id()}"
    now              = utcnow()
    db.session.add(PendingOrder(
        id=new_id(),
        user_id=user_id,
        course_id=data["course_id"],
        provider_order_id=expired_order_id,  # canonical (not paypal_order_id)
        amount=29.99,
        currency="USD",
        provider="paypal",
        status=PendingOrderStatus.pending,
        created_at=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),  # expired 1 hour ago
    ))
    db.session.commit()

    resp = client.post("/api/billing/capture", json={"provider_order_id": expired_order_id})
    assert resp.status_code == 409


# ── Admin billing views ────────────────────────────────────────────────────────

def test_admin_purchases_list(client: FlaskClient, app: Flask):
    _setup_admin(client, "plist")
    resp = client.get("/api/admin/purchases")
    assert resp.status_code == 200
    body = resp.json
    assert "items"    in body
    assert "total"    in body
    assert "page"     in body
    assert "per_page" in body


def test_admin_purchases_list_requires_admin(client: FlaskClient):
    _register_login(client, "plistguard")
    resp = client.get("/api/admin/purchases")
    assert resp.status_code == 403


def test_admin_webhook_events_list(client: FlaskClient, app: Flask):
    _setup_admin(client, "wh1")
    resp = client.get("/api/admin/webhook-events")
    assert resp.status_code == 200
    assert "items" in resp.json


def test_admin_webhook_events_requires_admin(client: FlaskClient):
    _register_login(client, "whguard")
    resp = client.get("/api/admin/webhook-events")
    assert resp.status_code == 403


# ── Webhook receiver ───────────────────────────────────────────────────────────

def test_paypal_webhook_always_returns_200(client: FlaskClient):
    """The webhook endpoint must always return 200 to prevent PayPal retry storms."""
    resp = client.post(
        "/api/webhooks/paypal",
        data=b'{"event_type":"PAYMENT.CAPTURE.COMPLETED","id":"EVT-001"}',
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json["received"] is True


def test_paypal_webhook_deduplicates_events(client: FlaskClient):
    """The same PAYPAL-TRANSMISSION-ID must not be stored twice."""
    headers = {"PAYPAL-TRANSMISSION-ID": "DEDUP-TXID-001"}
    payload = b'{"event_type":"TEST","id":"DEDUP-TXID-001"}'

    client.post("/api/webhooks/paypal", data=payload,
                content_type="application/json", headers=headers)
    client.post("/api/webhooks/paypal", data=payload,
                content_type="application/json", headers=headers)

    from stemquest.models.billing import WebhookEvent
    # canonical field is event_id (not provider_event_id)
    count = WebhookEvent.query.filter_by(event_id="DEDUP-TXID-001").count()
    assert count == 1
