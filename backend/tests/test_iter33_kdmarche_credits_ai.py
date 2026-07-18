"""Iter 33 — Backend tests for KDMARCHÉ public stats + vendor credits + AI Studio (no LLM cost calls)."""
import os
import io
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
VENDOR_ID = "vendor-demo-pro"
PRODUCT_ID = "vp-damoiseau-rhum-blanc"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PWD}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def hdr(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- Public stats ---
def test_public_kdmarche_stats():
    r = requests.get(f"{BASE}/api/public/kdmarche-stats", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("products", "vendors", "zones", "orders", "buyers"):
        assert k in d, f"missing {k}"
        assert isinstance(d[k], int)
        assert d[k] > 0, f"{k}={d[k]} should be > 0"


# --- Vendor credits GET ---
def test_vendor_credits_public():
    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert isinstance(d["credits"], int)
    assert len(d["pricing"]) == 5
    actions = {p["action"] for p in d["pricing"]}
    assert actions == {"product_submission", "photo_upload", "ai_image_generation", "ai_image_enhance", "ai_video_generation"}
    assert isinstance(d["transactions"], list)


# --- Admin credit pricing ---
def test_admin_credit_pricing_requires_auth():
    r = requests.get(f"{BASE}/api/admin/credit-pricing", timeout=15)
    assert r.status_code in (401, 403), r.text


def test_admin_credit_pricing_list(hdr):
    r = requests.get(f"{BASE}/api/admin/credit-pricing", headers=hdr, timeout=15)
    assert r.status_code == 200
    assert len(r.json()["pricing"]) == 5


def test_admin_credit_pricing_update_and_restore(hdr):
    # Update photo_upload to 2
    r = requests.put(f"{BASE}/api/admin/credit-pricing", headers=hdr,
                     json={"action": "photo_upload", "cost": 2}, timeout=15)
    assert r.status_code == 200
    assert r.json()["cost"] == 2
    # Verify
    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    pu = next(p for p in r.json()["pricing"] if p["action"] == "photo_upload")
    assert pu["cost"] == 2
    # Restore to 1
    r = requests.put(f"{BASE}/api/admin/credit-pricing", headers=hdr,
                     json={"action": "photo_upload", "cost": 1}, timeout=15)
    assert r.status_code == 200
    assert r.json()["cost"] == 1


# --- Admin grant credits (add and revert) ---
def test_admin_grant_credits_add_and_revert(hdr):
    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    initial = r.json()["credits"]

    r = requests.post(f"{BASE}/api/admin/vendors/{VENDOR_ID}/credits", headers=hdr,
                      json={"amount": 10}, timeout=15)
    assert r.status_code == 200
    assert r.json()["credits"] == initial + 10

    r = requests.post(f"{BASE}/api/admin/vendors/{VENDOR_ID}/credits", headers=hdr,
                      json={"amount": -10}, timeout=15)
    assert r.status_code == 200
    assert r.json()["credits"] == initial


# --- AI status ---
def test_ai_status():
    r = requests.get(f"{BASE}/api/vendor/ai/status", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert d["images"] is True
    assert d["video"] is False


def test_ai_video_503_no_credit_charge():
    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    before = r.json()["credits"]

    r = requests.post(f"{BASE}/api/vendor/ai/{VENDOR_ID}/{PRODUCT_ID}/generate-video",
                      json={"prompt": "test"}, timeout=15)
    assert r.status_code == 503, r.text
    assert "FAL_KEY" in r.json()["detail"] or "fal.ai" in r.json()["detail"].lower()

    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    after = r.json()["credits"]
    assert after == before, f"credits changed on 503: {before} -> {after}"


# --- Photo upload should 400 when product already has 3 photos WITHOUT consuming credits ---
def test_photo_upload_max_3_no_credit_charge():
    # Check current photos count
    r = requests.get(f"{BASE}/api/vendor/products/{VENDOR_ID}", timeout=15)
    assert r.status_code == 200
    products = r.json() if isinstance(r.json(), list) else r.json().get("products", [])
    prod = next((p for p in products if p["id"] == PRODUCT_ID), None)
    assert prod is not None, f"product {PRODUCT_ID} not found"
    n_photos = len(prod.get("images") or [])
    print(f"Product has {n_photos} photos")

    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    before = r.json()["credits"]

    # PNG 1x1
    png = bytes.fromhex(
        "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
        "0000000D49444154789C63000100000005000101"
        "0D0A2DB40000000049454E44AE426082"
    )
    files = {"file": ("t.png", io.BytesIO(png), "image/png")}
    r = requests.post(f"{BASE}/api/vendor/products/{VENDOR_ID}/{PRODUCT_ID}/upload-image",
                      files=files, timeout=20)
    if n_photos >= 3:
        assert r.status_code == 400, r.text
        assert "3" in r.json().get("detail", "")
    else:
        # Product doesn't have 3 photos — skip strict check (would consume credit)
        pytest.skip(f"Product only has {n_photos} photos; skipping to avoid modifying product")

    r = requests.get(f"{BASE}/api/vendor/credits/{VENDOR_ID}", timeout=15)
    after = r.json()["credits"]
    assert after == before, f"credits changed on 400: {before} -> {after}"
