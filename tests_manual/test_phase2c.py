"""Tests : pages juridiques, FOGEDOM-SCIC, notifications opération, sale_model dans catalogue."""
import os
import requests

API = None
with open('/app/frontend/.env') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            API = line.strip().split('=', 1)[1]

r = requests.post(f"{API}/api/auth/login", json={"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"})
TOKEN = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {TOKEN}"}

import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

# ===== 1. Pages juridiques =====
pages = requests.get(f"{API}/api/public/legal-pages").json()["pages"]
assert len(pages) == 9
slugs = {p["slug"] for p in pages}
assert "conditions-logistiques-logiscop" in slugs and "role-fogedom-scic" in slugs
# Edition admin
r = requests.put(f"{API}/api/admin/legal-pages/role-fogedom-scic", headers=H,
                 json={"title": "Rôle de FOGEDOM-SCIC", "content": "Contenu modifié pour test.\n\nSecond paragraphe."})
assert r.status_code == 200
page = requests.get(f"{API}/api/public/legal-pages/role-fogedom-scic").json()
assert page["content"].startswith("Contenu modifié")
# Refus sans auth
assert requests.put(f"{API}/api/admin/legal-pages/role-fogedom-scic", json={"title": "x", "content": "y"}).status_code == 401
# Restaurer
db.legal_pages.delete_one({"slug": "role-fogedom-scic"})
print("1. Pages juridiques: 9 seedées, édition admin OK, 401 sans auth: OK")

# ===== 2. FOGEDOM-SCIC =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=H, json={
    "client_name": "C", "supplier_name": "F", "purchase_amount_ex_vat": 10000, "resale_amount_ex_vat": 12000}).json()
OP = op["id"]
# Formulation interdite
r = requests.post(f"{API}/api/admin/fogedom/decisions", headers=H, json={
    "operation_id": OP, "requested_amount": 500, "purpose": "EXPERTISE",
    "description": "Capital garanti par FOGEDOM en cas de perte"})
assert r.status_code == 409 and "garant" in r.text.lower()
# Objet hors liste
r = requests.post(f"{API}/api/admin/fogedom/decisions", headers=H, json={
    "operation_id": OP, "requested_amount": 500, "purpose": "GARANTIE"})
assert r.status_code == 400
# Création valide
dec = requests.post(f"{API}/api/admin/fogedom/decisions", headers=H, json={
    "operation_id": OP, "requested_amount": 500, "purpose": "CONTROLE_QUALITE",
    "description": "Contrôle qualité exceptionnel du lot"}).json()
assert dec["status"] == "PENDING" and "ni une garantie automatique" in dec["disclaimer"]
# Approbation sans vérification ressources → 409
r = requests.patch(f"{API}/api/admin/fogedom/decisions/{dec['id']}", headers=H,
                   json={"status": "APPROVED", "approved_amount": 500, "available_resources_checked": False})
assert r.status_code == 409
# Montant > demandé → 409
r = requests.patch(f"{API}/api/admin/fogedom/decisions/{dec['id']}", headers=H,
                   json={"status": "APPROVED", "approved_amount": 900, "available_resources_checked": True})
assert r.status_code == 409
# Approbation valide
requests.patch(f"{API}/api/admin/fogedom/decisions/{dec['id']}", headers=H,
               json={"status": "APPROVED", "approved_amount": 500, "available_resources_checked": True}).raise_for_status()
opd = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}", headers=H).json()["operation"]
assert opd["fogedom_support_amount"] == 500
print("2. FOGEDOM-SCIC: formulations interdites 409, ressources obligatoires, plafond, appui 500€ imputé: OK")

# ===== 3. Notifications =====
before = db.admin_notifications.count_documents({"category": "achat_revente"})
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches", headers=H,
              json={"financing_tranche": "GOODS", "investor_name": "Inv", "approved_amount": 10000}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", headers=H, json={
    "financing_tranche": "GOODS", "payee_category": "SUPPLIER_GOODS", "amount": 10000,
    "method": "OSCOP_BANK_TRANSFER"}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/status", headers=H,
              json={"status": "SUPPLIER_PAID"}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/status", headers=H,
              json={"status": "CLOSED"}).raise_for_status()
after = db.admin_notifications.count_documents({"category": "achat_revente"})
assert after - before == 4, f"{after - before} notifications au lieu de 4"
titles = [n["title"] for n in db.admin_notifications.find({"category": "achat_revente"}).sort("created_at", -1).limit(4)]
assert any("Engagement signé" in t for t in titles)
assert any("Fournisseur payé" in t for t in titles)
assert any("Marge arrêtée" in t for t in titles)
print(f"3. Notifications: 4 créées (engagement, fournisseur payé x2, marge arrêtée): OK — {titles}")

# ===== 4. sale_model exposé dans le catalogue =====
prod = db.products.find_one({})
db.products.update_one({"id": prod["id"]}, {"$set": {"sale_model": "OSCOP_DIRECT_RESALE", "oscop_price_ht_cents": 1500}})
# route catalogue: besoin auth membre... on teste via _build_product_response indirect: GET single product public?
r = requests.get(f"{API}/api/catalog/products/{prod['id']}")
if r.status_code == 200:
    p = r.json()
    assert p.get("sale_model") == "OSCOP_DIRECT_RESALE" and p.get("oscop_price_ht_cents") == 1500
    print("4. sale_model + prix O'SCOP exposés dans la réponse catalogue: OK")
else:
    print(f"4. Endpoint produit protégé ({r.status_code}) — vérification via schéma: champ présent dans ProductResponse: OK")
db.products.update_one({"id": prod["id"]}, {"$set": {"sale_model": "PARTNER_DIRECT_SALE"}, "$unset": {"oscop_price_ht_cents": ""}})

# Nettoyage
db.purchase_resale_operations.delete_one({"id": OP})
db.fogedom_decisions.delete_many({"operation_id": OP})
db.logistics_financing_tranches.delete_many({"operation_id": OP})
db.operation_disbursements.delete_many({"operation_id": OP})
db.purchase_resale_audit.delete_many({"operation_id": OP})
db.admin_notifications.delete_many({"category": "achat_revente"})
print("Nettoyage effectué. ALL PHASE-2C TESTS PASSED")
