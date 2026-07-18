"""Iter 34 — Backend tests for KDMARCHÉ credit packs, promotions, analytics + buyer my-credits.

Coverage:
- GET /api/credit-packs (public) → 3 packs + bonus_percent field
- Credit promotions CRUD (create → applied to packs → update → archive → delete)
- POST /api/credit-packs/purchase → Stripe checkout URL (LIVE: do NOT pay)
- GET /api/credit-packs/status/{sid} → unpaid + applied:false
- GET /api/admin/credit-analytics → totals + ventilations
- Buyer /api/team/my-credits + admin adjustment tx visible then restored
"""
import os
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PWD = "Demo2026!"
VENDOR_ID = "vendor-demo-pro"


def _login(email, pwd):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PWD)


@pytest.fixture(scope="module")
def buyer_token():
    return _login(BUYER_EMAIL, BUYER_PWD)


@pytest.fixture(scope="module")
def admin_hdr(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="module")
def buyer_hdr(buyer_token):
    return {"Authorization": f"Bearer {buyer_token}"}


# --- Credit packs public listing ---
def test_credit_packs_public_lists_three_packs():
    r = requests.get(f"{BASE}/api/credit-packs", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    packs = d["packs"]
    ids = {p["id"] for p in packs}
    assert {"starter", "pro", "studio"}.issubset(ids)
    assert "bonus_percent" in d
    # Bonus should be numeric
    assert isinstance(d["bonus_percent"], (int, float))


# --- Credit promotions CRUD + effect on bonus_percent ---
def test_promotions_requires_auth():
    r = requests.get(f"{BASE}/api/admin/credit-promotions", timeout=15)
    assert r.status_code in (401, 403)
    r = requests.post(f"{BASE}/api/admin/credit-promotions", json={"name": "x", "promo_type": "bonus_purchase", "value_percent": 5}, timeout=15)
    assert r.status_code in (401, 403)


def test_promotion_lifecycle_and_effect_on_pack_bonus(admin_hdr):
    # Create bonus promo 15% vendor
    payload = {"name": "QA Bonus Iter34", "promo_type": "bonus_purchase",
               "value_percent": 15, "scope_profile": "vendor"}
    r = requests.post(f"{BASE}/api/admin/credit-promotions", headers=admin_hdr, json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    promo = r.json()["promotion"]
    pid = promo["id"]

    try:
        # Packs endpoint reflects bonus_percent >= 15 (there could be other active promos, use >= per assertion but expect exactly 15 if none)
        r2 = requests.get(f"{BASE}/api/credit-packs", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["bonus_percent"] >= 15

        # Update to 25%
        upd = {**payload, "value_percent": 25}
        r3 = requests.put(f"{BASE}/api/admin/credit-promotions/{pid}", headers=admin_hdr, json=upd, timeout=15)
        assert r3.status_code == 200, r3.text
        r4 = requests.get(f"{BASE}/api/credit-packs", timeout=15)
        assert r4.json()["bonus_percent"] >= 25

        # Archive → bonus_percent drops back (should no longer include this promo)
        r5 = requests.post(f"{BASE}/api/admin/credit-promotions/{pid}/archive", headers=admin_hdr, timeout=15)
        assert r5.status_code == 200
        r6 = requests.get(f"{BASE}/api/credit-packs", timeout=15)
        # Not this promo's contribution anymore
        assert r6.json()["bonus_percent"] < 25
    finally:
        # Always delete
        r7 = requests.delete(f"{BASE}/api/admin/credit-promotions/{pid}", headers=admin_hdr, timeout=15)
        assert r7.status_code == 200


# --- Stripe checkout session creation (LIVE — do NOT pay) ---
def test_credit_pack_purchase_creates_stripe_session(admin_hdr):
    payload = {"pack_id": "starter", "vendor_id": VENDOR_ID,
               "origin_url": BASE}
    r = requests.post(f"{BASE}/api/credit-packs/purchase", headers=admin_hdr, json=payload, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "url" in d and "checkout.stripe.com" in d["url"]
    sid = d["session_id"]

    # Status polling: should be unpaid + not applied
    r2 = requests.get(f"{BASE}/api/credit-packs/status/{sid}", headers=admin_hdr, timeout=20)
    assert r2.status_code == 200, r2.text
    d2 = r2.json()
    assert d2["applied"] is False
    assert d2["payment_status"] in ("unpaid", "open", "requires_payment_method")


# --- Analytics ---
def test_credit_analytics_requires_auth():
    r = requests.get(f"{BASE}/api/admin/credit-analytics", timeout=15)
    assert r.status_code in (401, 403)


def test_credit_analytics_shape_and_totals(admin_hdr):
    r = requests.get(f"{BASE}/api/admin/credit-analytics", headers=admin_hdr, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    totals = d["totals"]
    for key in ("purchased", "consumed", "refunded", "revenue_eur"):
        assert key in totals
    assert totals["consumed"] > 0  # historical consumption exists
    for key in ("by_service", "by_vendor", "by_territory", "by_category"):
        assert key in d
        assert isinstance(d[key], list)


# --- Buyer my-credits + admin adjustment ---
def test_buyer_my_credits_and_admin_adjustment_roundtrip(admin_hdr, buyer_hdr, buyer_token):
    # Initial state
    r = requests.get(f"{BASE}/api/team/my-credits", headers=buyer_hdr, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    initial_credits = int(d["credits"])
    assert "transactions" in d

    # Fetch buyer id
    r_me = requests.get(f"{BASE}/api/auth/me", headers=buyer_hdr, timeout=15)
    assert r_me.status_code == 200
    buyer_id = r_me.json()["id"]

    # Admin adjusts (add 1 credit)
    new_credits = initial_credits + 1
    r2 = requests.patch(f"{BASE}/api/admin/buyers/{buyer_id}/credits", headers=admin_hdr,
                        json={"credits": new_credits}, timeout=15)
    assert r2.status_code == 200, r2.text

    try:
        # Verify visible in my-credits
        r3 = requests.get(f"{BASE}/api/team/my-credits", headers=buyer_hdr, timeout=15)
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["credits"] == new_credits
        assert any(t.get("action") == "admin_adjustment" and t.get("owner_type") == "buyer"
                   for t in d3["transactions"])
    finally:
        # Restore
        r4 = requests.patch(f"{BASE}/api/admin/buyers/{buyer_id}/credits", headers=admin_hdr,
                            json={"credits": initial_credits}, timeout=15)
        assert r4.status_code == 200
        r5 = requests.get(f"{BASE}/api/team/my-credits", headers=buyer_hdr, timeout=15)
        assert r5.json()["credits"] == initial_credits
