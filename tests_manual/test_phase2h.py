"""Tests : relance paiement, comparateur multi-routes, journal audit global, réglages relance."""
import os
from datetime import datetime, timedelta, timezone
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

# ===== 1. Réglages relance (param + protection) =====
assert requests.put(f"{API}/api/oscop-checkout/reminder-settings", json={"delay_hours": 24}).status_code == 401
r = requests.put(f"{API}/api/oscop-checkout/reminder-settings", headers=ADMIN, json={"delay_hours": 24, "enabled": True})
assert r.status_code == 200 and r.json()["delay_hours"] == 24
assert requests.put(f"{API}/api/oscop-checkout/reminder-settings", headers=ADMIN, json={"delay_hours": 9999}).status_code == 400
s = requests.get(f"{API}/api/oscop-checkout/reminder-settings", headers=ADMIN).json()
assert s["delay_hours"] == 24 and s["enabled"]
print("1. Réglages relance: délai paramétrable, bornes 1-720h, 401 sans auth: OK")

# ===== 2. Relance automatique (exécution directe de la tâche) =====
old = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
oid = str(uuid.uuid4())
db.oscop_client_orders.insert_one({
    "id": oid, "order_number": "CMD-RAPPEL", "status": "pending_payment",
    "created_at": old, "customer_name": "Client Rappel", "customer_email": "rappel@test.fr",
    "total_ttc_cents": 5000, "stripe_session_id": "cs_test_invalid"})
import subprocess
out = subprocess.run(["python3", "-c", """
import asyncio, os
from dotenv import load_dotenv; load_dotenv('/app/backend/.env')
import sys; sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from routes_oscop_checkout import run_oscop_payment_reminders, set_oscop_checkout_database
async def m():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    set_oscop_checkout_database(db)
    n = await run_oscop_payment_reminders(db)
    print('SENT:', n)
asyncio.run(m())"""], capture_output=True, text=True, cwd="/app/backend")
assert "SENT: 1" in out.stdout, out.stdout + out.stderr
doc = db.oscop_client_orders.find_one({"id": oid})
assert doc["reminder_sent"] is True
# 2e passage : plus de relance (une seule)
out2 = subprocess.run(["python3", "-c", """
import asyncio, os
from dotenv import load_dotenv; load_dotenv('/app/backend/.env')
import sys; sys.path.insert(0, '/app/backend')
from motor.motor_asyncio import AsyncIOMotorClient
from routes_oscop_checkout import run_oscop_payment_reminders, set_oscop_checkout_database
async def m():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    set_oscop_checkout_database(db)
    print('SENT:', await run_oscop_payment_reminders(db))
asyncio.run(m())"""], capture_output=True, text=True, cwd="/app/backend")
assert "SENT: 0" in out2.stdout
print("2. Relance auto: email envoyé après délai, une seule fois (flag reminder_sent): OK")

# ===== 3. Comparateur multi-routes =====
c = requests.post(f"{API}/api/public/freight/compare", json={
    "route_id": "x", "container_type": "40HC", "quantity": 1}).json()
assert len(c["results"]) == 7
totals = [r["total_ex_vat"] for r in c["results"]]
assert totals == sorted(totals)
assert c["cheapest"] == c["results"][0]["route"]
print(f"3. Comparateur: 7 routes triées, plus économique = {c['cheapest']}: OK")

# ===== 4. Journal audit global =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 100, "resale_amount_ex_vat": 200}).json()
reg = requests.get(f"{API}/api/admin/purchase-resale/audit-register", headers=ADMIN).json()
assert reg["count"] >= 1 and "OPERATION_CREATED" in reg["actions"]
filt = requests.get(f"{API}/api/admin/purchase-resale/audit-register?action=OPERATION_CREATED&operation={op['reference']}", headers=ADMIN).json()
assert filt["count"] == 1 and filt["rows"][0]["operation"] == op["reference"]
csv_r = requests.get(f"{API}/api/admin/purchase-resale/audit-register?format=csv", headers=ADMIN)
assert csv_r.status_code == 200 and "journal-audit" in csv_r.headers["Content-Disposition"]
assert requests.get(f"{API}/api/admin/purchase-resale/audit-register").status_code == 401
print("4. Journal audit: filtres action+référence, export CSV, 401 sans auth: OK")

# Nettoyage
db.oscop_client_orders.delete_one({"id": oid})
db.purchase_resale_operations.delete_one({"id": op["id"]})
db.purchase_resale_audit.delete_many({"operation_id": op["id"]})
db.oscop_settings.update_one({"id": "payment_reminder"}, {"$set": {"delay_hours": 48}})
print("Nettoyage effectué. ALL PHASE-2H TESTS PASSED")
