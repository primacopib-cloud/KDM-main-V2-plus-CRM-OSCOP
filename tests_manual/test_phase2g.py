"""Tests : email décision investisseur, devis fret PDF, suivi logistique investisseur, alerte marge réelle."""
import os
import requests

API = None
with open('/app/frontend/.env') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            API = line.strip().split('=', 1)[1]

def login(email, pwd, portal=None):
    body = {"email": email, "password": pwd}
    if portal:
        body["portal"] = portal
    r = requests.post(f"{API}/api/auth/login", json=body)
    try:
        d = r.json()
    except Exception:
        return None
    return d.get("access_token") or d.get("token")

ADMIN = {"Authorization": f"Bearer {login('admin@kdmarche-oscop.fr', 'AdminKDM2025!', 'admin')}"}

import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

# ===== 1. Email décision investisseur (approve → email Brevo, vérif logs après) =====
db.investor_applications.delete_many({"email": "inv-mail@test.fr"})
db.users.delete_many({"email": "inv-mail@test.fr"})
requests.post(f"{API}/api/investor/apply", json={
    "name": "Inv Mail", "email": "inv-mail@test.fr", "password": "MotDePasse2026!"}).raise_for_status()
apps = requests.get(f"{API}/api/investor/applications", headers=ADMIN).json()["applications"]
aid = [a["id"] for a in apps if a["email"] == "inv-mail@test.fr"][0]
r = requests.post(f"{API}/api/investor/applications/{aid}/decision", headers=ADMIN, json={"decision": "approve"})
assert r.status_code == 200
print("1. Décision investisseur approuvée (email Brevo déclenché — vérif logs séparée): OK")

# ===== 2. Devis fret PDF =====
routes = requests.get(f"{API}/api/public/freight/routes").json()["routes"]
pdf = requests.post(f"{API}/api/public/freight/quote-pdf", json={
    "route_id": routes[0]["id"], "container_type": "40DV", "quantity": 1})
assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
assert "DF-" in pdf.headers["Content-Disposition"]
print(f"2. Devis fret PDF numéroté ({pdf.headers['Content-Disposition'].split(chr(34))[1]}): OK")

# ===== 3. Suivi logistique investisseur =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 1000,
    "resale_amount_ex_vat": 1500, "vat_rate": 8.5, "logistics_mode": "HYBRID",
    "logistics_budget_ex_vat": 200}).json()
OP = op["id"]
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches", headers=ADMIN,
              json={"financing_tranche": "GOODS", "investor_name": "Inv Mail",
                    "investor_email": "inv-mail@test.fr", "approved_amount": 1000}).raise_for_status()
shp = requests.post(f"{API}/api/admin/logiscop-ops/operations/{OP}/shipments", headers=ADMIN,
                    json={"origin": "Le Havre", "destination": "Pointe-à-Pitre"}).json()
requests.post(f"{API}/api/admin/logiscop-ops/shipments/{shp['id']}/milestones", headers=ADMIN,
              json={"milestone": "IN_MAIN_TRANSIT"}).raise_for_status()
tok = login("inv-mail@test.fr", "MotDePasse2026!")
dash = requests.get(f"{API}/api/investor/dashboard", headers={"Authorization": f"Bearer {tok}"}).json()
assert len(dash["shipments"]) == 1
assert dash["shipments"][0]["operation_reference"] == op["reference"]
assert dash["shipments"][0]["milestones"][0]["milestone"] == "IN_MAIN_TRANSIT"
print("3. Suivi logistique investisseur: expédition + jalon visibles dans son dashboard: OK")

# ===== 4. Alerte marge réelle =====
before = db.admin_notifications.count_documents({"title": {"$regex": "Alerte marge"}})
# encaissement quasi complet (1627.5 TTC) mais rémunération 20% → marge réalisée s'écarte de la prévisionnelle (500)
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", headers=ADMIN, json={
    "financing_tranche": "GOODS", "payee_category": "SUPPLIER_GOODS", "amount": 1000,
    "method": "OSCOP_BANK_TRANSFER"}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/settlement", headers=ADMIN,
              json={"collected_amount_ttc": 1627.5, "remuneration_rate": 20}).raise_for_status()
after = db.admin_notifications.count_documents({"title": {"$regex": "Alerte marge"}})
assert after == before + 1, f"{before} -> {after}"
notif = db.admin_notifications.find_one({"title": {"$regex": "Alerte marge"}}, sort=[("created_at", -1)])
assert "écart" in notif["message"]
print(f"4. Alerte marge réelle déclenchée: {notif['title']}: OK")

# Nettoyage
db.purchase_resale_operations.delete_one({"id": OP})
for coll in ["logistics_financing_tranches", "operation_disbursements", "cash_settlements",
             "purchase_resale_audit", "logiscop_shipments", "logiscop_milestones"]:
    db[coll].delete_many({"operation_id": OP})
db.investor_applications.delete_many({"email": "inv-mail@test.fr"})
db.users.delete_many({"email": "inv-mail@test.fr"})
db.admin_notifications.delete_many({"category": {"$in": ["achat_revente", "investisseur"]}})
print("Nettoyage effectué. ALL PHASE-2G TESTS PASSED")
