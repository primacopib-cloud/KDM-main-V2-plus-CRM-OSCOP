"""Iter39 — Spot diffusion grid + reservation security + register account_type.

Scope validated by review request (URL from env, no hardcoding).
The 24h/5cc reservation is expected to run ONCE (explicitly authorized).
"""
import os
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
VENDOR = ("vendor-pro@kdmarche.fr", "Demo2026!")
BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")
VENDOR_ID = "vendor-demo-pro"
PRODUCT_ID = "vp-damoiseau-rhum-blanc"

mongo = MongoClient(MONGO_URL)[DB_NAME]


def _login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def tokens():
    return {"admin": _login(*ADMIN), "vendor": _login(*VENDOR), "buyer": _login(*BUYER)}


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---- Grid ----
def test_public_diffusion_grid():
    r = requests.get(f"{BASE_URL}/api/diffusion-grid", timeout=10)
    assert r.status_code == 200
    data = r.json()
    opts = data["options"]
    assert data["total"] == len(opts) >= 3
    labels = {(o["unit"], o["quantity"], o["price_credits"]) for o in opts}
    assert ("hours", 24, 5) in labels
    assert ("days", 7, 15) in labels
    assert ("months", 1, 40) in labels


def test_admin_grid_requires_auth(tokens):
    assert requests.get(f"{BASE_URL}/api/admin/diffusion-grid", timeout=10).status_code in (401, 403)
    r = requests.get(f"{BASE_URL}/api/admin/diffusion-grid", headers=h(tokens["admin"]), timeout=10)
    assert r.status_code == 200
    assert "options" in r.json()


def test_admin_grid_rejects_invalid_payload(tokens):
    bad_unit = requests.post(f"{BASE_URL}/api/admin/diffusion-grid",
                             headers=h(tokens["admin"]),
                             json={"unit": "weeks", "quantity": 2, "price_credits": 10}, timeout=10)
    assert bad_unit.status_code == 400
    bad_qty = requests.post(f"{BASE_URL}/api/admin/diffusion-grid",
                            headers=h(tokens["admin"]),
                            json={"unit": "days", "quantity": 0, "price_credits": 10}, timeout=10)
    assert bad_qty.status_code == 400


# ---- Vendor diffusion security ----
def test_book_requires_auth():
    r = requests.post(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}/{PRODUCT_ID}/book",
                      json={"grid_id": "x"}, timeout=10)
    assert r.status_code in (401, 403)


def test_book_buyer_forbidden(tokens):
    r = requests.post(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}/{PRODUCT_ID}/book",
                      headers=h(tokens["buyer"]), json={"grid_id": "x"}, timeout=10)
    assert r.status_code == 403


def test_vendor_diffusions_lists_active(tokens):
    r = requests.get(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}",
                     headers=h(tokens["vendor"]), timeout=10)
    assert r.status_code == 200
    diffs = r.json()["diffusions"]
    # Expect at least 1 ACTIVE
    active = [d for d in diffs if d["status"] == "ACTIVE"]
    assert len(active) >= 1, f"expected at least 1 active diffusion, got {diffs}"


# ---- Paid reservation (authorized to run ONCE — 24h/5cc) ----
def test_book_24h_success_and_insufficient(tokens):
    # Get 24h option
    grid = requests.get(f"{BASE_URL}/api/diffusion-grid", timeout=10).json()["options"]
    opt24 = next(o for o in grid if o["unit"] == "hours" and o["quantity"] == 24)
    opt1m = next(o for o in grid if o["unit"] == "months" and o["quantity"] == 1)

    # Balance before
    vendor_doc = mongo.vendors.find_one({"id": VENDOR_ID}, {"_id": 0, "credits": 1})
    balance_before = int(vendor_doc["credits"])
    print(f"[iter39] balance_before = {balance_before}")

    # Existing active ends_at (for prolongation check)
    r_before = requests.get(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}",
                            headers=h(tokens["vendor"]), timeout=10).json()
    prev_active = [d for d in r_before["diffusions"] if d["status"] == "ACTIVE"
                   and d["product_id"] == PRODUCT_ID]
    prev_end = prev_active[0]["ends_at"] if prev_active else None

    # Book 24h
    r = requests.post(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}/{PRODUCT_ID}/book",
                      headers=h(tokens["vendor"]), json={"grid_id": opt24["id"]}, timeout=15)
    assert r.status_code == 200, f"book 24h failed: {r.status_code} {r.text}"
    body = r.json()
    assert body["status"] == "SUCCESS"
    assert body["credits_left"] == balance_before - 5
    diff = body["diffusion"]
    if prev_end:
        assert diff["starts_at"] == prev_end, f"prolongation: starts_at should equal previous ends_at ({prev_end}) got {diff['starts_at']}"

    # DB checks
    v = mongo.vendors.find_one({"id": VENDOR_ID}, {"_id": 0, "credits": 1})
    assert int(v["credits"]) == balance_before - 5

    tx = mongo.credit_transactions.find_one(
        {"vendor_id": VENDOR_ID, "action": "spot_diffusion"}, sort=[("at", -1)])
    assert tx is not None
    assert tx["cost"] == 5

    # Now attempt 1 month (40cc) with insufficient balance -> should be 402, balance unchanged
    balance_now = int(v["credits"])
    if balance_now < 40:
        r2 = requests.post(f"{BASE_URL}/api/vendor/diffusion/{VENDOR_ID}/{PRODUCT_ID}/book",
                           headers=h(tokens["vendor"]), json={"grid_id": opt1m["id"]}, timeout=15)
        assert r2.status_code == 402, f"expected 402, got {r2.status_code} {r2.text}"
        v2 = mongo.vendors.find_one({"id": VENDOR_ID}, {"_id": 0, "credits": 1})
        assert int(v2["credits"]) == balance_now, "atomic debit: balance should not change on failed booking"
    else:
        pytest.skip(f"balance {balance_now} >= 40, cannot test insufficient credits path")


