"""Tests manuels : checkout O'SCOP, documents PDF, ledger CREDI'SCOP-I, espace LOGI'SCOP."""
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
prod = db.products.find_one({})
PID = prod['id']

# ===== 1. CHECKOUT O'SCOP =====
# Offre non O'SCOP → 409
r = requests.get(f"{API}/api/oscop-checkout/offer/{PID}")
assert r.status_code == 409, r.text
# Configurer l'offre O'SCOP via PATCH admin
r = requests.patch(f"{API}/api/admin/sale-model/products/{PID}", headers=H, json={
    "sale_model": "OSCOP_DIRECT_RESALE", "oscop_price_ht_cents": 2500,
    "oscop_logistics_price_ht_cents": 800, "oscop_vat_rate": 8.5, "oscop_logistics_available": True})
assert r.status_code == 200, r.text
offer = requests.get(f"{API}/api/oscop-checkout/offer/{PID}").json()
assert offer["seller"] == "SCIC SAS OBJECTIF SCOP OUTREMER" and offer["logistics_available"]
print("1a. Offre O'SCOP configurée + publique: OK")

# CREDI'SCOP interdit comme moyen de paiement
r = requests.post(f"{API}/api/oscop-checkout/session", json={
    "product_id": PID, "customer_email": "test@test.fr", "customer_name": "T",
    "origin_url": API, "payment_method": "CREDISCOP"})
assert r.status_code == 409 and "CREDI" in r.text
print("1b. CREDI'SCOP-I refusé comme paiement produit (409): OK")

# Session Stripe marchandises + logistique
r = requests.post(f"{API}/api/oscop-checkout/session", json={
    "product_id": PID, "quantity": 2, "include_logistics": True,
    "customer_email": "client-test@oscop.fr", "customer_name": "Client Test", "origin_url": API})
assert r.status_code == 200, r.text
sess = r.json()
assert sess["goods_ht_cents"] == 5000 and sess["logistics_ht_cents"] == 800
assert "stripe.com" in sess["checkout_url"]
ORDER = sess["order_id"]
status = requests.get(f"{API}/api/oscop-checkout/status/{ORDER}").json()
assert status["status"] == "pending_payment"
assert status["roles_snapshot"]["seller"] == "SCIC SAS OBJECTIF SCOP OUTREMER"
assert "LOGI'SCOP" in status["roles_snapshot"]["logistics_operator"]
print(f"1c. Session Stripe créée ({sess['total_ttc_cents']/100:.2f}€ TTC), snapshot rôles O'SCOP: OK")

# ===== 2. DOCUMENTS PDF =====
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=H, json={
    "client_name": "Client Doc", "supplier_name": "Fournisseur Doc",
    "purchase_amount_ex_vat": 100000, "resale_amount_ex_vat": 130000,
    "logistics_mode": "HYBRID", "logistics_budget_ex_vat": 10000}).json()
OP = op["id"]
nums = []
for dt in ["SUPPLIER_PO", "INVESTOR_COMMITMENT", "MARGIN_STATEMENT"]:
    d = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/documents", headers=H, json={"doc_type": dt}).json()
    nums.append(d["doc_number"])
    pdf = requests.get(f"{API}/api/admin/purchase-resale/documents/{d['id']}/pdf", headers=H)
    assert pdf.content[:5] == b"%PDF-" and d["doc_number"] in pdf.headers["Content-Disposition"]
assert nums[0].startswith("BCF-") and nums[1].startswith("BE-") and nums[2].startswith("EM-")
docs = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}/documents", headers=H).json()
assert len(docs["documents"]) == 3
print(f"2. Documents PDF numérotés/archivés ({', '.join(nums)}): OK")

# ===== 3. LEDGER CREDI'SCOP-I =====
cat = requests.get(f"{API}/api/admin/service-credits/catalog", headers=H).json()
assert len(cat["items"]) == 11
item = [i for i in cat["items"] if i["code"] == "DATAROOM"][0]
# Barème administrable
requests.put(f"{API}/api/admin/service-credits/catalog/{item['id']}", headers=H, json={"units": 12}).raise_for_status()
item12 = [i for i in requests.get(f"{API}/api/admin/service-credits/catalog", headers=H).json()["items"] if i["code"] == "DATAROOM"][0]
assert item12["units"] == 12
requests.put(f"{API}/api/admin/service-credits/catalog/{item['id']}", headers=H, json={"units": 10}).raise_for_status()
print("3a. Catalogue fermé 11 services, barème administrable: OK")

