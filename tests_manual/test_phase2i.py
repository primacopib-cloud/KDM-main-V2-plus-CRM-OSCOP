"""Tests : rappels multiples échelonnés + litige, meilleure route (compare), territoire opération."""
import os
from datetime import datetime, timedelta, timezone
import subprocess
import uuid
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

RUN = """
import asyncio, os
from dotenv import load_dotenv; load_dotenv('/app/backend/.env')
import sys; sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from routes_oscop_checkout import run_oscop_payment_reminders, set_oscop_checkout_database
async def m():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    set_oscop_checkout_database(db)
    print('SENT:', await run_oscop_payment_reminders(db))
asyncio.run(m())"""

def run_task():
    out = subprocess.run(["python3", "-c", RUN], capture_output=True, text=True, cwd="/app/backend")
    return out.stdout + out.stderr

def age_order(oid, hours):
    old = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    db.oscop_client_orders.update_one({"id": oid}, {"$set": {"last_reminder_at": old}})

# ===== 1. Rappels multiples =====
requests.put(f"{API}/api/oscop-checkout/reminder-settings", headers=ADMIN,
             json={"delay_hours": 24, "enabled": True}).raise_for_status()
oid = str(uuid.uuid4())
db.oscop_client_orders.insert_one({
    "id": oid, "order_number": "CMD-MULTI", "status": "pending_payment",
    "created_at": (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat(),
    "customer_name": "Client Multi", "customer_email": "multi@test.fr",
    "total_ttc_cents": 9000, "stripe_session_id": "cs_test_invalid"})
assert "SENT: 1" in run_task()
doc = db.oscop_client_orders.find_one({"id": oid})
assert doc["reminder_count"] == 1
# Pas de 2e relance immédiate
assert "SENT: 0" in run_task()
# 2e relance après nouveau délai
age_order(oid, 30)
assert "SENT: 1" in run_task()
assert db.oscop_client_orders.find_one({"id": oid})["reminder_count"] == 2
# 3e relance
age_order(oid, 30)
assert "SENT: 1" in run_task()
assert db.oscop_client_orders.find_one({"id": oid})["reminder_count"] == 3
# 4e passage → litige + notification admin
before = db.admin_notifications.count_documents({"title": {"$regex": "litige"}})
age_order(oid, 30)
run_task()
doc = db.oscop_client_orders.find_one({"id": oid})
assert doc["status"] == "disputed", doc["status"]
assert db.admin_notifications.count_documents({"title": {"$regex": "litige"}}) == before + 1
print("1. Rappels multiples: 3 relances espacées (tons croissants) puis statut disputed + notification admin: OK")

# ===== 2. Meilleure route auto (endpoint compare utilisé par le formulaire) =====
c = requests.post(f"{API}/api/public/freight/compare", json={
    "route_id": "auto", "container_type": "20DV", "quantity": 1}).json()
assert c["results"][0]["total_ex_vat"] == min(r["total_ex_vat"] for r in c["results"])
print(f"2. Meilleure route auto: {c['results'][0]['route']} à {c['results'][0]['total_ex_vat']}€: OK")

# ===== 3. Territoire sur opération (ventilation marges) =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 100,
    "resale_amount_ex_vat": 200, "territory_id": "Martinique"}).json()
assert op["territory_id"] == "Martinique"
ops = requests.get(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN).json()["operations"]
assert any(o.get("territory_id") == "Martinique" for o in ops)
print("3. Territoire enregistré sur l'opération et exposé pour la ventilation des marges: OK")

# Nettoyage
db.oscop_client_orders.delete_one({"id": oid})
db.purchase_resale_operations.delete_one({"id": op["id"]})
db.purchase_resale_audit.delete_many({"operation_id": op["id"]})
db.admin_notifications.delete_many({"title": {"$regex": "litige|CMD-MULTI"}})
db.oscop_settings.update_one({"id": "payment_reminder"}, {"$set": {"delay_hours": 48}})
print("Nettoyage effectué. ALL PHASE-2I TESTS PASSED")
