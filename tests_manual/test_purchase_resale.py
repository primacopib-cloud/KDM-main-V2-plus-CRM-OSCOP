"""Test manuel du module achat-revente + LOGI'SCOP (exemple §26 du cahier des charges)."""
import os, sys, requests

API = None
with open('/app/frontend/.env') as f:
    for line in f:
        if line.startswith('REACT_APP_BACKEND_URL='):
            API = line.strip().split('=', 1)[1]
assert API

r = requests.post(f"{API}/api/auth/login", json={"email": "admin@kdmarche-oscop.fr", "password": "AdminKDM2025!", "portal": "admin"})
TOKEN = r.json().get("access_token") or r.json().get("token")
H = {"Authorization": f"Bearer {TOKEN}"}

# 1. Refus sans auth
assert requests.get(f"{API}/api/admin/purchase-resale/operations").status_code == 401
print("1. Refus sans auth: OK")

# 2. Création opération exemple §26 (500k marchandises + 80k logistique)
op_data = {
    "client_name": "Client Test §26", "supplier_name": "Fournisseur Test",
    "investor_name": "Investisseur Test",
    "purchase_amount_ex_vat": 500000, "resale_amount_ex_vat": 650000,
    "logistics_mode": "HYBRID", "logistics_budget_ex_vat": 80000,
    "logistics_resale_price_ex_vat": 90000, "min_margin_rate": 5,
    "cost_lines": {"pickup_precarriage": 10000, "main_freight": 35000,
                   "customs_transit": 12000, "warehousing": 8000,
                   "grouping_last_mile": 15000},
}
op = requests.post(f"{API}/api/admin/purchase-resale/operations", json=op_data, headers=H).json()
OP = op["id"]
assert op["full_cost_price_ex_vat"] == 580000, op["full_cost_price_ex_vat"]
assert op["expected_margin_ex_vat"] == 160000
assert op["logistics_actual_cost_ex_vat"] == 80000
assert op["blockers"] == []
print(f"2. Opération {op['reference']}: coût complet 580 000 €, marge 160 000 € ({op['expected_margin_rate']}%): OK")

# 3. Blocage marge négative
bad = requests.post(f"{API}/api/admin/purchase-resale/operations", json={
    "client_name": "X", "supplier_name": "Y", "purchase_amount_ex_vat": 100000,
    "resale_amount_ex_vat": 50000}, headers=H).json()
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{bad['id']}/status",
                  json={"status": "INVESTOR_COMMITTED"}, headers=H)
assert r.status_code == 409 and "négative" in str(r.json())
print("3. Blocage statut si marge négative (409): OK")

# 4. Tranches GOODS 500k + LOGISTICS 80k ; dépassement logistique refusé
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches",
                  json={"financing_tranche": "LOGISTICS", "investor_name": "Inv", "approved_amount": 100000}, headers=H)
assert r.status_code == 409
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches",
              json={"financing_tranche": "GOODS", "investor_name": "Inv", "approved_amount": 500000}, headers=H).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches",
              json={"financing_tranche": "LOGISTICS", "investor_name": "Inv", "approved_amount": 80000}, headers=H).raise_for_status()
print("4. Tranches 500k GOODS + 80k LOGISTICS approuvées, dépassement budget refusé: OK")

# 5. Décaissement investisseur → fournisseur 500k pour le compte d'O'SCOP
d = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", json={
    "financing_tranche": "GOODS", "payee_category": "SUPPLIER_GOODS",
    "amount": 500000, "method": "INVESTOR_BANK_TRANSFER_ON_BEHALF_OF_OSCOP"}, headers=H).json()
assert d["on_behalf_of"] == "SCIC SAS OBJECTIF SCOP OUTREMER"
print("5. Paiement fournisseur 500k pour le compte d'O'SCOP: OK")

# 6. Allocation interne LOGI'SCOP 25k : facture interdite, méthode analytique imposée
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", json={
    "financing_tranche": "LOGISTICS", "payee_category": "LOGISCOP_INTERNAL_ALLOCATION",
    "amount": 25000, "method": "INTERNAL_ANALYTIC_ALLOCATION", "invoice_reference": "FAC-001"}, headers=H)
assert r.status_code == 409 and "facture" in str(r.json()).lower()
alloc = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", json={
    "financing_tranche": "LOGISTICS", "payee_category": "LOGISCOP_INTERNAL_ALLOCATION",
    "amount": 25000, "method": "INTERNAL_ANALYTIC_ALLOCATION"}, headers=H).json()
assert alloc["internal_allocation"] is True
print("6. Allocation interne LOGI'SCOP 25k sans facture (facture refusée en 409): OK")

# 7. Prestataires externes 55k, puis dépassement plafond refusé
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", json={
    "financing_tranche": "LOGISTICS", "payee_category": "CARRIER",
    "amount": 55000, "method": "INVESTOR_CARD_ON_BEHALF_OF_OSCOP"}, headers=H).raise_for_status()
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", json={
    "financing_tranche": "LOGISTICS", "payee_category": "WAREHOUSE",
    "amount": 1000, "method": "OSCOP_BANK_TRANSFER"}, headers=H)
assert r.status_code == 409 and "plafond" in str(r.json()).lower()
print("7. Prestataires externes 55k OK, dépassement plafond logistique refusé (409): OK")

# 8. Détail : compteurs corrects
det = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}", headers=H).json()
o = det["operation"]
assert o["supplier_paid_amount"] == 500000
assert o["logiscop_internal_allocated_amount"] == 25000
assert o["logistics_external_paid_amount"] == 55000
lt = [t for t in det["tranches"] if t["financing_tranche"] == "LOGISTICS"][0]
assert lt["remaining_amount"] == 0 and lt["internal_allocated_amount"] == 25000
print("8. Compteurs: fournisseur 500k, alloc interne 25k, externes 55k, tranche logistique soldée: OK")

# 9. Passage de statut autorisé quand financé
r = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/status",
                  json={"status": "SUPPLIER_PAID"}, headers=H)
assert r.status_code == 200
print("9. Transition SUPPLIER_PAID avec financement confirmé: OK")

# Nettoyage
import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
for oid in [OP, bad['id']]:
    db.purchase_resale_operations.delete_one({"id": oid})
    db.logistics_financing_tranches.delete_many({"operation_id": oid})
    db.operation_disbursements.delete_many({"operation_id": oid})
    db.purchase_resale_audit.delete_many({"operation_id": oid})
print("Nettoyage effectué. ALL PURCHASE-RESALE TESTS PASSED")
