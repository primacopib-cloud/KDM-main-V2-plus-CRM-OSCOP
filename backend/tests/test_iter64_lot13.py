"""Iter 64 — Lot 13 KDMARCHÉ × O'SCOP.
Tests: (1) mission status LOGICOOP lifecycle, (2) audit CSV export, (3) email décision candidature.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
DEMO_PASS = "Demo2026!"


def _login(email, password, portal=None):
    s = requests.Session()
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = s.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    assert r.status_code == 200, f"Login failed {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN_EMAIL, ADMIN_PASS, portal="admin")


@pytest.fixture(scope="module")
def vendor_sess():
    return _login(VENDOR_EMAIL, DEMO_PASS)


@pytest.fixture(scope="module")
def buyer_sess():
    return _login(BUYER_EMAIL, DEMO_PASS)


# ---------- 1) LOGICOOP Missions ----------

class TestMissionStatus:
    def test_missions_available(self, vendor_sess):
        r = vendor_sess.get(f"{BASE_URL}/api/logicoop/missions", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        # We need at least one ENLEVEMENT mission without logistics
        pytest.mission_items = items
        print(f"Missions found: {len(items)}")
        assert len(items) >= 1, "Expected at least 1 mission for vendor-pro/Translog"
        # Pick the first mission without logistics
        cand = [m for m in items if not m.get("logistics")]
        assert cand, "Expected a mission without logistics (reset done)"
        pytest.order_id = cand[0]["order_id"]
        print(f"Selected order_id: {pytest.order_id}")

    def test_livree_before_prise_returns_409(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "LIVREE"}, timeout=15)
        assert r.status_code == 409
        assert "prise" in r.text.lower() or "charge" in r.text.lower()

    def test_prise_en_charge_ok(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "PRISE_EN_CHARGE"}, timeout=15)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_re_prise_tolere_or_ok(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "PRISE_EN_CHARGE"}, timeout=15)
        # Tolerated re-take (200) — or explicit reject (409). We accept both but flag if !=200.
        assert r.status_code in (200, 409), r.text
        print(f"Re-prise status: {r.status_code}")

    def test_livree_ok(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "LIVREE"}, timeout=15)
        assert r.status_code == 200, r.text

    def test_re_livree_returns_409(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "LIVREE"}, timeout=15)
        assert r.status_code == 409
        assert "déjà livrée" in r.text or "deja livree" in r.text.lower() or "livrée" in r.text.lower()

    def test_invalid_status_400(self, vendor_sess):
        r = vendor_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                             json={"status": "FOO"}, timeout=15)
        assert r.status_code == 400

    def test_buyer_forbidden_403(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/logicoop/missions/{pytest.order_id}/status",
                            json={"status": "PRISE_EN_CHARGE"}, timeout=15)
        assert r.status_code == 403

    def test_buyer_orders_include_logistics(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/v2/orders", timeout=15)
        assert r.status_code == 200
        orders = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
        if isinstance(orders, dict):
            orders = orders.get("items", [])
        match = [o for o in orders if o.get("id") == pytest.order_id]
        assert match, f"Order {pytest.order_id} not visible to buyer"
        logistics = match[0].get("logistics")
        assert logistics, f"logistics missing: {match[0]}"
        assert logistics.get("status") == "LIVREE"
        assert "Translog" in (logistics.get("operator_name") or "")
        print(f"Buyer logistics: {logistics}")


# ---------- 2) Audit CSV Export ----------

class TestAuditCSV:
    def test_export_csv_admin(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/audit/export.csv", timeout=20)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "").lower()
        content = r.content
        assert content.startswith(b"\xef\xbb\xbf"), "Missing BOM UTF-8"
        text = content.decode("utf-8-sig")
        first = text.split("\n", 1)[0]
        assert first.strip() == "seq;horodatage_utc;evenement;acteur;consultation_id;details;sha256", first
        print(f"CSV rows: {text.count(chr(10))}")

    def test_export_csv_filtered(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/audit/export.csv?event_type=TERRITORY_CREATED", timeout=20)
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        lines = [l for l in text.split("\n") if l.strip()]
        for line in lines[1:]:
            assert "TERRITORY_CREATED" in line, f"Non-filter line: {line[:120]}"
        print(f"Filtered lines: {len(lines)-1}")

    def test_export_csv_buyer_403(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/admin/audit/export.csv", timeout=15)
        assert r.status_code == 403


# ---------- 3) Email décision candidature ----------

class TestPartnerDecisionEmail:
    def test_find_marie_durand(self, admin_sess):
        r = admin_sess.get(f"{BASE_URL}/api/admin/partners/applications", timeout=15)
        assert r.status_code == 200
        items = r.json().get("items", [])
        marie = [a for a in items if "durand" in (a.get("name") or "").lower() and a.get("email") == BUYER_EMAIL]
        assert marie, f"Marie Durand application not found (email={BUYER_EMAIL})"
        pytest.marie_id = marie[0]["id"]
        pytest.marie_initial_status = marie[0].get("status")
        print(f"Marie ID: {pytest.marie_id}, status: {pytest.marie_initial_status}")

    def test_accept_ok(self, admin_sess):
        r = admin_sess.patch(f"{BASE_URL}/api/admin/partners/applications/{pytest.marie_id}",
                             json={"status": "ACCEPTEE"}, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_invalid_status_400(self, admin_sess):
        r = admin_sess.patch(f"{BASE_URL}/api/admin/partners/applications/{pytest.marie_id}",
                             json={"status": "FOO"}, timeout=15)
        assert r.status_code == 400

    def test_unknown_id_404(self, admin_sess):
        r = admin_sess.patch(f"{BASE_URL}/api/admin/partners/applications/does-not-exist-xxx",
                             json={"status": "ACCEPTEE"}, timeout=15)
        assert r.status_code == 404

    def test_reset_to_encours(self, admin_sess):
        # Reset to EN_COURS (bypass decision statuses to avoid another Brevo email)
        r = admin_sess.patch(f"{BASE_URL}/api/admin/partners/applications/{pytest.marie_id}",
                             json={"status": "EN_COURS"}, timeout=15)
        assert r.status_code == 200
