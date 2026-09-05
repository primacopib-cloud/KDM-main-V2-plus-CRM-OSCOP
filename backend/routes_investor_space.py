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
    try:
        from brevo_service import send_email, _wrap_html
        if decision == "approve":
            html = _wrap_html("Votre compte investisseur O'SCOP est ouvert", (
                f"<p style='font-size:14px;'>Bonjour {app_doc['name']},</p>"
                "<p style='font-size:14px;'>Votre candidature a été <b>approuvée</b> par l'équipe O'SCOP. "
                "Connectez-vous avec votre email et le mot de passe choisi lors de votre candidature, "
                "puis accédez à votre espace investisseur (engagements, remboursements, CREDI'SCOP-I).</p>"
                "<p style='font-size:12px;color:#B8A98F;'>Les CREDI'SCOP-I sont des unités internes de services : "
                "ils ne constituent ni un solde financier, ni le montant investi, ni un moyen de paiement du fournisseur.</p>"))
            subject = "Compte investisseur O'SCOP approuvé"
        else:
            html = _wrap_html("Votre candidature investisseur O'SCOP", (
                f"<p style='font-size:14px;'>Bonjour {app_doc['name']},</p>"
                "<p style='font-size:14px;'>Après examen, votre candidature n'a pas été retenue à ce stade. "
                "Vous pouvez contacter l'équipe O'SCOP pour compléter votre dossier.</p>"))
            subject = "Candidature investisseur O'SCOP — décision"
        await send_email(app_doc["email"], app_doc["name"], subject, html, tags=["investisseur"])
    except Exception:
        pass
    return {"success": True, "status": decision}


DISCLAIMER = ("Les CREDI'SCOP-I sont des unités internes de services. Ils ne constituent ni un solde financier, "
              "ni le montant investi, ni un moyen de paiement du fournisseur. Chaque investissement réel fait "
              "l'objet d'un Bon d'Engagement et d'un paiement distinct en monnaie ayant cours légal.")


@investor_router.post("/financing-interest")
async def financing_interest(payload: dict, current_user: dict = Depends(get_current_user_v2)):
    op_id = (payload or {}).get("operation_id")
    op = await db.purchase_resale_operations.find_one(
        {"id": op_id}, {"_id": 0, "reference": 1, "linked_product_name": 1, "territory_id": 1})
    if not op:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    email = (current_user.get("email") or "").lower()
    name = current_user.get("contact_name") or current_user.get("company_name") or email
    existing = await db.financing_interests.find_one({"operation_id": op_id, "investor_email": email})
    if existing:
        return {"success": True, "already_sent": True}
    await db.financing_interests.insert_one({
        "id": str(uuid.uuid4()), "operation_id": op_id, "operation_reference": op["reference"],
        "investor_email": email, "investor_name": name, "status": "NEW",
        "created_at": datetime.now(timezone.utc).isoformat()})
    try:
        from routes_purchase_resale import notify_admins
        await notify_admins(
            f"Intérêt investisseur — {op['reference']}",
            f"{name} ({email}) souhaite financer l'opération {op['reference']}"
            f" ({op.get('linked_product_name') or 'offre liée'}, {op.get('territory_id') or 'territoire n.c.'}).",
            category="investisseur")
    except Exception:
        pass
    return {"success": True, "already_sent": False}


@investor_router.get("/financing-interests")
async def list_financing_interests(admin: dict = Depends(_admin)):
    items = await db.financing_interests.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"interests": items}


@investor_router.post("/financing-interests/{interest_id}/decision")
async def decide_financing_interest(interest_id: str, payload: dict, admin: dict = Depends(_admin)):
    decision = (payload or {}).get("decision")
    if decision not in ("accept", "decline"):
        raise HTTPException(status_code=400, detail="decision: accept ou decline")
    doc = await db.financing_interests.find_one({"id": interest_id, "status": "NEW"})
    if not doc:
        raise HTTPException(status_code=404, detail="Intérêt introuvable ou déjà traité")
    new_status = "ACCEPTED" if decision == "accept" else "DECLINED"
    await db.financing_interests.update_one(
        {"id": interest_id},
        {"$set": {"status": new_status, "decided_by": admin.get("email"),
                  "decided_at": datetime.now(timezone.utc).isoformat()}})
    try:
        from brevo_service import send_email, _wrap_html
        if decision == "accept":
            html = _wrap_html("Votre proposition de financement est retenue", (
                f"<p style='font-size:14px;'>Bonjour {doc['investor_name']},</p>"
                f"<p style='font-size:14px;'>Votre intérêt pour financer l'opération <b>{doc['operation_reference']}</b> "
                "a été <b>retenu</b>. L'équipe O'SCOP vous contacte pour établir le Bon d'Engagement et les modalités "
                "(montant, tranche marchandises ou logistique, instrument juridique).</p>"
                "<p style='font-size:12px;color:#B8A98F;'>Tout investissement réel s'effectue en euros ou devises. "
                "Les CREDI'SCOP-I n'y participent jamais.</p>"))
            subject = f"Financement {doc['operation_reference']} — proposition retenue"
        else:
            html = _wrap_html("Votre proposition de financement", (
                f"<p style='font-size:14px;'>Bonjour {doc['investor_name']},</p>"
                f"<p style='font-size:14px;'>Votre intérêt pour l'opération <b>{doc['operation_reference']}</b> n'a pas "
                "été retenu à ce stade. D'autres opportunités restent visibles dans votre espace investisseur.</p>"))
            subject = f"Financement {doc['operation_reference']} — décision"
        await send_email(doc["investor_email"], doc["investor_name"], subject, html, tags=["investisseur"])
    except Exception:
        pass
    return {"success": True, "status": new_status}


@investor_router.post("/financing-interests/{interest_id}/commitment")
async def generate_commitment_from_interest(interest_id: str, admin: dict = Depends(_admin)):
    """Bon d'Engagement PDF pré-rempli avec l'investisseur retenu et l'opération liée."""
    it = await db.financing_interests.find_one({"id": interest_id}, {"_id": 0})
    if not it:
        raise HTTPException(status_code=404, detail="Intérêt introuvable")
    if it.get("status") != "ACCEPTED":
        raise HTTPException(status_code=400, detail="L'intérêt doit d'abord être accepté")
    op = await db.purchase_resale_operations.find_one({"id": it["operation_id"]}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    if not op.get("investor_name"):
        await db.purchase_resale_operations.update_one(
            {"id": op["id"]}, {"$set": {"investor_name": it["investor_name"]}})
        op["investor_name"] = it["investor_name"]
    from operation_docs_pdf import next_doc_number, doc_sections
    number = await next_doc_number(db, "INVESTOR_COMMITMENT")
    doc = {
        "id": str(uuid.uuid4()), "operation_id": op["id"],
        "doc_type": "INVESTOR_COMMITMENT", "doc_number": number,
        "sections": doc_sections("INVESTOR_COMMITMENT", op, {
            "investor_name": f"{it['investor_name']} ({it['investor_email']})"}),
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.operation_documents.insert_one(dict(doc))
    return {"success": True, "doc_id": doc["id"], "doc_number": number}


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
    shipments = await db.logiscop_shipments.find(
        {"operation_id": {"$in": op_ids}}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for s in shipments:
        s["operation_reference"] = ops_map.get(s["operation_id"], {}).get("reference")
        s["milestones"] = await db.logiscop_milestones.find(
            {"shipment_id": s["id"]}, {"_id": 0, "milestone": 1, "created_at": 1}).sort("created_at", 1).to_list(50)
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
        "shipments": shipments,
        "disclaimer": DISCLAIMER,
    }
