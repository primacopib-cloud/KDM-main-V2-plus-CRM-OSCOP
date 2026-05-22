"""Iter9 Sprint - PASS Subscription (Stripe natives) + i18n + LOGI'SCOP/O'SCOP pages."""
import os
import pytest
import requests
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to frontend/.env
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                    break
    except Exception:
        pass

MARIE = {"email": "marie@example.com", "password": "Demo2026!"}
ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!"}


def _login(creds):
    r = requests.post(f"{BASE_URL}/api/auth/login", json=creds, timeout=15)
    if r.status_code != 200:
        # try lolodrive login endpoint
        r = requests.post(f"{BASE_URL}/api/lolodrive/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    return data.get("access_token") or data.get("token")


@pytest.fixture(scope="module")
def marie_token():
    return _login(MARIE)


# ============== Subscription endpoints =================

def test_status_without_auth_returns_401():
    r = requests.get(f"{BASE_URL}/api/lolodrive/pass/subscription/status", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"


def test_status_with_marie(marie_token):
    r = requests.get(
        f"{BASE_URL}/api/lolodrive/pass/subscription/status",
        headers={"Authorization": f"Bearer {marie_token}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "has_subscription" in data
    # marie has no Stripe sub yet — has_subscription=False
    if not data["has_subscription"]:
        # is_auto_renew_soft can be true or false
        pass


def test_checkout_with_marie(marie_token):
    r = requests.post(
        f"{BASE_URL}/api/lolodrive/pass/subscription/checkout",
        json={"success_path": "/paiement/retour", "cancel_path": "/pass"},
        headers={"Authorization": f"Bearer {marie_token}"},
        timeout=30,
    )
    # Accept 200 or 502 (Stripe restricted in test sandbox) — must not crash
    assert r.status_code in (200, 502), f"unexpected: {r.status_code} {r.text[:300]}"
    if r.status_code == 200:
        data = r.json()
        assert "url" in data and ("stripe.com" in data["url"] or "stripe" in data["url"])
        assert "session_id" in data
    else:
        # 502 must come with Stripe error message
        assert "Stripe" in r.text or "stripe" in r.text


def test_cancel_without_active_sub(marie_token):
    r = requests.post(
        f"{BASE_URL}/api/lolodrive/pass/subscription/cancel",
        headers={"Authorization": f"Bearer {marie_token}"},
        timeout=15,
    )
    # No stripe_subscription_id on marie's PASS → 404
    assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text[:200]}"


def test_webhook_invoice_paid_idempotent():
    invoice_id = f"in_test_{uuid.uuid4().hex[:8]}"
    payload = {
        "type": "invoice.paid",
        "data": {
            "object": {
                "id": invoice_id,
                "subscription": f"sub_test_{uuid.uuid4().hex[:8]}",
                "customer": f"cus_test_{uuid.uuid4().hex[:8]}",
            }
        },
    }
    r1 = requests.post(
        f"{BASE_URL}/api/lolodrive/pass/subscription/webhook",
        json=payload,
        timeout=15,
    )
    assert r1.status_code == 200, r1.text
    # Second call with same invoice_id → duplicate
    r2 = requests.post(
        f"{BASE_URL}/api/lolodrive/pass/subscription/webhook",
        json=payload,
        timeout=15,
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2.get("duplicate") is True, f"expected duplicate=True, got {data2}"


def test_webhook_subscription_deleted():
    sub_id = f"sub_test_{uuid.uuid4().hex[:8]}"
    payload = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": sub_id}},
    }
    r = requests.post(
        f"{BASE_URL}/api/lolodrive/pass/subscription/webhook",
        json=payload,
        timeout=15,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("subscription_deleted") is True


# ============== Regression: iter8 still works =================

def test_iter8_stripe_mode_endpoint():
    # admin login
    token = _login(ADMIN)
    r = requests.get(
        f"{BASE_URL}/api/lolodrive/admin/stripe/mode",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("mode") == "test"


def test_lolo_points_listing():
    r = requests.get(f"{BASE_URL}/api/lolodrive/lolo-points", timeout=15)
    assert r.status_code == 200
    data = r.json()
    points = data if isinstance(data, list) else data.get("points", [])
    assert len(points) > 0
