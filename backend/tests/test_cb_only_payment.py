"""Tests for cb_only_payment (vendor 'card only' payment mode) feature."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")

VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
PASSWORD = "Demo2026!"
VENDOR_ID = "vendor-demo-pro"
CB_SKU = "DAM-RHUM-BLANC-1L"
OTHER_SKU = "ALI-RIZ-001"


def _login(email):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def vendor_token():
    return _login(VENDOR_EMAIL)


@pytest.fixture(scope="module")
def buyer_token():
    return _login(BUYER_EMAIL)


@pytest.fixture(scope="module", autouse=True)
def restore_state(vendor_token):
    """Ensure cb_only_payment is reset to False at teardown."""
    yield
    requests.put(
        f"{BASE_URL}/api/vendor/profile/{VENDOR_ID}",
        json={"cb_only_payment": False},
        headers={"Authorization": f"Bearer {vendor_token}"},
        timeout=30,
    )


# ============ Vendor profile PUT/GET ============

def test_vendor_profile_toggle_true(vendor_token):
    r = requests.put(
        f"{BASE_URL}/api/vendor/profile/{VENDOR_ID}",
        json={"cb_only_payment": True},
        headers={"Authorization": f"Bearer {vendor_token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    g = requests.get(
        f"{BASE_URL}/api/vendor/profile/{VENDOR_ID}",
        headers={"Authorization": f"Bearer {vendor_token}"},
        timeout=30,
    )
    assert g.status_code == 200
    assert g.json().get("cb_only_payment") is True


def test_cb_only_context_true_when_active(buyer_token):
    r = requests.get(
        f"{BASE_URL}/api/v2/checkout/cb-only-context",
        params={"skus": CB_SKU},
        headers={"Authorization": f"Bearer {buyer_token}"},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["cb_only"] is True
    assert any("Damoiseau" in n for n in data.get("vendor_names", []))


def test_cb_only_context_false_other_sku(buyer_token):
    r = requests.get(
        f"{BASE_URL}/api/v2/checkout/cb-only-context",
        params={"skus": OTHER_SKU},
        headers={"Authorization": f"Bearer {buyer_token}"},
        timeout=30,
    )
    assert r.status_code == 200
    assert r.json()["cb_only"] is False


def test_vendor_profile_toggle_false(vendor_token):
    r = requests.put(
        f"{BASE_URL}/api/vendor/profile/{VENDOR_ID}",
        json={"cb_only_payment": False},
        headers={"Authorization": f"Bearer {vendor_token}"},
        timeout=30,
    )
    assert r.status_code == 200
    r2 = requests.get(
        f"{BASE_URL}/api/v2/checkout/cb-only-context",
        params={"skus": CB_SKU},
        headers={"Authorization": f"Bearer {_login(BUYER_EMAIL)}"},
        timeout=30,
    )
    assert r2.json()["cb_only"] is False
