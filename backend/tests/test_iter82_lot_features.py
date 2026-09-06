"""Iter82 - CommunityPlace board join, LOLODRIVE visitor catalog, pro catalog visitor, admin CSV/visitor toggle."""
import os
import re
import pytest
import requests

def _load_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v.rstrip("/")
    env_path = "/app/frontend/.env"
    with open(env_path) as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().rstrip("/")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


BASE = _load_backend_url()
API = f"{BASE}/api"

ADMIN = {"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"}
BUYER_PRO = {"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="module")
def buyer_pro_token():
    r = requests.post(f"{API}/auth/login", json=BUYER_PRO, timeout=15)
    assert r.status_code == 200, r.text
    return r.json().get("token") or r.json().get("access_token")


# ---- Community board / join
class TestCommunityBoard:
    def test_public_board_has_joiners_fields(self):
        r = requests.get(f"{API}/public/community-board", timeout=15)
        assert r.status_code == 200
        demands = r.json()["demands"]
        assert isinstance(demands, list)
        assert len(demands) > 0
        for d in demands:
            assert "joiners_count" in d and isinstance(d["joiners_count"], int)
            assert "joined_quantity" in d and isinstance(d["joined_quantity"], int)
        refs = {d["reference"] for d in demands}
        assert "BES-2026-0901" in refs

    def test_join_success_and_duplicate_and_404(self):
        import uuid as _u
        email = f"test-join-{_u.uuid4().hex[:8]}@example.com"
        # Get initial counts
        r0 = requests.get(f"{API}/public/community-board", timeout=15).json()["demands"]
        initial = next(d for d in r0 if d["reference"] == "BES-2026-0901")
        r = requests.post(f"{API}/public/purchase-needs/BES-2026-0901/join",
                          json={"email": email, "quantity": 6}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["joiners_count"] == initial["joiners_count"] + 1
        assert body["joined_quantity"] == initial["joined_quantity"] + 6
        # Duplicate
        r2 = requests.post(f"{API}/public/purchase-needs/BES-2026-0901/join",
                           json={"email": email, "quantity": 3}, timeout=15)
        assert r2.status_code == 409
        # 404
        r3 = requests.post(f"{API}/public/purchase-needs/BES-DOES-NOT-EXIST/join",
                           json={"email": email, "quantity": 3}, timeout=15)
        assert r3.status_code == 404


# ---- Admin CSV export
class TestCommunityPlaceCSV:
    def test_csv_export_admin(self, admin_token):
        r = requests.get(f"{API}/admin/purchase-needs/stats/csv",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        assert "text/csv" in r.headers.get("content-type", "")
        text = r.text.lstrip("\ufeff")
        assert text.startswith("mois;revenus_eur")
        assert "TOTAL;" in text


# ---- LOLODRIVE visitor catalog
class TestLolodriveVisitorCatalog:
    def test_public_no_auth_returns_visitor_products_no_prices(self):
        r = requests.get(f"{API}/lolodrive/catalog/public", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data.get("visitor") is True
        products = data["products"]
        skus = {p["sku"] for p in products}
        for expected in ("RIZ-5KG", "LAIT-1L", "HUILE-1L", "FARINE-1KG"):
            assert expected in skus, f"Missing {expected} in visitor catalog"
        for p in products:
            assert "price_public_cents" not in p
            assert "price_pass_cents" not in p


# ---- LOLODRIVE admin visitor visibility
class TestVisitorVisibility:
    def test_list_and_toggle(self, admin_token):
        h = {"Authorization": f"Bearer {admin_token}"}
        r = requests.get(f"{API}/lolodrive/admin/products/visitor-visibility", headers=h, timeout=15)
        assert r.status_code == 200
        skus = {p["sku"] for p in r.json()["products"]}
        assert "RIZ-5KG" in skus
        # Toggle off
        r2 = requests.patch(f"{API}/lolodrive/admin/products/RIZ-5KG/visitor-visible",
                            json={"visible": False}, headers=h, timeout=15)
        assert r2.status_code == 200
        # Verify absent from public
        pub = requests.get(f"{API}/lolodrive/catalog/public", timeout=15).json()
        assert "RIZ-5KG" not in {p["sku"] for p in pub["products"]}
        # Restore
        r3 = requests.patch(f"{API}/lolodrive/admin/products/RIZ-5KG/visitor-visible",
                            json={"visible": True}, headers=h, timeout=15)
        assert r3.status_code == 200
        pub2 = requests.get(f"{API}/lolodrive/catalog/public", timeout=15).json()
        assert "RIZ-5KG" in {p["sku"] for p in pub2["products"]}


# ---- Pro catalog visitor vs buyer
class TestProCatalogVisitor:
    def test_visitor_only_flagged_no_prices(self):
        r = requests.get(f"{API}/v2/catalog/products", timeout=15)
        assert r.status_code == 200, r.text
        products = r.json()
        assert isinstance(products, list)
        # all shown products should not expose prices to visitors
        for p in products:
            # unit_price should be null/absent or price_visible False
            pv = p.get("price_visible")
            if pv is True:
                pytest.fail(f"Visitor received price_visible=true for {p.get('sku')}")

    def test_buyer_pro_gets_full_catalog(self, buyer_pro_token):
        r = requests.get(f"{API}/v2/catalog/products",
                         headers={"Authorization": f"Bearer {buyer_pro_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        products = r.json()
        assert len(products) >= 1
        # visitor scope: should return at least as many products or more (typically more)
        visitor = requests.get(f"{API}/v2/catalog/products", timeout=15).json()
        assert len(products) >= len(visitor)
