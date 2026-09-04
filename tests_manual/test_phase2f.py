"""Tests : candidature investisseur → login, registre CSV ventilations, injection fret (via PATCH)."""
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

# ===== 1. Compte investisseur dédié =====
db.investor_applications.delete_many({"email": "inv-nouveau@test.fr"})
db.users.delete_many({"email": "inv-nouveau@test.fr"})
r = requests.post(f"{API}/api/investor/apply", json={
    "name": "Investisseur Nouveau", "email": "inv-nouveau@test.fr",
    "password": "MotDePasse2026!", "phone": "+596000000"})
assert r.status_code == 200, r.text
# doublon pending refusé
assert requests.post(f"{API}/api/investor/apply", json={
    "name": "X", "email": "inv-nouveau@test.fr", "password": "MotDePasse2026!"}).status_code == 409
# login impossible avant validation
assert not login("inv-nouveau@test.fr", "MotDePasse2026!")
# approbation admin
apps = requests.get(f"{API}/api/investor/applications", headers=ADMIN).json()["applications"]
app = [a for a in apps if a["email"] == "inv-nouveau@test.fr"][0]
assert "password_hash" not in app
requests.post(f"{API}/api/investor/applications/{app['id']}/decision", headers=ADMIN,
              json={"decision": "approve"}).raise_for_status()
# login OK après validation + dashboard accessible
tok = login("inv-nouveau@test.fr", "MotDePasse2026!")
assert tok
dash = requests.get(f"{API}/api/investor/dashboard", headers={"Authorization": f"Bearer {tok}"}).json()
assert dash["email"] == "inv-nouveau@test.fr"
# endpoints admin refusés sans admin
assert requests.get(f"{API}/api/investor/applications", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
print("1. Compte investisseur: candidature → refus login avant validation → approbation → login + dashboard OK, hash non exposé: OK")

# ===== 2. Registre CSV ventilations =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 1000,
    "resale_amount_ex_vat": 1500, "vat_rate": 8.5}).json()
OP = op["id"]
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/settlement", headers=ADMIN,
              json={"collected_amount_ttc": 1627.5, "remuneration_rate": 0}).raise_for_status()
csv_resp = requests.get(f"{API}/api/admin/purchase-resale/settlements-register?format=csv", headers=ADMIN)
assert csv_resp.status_code == 200 and "registre-ventilations.csv" in csv_resp.headers["Content-Disposition"]
assert "reserve_tva" in csv_resp.text and op["reference"] in csv_resp.text
assert requests.get(f"{API}/api/admin/purchase-resale/settlements-register?format=csv").status_code == 401
print("2. Registre ventilations CSV: en-têtes + référence opération présents, 401 sans auth: OK")

# ===== 3. Injection fret dans opération (flux frontend simulé) =====
routes = requests.get(f"{API}/api/public/freight/routes").json()["routes"]
q = requests.post(f"{API}/api/public/freight/quote", json={
    "route_id": routes[0]["id"], "container_type": "20DV", "quantity": 1}).json()
det = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}", headers=ADMIN).json()["operation"]
cl = dict(det.get("cost_lines") or {})
cl["main_freight"] = q["total_ex_vat"]
upd = requests.patch(f"{API}/api/admin/purchase-resale/operations/{OP}", headers=ADMIN,
                     json={"cost_lines": cl}).json()
assert upd["cost_lines"]["main_freight"] == q["total_ex_vat"]
assert upd["full_cost_price_ex_vat"] == 1000 + q["total_ex_vat"]
print(f"3. Injection fret: devis {q['total_ex_vat']}€ → poste main_freight, coût de revient recalculé {upd['full_cost_price_ex_vat']}€: OK")

# Nettoyage
db.purchase_resale_operations.delete_one({"id": OP})
db.cash_settlements.delete_many({"operation_id": OP})
db.purchase_resale_audit.delete_many({"operation_id": OP})
db.investor_applications.delete_many({"email": "inv-nouveau@test.fr"})
db.users.delete_many({"email": "inv-nouveau@test.fr"})
db.admin_notifications.delete_many({"category": "investisseur"})
print("Nettoyage effectué. ALL PHASE-2F TESTS PASSED")
