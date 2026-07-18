"""Iter42 — Tests backend: Espace COOPER, Partnership, Registre CSV/PDF + suspend/reactivate + ACL."""
import os
import io
import time
import uuid
import requests
import pytest
from pymongo import MongoClient
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
COOPER = ("cooper-test@kdmarche.fr", "CooperNew2026!")
BUYER = ("acheteur-pro@kdmarche.fr", "Demo2026!")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_s(): return _login(*ADMIN)


@pytest.fixture(scope="module")
def cooper_s(): return _login(*COOPER)


@pytest.fixture(scope="module")
def buyer_s(): return _login(*BUYER)


@pytest.fixture(scope="module")
def mongo_db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


# ============== COOPER — adhesions / carriers / assign ==============
class TestCooperEspace:
    def test_cooper_adhesions_list(self, cooper_s):
        r = cooper_s.get(f"{BASE_URL}/api/cooper/adhesions", timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "applications" in j and "count" in j

    def test_cooper_carriers_list_has_transcaraibes(self, cooper_s):
        r = cooper_s.get(f"{BASE_URL}/api/cooper/carriers", timeout=15)
        assert r.status_code == 200
        carriers = r.json()["carriers"]
        names = [c["name"] for c in carriers]
        assert any("TransCaraïbes" in n for n in names), f"TransCaraïbes not in {names}"

    def test_cooper_cannot_create_carrier(self, cooper_s):
        r = cooper_s.post(f"{BASE_URL}/api/cooper/carriers",
                          json={"name": "TEST_carrier_forbidden", "territory": "GUADELOUPE"}, timeout=15)
        assert r.status_code == 403, f"Expected 403 got {r.status_code}"

    def test_buyer_cannot_list_adhesions(self, buyer_s):
        r = buyer_s.get(f"{BASE_URL}/api/cooper/adhesions", timeout=15)
        assert r.status_code == 403

    def test_admin_create_carrier_and_cooper_assign(self, admin_s, cooper_s, mongo_db):
        # create carrier via admin
        cname = f"TEST_carrier_{uuid.uuid4().hex[:6]}"
        r = admin_s.post(f"{BASE_URL}/api/cooper/carriers",
                         json={"name": cname, "territory": "GUADELOUPE"}, timeout=15)
        assert r.status_code == 200, r.text
        carrier_id = r.json()["id"]

        # pick an existing order or skip
        order = mongo_db.orders.find_one({}, {"id": 1})
        if not order:
            pytest.skip("No order to assign carrier")
        order_id = order["id"]
        r = cooper_s.post(f"{BASE_URL}/api/cooper/orders/{order_id}/assign-carrier",
                          json={"carrier_id": carrier_id}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json()["carrier"] == cname
        # verify persistence
        o = mongo_db.orders.find_one({"id": order_id}, {"_id": 0})
        assert o["carrier"]["id"] == carrier_id
        # cleanup
        mongo_db.logiscop_carriers.delete_one({"id": carrier_id})


# ============== PARTNERSHIP ==============
class TestPartnership:
    partnership_id = None

    def test_public_submit_no_auth(self):
        payload = {
            "structure_name": "TEST_Transporteur XYZ",
            "partner_type": "LOGISCOP",
            "territory": "GUADELOUPE",
            "contact_name": "Jean Test",
            "contact_email": f"test-{uuid.uuid4().hex[:6]}@test.fr",
            "contact_phone": "+590690000000",
            "message": "Demande test iter42 — au moins 10 caractères."
        }
        r = requests.post(f"{BASE_URL}/api/partnership/request", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["ok"] is True
        assert j["reference"].startswith("PART-")
        TestPartnership.partnership_id = j["reference"]

    def test_non_admin_cannot_list_requests(self, buyer_s):
        r = buyer_s.get(f"{BASE_URL}/api/partnership/admin/requests", timeout=15)
        assert r.status_code == 403

    def test_admin_list_requests(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/partnership/admin/requests", timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert "requests" in j and "counts" in j
        assert len(j["requests"]) >= 1

    def test_admin_change_status_recue_to_en_negociation(self, admin_s, mongo_db):
        req = mongo_db.partnership_requests.find_one({"reference": TestPartnership.partnership_id}, {"id": 1})
        assert req, "created partnership not found"
        r = admin_s.patch(f"{BASE_URL}/api/partnership/admin/requests/{req['id']}/status",
                          json={"status": "EN_NEGOCIATION", "note": "TEST — test iter42"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["status"] == "EN_NEGOCIATION"
        doc = mongo_db.partnership_requests.find_one({"id": req["id"]}, {"_id": 0})
        assert doc["status"] == "EN_NEGOCIATION"
        actions = [h["action"] for h in doc["history"]]
        assert "EN_NEGOCIATION" in actions

    def test_admin_coopers_list(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/partnership/admin/coopers", timeout=15)
        assert r.status_code == 200
        j = r.json()
        assert j["count"] >= 1
        emails = [c["email"] for c in j["coopers"]]
        assert any("cooper-test" in e for e in emails)


# ============== REGISTRE — export CSV/PDF + suspend/reactivate ==============
class TestRegistry:
    def test_export_csv(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/v2/admin/member-registry/export?member_type=BUYER_PRO&format=csv", timeout=20)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "Raison sociale" in r.text or "\ufeffRaison" in r.text

    def test_export_pdf(self, admin_s):
        r = admin_s.get(f"{BASE_URL}/api/v2/admin/member-registry/export?member_type=BUYER_PRO&format=pdf", timeout=20)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"

    def test_suspend_and_reactivate(self, admin_s, mongo_db):
        m = mongo_db.member_registry.find_one({"member_type": "BUYER_PRO"}, {"org_id": 1, "status": 1})
        if not m:
            pytest.skip("no buyer_pro in registry")
        oid = m["org_id"]
        r = admin_s.patch(f"{BASE_URL}/api/v2/admin/member-registry/{oid}/status",
                          json={"status": "SUSPENDED", "reason": "TEST iter42 suspend"}, timeout=15)
        assert r.status_code == 200
        doc = mongo_db.member_registry.find_one({"org_id": oid}, {"_id": 0})
        assert doc["status"] == "SUSPENDED"
        assert any(h["reason"] == "TEST iter42 suspend" for h in doc["history"])
        # reactivate
        r = admin_s.patch(f"{BASE_URL}/api/v2/admin/member-registry/{oid}/status",
                          json={"status": "ACTIVE", "reason": "TEST iter42 reactivate"}, timeout=15)
        assert r.status_code == 200
        doc = mongo_db.member_registry.find_one({"org_id": oid}, {"_id": 0})
        assert doc["status"] == "ACTIVE"

    def test_suspend_requires_reason(self, admin_s, mongo_db):
        m = mongo_db.member_registry.find_one({"member_type": "BUYER_PRO"}, {"org_id": 1})
        if not m:
            pytest.skip("no buyer_pro")
        r = admin_s.patch(f"{BASE_URL}/api/v2/admin/member-registry/{m['org_id']}/status",
                          json={"status": "SUSPENDED"}, timeout=15)
        assert r.status_code in (400, 422)


# ============== BUYER non-régression ==============
class TestBuyerNonRegression:
    def test_buyer_can_view_catalog(self, buyer_s):
        # Try common catalog endpoints
        endpoints = ["/api/v2/catalog/products", "/api/products", "/api/catalog/products"]
        ok = False
        for e in endpoints:
            r = buyer_s.get(f"{BASE_URL}{e}", timeout=15)
            if r.status_code == 200:
                ok = True
                break
        assert ok, "No working catalog endpoint returned 200"
