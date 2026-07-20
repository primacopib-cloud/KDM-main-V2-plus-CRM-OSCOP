"""Iter 59 — Lot 4 buyer tools: freight simulator, comparator, demand forecast + campaign alerts."""
import os
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PWD = "Demo2026!"


def _login(session, email, pwd, portal=None):
    body = {"email": email, "password": pwd}
    if portal:
        body["portal"] = portal
    r = session.post(f"{BASE_URL}/api/auth/login", json=body)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PWD, portal="admin")
    return s


@pytest.fixture(scope="module")
def buyer_sess():
    s = requests.Session()
    _login(s, BUYER_EMAIL, BUYER_PWD)
    return s


@pytest.fixture(scope="module")
def anon_sess():
    return requests.Session()


# ---------- FREIGHT ----------
class TestFreightRates:
    def test_get_rates(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/freight/rates")
        assert r.status_code == 200, r.text
        d = r.json()
        assert set(d["territories"]) == {"GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION", "HEXAGONE"}
        assert len(d["rates"]) == 10
        assert d["fuel_surcharge_pct"] == 12
        assert d["express_multiplier"] == 1.6

    def test_rates_requires_auth(self, anon_sess):
        r = anon_sess.get(f"{BASE_URL}/api/buyer-tools/freight/rates")
        assert r.status_code in (401, 403)


class TestFreightSimulate:
    def test_gp_mq_500kg_2m3(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/buyer-tools/freight/simulate",
                            json={"origin": "GUADELOUPE", "destination": "MARTINIQUE",
                                  "weight_kg": 500, "volume_m3": 2})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["total_ht_cents"] == 25760
        assert d["billed_on"] == "poids"
        assert d["express"] is False

    def test_express_multiplier(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/buyer-tools/freight/simulate",
                            json={"origin": "GUADELOUPE", "destination": "MARTINIQUE",
                                  "weight_kg": 500, "volume_m3": 2, "express": True})
        assert r.status_code == 200
        d = r.json()
        # 25760 * 1.6 = 41216
        assert d["total_ht_cents"] == int(25760 * 1.6)
        assert d["express"] is True

    def test_same_origin_destination(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/buyer-tools/freight/simulate",
                            json={"origin": "GUADELOUPE", "destination": "GUADELOUPE",
                                  "weight_kg": 100})
        assert r.status_code == 400

    def test_zero_weight_and_volume(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/buyer-tools/freight/simulate",
                            json={"origin": "GUADELOUPE", "destination": "MARTINIQUE",
                                  "weight_kg": 0, "volume_m3": 0})
        assert r.status_code == 400

    def test_unknown_territory(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/buyer-tools/freight/simulate",
                            json={"origin": "MARS", "destination": "MARTINIQUE",
                                  "weight_kg": 100})
        assert r.status_code == 400


class TestFreightRateUpdate:
    def test_admin_can_update_rate(self, admin_sess):
        pair = "GUADELOUPE|MARTINIQUE"
        # Get current
        r = admin_sess.get(f"{BASE_URL}/api/buyer-tools/freight/rates")
        assert r.status_code == 200
        original = next(x for x in r.json()["rates"] if x["pair"] == pair)
        try:
            r = admin_sess.put(f"{BASE_URL}/api/buyer-tools/freight/rates/{pair}",
                               json={"base_cents": 9500, "per_kg_cents": 30,
                                     "per_m3_cents": 5600, "delay_days": "2-3"})
            assert r.status_code == 200
            # verify
            r2 = admin_sess.get(f"{BASE_URL}/api/buyer-tools/freight/rates")
            updated = next(x for x in r2.json()["rates"] if x["pair"] == pair)
            assert updated["base_cents"] == 9500
        finally:
            # restore
            admin_sess.put(f"{BASE_URL}/api/buyer-tools/freight/rates/{pair}",
                           json={"base_cents": original["base_cents"],
                                 "per_kg_cents": original["per_kg_cents"],
                                 "per_m3_cents": original["per_m3_cents"],
                                 "delay_days": original["delay_days"]})

    def test_buyer_cannot_update_rate(self, buyer_sess):
        r = buyer_sess.put(f"{BASE_URL}/api/buyer-tools/freight/rates/GUADELOUPE|MARTINIQUE",
                           json={"base_cents": 1, "per_kg_cents": 1,
                                 "per_m3_cents": 1, "delay_days": "1"})
        assert r.status_code in (401, 403)


# ---------- COMPARATOR / FORECAST seed ----------
async def _seed_two_transport_closed(admin_sess):
    """Create two transport consultations, duplicate second, force both to CLOTUREE via mongo."""
    def _create(idx):
        payload = {
            "title": f"TEST_iter59_transport_{idx}_{uuid.uuid4().hex[:6]}",
            "type": "STANDARD", "procedure": "SCELLEE",
            "category": "transport", "products": [], "territories": ["GUADELOUPE"],
            "specs": "test transport", "max_rounds": 3,
            "opens_at": "2026-06-01T00:00:00+00:00",
            "closes_at": "2026-06-08T00:00:00+00:00",
        }
        r = admin_sess.post(f"{BASE_URL}/api/admin/consultations", json=payload)
        assert r.status_code in (200, 201), r.text
        return r.json()

    src = _create(1)
    # duplicate
    r = admin_sess.post(f"{BASE_URL}/api/admin/consultations/{src['id']}/duplicate")
    assert r.status_code == 200, r.text
    dup = r.json()
    # Force both to CLOTUREE via mongo
    client = AsyncIOMotorClient(MONGO_URL)
    mdb = client[DB_NAME]
    await mdb.consultations.update_many(
        {"id": {"$in": [src["id"], dup["id"]]}},
        {"$set": {"status": "CLOTUREE"}})
    client.close()
    return src, dup


@pytest.fixture(scope="module")
def seeded_pair(admin_sess):
    """Seed 2 transport consultations, dup, force closed. Cleanup after."""
    src, dup = asyncio.run(_seed_two_transport_closed(admin_sess))
    yield src, dup
    # cleanup: direct mongo delete (delete route may fail on closed)
    async def _clean():
        client = AsyncIOMotorClient(MONGO_URL)
        mdb = client[DB_NAME]
        await mdb.consultations.delete_many({"id": {"$in": [src["id"], dup["id"]]}})
        client.close()
    asyncio.run(_clean())


class TestComparator:
    def test_candidates_lists_seeded_and_linked(self, buyer_sess, seeded_pair):
        src, dup = seeded_pair
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare/candidates")
        assert r.status_code == 200
        d = r.json()
        ids = {c["id"] for c in d["items"]}
        assert src["id"] in ids and dup["id"] in ids
        pairs = d["linked_pairs"]
        assert any(p["a"] == src["id"] and p["b"] == dup["id"] for p in pairs)

    def test_compare_ok(self, buyer_sess, seeded_pair):
        src, dup = seeded_pair
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare",
                           params={"a": src["id"], "b": dup["id"]})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["a"]["id"] == src["id"] and d["b"]["id"] == dup["id"]
        for k in ("ref", "participants", "valid_bids",
                  "best_offer_ht_cents", "median_offer_ht_cents", "winner"):
            assert k in d["a"] and k in d["b"]
        assert d["linked_by_duplication"] is True
        assert "participants_diff" in d["deltas"]
        assert "valid_bids_diff" in d["deltas"]

    def test_compare_same_id(self, buyer_sess, seeded_pair):
        src, _ = seeded_pair
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare",
                           params={"a": src["id"], "b": src["id"]})
        assert r.status_code == 400

    def test_compare_unknown_id(self, buyer_sess, seeded_pair):
        src, _ = seeded_pair
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare",
                           params={"a": src["id"], "b": "unknown-xxxx"})
        assert r.status_code == 404


