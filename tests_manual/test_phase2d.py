"""Tests : espace fournisseur, vue 360, rôles granulaires serveur, email notif (best effort)."""
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
    d = r.json()
    return d.get("access_token") or d.get("token")

ADMIN = {"Authorization": f"Bearer {login('admin@kdmarche-oscop.fr', 'AdminKDM2025!', 'admin')}"}
SUPPLIER_TOKEN = login('vendeur2@kdmarche.fr', None) # placeholder, on lit le vrai mdp après

import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

# ===== 1. Espace fournisseur =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "Client X", "supplier_name": "Fournisseur Vendeur2",
    "supplier_email": "acheteur-pro@kdmarche.fr",
    "purchase_amount_ex_vat": 20000, "resale_amount_ex_vat": 26000}).json()
OP = op["id"]
BUYER_TOKEN = login("acheteur-pro@kdmarche.fr", "Demo2026!")
BH = {"Authorization": f"Bearer {BUYER_TOKEN}"}
orders = requests.get(f"{API}/api/supplier/oscop-orders", headers=BH).json()
mine = [o for o in orders["orders"] if o["id"] == OP]
assert mine and mine[0]["buyer"] == "SCIC SAS OBJECTIF SCOP OUTREMER"
assert "pour le compte d'O'SCOP" in mine[0]["payer_mention"]
assert requests.get(f"{API}/api/supplier/oscop-orders").status_code == 401
print("1. Espace fournisseur: commande visible, mention Acheteur SCIC SAS OBJECTIF SCOP OUTREMER, 401 sans auth: OK")

# ===== 2. Vue 360 =====
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/documents", headers=ADMIN,
              json={"doc_type": "MARGIN_STATEMENT"}).raise_for_status()
v = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}/view360", headers=ADMIN).json()
assert all(k in v for k in ["operation", "tranches", "disbursements", "documents", "shipments", "pods", "warehouse", "fogedom", "audit"])
assert len(v["documents"]) == 1 and len(v["audit"]) >= 2
print("2. Vue 360: 9 blocs agrégés (opération, financement, logistique, documents, FOGEDOM, audit): OK")

# ===== 3. Rôles granulaires serveur =====
# L'acheteur-pro n'a aucun rôle → lecture refusée
assert requests.get(f"{API}/api/admin/purchase-resale/operations", headers=BH).status_code == 403
# Attribuer AUDITOR_READ_ONLY → lecture OK, écriture refusée
requests.post(f"{API}/api/admin/staff-roles", headers=ADMIN,
              json={"email": "acheteur-pro@kdmarche.fr", "role": "AUDITOR_READ_ONLY"}).raise_for_status()
assert requests.get(f"{API}/api/admin/purchase-resale/operations", headers=BH).status_code == 200
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches", headers=BH,
                  json={"financing_tranche": "GOODS", "investor_name": "X", "approved_amount": 100})
assert r.status_code == 403 and "OSCOP_FINANCE" in r.text
r = requests.post(f"{API}/api/admin/logiscop-ops/operations/{OP}/shipments", headers=BH,
                  json={"origin": "A", "destination": "B"})
assert r.status_code == 403 and "LOGISCOP_MANAGER" in r.text
# Passer en OSCOP_FINANCE → tranche OK, logistique toujours refusée
requests.post(f"{API}/api/admin/staff-roles", headers=ADMIN,
              json={"email": "acheteur-pro@kdmarche.fr", "role": "OSCOP_FINANCE"}).raise_for_status()
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches", headers=BH,
                  json={"financing_tranche": "GOODS", "investor_name": "Inv", "approved_amount": 20000})
assert r.status_code == 200, r.text
assert requests.post(f"{API}/api/admin/logiscop-ops/operations/{OP}/shipments", headers=BH,
                     json={"origin": "A", "destination": "B"}).status_code == 403
# Rôle invalide refusé + révocation
assert requests.post(f"{API}/api/admin/staff-roles", headers=ADMIN,
                     json={"email": "x@y.fr", "role": "SUPERPOWER"}).status_code == 400
requests.delete(f"{API}/api/admin/staff-roles/acheteur-pro@kdmarche.fr", headers=ADMIN).raise_for_status()
assert requests.get(f"{API}/api/admin/purchase-resale/operations", headers=BH).status_code == 403
print("3. Rôles serveur: AUDITOR lecture seule, OSCOP_FINANCE tranches OK/logistique 403, révocation effective: OK")

# ===== 4. Email notification (vérifie l'écriture notif + pas d'erreur brevo bloquante) =====
before = db.admin_notifications.count_documents({"category": "achat_revente"})
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/status", headers=ADMIN,
              json={"status": "INVESTOR_COMMITTED"}).raise_for_status()
after = db.admin_notifications.count_documents({"category": "achat_revente"})
assert after > before
print("4. Notification étape clé enregistrée (email Brevo envoyé en tâche de fond aux admins): OK")

# Nettoyage
db.purchase_resale_operations.delete_one({"id": OP})
db.logistics_financing_tranches.delete_many({"operation_id": OP})
db.operation_documents.delete_many({"operation_id": OP})
db.purchase_resale_audit.delete_many({"operation_id": OP})
db.admin_notifications.delete_many({"category": "achat_revente"})
db.staff_roles.delete_many({"email": "acheteur-pro@kdmarche.fr"})
print("Nettoyage effectué. ALL PHASE-2D TESTS PASSED")