# ---- Public gallery filter ----
def test_public_gallery_only_active():
    r = requests.get(f"{BASE_URL}/api/public/kdmarche-videos", timeout=10)
    assert r.status_code == 200
    items = r.json().get("videos", [])
    names = [i.get("product_name") or i.get("name") or "" for i in items]
    print(f"[iter39] public gallery items: {names}")
    joined = " | ".join(names).lower()
    assert "rhum blanc" in joined, f"expected Rhum blanc in gallery, got {names}"
    assert "vsop" not in joined, f"VSOP should not be in gallery, got {names}"


# ---- Register account_type ----
def test_register_vendor_and_buyer_and_cleanup():
    ts = int(time.time())
    v_email = f"qa-vendeur-{ts}@test.fr"
    b_email = f"qa-acheteur-{ts}@test.fr"
    payload_common = {"password": "TestPass2026!", "siret": "12345678901234",
                       "contact_name": "QA Test", "phone": "0600000000",
                       "country": "FR"}

    r_v = requests.post(f"{BASE_URL}/api/auth/register", json={
        **payload_common, "email": v_email, "company_name": "QA Vendeur",
        "account_type": "vendor"}, timeout=15)
    assert r_v.status_code == 201, f"register vendor: {r_v.status_code} {r_v.text}"

    r_b = requests.post(f"{BASE_URL}/api/auth/register", json={
        **payload_common, "email": b_email, "company_name": "QA Acheteur",
        "account_type": "buyer"}, timeout=15)
    assert r_b.status_code == 201, f"register buyer: {r_b.status_code} {r_b.text}"

    try:
        u_v = mongo.users.find_one({"email": v_email})
        u_b = mongo.users.find_one({"email": b_email})
        assert u_v and u_v.get("role") == "vendor" and u_v.get("vendor_id")
        assert u_b and u_b.get("role") == "buyer"
        assert "vendor_id" not in u_b or not u_b.get("vendor_id")

        vendor_doc = mongo.vendors.find_one({"id": u_v["vendor_id"]})
        assert vendor_doc and vendor_doc["status"] == "pending"
        assert int(vendor_doc.get("credits", 0)) == 0

        # Both can login
        for email in (v_email, b_email):
            lg = requests.post(f"{BASE_URL}/api/auth/login",
                               json={"email": email, "password": "TestPass2026!"}, timeout=10)
            assert lg.status_code == 200, f"login {email}: {lg.status_code} {lg.text}"
    finally:
        # Cleanup
        if u_v:
            if u_v.get("vendor_id"):
                mongo.vendors.delete_one({"id": u_v["vendor_id"]})
            mongo.users.delete_one({"email": v_email})
        if u_b:
            mongo.users.delete_one({"email": b_email})


# ---- Regression ----
def test_me_crediscop(tokens):
    r = requests.get(f"{BASE_URL}/api/me/crediscop", headers=h(tokens["vendor"]), timeout=10)
    assert r.status_code == 200
    body = r.json()
    assert "balance" in body or "credits" in body
    assert isinstance(body.get("balance", body.get("credits")), int)


def test_public_plans():
    r = requests.get(f"{BASE_URL}/api/public/plans", timeout=10)
    assert r.status_code == 200
    plans = r.json().get("plans", r.json())
    assert len(plans) == 3
