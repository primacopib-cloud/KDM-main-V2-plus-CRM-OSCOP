"""Tests : relance/annulation litiges, export marges territoire, compare par conteneur."""
import os
import uuid
from datetime import datetime, timezone
import requests

API = None
with open('/app/frontend/.env') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            API = line.strip().split('=', 1)[1]

d = requests.post(f"{API}/api/auth/login", json={"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"}).json()
ADMIN = {"Authorization": f"Bearer {d.get('access_token') or d.get('token')}"}

import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

# ===== 1. Relance / annulation litiges =====
def mk_disputed():
    oid = str(uuid.uuid4())
    db.oscop_client_orders.insert_one({
        "id": oid, "order_number": f"CMD-LIT-{oid[:4]}", "status": "disputed",
        "disputed_at": datetime.now(timezone.utc).isoformat(),
        "customer_name": "Client Litige", "customer_email": "litige@test.fr",
        "total_ttc_cents": 7000, "stripe_session_id": "cs_test_invalid",
        "reminder_count": 3, "created_at": datetime.now(timezone.utc).isoformat()})
    return oid

o1, o2 = mk_disputed(), mk_disputed()
lst = requests.get(f"{API}/api/oscop-checkout/disputed-orders", headers=ADMIN).json()["orders"]
assert len([o for o in lst if o["id"] in (o1, o2)]) == 2
assert requests.get(f"{API}/api/oscop-checkout/disputed-orders").status_code == 401
# Relance manuelle → repasse en pending_payment
r = requests.post(f"{API}/api/oscop-checkout/orders/{o1}/dispute-action", headers=ADMIN, json={"action": "remind"})
assert r.status_code == 200 and r.json()["status"] == "pending_payment"
assert db.oscop_client_orders.find_one({"id": o1})["status"] == "pending_payment"
# Annulation → cancelled + email
r = requests.post(f"{API}/api/oscop-checkout/orders/{o2}/dispute-action", headers=ADMIN, json={"action": "cancel"})
assert r.status_code == 200 and r.json()["status"] == "cancelled"
assert db.oscop_client_orders.find_one({"id": o2})["status"] == "cancelled"
# Action invalide
assert requests.post(f"{API}/api/oscop-checkout/orders/{o1}/dispute-action", headers=ADMIN, json={"action": "x"}).status_code == 400
print("1. Litiges: relance manuelle → pending, annulation → cancelled + emails, 401 sans auth: OK")

# ===== 2. Export marges par territoire =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 100,
    "resale_amount_ex_vat": 300, "territory_id": "Guadeloupe"}).json()
j = requests.get(f"{API}/api/admin/purchase-resale/margins-by-territory", headers=ADMIN).json()
gp = [r for r in j["rows"] if r["territoire"] == "Guadeloupe"][0]
assert gp["marge_previsionnelle"] == 200 and gp["operations"] == 1
csv_r = requests.get(f"{API}/api/admin/purchase-resale/margins-by-territory?format=csv", headers=ADMIN)
assert csv_r.status_code == 200 and "marges-par-territoire.csv" in csv_r.headers["Content-Disposition"]
assert "Guadeloupe" in csv_r.text and "marge_previsionnelle" in csv_r.text
print("2. Marges par territoire: agrégation correcte + export CSV: OK")

# ===== 3. Compare par type de conteneur (suggestion) =====
t20 = requests.post(f"{API}/api/public/freight/compare", json={"route_id": "a", "container_type": "20DV", "quantity": 1}).json()
t40 = requests.post(f"{API}/api/public/freight/compare", json={"route_id": "a", "container_type": "40HC", "quantity": 1}).json()
assert t40["results"][0]["total_ex_vat"] > t20["results"][0]["total_ex_vat"]
print("3. Suggestion par conteneur: totaux distincts 20DV vs 40HC: OK")

# Nettoyage
db.oscop_client_orders.delete_many({"id": {"$in": [o1, o2]}})
db.purchase_resale_operations.delete_one({"id": op["id"]})
db.purchase_resale_audit.delete_many({"operation_id": op["id"]})
print("Nettoyage effectué. ALL PHASE-2J TESTS PASSED")
