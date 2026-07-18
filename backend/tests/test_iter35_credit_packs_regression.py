"""Iter 35 — Non-regression tests for KDMARCHÉ credit packs + credit endpoints.

CRITICAL: Stripe is in LIVE mode. Only create checkout session, do NOT pay.
Do NOT consume vendor credits (no image/video generation calls).
"""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PWD = "Demo2026!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PWD = "Demo2026!"

VENDOR_ID = "vendor-demo-pro"
VIDEO_JOB_ID = "efa3586f-69bb-4cb7-b047-72a25ce3950e"


def _login(email, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def vendor_hdr():
    return {"Authorization": f"Bearer {_login(VENDOR_EMAIL, VENDOR_PWD)}"}


@pytest.fixture(scope="module")
def admin_hdr():
    return {"Authorization": f"Bearer {_login(ADMIN_EMAIL, ADMIN_PWD)}"}


@pytest.fixture(scope="module")
def buyer_hdr():
    return {"Authorization": f"Bearer {_login(BUYER_EMAIL, BUYER_PWD)}"}


# --- Auth regression ---
def test_login_vendor():
    tok = _login(VENDOR_EMAIL, VENDOR_PWD)
    assert isinstance(tok, str) and len(tok) > 10


def test_login_admin():
    tok = _login(ADMIN_EMAIL, ADMIN_PWD)
    assert isinstance(tok, str) and len(tok) > 10


# --- Credit packs listing ---
def test_credit_packs_list_active_three_packs():
    r = requests.get(f"{BASE}/api/credit-packs", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    packs = {p["id"]: p for p in d["packs"]}
    assert {"starter", "pro", "studio"}.issubset(packs.keys())
    # Prices/credits sanity check
    assert packs["starter"]["credits"] == 50 and abs(packs["starter"]["price_eur"] - 9.90) < 0.01
    assert packs["pro"]["credits"] == 200 and abs(packs["pro"]["price_eur"] - 29.90) < 0.01
    assert packs["studio"]["credits"] == 500 and abs(packs["studio"]["price_eur"] - 59.90) < 0.01
    assert "bonus_percent" in d
    assert isinstance(d["bonus_percent"], (int, float))


# --- Purchase → Stripe session (LIVE — no payment) ---
@pytest.fixture(scope="module")
def stripe_session(vendor_hdr):
    payload = {"pack_id": "starter", "vendor_id": VENDOR_ID,
               "origin_url": "https://coop-dashboard-8.preview.emergentagent.com"}
    r = requests.post(f"{BASE}/api/credit-packs/purchase", headers=vendor_hdr, json=payload, timeout=25)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "checkout.stripe.com" in d["url"]
    assert "session_id" in d and d["session_id"].startswith("cs_")
    return d


def test_purchase_returns_stripe_url(stripe_session):
    assert "checkout.stripe.com" in stripe_session["url"]


def test_payment_transaction_persisted_in_db(stripe_session, vendor_hdr):
    # Verify via status endpoint (transaction exists since polling doesn't 404)
    r = requests.get(f"{BASE}/api/credit-packs/status/{stripe_session['session_id']}",
                     headers=vendor_hdr, timeout=20)
    assert r.status_code == 200, r.text


def test_status_unpaid_not_applied(stripe_session, vendor_hdr):
    r = requests.get(f"{BASE}/api/credit-packs/status/{stripe_session['session_id']}",
                     headers=vendor_hdr, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["applied"] is False
    assert d["payment_status"] in ("unpaid", "open", "requires_payment_method")
    assert d.get("credited", 0) == 0


def test_status_from_other_user_returns_403(stripe_session, buyer_hdr):
    r = requests.get(f"{BASE}/api/credit-packs/status/{stripe_session['session_id']}",
                     headers=buyer_hdr, timeout=20)
    assert r.status_code == 403, f"expected 403 got {r.status_code}: {r.text}"


def test_purchase_unknown_pack_returns_404(vendor_hdr):
    payload = {"pack_id": "nonexistent-pack-xyz", "vendor_id": VENDOR_ID,
               "origin_url": "https://coop-dashboard-8.preview.emergentagent.com"}
    r = requests.post(f"{BASE}/api/credit-packs/purchase", headers=vendor_hdr, json=payload, timeout=20)
    assert r.status_code == 404, f"expected 404 got {r.status_code}: {r.text}"


# --- Vendor credits balance ---
def test_vendor_credits_balance_is_152():
    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["credits"] == 152, f"expected 152 credits, got {d['credits']}"
    # Pricing has 5 actions
    assert isinstance(d["pricing"], list)
    assert len(d["pricing"]) >= 5
    actions = {p["action"] for p in d["pricing"]}
    for expected in ("product_submission", "photo_upload", "ai_image_generation",
                     "ai_image_enhance", "ai_video_generation"):
        assert expected in actions, f"missing action {expected}"
    assert isinstance(d["transactions"], list)


# --- Admin credit-analytics ---
def test_credit_analytics_admin(admin_hdr):
    r = requests.get(f"{BASE}/api/admin/credit-analytics", headers=admin_hdr, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    totals = d["totals"]
    for k in ("purchased", "consumed", "refunded", "revenue_eur"):
        assert k in totals, f"missing totals.{k}"
    for k in ("by_service", "by_vendor", "by_territory", "by_category", "by_profile"):
        assert k in d, f"missing {k}"
        assert isinstance(d[k], list)


def test_credit_analytics_non_admin_403(vendor_hdr):
    r = requests.get(f"{BASE}/api/admin/credit-analytics", headers=vendor_hdr, timeout=15)
    assert r.status_code == 403


# --- Vendor AI status & video jobs ---
def test_vendor_ai_status(vendor_hdr):
    r = requests.get(f"{BASE}/api/vendor/ai/status", headers=vendor_hdr, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("images") is True
    assert d.get("video") is True


def test_video_job_error_exhausted_balance(vendor_hdr):
    r = requests.get(f"{BASE}/api/vendor/ai/video-jobs/{VIDEO_JOB_ID}", headers=vendor_hdr, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("status") == "ERROR", f"expected ERROR status, got {d.get('status')}"
    msg = (d.get("message") or d.get("error") or "") + " " + str(d)
    assert "Exhausted balance" in msg or "exhausted" in msg.lower(), f"expected 'Exhausted balance', got: {d}"
