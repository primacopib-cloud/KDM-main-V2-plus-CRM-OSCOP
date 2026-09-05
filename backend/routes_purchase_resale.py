"""Module achat-revente O'SCOP + logistique LOGI'SCOP (Phase 2 noyau)."""
from datetime import datetime, timezone
from typing import Optional, Dict, List
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2
from routes_staff_roles import require_reader, require_finance

logger = logging.getLogger(__name__)
pr_router = APIRouter(prefix="/api", tags=["Achat-Revente"])
db = None


def set_purchase_resale_database(database):
    global db
    db = database


LOGISCOP_NOTICE = (
    "LOGI'SCOP est l'établissement logistique de la SCIC SAS OBJECTIF SCOP OUTREMER. "
    "Les engagements contractuels et factures sont émis par la SCIC SAS OBJECTIF SCOP OUTREMER, "
    "agissant par son établissement LOGI'SCOP."
)

OPERATION_STATUSES = [
    "DRAFT", "CLIENT_ORDER_PENDING", "CLIENT_ORDER_CONFIRMED", "SUPPLIER_VALIDATION",
    "FOGEDOM_REVIEW", "INVESTOR_REVIEW", "INVESTOR_COMMITTED", "SUPPLIER_ORDERED",
    "SUPPLIER_PAYMENT_PENDING", "SUPPLIER_PAID", "IN_PRODUCTION", "IN_TRANSIT",
    "RECEIVED", "DELIVERED_TO_CLIENT", "CLIENT_INVOICED", "CLIENT_PAYMENT_PENDING",
    "CLIENT_PAID", "INVESTOR_REPAYMENT_PENDING", "INVESTOR_REPAID", "CLOSED",
    "SUSPENDED", "CANCELLED", "DISPUTED",
]

LOGISTICS_STATUSES = [
    "LOGISTICS_DRAFT", "LOGISTICS_QUOTED", "LOGISTICS_APPROVED", "LOGISTICS_FUNDING_PENDING",
    "LOGISTICS_FUNDED", "PICKUP_SCHEDULED", "PICKED_UP", "IN_MAIN_TRANSIT",
    "CUSTOMS_PROCESSING", "WAREHOUSED", "ORDER_PREPARATION", "OUT_FOR_DELIVERY",
    "DELIVERED", "POD_VALIDATED", "LOGISTICS_INCIDENT", "LOGISTICS_CLOSED",
]

LOGISTICS_MODES = ["INTERNAL_LOGISCOP", "EXTERNAL_PROVIDER", "HYBRID", "CUSTOMER_HANDLED"]
TRANCHES = ["GOODS", "LOGISTICS", "TAXES_INSURANCE"]
PAYEE_CATEGORIES = [
    "SUPPLIER_GOODS", "CARRIER", "FREIGHT_FORWARDER", "WAREHOUSE", "HANDLING_PROVIDER",
    "CUSTOMS_BROKER", "TRANSPORT_INSURER", "LOGISCOP_INTERNAL_ALLOCATION", "OTHER_LOGISTICS_PROVIDER",
]
DISBURSEMENT_METHODS = [
    "OSCOP_BANK_TRANSFER", "OSCOP_CARD", "INVESTOR_BANK_TRANSFER_ON_BEHALF_OF_OSCOP",
    "INVESTOR_CARD_ON_BEHALF_OF_OSCOP", "BANK_DOCUMENTARY_CREDIT",
    "OTHER_AUTHORIZED_PSP_METHOD", "INTERNAL_ANALYTIC_ALLOCATION",
]

COST_LINE_KEYS = [
    "pickup_precarriage", "main_freight", "grouping_last_mile", "transport_insurance",
    "duties_taxes", "octroi_mer", "customs_transit", "handling", "warehousing",
    "order_preparation", "quality_control", "external_logistics_fees",
    "internal_logiscop_cost", "fx_hedge", "goods_financing_cost",
    "logistics_financing_cost", "other_direct_costs",
]


