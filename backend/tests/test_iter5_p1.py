"""
Iteration 5 — Sprint P1 backend tests:
- Manager: my-timeseries (default 30d, 7d), network-ranking (with my_rank for gerant)
- Emergent OAuth scaffolding (POST /session invalid id, GET /me unauthenticated)
- Catalog territory filter (GP / MQ — products with empty territories must be returned in both)
- POS orders territory filter (GP returns Guadeloupe orders, MQ returns 0)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
MARIE = ("marie@example.com", "Demo2026!")
GERANT = ("gerant@lolopoint.fr", "Demo2026!")


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def marie_token():
    return _login(*MARIE)


@pytest.fixture(scope="session")
def gerant_token():
    return _login(*GERANT)


# ---------- Manager: my-timeseries ----------
class TestManagerTimeseries:
    def test_timeseries_30d(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-timeseries?days=30", headers=H(gerant_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "point" in data and data["days"] == 30
        assert "series" in data and isinstance(data["series"], list)
        assert len(data["series"]) == 30
        first = data["series"][0]
        for k in ("date", "orders", "revenue_cents", "fulfilled"):
            assert k in first, f"missing key {k} in series entry"
        # Point is the gerant's lolo point (LP-CAP / lp-2)
        assert data["point"]["code"] in ("LP-CAP",) or data["point"]["id"] == "lp-2"

    def test_timeseries_7d(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-timeseries?days=7", headers=H(gerant_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["days"] == 7
        assert len(data["series"]) == 7

    def test_timeseries_unauthorized(self):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-timeseries", timeout=20)
        # FastAPI HTTPBearer returns 403 when Authorization header missing; accept either
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code} - {r.text}"


# ---------- Manager: network-ranking ----------
class TestManagerNetworkRanking:
    def test_network_ranking(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/network-ranking?days=30", headers=H(gerant_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "ranking" in data and isinstance(data["ranking"], list)
        # All ranked entries have rank
        for i, e in enumerate(data["ranking"]):
            assert "rank" in e
            assert e["rank"] == i + 1
        # Sort desc by revenue_cents (stable on orders)
        revs = [e["revenue_cents"] for e in data["ranking"]]
        assert revs == sorted(revs, reverse=True)
        assert "total_points" in data and data["total_points"] == len(data["ranking"])
        # my_rank must point to gerant's lp-2
        assert data["my_rank"] is not None
        assert data["my_rank"]["point_id"] == "lp-2"
        assert "rank" in data["my_rank"]


# ---------- Emergent OAuth scaffolding ----------
class TestEmergentAuth:
    def test_session_invalid(self):
        r = requests.post(f"{BASE_URL}/api/auth/emergent/session", json={"session_id": "INVALID"}, timeout=20)
        assert r.status_code == 401, f"expected 401, got {r.status_code} - {r.text[:200]}"
        body = r.json()
        assert body.get("detail") == "Session Emergent invalide"

    def test_me_no_cookie(self):
        # Use a fresh session to ensure no cookies
        s = requests.Session()
        r = s.get(f"{BASE_URL}/api/auth/emergent/me", timeout=20)
        assert r.status_code == 401, f"expected 401, got {r.status_code} - {r.text[:200]}"


# ---------- Catalog territory filter ----------
class TestCatalogTerritory:
    def test_catalog_gp(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?territory=GP", headers=H(marie_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        products = data.get("products", data) if isinstance(data, dict) else data
        assert isinstance(products, list)
        assert len(products) >= 1, f"expected products for GP, got {len(products)}"

    def test_catalog_mq(self, marie_token):
        # Default empty territories must return same set of products in MQ as well
        r = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?territory=MQ", headers=H(marie_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        products = data.get("products", data) if isinstance(data, dict) else data
        assert isinstance(products, list)
        assert len(products) >= 1, "MQ should still return products with empty territories field"

    def test_catalog_gp_eq_mq_by_default(self, marie_token):
        r1 = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?territory=GP", headers=H(marie_token), timeout=20)
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?territory=MQ", headers=H(marie_token), timeout=20)
        assert r1.status_code == 200 and r2.status_code == 200
        d1, d2 = r1.json(), r2.json()
        p1 = d1.get("products", d1) if isinstance(d1, dict) else d1
        p2 = d2.get("products", d2) if isinstance(d2, dict) else d2
        ids1 = sorted([p["id"] for p in p1])
        ids2 = sorted([p["id"] for p in p2])
        common = set(ids1) & set(ids2)
        assert len(common) >= 1, "expected at least one product available in both GP & MQ (empty territories array)"


# ---------- POS orders territory filter ----------
class TestPosOrdersTerritory:
    def test_pos_orders_gp(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pos/orders?territory=GP", headers=H(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        orders = data.get("orders", data) if isinstance(data, dict) else data
        assert isinstance(orders, list)
        # Get GP point ids to validate
        rp = requests.get(f"{BASE_URL}/api/lolodrive/lolo-points?territory=GP", timeout=20)
        assert rp.status_code == 200
        pdata = rp.json()
        gp_points = pdata.get("points", pdata) if isinstance(pdata, dict) else pdata
        gp_ids = {p["id"] for p in gp_points}
        for o in orders:
            assert o["lolo_point_id"] in gp_ids, f"order {o.get('id')} has lolo_point_id {o.get('lolo_point_id')} not in GP set"

    def test_pos_orders_mq_empty(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pos/orders?territory=MQ", headers=H(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        orders = data.get("orders", data) if isinstance(data, dict) else data
        assert isinstance(orders, list)
        # Per spec: no orders seeded in Martinique
        assert len(orders) == 0, f"expected 0 MQ orders, got {len(orders)}"
