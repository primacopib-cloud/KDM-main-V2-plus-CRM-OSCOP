"""Espace investisseur connecté : engagements, tranches, CREDI'SCOP-I et remboursements réels."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timezone
import uuid

from routes_v2 import get_current_user_v2

investor_router = APIRouter(prefix="/api/investor", tags=["Espace investisseur"])
db = None


def set_investor_space_database(database):
    global db
    db = database


class InvestorApplication(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str = ""
    message: str = ""


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@investor_router.post("/apply")
async def apply_investor(payload: InvestorApplication):
    from auth import get_password_hash
    email = payload.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email — connectez-vous")
    if await db.investor_applications.find_one({"email": email, "status": "pending"}):
        raise HTTPException(status_code=409, detail="Candidature déjà en cours de validation par O'SCOP")
    app_doc = {"id": str(uuid.uuid4()), "name": payload.name, "email": email,
               "phone": payload.phone, "message": payload.message,
               "password_hash": get_password_hash(payload.password),
               "status": "pending", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.investor_applications.insert_one(dict(app_doc))
    await db.admin_notifications.insert_one({
        "id": str(uuid.uuid4()), "title": "Nouvelle candidature investisseur",
        "message": f"{payload.name} ({email}) demande l'ouverture d'un compte investisseur.",
        "type": "info", "category": "investisseur", "target_user_id": None,
        "action_url": "/super-admin", "metadata": {}, "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()})
    return {"success": True, "message": "Candidature transmise — l'équipe O'SCOP valide chaque compte investisseur."}


@investor_router.get("/applications")
async def list_applications(admin: dict = Depends(_admin)):
    apps = await db.investor_applications.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(100)
    return {"applications": apps}


@investor_router.post("/applications/{app_id}/decision")
async def decide_application(app_id: str, payload: dict, admin: dict = Depends(_admin)):
    decision = payload.get("decision")
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="decision: approve ou reject")
    app_doc = await db.investor_applications.find_one({"id": app_id, "status": "pending"})
    if not app_doc:
        raise HTTPException(status_code=404, detail="Candidature introuvable ou déjà traitée")
    now = datetime.now(timezone.utc).isoformat()
    if decision == "approve":
        await db.users.insert_one({
            "id": str(uuid.uuid4()), "email": app_doc["email"],
            "password_hash": app_doc["password_hash"],
            "company_name": app_doc["name"], "contact_name": app_doc["name"],
            "phone": app_doc.get("phone", ""), "siret": "",
            "subscription": "ess-acces-pro", "credits": 0,
            "role": "buyer", "is_investor": True, "is_admin": False,
            "is_active": True, "created_at": now})
    await db.investor_applications.update_one(
        {"id": app_id},
        {"$set": {"status": "approved" if decision == "approve" else "rejected",
                  "decided_by": admin.get("email"), "decided_at": now}})
    return {"success": True, "status": decision}


DISCLAIMER = ("Les CREDI'SCOP-I sont des unités internes de services. Ils ne constituent ni un solde financier, "
              "ni le montant investi, ni un moyen de paiement du fournisseur. Chaque investissement réel fait "
              "l'objet d'un Bon d'Engagement et d'un paiement distinct en monnaie ayant cours légal.")


@investor_router.get("/dashboard")
async def investor_dashboard(current_user: dict = Depends(get_current_user_v2)):
    email = (current_user.get("email") or "").lower()
    tranches = await db.logistics_financing_tranches.find(
        {"investor_email": email}, {"_id": 0}).sort("created_at", -1).to_list(100)
    op_ids = list({t["operation_id"] for t in tranches})
    ops = await db.purchase_resale_operations.find(
        {"id": {"$in": op_ids}},
        {"_id": 0, "id": 1, "reference": 1, "status": 1, "currency": 1,
         "investor_repaid_amount": 1, "client_collected_amount": 1,
         "expected_margin_ex_vat": 1, "logistics_status": 1},
    ).to_list(100)
    ops_map = {o["id"]: o for o in ops}
    commitments = []
    total_committed = total_disbursed = 0.0
    for t in tranches:
        op = ops_map.get(t["operation_id"], {})
        disbursed = t.get("external_disbursed_amount", 0) + t.get("internal_allocated_amount", 0)
        total_committed += t.get("approved_amount", 0)
        total_disbursed += disbursed
        commitments.append({
            "operation_reference": op.get("reference"), "operation_status": op.get("status"),
            "financing_tranche": t["financing_tranche"], "legal_instrument": t.get("legal_instrument"),
            "approved_amount": t.get("approved_amount", 0), "disbursed_amount": disbursed,
            "remaining_amount": t.get("remaining_amount", 0), "currency": t.get("currency", "EUR"),
            "created_at": t.get("created_at"),
        })
    total_repaid = sum(o.get("investor_repaid_amount", 0) for o in ops)
    settlements = await db.cash_settlements.find(
        {"operation_id": {"$in": op_ids}}, {"_id": 0}).sort("created_at", -1).to_list(50)
    account = await db.service_credit_accounts.find_one({"investor_email": email}, {"_id": 0})
    ledger = []
    if account:
        ledger = await db.service_credit_ledger.find(
            {"account_id": account["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {
        "email": email,
        "commitments": commitments,
        "totals": {"committed": round(total_committed, 2), "disbursed": round(total_disbursed, 2),
                   "repaid": round(total_repaid, 2),
                   "outstanding": round(total_disbursed - total_repaid, 2)},
        "repayments": [{"operation_id": s["operation_id"],
                        "goods_principal": s["breakdown"].get("goods_principal", 0),
                        "logistics_principal": s["breakdown"].get("logistics_principal", 0),
                        "remuneration": s["breakdown"].get("remuneration", 0),
                        "created_at": s["created_at"]} for s in settlements],
        "service_credits": {"account": account, "ledger": ledger},
        "disclaimer": DISCLAIMER,
    }