class OperationCreate(BaseModel):
    reference: Optional[str] = None
    territory_id: Optional[str] = None
    client_name: str
    supplier_name: str
    supplier_email: Optional[str] = None
    investor_name: Optional[str] = None
    currency: str = "EUR"
    purchase_amount_ex_vat: float = Field(ge=0)
    resale_amount_ex_vat: float = Field(ge=0)
    vat_rate: float = Field(default=0.0, ge=0, le=100)
    logistics_mode: str = "CUSTOMER_HANDLED"
    logistics_budget_ex_vat: float = Field(default=0.0, ge=0)
    logistics_resale_price_ex_vat: float = Field(default=0.0, ge=0)
    cost_lines: Dict[str, float] = {}
    min_margin_rate: float = Field(default=0.0, ge=0, le=100)
    funding_instrument: Optional[str] = None
    linked_product_id: Optional[str] = None
    linked_product_name: Optional[str] = None
    notes: Optional[str] = None


class OperationUpdate(BaseModel):
    purchase_amount_ex_vat: Optional[float] = None
    resale_amount_ex_vat: Optional[float] = None
    logistics_mode: Optional[str] = None
    logistics_budget_ex_vat: Optional[float] = None
    logistics_resale_price_ex_vat: Optional[float] = None
    cost_lines: Optional[Dict[str, float]] = None
    min_margin_rate: Optional[float] = None
    client_name: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_email: Optional[str] = None
    investor_name: Optional[str] = None
    funding_instrument: Optional[str] = None
    logistics_status: Optional[str] = None
    linked_product_id: Optional[str] = None
    linked_product_name: Optional[str] = None
    notes: Optional[str] = None


class StatusChange(BaseModel):
    status: str
    comment: Optional[str] = None


class TrancheCreate(BaseModel):
    financing_tranche: str
    investor_name: str
    investor_email: Optional[str] = None
    approved_amount: float = Field(gt=0)
    legal_instrument: str = "Bon d'Engagement"
    currency: str = "EUR"


class SettlementCreate(BaseModel):
    collected_amount_ttc: float = Field(gt=0)
    external_costs_due: float = Field(default=0.0, ge=0)
    remuneration_rate: float = Field(default=0.0, ge=0, le=100)
    fogedom_allocation: float = Field(default=0.0, ge=0)


class DisbursementCreate(BaseModel):
    financing_tranche: str
    payee_category: str
    payee_name: Optional[str] = None
    amount: float = Field(gt=0)
    method: str
    invoice_reference: Optional[str] = None
    comment: Optional[str] = None


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


def compute_costs(op: dict) -> dict:
    lines = {k: float(op.get("cost_lines", {}).get(k, 0) or 0) for k in COST_LINE_KEYS}
    total_costs = sum(lines.values())
    full_cost = float(op.get("purchase_amount_ex_vat", 0)) + total_costs
    resale_goods = float(op.get("resale_amount_ex_vat", 0))
    resale_logistics = float(op.get("logistics_resale_price_ex_vat", 0))
    resale_total = resale_goods + resale_logistics
    margin = resale_total - full_cost
    logistics_cost = (
        lines["pickup_precarriage"] + lines["main_freight"] + lines["grouping_last_mile"]
        + lines["transport_insurance"] + lines["customs_transit"] + lines["handling"]
        + lines["warehousing"] + lines["order_preparation"]
        + lines["external_logistics_fees"] + lines["internal_logiscop_cost"]
        + lines["logistics_financing_cost"]
    )
    goods_cost = full_cost - logistics_cost
    return {
        "cost_lines": lines,
        "direct_costs_ex_vat": total_costs,
        "full_cost_price_ex_vat": round(full_cost, 2),
        "logistics_actual_cost_ex_vat": round(logistics_cost, 2),
        "expected_margin_ex_vat": round(margin, 2),
        "expected_goods_margin_ex_vat": round(resale_goods - goods_cost, 2),
        "expected_logistics_margin_ex_vat": round(resale_logistics - logistics_cost, 2),
        "expected_margin_rate": round(margin / resale_total * 100, 2) if resale_total > 0 else 0.0,
        "markup_rate": round(margin / full_cost * 100, 2) if full_cost > 0 else 0.0,
        "resale_total_ex_vat": round(resale_total, 2),
    }


def authorization_blockers(op: dict) -> List[str]:
    blockers = []
    if float(op.get("purchase_amount_ex_vat", 0)) <= 0:
        blockers.append("Coût de revient incomplet : prix fournisseur manquant")
    if float(op.get("resale_amount_ex_vat", 0)) <= 0:
        blockers.append("Prix de revente client manquant")
    if float(op.get("expected_margin_ex_vat", 0)) < 0:
        blockers.append("Marge prévisionnelle négative")
    if float(op.get("expected_margin_rate", 0)) < float(op.get("min_margin_rate", 0)):
        blockers.append(f"Seuil de marge minimal non atteint ({op.get('min_margin_rate', 0)}%)")
    if op.get("logistics_mode") != "CUSTOMER_HANDLED" and float(op.get("logistics_budget_ex_vat", 0)) <= 0:
        blockers.append("Plan logistique LOGI'SCOP non chiffré")
    return blockers