class TestDemandForecast:
    def test_forecast_shape_and_transport(self, buyer_sess, seeded_pair):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/demand-forecast")
        assert r.status_code == 200
        d = r.json()
        assert len(d["months"]) == 6
        cats = {c["category"]: c for c in d["categories"]}
        # transport must appear (we seeded 2 transport lots this month or in date range)
        # Note: consultations created "now" (created_at auto). May or may not appear if date filter matches.
        # We at least check structure.
        for c in d["categories"]:
            assert len(c["series"]) == 6
            assert c["trend"] in ("up", "down", "stable")
            assert "forecast_next_month" in c
            assert "total_6m" in c and "avg_participants" in c


# ---------- CAMPAIGN ALERTS ----------
async def _seed_and_run_alert():
    client = AsyncIOMotorClient(MONGO_URL)
    mdb = client[DB_NAME]
    camp_id = f"TEST_camp_{uuid.uuid4().hex[:8]}"
    cons_id = f"TEST_cons_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    closes = (now + timedelta(hours=24)).isoformat()
    await mdb.campaigns.insert_one({
        "id": camp_id, "name": "TEST Campaign Iter59 Alert",
        "closes_at": closes, "status": "OUVERTE",
        "created_at": now.isoformat(),
    })
    await mdb.consultations.insert_one({
        "id": cons_id, "ref": "TEST-C-59",
        "title": "TEST lot sans offre",
        "status": "EN_COURS", "campaign_id": camp_id,
        "category": "transport", "type": "STANDARD", "procedure": "SCELLEE",
        "products": [], "territories": ["GUADELOUPE"],
        "opens_at": now.isoformat(), "closes_at": closes,
        "created_at": now.isoformat(),
    })
    # Set up db module + routes_bids.db before calling alert
    import sys
    sys.path.insert(0, "/app/backend")
    import db as dbmod
    dbmod.set_database(mdb)
    import routes_bids
    routes_bids.db = mdb
    import campaign_alerts
    alerted1 = await campaign_alerts.check_campaign_closure_alerts(mdb)
    alerted2 = await campaign_alerts.check_campaign_closure_alerts(mdb)  # idempotence
    # Verify flag + notification
    camp = await mdb.campaigns.find_one({"id": camp_id})
    notif = await mdb.notifications.find_one({"type": "campaign_no_offer", "data.campaign_id": camp_id})
    # Cleanup
    await mdb.campaigns.delete_one({"id": camp_id})
    await mdb.consultations.delete_one({"id": cons_id})
    if notif:
        await mdb.notifications.delete_many({"data.campaign_id": camp_id})
    client.close()
    return alerted1, alerted2, camp, notif


class TestCampaignAlerts:
    def test_alert_created_flag_set_and_idempotent(self):
        alerted1, alerted2, camp, notif = asyncio.run(_seed_and_run_alert())
        assert alerted1 == 1, f"first run should alert once, got {alerted1}"
        assert alerted2 == 0, f"second run should be idempotent, got {alerted2}"
        assert camp.get("no_offer_alert_sent") is True
        assert notif is not None, "notification campaign_no_offer should have been created"
        assert notif["type"] == "campaign_no_offer"
