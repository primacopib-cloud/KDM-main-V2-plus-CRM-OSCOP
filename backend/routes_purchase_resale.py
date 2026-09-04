"""Module achat-revente O'SCOP + logistique LOGI'SCOP (Phase 2 noyau)."""
from datetime import datetime, timezone
from typing import Optional, Dict, List
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routes_v2 import get_current_user_v2

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
    investor_name: Optional[str] = None
    funding_instrument: Optional[str] = None
    logistics_status: Optional[str] = None
    notes: Optional[str] = None


class StatusChange(BaseModel):
    status: str
    comment: Optional[str] = None


class TrancheCreate(BaseModel):
    financing_tranche: str
    investor_name: str
    approved_amount: float = Field(gt=0)
    legal_instrument: str = "Bon d'Engagement"
    currency: str = "EUR"


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


@pr_router.get("/admin/purchase-resale/operations")
async def list_operations(admin: dict = Depends(_admin)):
    ops = await db.purchase_resale_operations.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for op in ops:
        op["blockers"] = authorization_blockers(op)
    return {"operations": ops, "statuses": OPERATION_STATUSES, "logistics_statuses": LOGISTICS_STATUSES,
            "logistics_modes": LOGISTICS_MODES, "cost_line_keys": COST_LINE_KEYS,
            "payee_categories": PAYEE_CATEGORIES, "methods": DISBURSEMENT_METHODS,
            "tranches": TRANCHES, "logiscop_notice": LOGISCOP_NOTICE}


@pr_router.get("/admin/purchase-resale/operations/{operation_id}")
async def get_operation(operation_id: str, admin: dict = Depends(_admin)):
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
async def change_status(operation_id: str, payload: StatusChange, admin: dict = Depends(_admin)):
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
async def create_tranche(operation_id: str, payload: TrancheCreate, admin: dict = Depends(_admin)):
    if payload.financing_tranche not in TRANCHES:
        raise HTTPException(status_code=400, detail="Tranche invalide")
    op = await _get_op(operation_id)
    if payload.financing_tranche == "LOGISTICS" and payload.approved_amount > float(op.get("logistics_budget_ex_vat", 0)):
        raise HTTPException(status_code=409, detail="La tranche logistique dépasse le budget logistique approuvé")
    tranche = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        **payload.dict(),
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
async def create_disbursement(operation_id: str, payload: DisbursementCreate, admin: dict = Depends(_admin)):
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
    doc = {
        "id": str(uuid.uuid4()), "operation_id": operation_id,
        "doc_type": payload.doc_type, "doc_number": number,
        "sections": doc_sections(payload.doc_type, op, payload.extra or {}),
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.operation_documents.insert_one(dict(doc))
    await _audit("DOCUMENT_GENERATED", operation_id, admin, {"doc_number": number, "type": payload.doc_type})
    return doc


@pr_router.get("/admin/purchase-resale/operations/{operation_id}/documents")
async def list_documents(operation_id: str, admin: dict = Depends(_admin)):
    docs = await db.operation_documents.find(
        {"operation_id": operation_id}, {"_id": 0, "sections": 0}).sort("created_at", -1).to_list(100)
    return {"documents": docs}


@pr_router.get("/admin/purchase-resale/documents/{doc_id}/pdf")
async def download_document_pdf(doc_id: str, admin: dict = Depends(_admin)):
    from fastapi.responses import Response
    from operation_docs_pdf import build_operation_pdf
    doc = await db.operation_documents.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    pdf = build_operation_pdf(doc)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{doc["doc_number"]}.pdf"'})
