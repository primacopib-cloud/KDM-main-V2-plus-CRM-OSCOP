"""Iter 32 — Mandatory password change on first login + Catalog v2 photo publication."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback for internal test runs
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PASS = "Demo2026!"
TEST_MEMBER_EMAIL = "pwd-test-qa@kdmarche.fr"


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    return r


@pytest.fixture(scope="module")
def admin_token():
    r = _login(ADMIN_EMAIL, ADMIN_PASS)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def cleanup_test_member():
    yield
    # Cleanup at end of module: delete via mongo
    try:
        from pymongo import MongoClient
        with open("/app/backend/.env") as f:
            env = {}
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env[k] = v.strip('"').strip("'")
        client = MongoClient(env["MONGO_URL"])
        db = client[env["DB_NAME"]]
        db.users.delete_one({"email": TEST_MEMBER_EMAIL})
        client.close()
    except Exception as e:
        print(f"Cleanup error: {e}")


# ============ Feature 1: mandatory password change ============

class TestPasswordChangeFlow:
    def test_full_flow(self, admin_token, cleanup_test_member):
        # Pre-cleanup in case a previous run left the user around
        try:
            from pymongo import MongoClient
            with open("/app/backend/.env") as f:
                env = {}
                for line in f:
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        env[k] = v.strip('"').strip("'")
            client = MongoClient(env["MONGO_URL"])
            db = client[env["DB_NAME"]]
            db.users.delete_one({"email": TEST_MEMBER_EMAIL})
            client.close()
        except Exception:
            pass

        # 1) Create member
        r = requests.post(
            f"{BASE_URL}/api/admin/team/create",
            json={"email": TEST_MEMBER_EMAIL, "contact_name": "Pwd Test", "role": "EXPERT"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "SUCCESS"
        temp_pwd = data["temp_password"]
        assert temp_pwd and len(temp_pwd) > 5

        # 2) Login with temp password
        r2 = _login(TEST_MEMBER_EMAIL, temp_pwd)
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body["user"]["must_change_password"] is True
        token = body["access_token"]

        # 3) Error case: wrong current password
        r3 = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": "WRONGPWD123", "new_password": "NewPwdQA2026!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r3.status_code == 400, r3.text

        # 4) Error case: new password too short
        r4 = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": temp_pwd, "new_password": "short"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r4.status_code == 400, r4.text

        # 5) Error case: no auth
        r5 = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": temp_pwd, "new_password": "NewPwdQA2026!"},
        )
        assert r5.status_code in (401, 403), r5.text

        # 6) Success: change password
        r6 = requests.post(
            f"{BASE_URL}/api/auth/change-password",
            json={"current_password": temp_pwd, "new_password": "NewPwdQA2026!"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r6.status_code == 200, r6.text

        # 7) Re-login with new password
        r7 = _login(TEST_MEMBER_EMAIL, "NewPwdQA2026!")
        assert r7.status_code == 200, r7.text
        assert r7.json()["user"]["must_change_password"] is False


# ============ Feature 2: catalog v2 shows product image ============

class TestCatalogV2Photo:
    def test_product_in_catalog(self):
        r = _login(BUYER_EMAIL, BUYER_PASS)
        assert r.status_code == 200
        token = r.json()["access_token"]

        r2 = requests.get(
            f"{BASE_URL}/api/v2/catalog/products",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 200, r2.text
        data = r2.json()
        products = data if isinstance(data, list) else data.get("products", [])
        rhum = next((p for p in products if p.get("id") == "vp-damoiseau-rhum-blanc"), None)
        assert rhum is not None, f"Product not found in catalog. Keys sample: {[p.get('id') for p in products[:5]]}"
        assert rhum.get("image_url") == "/api/uploads/products/vp-damoiseau-rhum-blanc-photo.png", rhum
        assert rhum.get("price_ht_cents") == 1659, rhum
        assert rhum.get("category_name") == "Boissons", rhum
        assert rhum.get("price_visible") is True, rhum

    def test_image_file_accessible(self):
        r = requests.get(f"{BASE_URL}/api/uploads/products/vp-damoiseau-rhum-blanc-photo.png")
        assert r.status_code == 200, r.status_code
        assert r.headers.get("content-type", "").startswith("image/"), r.headers.get("content-type")


class TestApproveIdempotency:
    def test_reapprove_no_duplicate(self, admin_token):
        r = requests.post(
            f"{BASE_URL}/api/vendor/admin/products/vp-damoiseau-rhum-blanc/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert r.status_code == 200, r.text

        # Re-check catalog: no duplicates, both zones active
        r2 = _login(BUYER_EMAIL, BUYER_PASS)
        buyer_token = r2.json()["access_token"]
        r3 = requests.get(
            f"{BASE_URL}/api/v2/catalog/products",
            headers={"Authorization": f"Bearer {buyer_token}"},
        )
        rj = r3.json()
        products = rj if isinstance(rj, list) else rj.get("products", [])
        matches = [p for p in products if p.get("id") == "vp-damoiseau-rhum-blanc"]
        assert len(matches) == 1, f"Duplicates found: {len(matches)}"
        assert matches[0].get("image_url", "").endswith("vp-damoiseau-rhum-blanc-photo.png")