def financing_blockers(op: dict, tranches: List[dict]) -> List[str]:
    blockers = list(authorization_blockers(op))
    approved = sum(t["approved_amount"] for t in tranches if t.get("status") != "CANCELLED")
    if approved <= 0:
        blockers.append("Financement non confirmé : aucune tranche approuvée")
    return blockers


async def _get_op(operation_id: str) -> dict:
    op = await db.purchase_resale_operations.find_one({"id": operation_id}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Opération introuvable")
    return op


async def _audit(action: str, op_id: str, admin: dict, detail: dict = None):
    await db.purchase_resale_audit.insert_one({
        "id": str(uuid.uuid4()), "operation_id": op_id, "action": action,
        "by": admin.get("email"), "detail": detail or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


NOTIFY_STATUSES = {
    "INVESTOR_COMMITTED": "Engagement investisseur confirmé",
    "SUPPLIER_PAID": "Fournisseur payé",
    "DELIVERED_TO_CLIENT": "Livraison au client confirmée",
    "CLIENT_PAID": "Paiement client reçu",
    "INVESTOR_REPAID": "Remboursement investisseur réalisé",
    "CLOSED": "Marge arrêtée — opération clôturée",
}


async def notify_admins(title: str, message: str, category: str = "achat_revente"):
    await db.admin_notifications.insert_one({
        "id": str(uuid.uuid4()), "title": title, "message": message,
        "type": "info", "category": category, "target_user_id": None,
        "action_url": "/super-admin", "metadata": {}, "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    try:
        from brevo_service import send_email, _wrap_html
        admins = await db.users.find({"is_admin": True}, {"_id": 0, "email": 1}).to_list(5)
        html = _wrap_html(title, f"<p style='font-size:14px;'>{message}</p><p style='font-size:12px;color:#B8A98F;'>Retrouvez le détail dans le back-office, onglet Achat-Revente.</p>")
        for a in admins:
            if a.get("email"):
                await send_email(a["email"], "Admin O'SCOP", f"[O'SCOP] {title}", html, tags=["achat_revente"])
    except Exception as exc:
        logger.warning(f"Email notification achat-revente non envoyé: {exc}")


@pr_router.get("/public/logiscop/notice")
async def get_logiscop_notice():
    return {"notice": LOGISCOP_NOTICE, "logistics_modes": LOGISTICS_MODES}


@pr_router.post("/admin/purchase-resale/operations")
async def create_operation(payload: OperationCreate, admin: dict = Depends(_admin)):
    if payload.logistics_mode not in LOGISTICS_MODES:
        raise HTTPException(status_code=400, detail="logistics_mode invalide")
    now = datetime.now(timezone.utc)
    ref = payload.reference or f"AR-{now.strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    op = {
        "id": str(uuid.uuid4()), "reference": ref,
        "sale_model": "OSCOP_DIRECT_RESALE",
        "status": "DRAFT", "logistics_status": "LOGISTICS_DRAFT",
        "status_history": [{"status": "DRAFT", "at": now.isoformat(), "by": admin.get("email")}],
        **payload.dict(exclude={"reference"}),
        "supplier_paid_amount": 0.0, "client_collected_amount": 0.0,
        "investor_repaid_amount": 0.0, "logistics_external_paid_amount": 0.0,
        "logiscop_internal_allocated_amount": 0.0, "fogedom_support_amount": 0.0,
        "realized_margin_ex_vat": None,
        "created_at": now.isoformat(), "updated_at": now.isoformat(),
    }
    op.update(compute_costs(op))
    await db.purchase_resale_operations.insert_one(dict(op))
    await _audit("OPERATION_CREATED", op["id"], admin, {"reference": ref})
    op["blockers"] = authorization_blockers(op)
    return op


@pr_router.get("/public/financing-opportunities")
async def financing_opportunities():
    """Opérations d'achat-revente liées à une offre finançable, proposées aux investisseurs."""
    ops = await db.purchase_resale_operations.find(
        {"linked_product_id": {"$nin": [None, ""]}, "status": {"$nin": ["CLOSED", "CANCELLED"]}},
        {"_id": 0, "id": 1, "reference": 1, "status": 1, "territory_id": 1,
         "linked_product_id": 1, "linked_product_name": 1,
         "purchase_amount_ex_vat": 1, "resale_amount_ex_vat": 1,
         "logistics_mode": 1, "expected_margin_ex_vat": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(50)
    return {"opportunities": ops, "notice": "Financement en euros ou devises uniquement. Les CREDI'SCOP-I n'y participent jamais."}


@pr_router.get("/admin/purchase-resale/operations")
async def list_operations(admin: dict = Depends(require_reader)):
    ops = await db.purchase_resale_operations.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for op in ops:
        op["blockers"] = authorization_blockers(op)
    return {"operations": ops, "statuses": OPERATION_STATUSES, "logistics_statuses": LOGISTICS_STATUSES,
            "logistics_modes": LOGISTICS_MODES, "cost_line_keys": COST_LINE_KEYS,
            "payee_categories": PAYEE_CATEGORIES, "methods": DISBURSEMENT_METHODS,
            "tranches": TRANCHES, "logiscop_notice": LOGISCOP_NOTICE}


@pr_router.get("/admin/purchase-resale/operations/{operation_id}")
async def get_operation(operation_id: str, admin: dict = Depends(require_reader)):
    op = await _get_op(operation_id)
    tranches = await db.logistics_financing_tranches.find({"operation_id": operation_id}, {"_id": 0}).to_list(100)
    disbursements = await db.operation_disbursements.find({"operation_id": operation_id}, {"_id": 0}).to_list(200)
    op["blockers"] = financing_blockers(op, tranches)
    return {"operation": op, "tranches": tranches, "disbursements": disbursements}


@pr_router.patch("/admin/purchase-resale/operations/{operation_id}")
async def update_operation(operation_id: str, payload: OperationUpdate, admin: dict = Depends(_admin)):
    op = await _get_op(operation_id)
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if "logistics_mode" in updates and updates["logistics_mode"] not in LOGISTICS_MODES:
        raise HTTPException(status_code=400, detail="logistics_mode invalide")
    if "logistics_status" in updates and updates["logistics_status"] not in LOGISTICS_STATUSES:
        raise HTTPException(status_code=400, detail="Statut logistique invalide")
    op.update(updates)
    op.update(compute_costs(op))
    op["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.purchase_resale_operations.update_one({"id": operation_id}, {"$set": {k: v for k, v in op.items() if k != "_id"}})
    await _audit("OPERATION_UPDATED", operation_id, admin, {"fields": list(updates.keys())})
    op["blockers"] = authorization_blockers(op)
    return op


@pr_router.post("/admin/purchase-resale/operations/{operation_id}/status")
async def change_status(operation_id: str, payload: StatusChange, admin: dict = Depends(require_finance)):
    if payload.status not in OPERATION_STATUSES:
        raise HTTPException(status_code=400, detail="Statut invalide")
    op = await _get_op(operation_id)
    gated = {"INVESTOR_COMMITTED", "SUPPLIER_ORDERED", "SUPPLIER_PAYMENT_PENDING", "SUPPLIER_PAID"}
    if payload.status in gated:
        tranches = await db.logistics_financing_tranches.find({"operation_id": operation_id}, {"_id": 0}).to_list(100)
        blockers = financing_blockers(op, tranches) if payload.status != "INVESTOR_COMMITTED" else authorization_blockers(op)
        if blockers:
            raise HTTPException(status_code=409, detail={"message": "Opération bloquée", "blockers": blockers})
    now = datetime.now(timezone.utc).isoformat()
    await db.purchase_resale_operations.update_one(
        {"id": operation_id},
        {"$set": {"status": payload.status, "updated_at": now},
         "$push": {"status_history": {"status": payload.status, "at": now, "by": admin.get("email"), "comment": payload.comment}}},
    )
    await _audit("STATUS_CHANGED", operation_id, admin, {"to": payload.status})
    if payload.status in NOTIFY_STATUSES:
        await notify_admins(f"{NOTIFY_STATUSES[payload.status]} — {op['reference']}",
                            f"Opération {op['reference']} ({op.get('client_name')}) : statut {payload.status}.")
    return {"success": True, "status": payload.status}


@pr_router.post("/admin/purchase-resale/operations/{operation_id}/tranches")
async def create_tranche(operation_id: str, payload: TrancheCreate, admin: dict = Depends(require_finance)):
    if payload.financing_tranche not in TRANCHES:
        raise HTTPException(status_code=400, detail="Tranche invalide")
    op = await _get_op(operation_id)
    if payload.financing_tranche == "LOGISTICS" and payload.approved_amount > float(op.get("logistics_budget_ex_vat", 0)):
        raise HTTPException(status_code=409, detail="La tranche logistique dépasse le budget logistique approuvé")
    tranche = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        **payload.dict(),
        "investor_email": (payload.investor_email or "").lower() or None,
        "committed_amount": payload.approved_amount,
        "external_disbursed_amount": 0.0, "internal_allocated_amount": 0.0,
        "remaining_amount": payload.approved_amount,
        "status": "APPROVED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.logistics_financing_tranches.insert_one(dict(tranche))
    await _audit("TRANCHE_APPROVED", operation_id, admin, {"tranche": payload.financing_tranche, "amount": payload.approved_amount})
    await notify_admins(f"Engagement signé — {op['reference']}",
                        f"Tranche {payload.financing_tranche} de {payload.approved_amount:,.2f} {payload.currency} approuvée par {payload.investor_name} ({payload.legal_instrument}).")
    return tranche


@pr_router.post("/admin/purchase-resale/operations/{operation_id}/disbursements")
async def create_disbursement(operation_id: str, payload: DisbursementCreate, admin: dict = Depends(require_finance)):
    if payload.financing_tranche not in TRANCHES:
        raise HTTPException(status_code=400, detail="Tranche invalide")
    if payload.payee_category not in PAYEE_CATEGORIES:
        raise HTTPException(status_code=400, detail="Catégorie bénéficiaire invalide")
    if payload.method not in DISBURSEMENT_METHODS:
        raise HTTPException(status_code=400, detail="Méthode invalide")
    op = await _get_op(operation_id)
    is_internal = payload.payee_category == "LOGISCOP_INTERNAL_ALLOCATION"
    if is_internal and payload.invoice_reference:
        raise HTTPException(status_code=409, detail="Aucune facture ne peut exister entre O'SCOP et LOGI'SCOP : affectation analytique interne uniquement")
    if is_internal and payload.method != "INTERNAL_ANALYTIC_ALLOCATION":
        raise HTTPException(status_code=409, detail="Une allocation interne LOGI'SCOP utilise la méthode INTERNAL_ANALYTIC_ALLOCATION")
    if not is_internal and payload.method == "INTERNAL_ANALYTIC_ALLOCATION":
        raise HTTPException(status_code=409, detail="INTERNAL_ANALYTIC_ALLOCATION est réservée aux allocations internes LOGI'SCOP")
    tranches = await db.logistics_financing_tranches.find(
        {"operation_id": operation_id, "financing_tranche": payload.financing_tranche}, {"_id": 0}).to_list(50)
    if not tranches:
        raise HTTPException(status_code=409, detail=f"Aucune tranche {payload.financing_tranche} approuvée pour cette opération")
    remaining = sum(t["remaining_amount"] for t in tranches)
    if payload.amount > remaining + 0.001:
        raise HTTPException(status_code=409, detail=f"Dépassement du plafond financé : restant {remaining:.2f} {op.get('currency', 'EUR')}")
    disb = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        **payload.dict(),
        "internal_allocation": is_internal,
        "on_behalf_of": "SCIC SAS OBJECTIF SCOP OUTREMER" if payload.method.startswith("INVESTOR_") else None,
        "status": "PAID_OR_ALLOCATED",
        "paid_or_allocated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": admin.get("email"),
    }
    await db.operation_disbursements.insert_one(dict(disb))
    amt = payload.amount
    for t in tranches:
        take = min(t["remaining_amount"], amt)
        if take <= 0:
            continue
        field = "internal_allocated_amount" if is_internal else "external_disbursed_amount"
        await db.logistics_financing_tranches.update_one(
            {"id": t["id"]}, {"$inc": {field: take, "remaining_amount": -take}})
        amt -= take
        if amt <= 0:
            break
    inc_field = "logiscop_internal_allocated_amount" if is_internal else (
        "supplier_paid_amount" if payload.payee_category == "SUPPLIER_GOODS" else "logistics_external_paid_amount")
    await db.purchase_resale_operations.update_one({"id": operation_id}, {"$inc": {inc_field: payload.amount}})
    await _audit("DISBURSEMENT", operation_id, admin, {"category": payload.payee_category, "amount": payload.amount, "internal": is_internal})
    if payload.payee_category == "SUPPLIER_GOODS":
        await notify_admins(f"Fournisseur payé — {op['reference']}",
                            f"Paiement fournisseur de {payload.amount:,.2f} {op.get('currency', 'EUR')} ({payload.method}) enregistré.")
    return disb


class DocumentCreate(BaseModel):
    doc_type: str
    extra: Optional[Dict] = None


@pr_router.post("/admin/purchase-resale/operations/{operation_id}/documents")
async def generate_document(operation_id: str, payload: DocumentCreate, admin: dict = Depends(_admin)):
    from operation_docs_pdf import DOC_TYPES, next_doc_number, doc_sections
    if payload.doc_type not in DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Type invalide : {list(DOC_TYPES)}")
    op = await _get_op(operation_id)
    number = await next_doc_number(db, payload.doc_type)
    extra = payload.extra or {}
    if payload.doc_type == "FOGEDOM_REPORT":
        extra.setdefault("blockers", authorization_blockers(op))
    doc = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        "doc_type": payload.doc_type, "doc_number": number,
        "sections": doc_sections(payload.doc_type, op, extra),
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.operation_documents.insert_one(dict(doc))
    await _audit("DOCUMENT_GENERATED", operation_id, admin, {"doc_number": number, "type": payload.doc_type})
    return doc


@pr_router.get("/admin/purchase-resale/operations/{operation_id}/documents")
async def list_documents(operation_id: str, admin: dict = Depends(require_reader)):
    docs = await db.operation_documents.find(
        {"operation_id": operation_id}, {"_id": 0, "sections": 0}).sort("created_at", -1).to_list(100)
    return {"documents": docs}


@pr_router.get("/admin/purchase-resale/documents/{doc_id}/pdf")
async def download_document_pdf(doc_id: str, admin: dict = Depends(require_reader)):
    from fastapi.responses import Response
    from operation_docs_pdf import build_operation_pdf
    doc = await db.operation_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    pdf = build_operation_pdf(doc)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{doc["doc_number"]}.pdf"'})


OSCOP_BUYER = "SCIC SAS OBJECTIF SCOP OUTREMER"


@pr_router.get("/supplier/oscop-orders")
async def supplier_oscop_orders(current_user: dict = Depends(get_current_user_v2)):
    """Espace fournisseur : commandes d'achat O'SCOP liées à l'email du fournisseur connecté."""
    email = (current_user.get("email") or "").lower()
    ops = await db.purchase_resale_operations.find(
        {"supplier_email": email},
        {"_id": 0, "id": 1, "reference": 1, "status": 1, "purchase_amount_ex_vat": 1,
         "currency": 1, "logistics_mode": 1, "supplier_paid_amount": 1,
         "client_name": 1, "created_at": 1, "supplier_name": 1},
    ).sort("created_at", -1).to_list(100)
    for op in ops:
        op["buyer"] = OSCOP_BUYER
        op["payer_mention"] = "O'SCOP ou investisseur pour le compte d'O'SCOP"
        op["recipient"] = "O'SCOP ou client final désigné"
    return {"orders": ops, "buyer": OSCOP_BUYER}


@pr_router.get("/admin/purchase-resale/operations/{operation_id}/view360")
async def view_360(operation_id: str, admin: dict = Depends(require_reader)):
    """Vue 360° : client, fournisseur, financement, logistique, documents, marge, FOGEDOM, audit."""
    op = await _get_op(operation_id)
    tranches = await db.logistics_financing_tranches.find({"operation_id": operation_id}, {"_id": 0}).to_list(100)
    op["blockers"] = financing_blockers(op, tranches)
    disbursements = await db.operation_disbursements.find({"operation_id": operation_id}, {"_id": 0}).to_list(200)
    documents = await db.operation_documents.find({"operation_id": operation_id}, {"_id": 0, "sections": 0}).to_list(100)
    shipments = await db.logiscop_shipments.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    pods = await db.logiscop_pods.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    warehouse = await db.logiscop_warehouse.find({"operation_id": operation_id}, {"_id": 0}).to_list(100)
    fogedom = await db.fogedom_decisions.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    audit = await db.purchase_resale_audit.find({"operation_id": operation_id}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return {"operation": op, "tranches": tranches, "disbursements": disbursements,
            "documents": documents, "shipments": shipments, "pods": pods,
            "warehouse": warehouse, "fogedom": fogedom, "audit": audit}


@pr_router.post("/admin/purchase-resale/operations/{operation_id}/settlement")
async def settle_collection(operation_id: str, payload: SettlementCreate, admin: dict = Depends(require_finance)):
    """Cascade §13.6 : réserve TVA → coûts externes dus → principal marchandises → principal logistique → rémunération → marge O'SCOP (→ FOGEDOM-SCIC optionnel)."""
    op = await _get_op(operation_id)
    vat_rate = float(op.get("vat_rate", 0))
    vat_reserve = round(payload.collected_amount_ttc * vat_rate / (100 + vat_rate), 2) if vat_rate else 0.0
    remaining = payload.collected_amount_ttc - vat_reserve
    breakdown = {"vat_reserve": vat_reserve}

    external_costs = min(payload.external_costs_due, remaining)
    breakdown["external_costs"] = round(external_costs, 2)
    remaining -= external_costs

    tranches = await db.logistics_financing_tranches.find({"operation_id": operation_id}, {"_id": 0}).to_list(50)
    already = float(op.get("investor_repaid_amount", 0))
    goods_due = max(sum(t["approved_amount"] - t["remaining_amount"] for t in tranches if t["financing_tranche"] == "GOODS") - already, 0)
    goods_principal = min(goods_due, remaining)
    breakdown["goods_principal"] = round(goods_principal, 2)
    remaining -= goods_principal

    logi_due = max(sum(t["approved_amount"] - t["remaining_amount"] for t in tranches if t["financing_tranche"] == "LOGISTICS") - max(already - goods_due, 0), 0)
    logistics_principal = min(logi_due, remaining)
    breakdown["logistics_principal"] = round(logistics_principal, 2)
    remaining -= logistics_principal

    remuneration = min(round((goods_principal + logistics_principal) * payload.remuneration_rate / 100, 2), remaining)
    breakdown["remuneration"] = remuneration
    remaining -= remuneration

    fogedom = min(payload.fogedom_allocation, remaining)
    breakdown["fogedom_allocation"] = round(fogedom, 2)
    remaining -= fogedom
    breakdown["oscop_margin"] = round(remaining, 2)

    settlement = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        "collected_amount_ttc": payload.collected_amount_ttc,
        "remuneration_rate": payload.remuneration_rate,
        "breakdown": breakdown, "order": ["vat_reserve", "external_costs", "goods_principal",
                                          "logistics_principal", "remuneration", "fogedom_allocation", "oscop_margin"],
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cash_settlements.insert_one(dict(settlement))
    repaid = goods_principal + logistics_principal + remuneration
    await db.purchase_resale_operations.update_one(
        {"id": operation_id},
        {"$inc": {"client_collected_amount": payload.collected_amount_ttc,
                  "investor_repaid_amount": repaid},
         "$set": {"realized_margin_ex_vat": round(float(op.get("realized_margin_ex_vat") or 0) + breakdown["oscop_margin"], 2)}})
    await _audit("CASH_SETTLEMENT", operation_id, admin, breakdown)
    new_realized = round(float(op.get("realized_margin_ex_vat") or 0) + breakdown["oscop_margin"], 2)
    expected = float(op.get("expected_margin_ex_vat") or 0)
    collected_total = float(op.get("client_collected_amount", 0)) + payload.collected_amount_ttc
    resale_ttc = float(op.get("resale_total_ex_vat", 0)) * (1 + vat_rate / 100)
    if expected > 0 and resale_ttc > 0 and collected_total >= resale_ttc * 0.99:
        deviation = (new_realized - expected) / expected * 100
        if abs(deviation) > 10:
            await notify_admins(
                f"Alerte marge réelle — {op['reference']}",
                f"Marge réalisée {new_realized:,.2f} € vs prévisionnelle {expected:,.2f} € "
                f"(écart {deviation:+.1f} %). Vérification recommandée.")
    if repaid > 0:
        await notify_admins(f"Remboursement investisseur — {op['reference']}",
                            f"Cascade appliquée : principal marchandises {goods_principal:,.2f} €, principal logistique {logistics_principal:,.2f} €, rémunération {remuneration:,.2f} €.")
    return settlement


@pr_router.get("/admin/purchase-resale/operations/{operation_id}/settlements")
async def list_settlements(operation_id: str, admin: dict = Depends(require_reader)):
    s = await db.cash_settlements.find({"operation_id": operation_id}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"settlements": s}


@pr_router.get("/admin/purchase-resale/settlements-register")
async def settlements_register(format: str = "json", admin: dict = Depends(require_reader)):
    """Registre des ventilations d'encaissement (cascade §13.6), exportable CSV."""
    settlements = await db.cash_settlements.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    refs = {o["id"]: o.get("reference") for o in await db.purchase_resale_operations.find(
        {"id": {"$in": list({s["operation_id"] for s in settlements})}}, {"_id": 0, "id": 1, "reference": 1}).to_list(500)}
    rows = []
    for s in settlements:
        b = s["breakdown"]
        rows.append({"date": s["created_at"][:19], "operation": refs.get(s["operation_id"], s["operation_id"]),
                     "encaisse_ttc": s["collected_amount_ttc"], "reserve_tva": b.get("vat_reserve", 0),
                     "couts_externes": b.get("external_costs", 0), "principal_marchandises": b.get("goods_principal", 0),
                     "principal_logistique": b.get("logistics_principal", 0), "remuneration": b.get("remuneration", 0),
                     "fogedom": b.get("fogedom_allocation", 0), "marge_oscop": b.get("oscop_margin", 0),
                     "par": s.get("created_by", "")})
    if format == "csv":
        from fastapi.responses import Response
        import csv
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else
                                ["date", "operation", "encaisse_ttc", "reserve_tva", "couts_externes",
                                 "principal_marchandises", "principal_logistique", "remuneration",
                                 "fogedom", "marge_oscop", "par"], delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="registre-ventilations.csv"'})
    return {"rows": rows, "count": len(rows)}


@pr_router.get("/admin/purchase-resale/margins-by-territory")
async def margins_by_territory(format: str = "json", admin: dict = Depends(require_reader)):
    ops = await db.purchase_resale_operations.find({}, {"_id": 0}).to_list(1000)
    agg = {}
    for o in ops:
        t = o.get("territory_id") or "Non renseigné"
        a = agg.setdefault(t, {"territoire": t, "operations": 0, "marge_previsionnelle": 0.0,
                               "marge_realisee": 0.0, "revente_ht": 0.0})
        a["operations"] += 1
        a["marge_previsionnelle"] += float(o.get("expected_margin_ex_vat") or 0)
        a["marge_realisee"] += float(o.get("realized_margin_ex_vat") or 0)
        a["revente_ht"] += float(o.get("resale_total_ex_vat") or 0)
    rows = sorted([{k: (round(v, 2) if isinstance(v, float) else v) for k, v in a.items()}
                   for a in agg.values()], key=lambda r: -r["marge_previsionnelle"])
    if format == "csv":
        from fastapi.responses import Response
        import csv
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["territoire", "operations", "revente_ht",
                                                 "marge_previsionnelle", "marge_realisee"], delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="marges-par-territoire.csv"'})
    return {"rows": rows}


@pr_router.get("/admin/purchase-resale/audit-register")
async def audit_register(action: Optional[str] = None, operation: Optional[str] = None,
                         format: str = "json", admin: dict = Depends(require_reader)):
    """Journal d'audit global achat-revente, filtrable et exportable CSV."""
    query = {}
    if action:
        query["action"] = action
    entries = await db.purchase_resale_audit.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    refs = {o["id"]: o.get("reference") for o in await db.purchase_resale_operations.find(
        {}, {"_id": 0, "id": 1, "reference": 1}).to_list(1000)}
    rows = []
    for e in entries:
        ref = refs.get(e["operation_id"], e["operation_id"][:8])
        if operation and operation.lower() not in (ref or "").lower():
            continue
        rows.append({"date": e["created_at"][:19], "operation": ref, "action": e["action"],
                     "par": e.get("by", ""), "detail": str(e.get("detail", ""))[:200]})
    actions = sorted({e["action"] for e in entries})
    if format == "csv":
        from fastapi.responses import Response
        import csv
        import io
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["date", "operation", "action", "par", "detail"], delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
        return Response(content="\ufeff" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="journal-audit-achat-revente.csv"'})
    return {"rows": rows[:300], "count": len(rows), "actions": actions}
