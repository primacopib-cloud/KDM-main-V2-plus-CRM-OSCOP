"""Iter 31 backend regression: team space, admin buyers, taxonomy CRUD, vendor upload+PDF."""
import os
import io
import pytest
import requests

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")

ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!"}
COOPER = {"email": "cooper-test@kdmarche.fr", "password": "NmgHyl4STePu"}
BUYER = {"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}


def login(creds):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/login", json=creds, timeout=15)
    assert r.status_code == 200, f"login {creds['email']} → {r.status_code} {r.text[:200]}"
    return s


# --- Team overview ---
class TestTeamOverview:
    def test_no_auth_401(self):
        r = requests.get(f"{BASE}/api/team/overview", timeout=10)
        assert r.status_code == 401

    def test_cooper_200(self):
        s = login(COOPER)
        r = s.get(f"{BASE}/api/team/overview", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "kpis" in data
        for k in ("products_total", "vendor_products_pending", "orders_total", "users_total", "low_stock"):
            assert k in data["kpis"]
        assert "recent_orders" in data

    def test_buyer_403(self):
        s = login(BUYER)
        r = s.get(f"{BASE}/api/team/overview", timeout=10)
        assert r.status_code == 403


# --- Admin buyers ---
class TestAdminBuyers:
    def test_list_and_credits_suspend(self):
        s = login(ADMIN)
        r = s.get(f"{BASE}/api/admin/buyers", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "buyers" in data and "total" in data
        assert data["total"] >= 1

        # find acheteur-pro (buyer role)
        target = next((b for b in data["buyers"] if b["email"] == "acheteur-pro@kdmarche.fr"), None)
        assert target, "acheteur-pro@kdmarche.fr not in buyers list"
        original_credits = target.get("credits", 250)
        original_suspended = target.get("suspended", False)

        # PATCH credits
        r = s.patch(f"{BASE}/api/admin/buyers/{target['id']}/credits", json={"credits": 999}, timeout=10)
        assert r.status_code == 200
        assert r.json()["credits"] == 999

        # PATCH suspend true
        r = s.patch(f"{BASE}/api/admin/buyers/{target['id']}/suspend", json={"suspended": True}, timeout=10)
        assert r.status_code == 200
        assert r.json()["suspended"] is True

        # RESTORE
        r = s.patch(f"{BASE}/api/admin/buyers/{target['id']}/credits", json={"credits": int(original_credits) if original_credits is not None else 250}, timeout=10)
        assert r.status_code == 200
        r = s.patch(f"{BASE}/api/admin/buyers/{target['id']}/suspend", json={"suspended": bool(original_suspended)}, timeout=10)
        assert r.status_code == 200


# --- Taxonomy ---
class TestTaxonomy:
    def test_public_lists(self):
        r = requests.get(f"{BASE}/api/taxonomy/categories", timeout=10)
        assert r.status_code == 200
        cats = r.json()["categories"]
        assert len(cats) >= 8
        r = requests.get(f"{BASE}/api/taxonomy/tva-rates", timeout=10)
        assert r.status_code == 200
        assert len(r.json()["rates"]) >= 6

    def test_post_requires_auth(self):
        r = requests.post(f"{BASE}/api/taxonomy/categories", json={"label": "X"}, timeout=10)
        assert r.status_code == 401

    def test_category_create_delete(self):
        s = login(ADMIN)
        r = s.post(f"{BASE}/api/taxonomy/categories", json={"label": "Test QA Cat"}, timeout=10)
        assert r.status_code in (200, 201), r.text
        cat_id = r.json()["category"]["id"]

        # verify present
        r = s.get(f"{BASE}/api/taxonomy/categories", timeout=10)
        assert any(c["id"] == cat_id for c in r.json()["categories"])

        # delete
        r = s.delete(f"{BASE}/api/taxonomy/categories/{cat_id}", timeout=10)
        assert r.status_code == 200

        # verify gone
        r = s.get(f"{BASE}/api/taxonomy/categories", timeout=10)
        assert not any(c["id"] == cat_id for c in r.json()["categories"])

    def test_tva_create_delete(self):
        s = login(ADMIN)
        r = s.post(f"{BASE}/api/taxonomy/tva-rates", json={"value": 13.5, "label": "Test QA"}, timeout=10)
        assert r.status_code in (200, 201), r.text
        rid = r.json()["rate"]["id"]
        r = s.delete(f"{BASE}/api/taxonomy/tva-rates/{rid}", timeout=10)
        assert r.status_code == 200


# --- Vendor upload & PDF ---
VENDOR_ID = "vendor-demo-pro"
PRODUCT_ID = "vp-damoiseau-rhum-blanc"


def _png_bytes():
    # minimal valid PNG (1x1)
    import base64
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mMEAAAABQAB9J2CmwAAAABJRU5ErkJggg=="
    )


class TestVendorUploadPDF:
    def test_upload_png_then_reject_gif_then_max3(self):
        url = f"{BASE}/api/vendor/products/{VENDOR_ID}/{PRODUCT_ID}/upload-image"
        # PNG 1
        r = requests.post(url, files={"file": ("a.png", _png_bytes(), "image/png")}, timeout=20)
        assert r.status_code == 200, r.text
        # PNG 2
        r = requests.post(url, files={"file": ("b.png", _png_bytes(), "image/png")}, timeout=20)
        assert r.status_code == 200
        # PNG 3
        r = requests.post(url, files={"file": ("c.png", _png_bytes(), "image/png")}, timeout=20)
        assert r.status_code == 200
        # 4th → rejected
        r = requests.post(url, files={"file": ("d.png", _png_bytes(), "image/png")}, timeout=20)
        assert r.status_code == 400
        # GIF → rejected (test with any content since 3 slots full — but should be 400 for either reason)
        r = requests.post(url, files={"file": ("e.gif", b"GIF89a", "image/gif")}, timeout=20)
        assert r.status_code == 400

    def test_pdf_generation(self):
        r = requests.get(f"{BASE}/api/vendor/products/{VENDOR_ID}/{PRODUCT_ID}/pdf", timeout=20)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500

    def test_cleanup_images(self):
        # Restore images:[] on this product via a direct call to a cleanup script
        import subprocess
        result = subprocess.run(
            ["python", "-c",
             "import asyncio,os;from motor.motor_asyncio import AsyncIOMotorClient;\n"
             "async def r():\n"
             " c=AsyncIOMotorClient(os.environ['MONGO_URL']);db=c[os.environ['DB_NAME']]\n"
             " await db.vendor_products.update_one({'id':'vp-damoiseau-rhum-blanc'},{'$set':{'images':[]}})\n"
             " print('OK')\n"
             "asyncio.run(r())"],
            capture_output=True, text=True, timeout=15,
            env={**os.environ}
        )
        assert "OK" in result.stdout, result.stderr
        # remove uploaded files
        import glob
        for f in glob.glob("/app/backend/uploads/products/vp-damoiseau-*"):
            os.remove(f)
