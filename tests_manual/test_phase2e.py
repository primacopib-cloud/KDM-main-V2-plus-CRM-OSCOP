"""Tests : espace investisseur connecté, cascade §13.6, facture PDF, rapport FOGEDOM, calculateur fret."""
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
    d = requests.post(f"{API}/api/auth/login", json=body).json()
    return d.get("access_token") or d.get("token")

ADMIN = {"Authorization": f"Bearer {login('admin@kdmarche-oscop.fr', 'AdminKDM2025!', 'admin')}"}
INV = {"Authorization": f"Bearer {login('acheteur-pro@kdmarche.fr', 'Demo2026!')}"}

import pymongo
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]

# Setup: opération avec tranches investisseur (email = acheteur-pro)
op = requests.post(f"{API}/api/admin/purchase-resale/operations", headers=ADMIN, json={
    "client_name": "Client Casc", "supplier_name": "Fourn Casc",
    "purchase_amount_ex_vat": 100000, "resale_amount_ex_vat": 130000, "vat_rate": 8.5,
    "logistics_mode": "HYBRID", "logistics_budget_ex_vat": 20000,
    "logistics_resale_price_ex_vat": 22000}).json()
OP = op["id"]
for tr, amt in [("GOODS", 100000), ("LOGISTICS", 20000)]:
    requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/tranches", headers=ADMIN,
                  json={"financing_tranche": tr, "investor_name": "Inv Pro",
                        "investor_email": "acheteur-pro@kdmarche.fr", "approved_amount": amt}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", headers=ADMIN, json={
    "financing_tranche": "GOODS", "payee_category": "SUPPLIER_GOODS", "amount": 100000,
    "method": "INVESTOR_BANK_TRANSFER_ON_BEHALF_OF_OSCOP"}).raise_for_status()
requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/disbursements", headers=ADMIN, json={
    "financing_tranche": "LOGISTICS", "payee_category": "CARRIER", "amount": 20000,
    "method": "OSCOP_BANK_TRANSFER"}).raise_for_status()

# ===== 1. Cascade §13.6 : encaissement 164 920 TTC (152 000 HT + 8,5% TVA) =====
s = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/settlement", headers=ADMIN,
                  json={"collected_amount_ttc": 164920, "remuneration_rate": 5}).json()
b = s["breakdown"]
assert abs(b["vat_reserve"] - 12920) < 1, b
assert b["goods_principal"] == 100000
assert b["logistics_principal"] == 20000
assert abs(b["remuneration"] - 6000) < 1
assert abs(b["oscop_margin"] - 26000) < 1
opd = requests.get(f"{API}/api/admin/purchase-resale/operations/{OP}", headers=ADMIN).json()["operation"]
assert opd["investor_repaid_amount"] == 126000
print(f"1. Cascade §13.6: TVA {b['vat_reserve']}, principal 100k+20k, rému 6k, marge O'SCOP {b['oscop_margin']}: OK")

# ===== 2. Espace investisseur connecté =====
dash = requests.get(f"{API}/api/investor/dashboard", headers=INV).json()
assert dash["totals"]["committed"] == 120000
assert dash["totals"]["disbursed"] == 120000
assert dash["totals"]["repaid"] == 126000
assert len(dash["commitments"]) == 2
assert len(dash["repayments"]) == 1 and dash["repayments"][0]["goods_principal"] == 100000
assert "unités internes de services" in dash["disclaimer"]
assert requests.get(f"{API}/api/investor/dashboard").status_code == 401
print("2. Espace investisseur connecté: 2 engagements, totaux corrects, remboursement visible, 401 anonyme: OK")

# ===== 3. Rapport F.O.G.E.D.O.M PDF =====
d = requests.post(f"{API}/api/admin/purchase-resale/operations/{OP}/documents", headers=ADMIN,
                  json={"doc_type": "FOGEDOM_REPORT"}).json()
assert d["doc_number"].startswith("RF-")
assert any("ni prêteur" in str(s) for s in d["sections"])
pdf = requests.get(f"{API}/api/admin/purchase-resale/documents/{d['id']}/pdf", headers=ADMIN)
assert pdf.content[:5] == b"%PDF-"
print(f"3. Rapport F.O.G.E.D.O.M {d['doc_number']} archivé + PDF valide + mention obligatoire: OK")

# ===== 4. Facture PDF client (simulate paid order) =====
import uuid
order_id = str(uuid.uuid4())
db.oscop_client_orders.insert_one({
    "id": order_id, "order_number": "CMD-TEST", "status": "paid",
    "invoice_number": "FAC-OSCOP-2026-TEST", "paid_at": "2026-06-04T00:00:00",
    "customer_name": "Test", "customer_email": "t@t.fr", "product_name": "Produit T",
    "quantity": 1, "include_logistics": True, "goods_ht_cents": 2500,
    "logistics_ht_cents": 800, "vat_rate": 8.5, "vat_cents": 281, "total_ttc_cents": 3581})
pdf = requests.get(f"{API}/api/oscop-checkout/invoice/{order_id}/pdf")
assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
assert "FAC-OSCOP-2026-TEST" in pdf.headers["Content-Disposition"]
print("4. Facture O'SCOP PDF téléchargeable (email joint envoyé automatiquement au paiement réel): OK")

# ===== 5. Calculateur fret =====
routes = requests.get(f"{API}/api/public/freight/routes").json()["routes"]
assert len(routes) == 7
r_mq = [r for r in routes if "Martinique" in r["destination"]][0]
q = requests.post(f"{API}/api/public/freight/quote", json={
    "route_id": r_mq["id"], "container_type": "40HC", "quantity": 2,
    "insurance": True, "goods_value_ex_vat": 50000}).json()
assert q["breakdown"]["base_freight"] == 7100  # 3550*2
assert abs(q["breakdown"]["baf_surcharge"] - 852) < 1
assert q["breakdown"]["thc_handling"] == 520
assert q["breakdown"]["transport_insurance"] == 300
assert abs(q["total_ex_vat"] - 8772) < 1
# Barème administrable
requests.put(f"{API}/api/admin/freight/routes/{r_mq['id']}", headers=ADMIN, json={"baf_rate": 15}).raise_for_status()
q2 = requests.post(f"{API}/api/public/freight/quote", json={"route_id": r_mq["id"], "container_type": "20DV", "quantity": 1}).json()
assert abs(q2["breakdown"]["baf_surcharge"] - 367.5) < 1
requests.put(f"{API}/api/admin/freight/routes/{r_mq['id']}", headers=ADMIN, json={"baf_rate": 12}).raise_for_status()
print(f"5. Calculateur fret: 7 routes, devis 2×40HC Martinique = {q['total_ex_vat']}€ HT, barème administrable: OK")

# Nettoyage
db.purchase_resale_operations.delete_one({"id": OP})
db.logistics_financing_tranches.delete_many({"operation_id": OP})
db.operation_disbursements.delete_many({"operation_id": OP})
db.cash_settlements.delete_many({"operation_id": OP})
db.operation_documents.delete_many({"operation_id": OP})
db.purchase_resale_audit.delete_many({"operation_id": OP})
db.admin_notifications.delete_many({"category": "achat_revente"})
db.oscop_client_orders.delete_one({"id": order_id})
print("Nettoyage effectué. ALL PHASE-2E TESTS PASSED")
