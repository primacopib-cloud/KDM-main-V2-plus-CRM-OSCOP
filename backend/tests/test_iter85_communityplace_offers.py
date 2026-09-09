"""Iter85 — CommunityPlace offers (OFFRE/DEMANDE), cooper assignment, fees, webhook invoice."""
import os
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


def _admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json().get("token")


# ------- FEES -------

def test_public_fees_shape():
    r = requests.get(f"{BASE_URL}/api/public/communityplace/fees", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "demand_fee_eur" in d and "offer_fee_eur" in d
    assert isinstance(d["demand_fee_eur"], (int, float))
    assert isinstance(d["offer_fee_eur"], (int, float))


def test_admin_fees_requires_auth():
    r = requests.put(f"{BASE_URL}/api/admin/communityplace/fees",
                     json={"offer_fee_eur": 30}, timeout=15)
    assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"


def test_admin_fees_update_then_restore():
    token = _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    # change to 33
    r = requests.put(f"{BASE_URL}/api/admin/communityplace/fees",
                     json={"offer_fee_eur": 33}, headers=h, timeout=15)
    assert r.status_code == 200, r.text
    assert r.json()["offer_fee_eur"] == 33
    # verify public GET
    r2 = requests.get(f"{BASE_URL}/api/public/communityplace/fees", timeout=15)
    assert r2.json()["offer_fee_eur"] == 33
    # restore
    r3 = requests.put(f"{BASE_URL}/api/admin/communityplace/fees",
                      json={"demand_fee_eur": 50, "offer_fee_eur": 25}, headers=h, timeout=15)
    assert r3.status_code == 200
    assert r3.json()["offer_fee_eur"] == 25
    assert r3.json()["demand_fee_eur"] == 50


# ------- COOPERS -------

def test_public_coopers_list():
    r = requests.get(f"{BASE_URL}/api/public/coopers", timeout=15)
    assert r.status_code == 200
    d = r.json()
    assert "coopers" in d and isinstance(d["coopers"], list)
    assert len(d["coopers"]) >= 1, "at least one COOPER should exist"
    c = d["coopers"][0]
    assert set(c.keys()) == {"id", "name"}, f"unexpected keys: {c.keys()}"


# ------- BATCH with cooper_id -------

def _create_batch(cooper_id, listing_type="OFFRE", suffix="A"):
    body = {
        "company": f"TEST_Iter85_{suffix}",
        "contact_name": "Test QA",
        "email": "qa+iter85@example.com",
        "phone": "0690000000",
        "territory": "Martinique",
        "listing_type": listing_type,
        "items": [{"product": f"Test Produit {suffix}", "quantity": "10 unités", "budget_eur": 100}],
    }
    if cooper_id:
        body["cooper_id"] = cooper_id
    r = requests.post(f"{BASE_URL}/api/public/purchase-needs/batch", json=body, timeout=30)
    return r


def test_batch_offer_with_valid_cooper_assigns():
    coopers = requests.get(f"{BASE_URL}/api/public/coopers", timeout=15).json()["coopers"]
    assert coopers
    cooper_id = coopers[0]["id"]
    r = _create_batch(cooper_id, "OFFRE", "COOP")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["count"] == 1
    ref = d["references"][0]["reference"]
    # verify via admin list
    token = _admin_token()
    lst = requests.get(f"{BASE_URL}/api/admin/purchase-needs",
                       headers={"Authorization": f"Bearer {token}"}, timeout=20).json()["needs"]
    match = [n for n in lst if n["reference"] == ref]
    assert match, "created need not found in admin listing"
    n = match[0]
    assert n["status"] == "ASSIGNED"
    assert n["assigned_role"] == "COOPER"
    assert n["assigned_vendor"], "assigned_vendor email should be set"
    assert n["listing_type"] == "OFFRE"


def test_batch_without_cooper_is_new():
    r = _create_batch(None, "OFFRE", "NOCOOP")
    assert r.status_code == 200, r.text
    ref = r.json()["references"][0]["reference"]
    token = _admin_token()
    lst = requests.get(f"{BASE_URL}/api/admin/purchase-needs",
                       headers={"Authorization": f"Bearer {token}"}, timeout=20).json()["needs"]
    match = [n for n in lst if n["reference"] == ref]
    assert match
    assert match[0]["status"] == "NEW"
    assert not match[0].get("assigned_vendor")


def test_batch_with_invalid_cooper_id_falls_back_to_new():
    r = _create_batch("does-not-exist-12345", "OFFRE", "BADCOOP")
    assert r.status_code == 200
    ref = r.json()["references"][0]["reference"]
    token = _admin_token()
    lst = requests.get(f"{BASE_URL}/api/admin/purchase-needs",
                       headers={"Authorization": f"Bearer {token}"}, timeout=20).json()["needs"]
    n = [x for x in lst if x["reference"] == ref][0]
    assert n["status"] == "NEW"


# ------- PUBLISH COMMUNITYPLACE default fee -------

def test_publish_communityplace_default_fee_offer_25_demand_50():
    token = _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    # OFFRE
    ro = _create_batch(None, "OFFRE", "PUBO")
    id_o = requests.get(f"{BASE_URL}/api/admin/purchase-needs", headers=h, timeout=20).json()["needs"]
    id_offer = [n["id"] for n in id_o if n["reference"] == ro.json()["references"][0]["reference"]][0]
    pub_o = requests.post(f"{BASE_URL}/api/admin/purchase-needs/{id_offer}/communityplace",
                          json={}, headers=h, timeout=30)
    assert pub_o.status_code == 200, pub_o.text
    assert pub_o.json()["fee_eur"] == 25.0
    # DEMANDE
    rd = _create_batch(None, "DEMANDE", "PUBD")
    id_d = requests.get(f"{BASE_URL}/api/admin/purchase-needs", headers=h, timeout=20).json()["needs"]
    id_dem = [n["id"] for n in id_d if n["reference"] == rd.json()["references"][0]["reference"]][0]
    pub_d = requests.post(f"{BASE_URL}/api/admin/purchase-needs/{id_dem}/communityplace",
                          json={}, headers=h, timeout=30)
    assert pub_d.status_code == 200
    assert pub_d.json()["fee_eur"] == 50.0


# ------- WEBHOOK -------

def test_webhook_marks_paid_and_sends_invoice():
    # create need + publish
    token = _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    ro = _create_batch(None, "OFFRE", "WEBH")
    ref = ro.json()["references"][0]["reference"]
    lst = requests.get(f"{BASE_URL}/api/admin/purchase-needs", headers=h, timeout=20).json()["needs"]
    nid = [n["id"] for n in lst if n["reference"] == ref][0]
    requests.post(f"{BASE_URL}/api/admin/purchase-needs/{nid}/communityplace",
                  json={}, headers=h, timeout=30)
    # simulate webhook
    payload = {
        "type": "checkout.session.completed",
        "data": {"object": {"payment_status": "paid",
                            "metadata": {"purchase_need_id": nid, "kind": "COMMUNITYPLACE_FEE"}}},
    }
    r = requests.post(f"{BASE_URL}/api/public/purchase-needs/webhook", json=payload, timeout=30)
    assert r.status_code == 200
    # verify PAID via admin invoices
    inv = requests.get(f"{BASE_URL}/api/admin/communityplace/invoices", headers=h, timeout=20).json()
    assert any(i["id"] == nid for i in inv["invoices"]), "need should appear in paid invoices"
    # verify PDF download
    pdf = requests.get(f"{BASE_URL}/api/admin/communityplace/invoices/{nid}/pdf", headers=h, timeout=30)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF"), "invoice must be a valid PDF"


# ------- COOPER SPACE -------

def test_cooper_login_and_see_assigned_needs():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "cooper-test@kdmarche.fr", "password": "CooperNew2026!"}, timeout=20)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token") or r.json().get("token")
    # first make sure at least one need is assigned to this cooper
    coopers = requests.get(f"{BASE_URL}/api/public/coopers", timeout=15).json()["coopers"]
    target = next((c for c in coopers if "cooper-test" in c.get("name", "").lower()
                   or "COOPER'S" in c.get("name", "")), coopers[0])
    _create_batch(target["id"], "OFFRE", "COOPER-SEE")
    lst = requests.get(f"{BASE_URL}/api/cooper/purchase-needs",
                       headers={"Authorization": f"Bearer {tok}"}, timeout=20)
    assert lst.status_code == 200, lst.text
    d = lst.json()
    assert "needs" in d


# ------- CLEANUP -------

def test_zzz_cleanup_test_data():
    """Cleanup all TEST_Iter85_* records and restore fees."""
    token = _admin_token()
    h = {"Authorization": f"Bearer {token}"}
    # restore fees
    requests.put(f"{BASE_URL}/api/admin/communityplace/fees",
                 json={"demand_fee_eur": 50, "offer_fee_eur": 25}, headers=h, timeout=15)
    # cleanup via direct mongo
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")

    async def _clean():
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        res = await db.purchase_needs.delete_many({"company": {"$regex": "^TEST_Iter85_"}})
        client.close()
        return res.deleted_count

    n = asyncio.run(_clean())
    print(f"Cleaned {n} test records")
    assert n >= 0