acc = requests.post(f"{API}/api/admin/service-credits/accounts", headers=H,
                    json={"investor_name": "Inv Test", "investor_email": "inv-test@oscop.fr"}).json()
ACC = acc["id"]
# euro_value techniquement interdit (extra=forbid → 422)
r = requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
                  json={"entry_type": "ALLOCATION", "units": 50, "euro_value": 100})
assert r.status_code == 422
print("3b. Champ euro_value rejeté techniquement (422): OK")
# Allocation 50, débit sans service refusé, débit avec mauvais nb d'unités refusé, débit OK
requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
              json={"entry_type": "ALLOCATION", "units": 50}).raise_for_status()
r = requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
                  json={"entry_type": "DEBIT", "units": 10})
assert r.status_code == 409
r = requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
                  json={"entry_type": "DEBIT", "units": 7, "service_catalog_item_id": item["id"]})
assert r.status_code == 409
requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
              json={"entry_type": "DEBIT", "units": 10, "service_catalog_item_id": item["id"]}).raise_for_status()
# Solde insuffisant
r = requests.post(f"{API}/api/admin/service-credits/accounts/{ACC}/entries", headers=H,
                  json={"entry_type": "EXPIRY", "units": 999})
assert r.status_code == 409
accs = requests.get(f"{API}/api/admin/service-credits/accounts", headers=H).json()["accounts"]
a = [x for x in accs if x["id"] == ACC][0]
assert a["available_units"] == 40
ledger = requests.get(f"{API}/api/admin/service-credits/accounts/{ACC}/ledger", headers=H).json()["entries"]
assert len(ledger) == 2
print("3c. Ledger: allocation 50, débit catalogue 10 (solde 40), débits hors catalogue/solde refusés: OK")

# ===== 4. ESPACE LOGI'SCOP =====
ops = requests.get(f"{API}/api/admin/logiscop-ops/operations", headers=H).json()
assert any(o["id"] == OP for o in ops["operations"])
shp = requests.post(f"{API}/api/admin/logiscop-ops/operations/{OP}/shipments", headers=H, json={
    "origin": "Le Havre", "destination": "Fort-de-France", "transport_mode": "MARITIME",
    "carrier_name": "CMA Test"}).json()
assert shp["shipment_number"].startswith("EXP-")
requests.post(f"{API}/api/admin/logiscop-ops/shipments/{shp['id']}/milestones", headers=H,
              json={"milestone": "IN_MAIN_TRANSIT"}).raise_for_status()
requests.post(f"{API}/api/admin/logiscop-ops/operations/{OP}/warehouse", headers=H,
              json={"location": "Entrepôt Lamentin", "movement": "IN", "quantity": 120}).raise_for_status()
pod = requests.post(f"{API}/api/admin/logiscop-ops/shipments/{shp['id']}/pod", headers=H,
                    json={"received_by": "M. Client", "reference": "BL-001"}).json()
assert pod["pod_number"].startswith("POD-")
det = requests.get(f"{API}/api/admin/logiscop-ops/operations/{OP}", headers=H).json()
assert det["operation"]["logistics_status"] == "POD_VALIDATED"
assert len(det["shipments"][0]["milestones"]) == 1 and len(det["warehouse"]) == 1
r = requests.get(f"{API}/api/admin/logiscop-ops/operations")
assert r.status_code == 401
print("4. LOGI'SCOP: expédition, jalon, stock, POD → statut POD_VALIDATED, refus sans auth: OK")

# ===== Nettoyage =====
db.products.update_one({"id": PID}, {"$set": {"sale_model": "PARTNER_DIRECT_SALE"},
                                     "$unset": {"oscop_price_ht_cents": "", "oscop_logistics_price_ht_cents": "",
                                                "oscop_vat_rate": "", "oscop_logistics_available": ""}})
db.oscop_client_orders.delete_one({"id": ORDER})
db.purchase_resale_operations.delete_one({"id": OP})
db.operation_documents.delete_many({"operation_id": OP})
db.purchase_resale_audit.delete_many({"operation_id": OP})
db.logiscop_shipments.delete_many({"operation_id": OP})
db.logiscop_milestones.delete_many({"operation_id": OP})
db.logiscop_warehouse.delete_many({"operation_id": OP})
db.logiscop_pods.delete_many({"operation_id": OP})
db.service_credit_accounts.delete_one({"id": ACC})
db.service_credit_ledger.delete_many({"account_id": ACC})
print("Nettoyage effectué. ALL 4-MODULE TESTS PASSED")
