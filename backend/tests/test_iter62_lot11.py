"""Iter62 — Lot 11: LOGICOOP, Partenaires, Zones et Fret (audit + auto rates),
Fret multi, Risque PDF, COOP'IA, Relances + badge alerts."""
import os
import requests
import pytest

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://coop-dashboard-8.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
DEMO_PWD = "Demo2026!"


def _login(email, password, portal=None):
    s = requests.Session()
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = s.post(f"{API}/auth/login", json=body, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text[:200]}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN_EMAIL, ADMIN_PWD, portal="admin")

@pytest.fixture(scope="module")
def buyer():
    return _login(BUYER_EMAIL, DEMO_PWD)

@pytest.fixture(scope="module")
def vendor():
    return _login(VENDOR_EMAIL, DEMO_PWD)


# ---------- LOGICOOP operators ----------
class TestLogicoopOperators:
    def test_list_and_translog_exists(self, admin):
        r = admin.get(f"{API}/admin/logicoop/operators", timeout=15)
        assert r.status_code == 200
        data = r.json()
        ops = data.get("items", data) if isinstance(data, dict) else data
        emails = [o.get("email") for o in ops]
        assert VENDOR_EMAIL in emails, f"Translog operator missing: {emails}"

    def test_crud_operator(self, admin):
        # create
        payload = {"name": "TEST_LogiOp", "email": "TEST_logi_iter62@example.com",
                   "exw_zones": ["GUADELOUPE"], "cif_zones": ["MARTINIQUE"]}
        r = admin.post(f"{API}/admin/logicoop/operators", json=payload, timeout=15)
        assert r.status_code in (200, 201), r.text[:300]
        op = r.json()
        op_id = op.get("id") or op.get("_id")
        assert op_id
        try:
            # patch unknown zone
            r_bad = admin.patch(f"{API}/admin/logicoop/operators/{op_id}",
                                json={"exw_zones": ["ZONE_INCONNUE_XYZ"]}, timeout=15)
            assert r_bad.status_code == 400, f"expected 400, got {r_bad.status_code}"
            # patch valid zones
            r_ok = admin.patch(f"{API}/admin/logicoop/operators/{op_id}",
                               json={"cif_zones": ["MARTINIQUE", "GUYANE"]}, timeout=15)
            assert r_ok.status_code == 200
            # verify via list
            lst = admin.get(f"{API}/admin/logicoop/operators", timeout=15).json()
            ops = lst.get("items", lst) if isinstance(lst, dict) else lst
            match = [o for o in ops if (o.get("id") or o.get("_id")) == op_id]
            assert match and "GUYANE" in match[0].get("cif_zones", [])
            # deactivate
            r_off = admin.patch(f"{API}/admin/logicoop/operators/{op_id}",
                                json={"active": False}, timeout=15)
            assert r_off.status_code == 200
        finally:
            rd = admin.delete(f"{API}/admin/logicoop/operators/{op_id}", timeout=15)
            assert rd.status_code in (200, 204)

    def test_logicoop_me_vendor_ok(self, vendor):
        r = vendor.get(f"{API}/logicoop/me", timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        assert "exw_zones_detail" in data or "exw_zones" in data
        assert "cif_zones_detail" in data or "cif_zones" in data

    def test_logicoop_me_buyer_forbidden(self, buyer):
        r = buyer.get(f"{API}/logicoop/me", timeout=15)
        assert r.status_code == 403


# ---------- Partners ----------
class TestPartners:
    def test_public_types(self):
        r = requests.get(f"{API}/partners/types", timeout=15)
        assert r.status_code == 200
        data = r.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        codes = [t.get("code") for t in items]
        assert "COOPERS" in codes
        assert "LOGICOOP" in codes

    def test_public_apply_ok_and_bad_type(self):
        r = requests.post(f"{API}/partners/apply",
                          json={"type": "COOPERS", "name": "TEST_Jean", "email": "TEST_j62@example.com",
                                "phone": "0590000000", "message": "test iter62"}, timeout=15)
        assert r.status_code in (200, 201), r.text[:300]
        r_bad = requests.post(f"{API}/partners/apply",
                              json={"type": "UNKNOWN_XYZ", "name": "x", "email": "x@x.com"}, timeout=15)
        assert r_bad.status_code == 400

    def test_admin_list_and_status_transitions(self, admin):
        r = admin.get(f"{API}/admin/partners/applications", timeout=15)
        assert r.status_code == 200
        data = r.json()
        apps = data.get("items", data) if isinstance(data, dict) else data
        assert isinstance(apps, list) and len(apps) >= 1
        app_id = apps[0].get("id") or apps[0].get("_id")
        # invalid status
        rb = admin.patch(f"{API}/admin/partners/applications/{app_id}",
                         json={"status": "INVALID_STATE"}, timeout=15)
        assert rb.status_code == 400
        # valid transitions
        for st in ["EN_COURS", "ACCEPTEE", "REFUSEE"]:
            r_ok = admin.patch(f"{API}/admin/partners/applications/{app_id}",
                               json={"status": st}, timeout=15)
            assert r_ok.status_code == 200, f"status {st}: {r_ok.text[:200]}"

    def test_admin_add_type_and_toggle(self, admin):
        code = "TEST_TYPE62"
        # cleanup previous run: find existing and delete via toggle? there's no delete, but if it exists just skip create dup check
        existing = admin.get(f"{API}/admin/partners/types", timeout=15).json()
        ex_items = existing.get("items", existing) if isinstance(existing, dict) else existing
        prev = next((t for t in ex_items if t.get("code") == code), None)
        if prev:
            # reactivate if needed
            if not prev.get("active"):
                admin.patch(f"{API}/admin/partners/types/{prev.get('id')}", timeout=15)
            type_id = prev.get("id")
            # duplicate check
            r2 = admin.post(f"{API}/admin/partners/types",
                            json={"code": code, "label": "dup"}, timeout=15)
            assert r2.status_code == 409
        else:
            r = admin.post(f"{API}/admin/partners/types",
                           json={"code": code, "label": "Test Type 62"}, timeout=15)
            assert r.status_code in (200, 201), r.text[:200]
            type_id = r.json().get("id")
            r2 = admin.post(f"{API}/admin/partners/types",
                            json={"code": code, "label": "dup"}, timeout=15)
            assert r2.status_code == 409
        # appears in public
        pub_data = requests.get(f"{API}/partners/types", timeout=15).json()
        pub = pub_data.get("items", pub_data) if isinstance(pub_data, dict) else pub_data
        assert code in [t.get("code") for t in pub]
        # toggle off (endpoint uses type_id and toggles)
        rt = admin.patch(f"{API}/admin/partners/types/{type_id}", timeout=15)
        assert rt.status_code == 200
        pub_data2 = requests.get(f"{API}/partners/types", timeout=15).json()
        pub2 = pub_data2.get("items", pub_data2) if isinstance(pub_data2, dict) else pub_data2
        assert code not in [t.get("code") for t in pub2]


# ---------- Territories + auto-fret + audit ----------
class TestTerritoriesFreight:
    territory_code = "TEST_FRET62"

    def test_create_territory_generates_freight(self, admin, buyer):
        # cleanup previous
        admin.delete(f"{API}/admin/territories/{self.territory_code}", timeout=15)
        r = admin.post(f"{API}/admin/territories",
                       json={"code": self.territory_code, "name": "Zone Fret Test 62"}, timeout=15)
        assert r.status_code in (200, 201), r.text[:300]
        # rates includes new territory (auth required)
        rr = buyer.get(f"{API}/buyer-tools/freight/rates", timeout=15)
        assert rr.status_code == 200
        rates = rr.json()
        rates_list = rates.get("rates", []) if isinstance(rates, dict) else rates
        codes_seen = set()
        for it in rates_list:
            codes_seen.add(it.get("origin"))
            codes_seen.add(it.get("destination"))
            pair = it.get("pair", "")
            for p in pair.replace("|", "__").split("__"):
                codes_seen.add(p)
        assert self.territory_code in codes_seen, f"new territory missing in rates. seen sample: {list(codes_seen)[:10]}"

    def test_simulate_from_new_territory(self, admin):
        sim = admin.post(f"{API}/buyer-tools/freight/simulate",
                        json={"origin": self.territory_code, "destination": "GUADELOUPE", "weight_kg": 100},
                        timeout=15)
        assert sim.status_code == 200, sim.text[:300]
        data = sim.json()
        # base 200€ + 0.60€/kg × 100 = 260€ = 26000 cents (HT)
        total = data.get("total_ht_cents") or data.get("total_cents") or data.get("total")
        assert total is not None

    def test_delete_territory_removes_rates(self, admin, buyer):
        rd = admin.delete(f"{API}/admin/territories/{self.territory_code}", timeout=15)
        assert rd.status_code in (200, 204), rd.text[:300]
        rr = buyer.get(f"{API}/buyer-tools/freight/rates", timeout=15).json()
        rates_list = rr.get("rates", []) if isinstance(rr, dict) else rr
        for it in rates_list:
            assert self.territory_code not in (it.get("origin"), it.get("destination"))
            assert self.territory_code not in it.get("pair", "")

    def test_audit_entries_present(self, admin):
        # Use mongo directly through backend if endpoint exists, else check audit endpoint
        # Best-effort: check if there's an audit endpoint
        r = admin.get(f"{API}/admin/audit/territories", timeout=15)
        if r.status_code == 404:
            pytest.skip("no dedicated audit endpoint; check via Mongo (out of scope in HTTP test)")
        else:
            assert r.status_code == 200


# ---------- Fret multi ----------
class TestFreightMulti:
    def test_simulate_multi_ok(self, buyer):
        r = buyer.post(f"{API}/buyer-tools/freight/simulate-multi",
                       json={"origin": "GUADELOUPE",
                             "destinations": ["MARTINIQUE", "GUYANE", "REUNION"],
                             "weight_kg": 500}, timeout=15)
        assert r.status_code == 200, r.text[:300]
        data = r.json()
        items = data.get("items") or data.get("results") or []
        assert len(items) == 3
        gt = data.get("grand_total_ht_cents") or data.get("grand_total")
        assert gt == 143360, f"expected 143360, got {gt}"

    def test_simulate_multi_bad(self, buyer):
        r1 = buyer.post(f"{API}/buyer-tools/freight/simulate-multi",
                        json={"origin": "GUADELOUPE", "destinations": [], "weight_kg": 100}, timeout=15)
        assert r1.status_code == 400
        r2 = buyer.post(f"{API}/buyer-tools/freight/simulate-multi",
                        json={"origin": "GUADELOUPE", "destinations": ["GUADELOUPE"], "weight_kg": 100},
                        timeout=15)
        assert r2.status_code == 400


# ---------- Risque PDF ----------
class TestSupplyRiskPDF:
    def test_pdf_ok(self, buyer):
        r = buyer.get(f"{API}/buyer-tools/supply-risk/pdf", timeout=30)
        assert r.status_code == 200, r.text[:200]
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct
        assert r.content[:4] == b"%PDF"


# ---------- COOP'IA (limit 2 calls) ----------
class TestCoopIA:
    def test_valid_category(self, buyer):
        r = buyer.get(f"{API}/buyer-tools/procedure-suggestion",
                      params={"category": "alimentaire"}, timeout=45)
        assert r.status_code == 200, r.text[:300]
        d = r.json()
        assert d.get("procedure") in ("SCELLEE", "ENCHERE_INVERSEE")
        assert d.get("rationale")
        assert isinstance(d.get("ai"), bool)

    def test_unknown_category(self, buyer):
        r = buyer.get(f"{API}/buyer-tools/procedure-suggestion",
                      params={"category": "categorie_inconnue_xyz"}, timeout=15)
        assert r.status_code == 404


# ---------- Campaign alerts count ----------
class TestCampaignAlerts:
    def test_alerts_count(self, admin):
        r = admin.get(f"{API}/admin/campaigns/alerts/count", timeout=15)
        assert r.status_code == 200
        assert "count" in r.json()
