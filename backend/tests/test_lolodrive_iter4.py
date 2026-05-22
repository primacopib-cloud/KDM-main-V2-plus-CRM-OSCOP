"""
Iteration 4 - Phase 2 backend tests:
- LOLO HOUR (events scope, detail, reserve, cancel, list reservations, link products)
- LOLO POINTS manager dedicated (my-point, my-orders, my-payout-preview)
- Reporting timeseries
- CRM PATCH opps/stage, tasks/status, dossiers/status
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")

ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
MARIE = ("marie@example.com", "Demo2026!")
POS = ("pos@lolodrive.fr", "Demo2026!")
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


# ============ LOLO HOUR ============

class TestLoloHourEvents:
    def test_list_events_scope_all(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/events?scope=all", headers=H(marie_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "events" in data and isinstance(data["events"], list)
        # ev-1 should be in seed
        if data["events"]:
            ev = data["events"][0]
            assert "reservations_count" in ev
            assert "remaining_stock" in ev

    @pytest.mark.parametrize("scope", ["upcoming", "live", "ended", "all"])
    def test_list_events_each_scope(self, marie_token, scope):
        r = requests.get(f"{BASE_URL}/api/lolodrive/events?scope={scope}", headers=H(marie_token))
        assert r.status_code == 200, r.text
        assert isinstance(r.json().get("events"), list)

    def test_event_detail_with_my_reservation_field(self, marie_token):
        # find an event id
        r = requests.get(f"{BASE_URL}/api/lolodrive/events?scope=all", headers=H(marie_token))
        events = r.json().get("events", [])
        if not events:
            pytest.skip("no event seeded")
        ev_id = events[0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/events/{ev_id}", headers=H(marie_token))
        assert r2.status_code == 200, r2.text
        data = r2.json()
        assert data["id"] == ev_id
        assert "my_reservation" in data
        assert "linked_products" in data
        assert "remaining_stock" in data

    def test_reserve_event_marie_then_duplicate(self, marie_token):
        # ev-1 is the standard event per seed
        ev_id = "ev-1"
        # Cancel ALL existing reservations for marie (loop until none)
        for _ in range(10):
            cd = requests.delete(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token))
            if cd.status_code == 404:
                break
        # fetch event to discover per_user_limit
        ev = requests.get(f"{BASE_URL}/api/lolodrive/events/{ev_id}", headers=H(marie_token)).json()
        per_user_limit = ev.get("per_user_limit") or 1
        # Fill up to limit
        for _ in range(per_user_limit):
            # cancel current to free slot, then reserve fresh (CONFIRMED count grows because cancel marks one as CANCELLED)
            r = requests.post(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token), json={})
            if r.status_code == 404:
                pytest.skip("ev-1 not seeded")
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "CONFIRMED"
        # Next reservation must hit limit
        r2 = requests.post(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token), json={})
        assert r2.status_code == 400, r2.text
        assert "Limite" in r2.text or "limite" in r2.text.lower()

    def test_cancel_reservation(self, marie_token):
        ev_id = "ev-1"
        # Ensure one exists (reserve if needed)
        requests.post(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token), json={})
        r = requests.delete(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token))
        if r.status_code == 404:
            pytest.skip("event/reservation absent")
        assert r.status_code == 200, r.text
        assert r.json().get("ok") is True

    def test_reserve_pass_only_requires_pass(self, admin_token):
        # ev-3 is is_pass_only=true per seed. Admin generally has no PASS active.
        ev_id = "ev-3"
        # Cancel previous reservations as admin for safety
        requests.delete(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(admin_token))
        r = requests.post(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(admin_token), json={})
        if r.status_code == 404:
            pytest.skip("ev-3 not seeded")
        assert r.status_code in (403,), f"expected 403, got {r.status_code} {r.text}"

    def test_admin_list_reservations(self, admin_token, marie_token):
        ev_id = "ev-1"
        # Ensure marie has a reservation
        requests.post(f"{BASE_URL}/api/lolodrive/events/{ev_id}/reserve", headers=H(marie_token), json={})
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/events/{ev_id}/reservations", headers=H(admin_token))
        if r.status_code == 404:
            pytest.skip("ev-1 not seeded")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "reservations" in data and isinstance(data["reservations"], list)
        if data["reservations"]:
            sample = data["reservations"][0]
            assert "user_email" in sample
            assert "user_name" in sample

    def test_admin_link_products_to_event(self, admin_token):
        ev_id = "ev-1"
        payload = {"linked_products": [
            {"sku": "SKU-FLASH-1", "flash_price_cents": 199, "flash_price_uc": 20},
            {"sku": "SKU-FLASH-2", "flash_price_cents": 299, "flash_price_uc": 30},
        ]}
        r = requests.post(f"{BASE_URL}/api/lolodrive/admin/events/{ev_id}/products", headers=H(admin_token), json=payload)
        if r.status_code == 404:
            pytest.skip("ev-1 not seeded")
        assert r.status_code == 200, r.text
        assert r.json().get("count") == 2
        # Verify persisted via detail
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/events/{ev_id}", headers=H(admin_token))
        assert r2.status_code == 200
        linked = r2.json().get("linked_products", [])
        skus = {p.get("sku") for p in linked}
        assert "SKU-FLASH-1" in skus and "SKU-FLASH-2" in skus


# ============ LOLO POINTS MANAGER ============

class TestManager:
    def test_manager_my_point_gerant(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-point", headers=H(gerant_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("id") == "lp-2"
        assert data.get("code") == "LP-CAP" or "CAP" in (data.get("name") or "") or data.get("manager_user_id") == "user-gerant-1"

    def test_manager_my_point_admin_no_assign(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-point", headers=H(admin_token))
        assert r.status_code == 404

    def test_manager_my_orders(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-orders", headers=H(gerant_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert "point" in data and "orders" in data
        assert isinstance(data["orders"], list)

    def test_manager_my_payout_preview(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/manager/my-payout-preview", headers=H(gerant_token))
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("calculated_cents", "capped_cents", "components", "caps", "consumption_volume_cents"):
            assert k in data, f"missing {k}"
        assert data["capped_cents"] <= data["calculated_cents"]


# ============ TIMESERIES ============

class TestTimeseries:
    @pytest.mark.parametrize("metric", ["revenue", "orders", "uc_consumed", "pass_activations"])
    def test_timeseries(self, admin_token, metric):
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/timeseries?metric={metric}&days=30", headers=H(admin_token))
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["metric"] == metric
        assert data["days"] == 30
        assert isinstance(data["points"], list)
        for p in data["points"]:
            assert "date" in p and "value" in p

    def test_timeseries_invalid_metric(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/admin/kpi/timeseries?metric=foobar", headers=H(admin_token))
        assert r.status_code == 400


# ============ CRM PATCH ============

class TestCrmPatches:
    def _list_opps(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/opportunities?limit=100", headers=H(admin_token))
        assert r.status_code == 200, r.text
        return r.json().get("opportunities", [])

    def test_update_opp_stage(self, admin_token):
        opps = self._list_opps(admin_token)
        if not opps:
            pytest.skip("no opps seeded")
        opp = opps[0]
        r = requests.patch(f"{BASE_URL}/api/crm/opportunities/{opp['id']}/stage", headers=H(admin_token), json={"stage": "gagne"})
        assert r.status_code == 200, r.text
        assert r.json().get("stage") == "gagne"
        # Verify via list
        r2 = requests.get(f"{BASE_URL}/api/crm/opportunities?stage=gagne", headers=H(admin_token))
        assert r2.status_code == 200
        ids = [o["id"] for o in r2.json().get("opportunities", [])]
        assert opp["id"] in ids

    def test_update_opp_stage_missing_body(self, admin_token):
        opps = self._list_opps(admin_token)
        if not opps:
            pytest.skip("no opps seeded")
        r = requests.patch(f"{BASE_URL}/api/crm/opportunities/{opps[0]['id']}/stage", headers=H(admin_token), json={})
        assert r.status_code == 400

    def test_update_task_status_done(self, admin_token):
        # ensure at least one task exists
        r = requests.get(f"{BASE_URL}/api/crm/tasks", headers=H(admin_token))
        tasks = r.json().get("tasks", [])
        if not tasks:
            # create one
            create = requests.post(f"{BASE_URL}/api/crm/tasks", headers=H(admin_token), json={
                "title": "TEST_task_iter4", "type_action": "RELANCE_PROSPECT", "status": "todo",
            })
            assert create.status_code == 200, create.text
            tid = create.json()["id"]
        else:
            tid = tasks[0]["id"]
        r = requests.patch(f"{BASE_URL}/api/crm/tasks/{tid}/status", headers=H(admin_token), json={"status": "done"})
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "done"

    def test_update_task_status_invalid(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/tasks", headers=H(admin_token))
        tasks = r.json().get("tasks", [])
        if not tasks:
            pytest.skip("no task")
        r = requests.patch(f"{BASE_URL}/api/crm/tasks/{tasks[0]['id']}/status", headers=H(admin_token), json={"status": "WRONG"})
        assert r.status_code == 400

    def test_update_dossier_status(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/crm/dossiers", headers=H(admin_token))
        dossiers = r.json().get("dossiers", [])
        if not dossiers:
            pytest.skip("no dossier seeded")
        did = dossiers[0]["id"]
        r2 = requests.patch(f"{BASE_URL}/api/crm/dossiers/{did}/status", headers=H(admin_token), json={"statut": "cloture"})
        assert r2.status_code == 200, r2.text
        assert r2.json().get("statut") == "cloture"
