"""
Iteration 94 backend tests: LOLODRIVE capacités distinctes retrait/livraison,
planning gérant/POS, fulfill, checkout capacité par type, sécurité.
"""
import os
import requests
import pytest

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
# Load MONGO from backend .env
try:
    from dotenv import load_dotenv as _ld
    _ld("/app/backend/.env", override=False)
except Exception:
    pass
API = f"{BASE_URL}/api"

MARIE = ("marie@example.com", "Demo2026!")
GERANT = ("gerant@lolopoint.fr", "Demo2026!")
POS_OP = ("lucie.operateur@lolopoint.fr", "Operateur2026!")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def marie_token():
    return _login(*MARIE)


@pytest.fixture(scope="session")
def gerant_token():
    return _login(*GERANT)


@pytest.fixture(scope="session")
def pos_token():
    return _login(*POS_OP)


# ---------------- Capacités distinctes ----------------

class TestRelayCapacities:
    def test_availability_pickup_capacity_2(self):
        r = requests.get(f"{API}/lolodrive/lolo-points/LP-CAP/availability", params={"kind": "pickup"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # capacity should be 2
        cap = data.get("capacity") or data.get("slot_capacity")
        assert cap == 2, f"pickup capacity expected 2, got {cap}. payload={data}"

    def test_availability_delivery_capacity_1(self):
        r = requests.get(f"{API}/lolodrive/lolo-points/LP-CAP/availability", params={"kind": "delivery"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        cap = data.get("capacity") or data.get("slot_capacity")
        assert cap == 1, f"delivery capacity expected 1, got {cap}. payload={data}"

    def test_calendar_put_rejects_negative_delivery_capacity(self, gerant_token):
        r = requests.put(
            f"{API}/lolodrive/manager/my-point/calendar",
            headers={"Authorization": f"Bearer {gerant_token}"},
            json={"pickup_days": [0, 2, 4], "delivery_days": [1, 3], "closed_dates": [],
                  "slot_capacity": 2, "delivery_slot_capacity": -1},
            timeout=15,
        )
        assert r.status_code == 400, f"expected 400 got {r.status_code} {r.text}"

    def test_calendar_put_accepts_delivery_capacity(self, gerant_token):
        r = requests.put(
            f"{API}/lolodrive/manager/my-point/calendar",
            headers={"Authorization": f"Bearer {gerant_token}"},
            json={"pickup_days": [0, 2, 4], "delivery_days": [1, 3], "closed_dates": [],
                  "slot_capacity": 2, "delivery_slot_capacity": 1},
            timeout=15,
        )
        assert r.status_code == 200, r.text


# ---------------- Planning gérant / POS ----------------

class TestManagerPlanning:
    def test_gerant_planning_ok(self, gerant_token):
        r = requests.get(f"{API}/lolodrive/manager/planning",
                         headers={"Authorization": f"Bearer {gerant_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "point" in data or "planning" in data or "slots" in data, f"unexpected payload keys: {list(data.keys())}"

    def test_pos_operator_can_access_planning(self, pos_token):
        r = requests.get(f"{API}/lolodrive/manager/planning",
                         headers={"Authorization": f"Bearer {pos_token}"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        # point should be LP-CAP
        pt = data.get("point") or {}
        code = pt.get("code") if isinstance(pt, dict) else None
        assert code == "LP-CAP" or "LP-CAP" in str(data), f"expected LP-CAP in payload, got {data}"

    def test_member_cannot_access_planning(self, marie_token):
        r = requests.get(f"{API}/lolodrive/manager/planning",
                         headers={"Authorization": f"Bearer {marie_token}"}, timeout=15)
        assert r.status_code == 404, f"expected 404 got {r.status_code} {r.text}"

    def test_planning_requires_auth(self):
        r = requests.get(f"{API}/lolodrive/manager/planning", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


# ---------------- Checkout capacité par type ----------------

class TestCheckoutCapacityPerType:
    created_order_numbers = []

    def _order_payload(self, fulfillment_type, pickup_date, slot_id):
        payload = {
            "fulfillment_type": fulfillment_type,
            "items": [{"sku": "HUILE-1L", "qty": 3}],
            "pickup_date": pickup_date,
            "reference_point_code": "LP-CAP",
        }
        if fulfillment_type == "DELIVERY":
            payload["delivery_slot_id"] = slot_id
        else:
            payload["pickup_slot_id"] = slot_id
        return payload

    def test_delivery_slot_full_returns_409(self, marie_token):
        # cap=1 déjà pris par LD-20260913-686648 sur 15/09 AM
        r = requests.post(
            f"{API}/lolodrive/orders",
            headers={"Authorization": f"Bearer {marie_token}"},
            json=self._order_payload("DELIVERY", "2026-09-15", "AM"),
            timeout=15,
        )
        assert r.status_code == 409, f"expected 409 got {r.status_code} {r.text}"

    def test_drive_capacity_2_accepts_second_then_refuses_third(self, marie_token):
        # 1 commande déjà prise (LD-20260913-0B4148 READY). cap=2 -> 2ème OK, 3ème 409.
        r1 = requests.post(
            f"{API}/lolodrive/orders",
            headers={"Authorization": f"Bearer {marie_token}"},
            json=self._order_payload("DRIVE", "2026-09-14", "AM"),
            timeout=20,
        )
        assert r1.status_code == 200, f"expected 200 got {r1.status_code} {r1.text}"
        body1 = r1.json()
        onum = body1.get("order_number") or (body1.get("order") or {}).get("order_number")
        if onum:
            TestCheckoutCapacityPerType.created_order_numbers.append(onum)

        r2 = requests.post(
            f"{API}/lolodrive/orders",
            headers={"Authorization": f"Bearer {marie_token}"},
            json=self._order_payload("DRIVE", "2026-09-14", "AM"),
            timeout=20,
        )
        assert r2.status_code == 409, f"expected 409 got {r2.status_code} {r2.text}"

    def test_cleanup_created_orders(self):
        # cleanup via mongo direct
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_url = os.environ.get("MONGO_URL")
        db_name = os.environ.get("DB_NAME")
        if not mongo_url or not db_name:
            pytest.skip("MONGO_URL/DB_NAME not available")

        async def _clean():
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            if TestCheckoutCapacityPerType.created_order_numbers:
                res = await db.lolodrive_orders.delete_many(
                    {"order_number": {"$in": TestCheckoutCapacityPerType.created_order_numbers}}
                )
                print(f"Cleaned {res.deleted_count} orders: {TestCheckoutCapacityPerType.created_order_numbers}")
            client.close()

        asyncio.run(_clean())
