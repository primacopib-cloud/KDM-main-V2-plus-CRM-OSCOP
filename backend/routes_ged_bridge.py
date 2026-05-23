"""
Pont GED ESS externe pour KDMARCHE × O'SCOP.

Namespace : /api/ged-bridge/*

Ce routeur ne remplace pas la GED interne existante /api/ged.
Il connecte le code actuel à un microservice GED ESS externe :
- PostgreSQL / S3-R2 / audit probant / webhooks / PDF institutionnels
- synchronisation CRM, LOLODRIVE, KDMARCHE, O'SCOP, COPPAM, FOGEDOM
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import get_current_user_id
from ged_external_client import (
    GedExternalClient,
    GedExternalError,
    PDF_TEMPLATE_BY_SCOPE,
    build_ged_business_metadata,
    resolve_scope_code,
)


ged_bridge_router = APIRouter(prefix="/api/ged-bridge", tags=["GED ESS Bridge"])

db = None


def set_ged_bridge_database(database):
    global db
    db = database


# ------------------------------------------------------------------
# Modèles API
# ------------------------------------------------------------------

class GedBridgeGenerateRequest(BaseModel):
    title: str
    source: str = Field(default="general", description="coppam | oscop | kdmarche | lolodrive | fogedom | ftpe | general")
    entity_id: str = Field(..., description="Identifiant entité côté microservice GED")
    scope_id: str = Field(..., description="Identifiant périmètre côté microservice GED")
    family: str = "CADRE_CIVIL_ESS"
    template_code: Optional[str] = None
    confidentiality: str = "INTERNE"
    project_code: Optional[str] = None
    member_reference: Optional[str] = None
    external_crm_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class GedBridgeCreateDocumentRequest(BaseModel):
    title: str
    source: str = "general"
    entity_id: str
    scope_id: str
    family: str = "AUTRE"
    confidentiality: str = "INTERNE"
    tags: Optional[str] = None
    description: Optional[str] = None
    project_code: Optional[str] = None
    member_reference: Optional[str] = None
    external_crm_id: Optional[str] = None
    external_erp_id: Optional[str] = None
    business_metadata: Dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    role = user.get("role") or user.get("user_role") or user.get("role_v2")
    allowed_roles = {
        "oscop_super_admin",
        "kdm_b2b_admin",
        "admin",
        "ADMIN",
        "SUPER_ADMIN",
        "COOP_BOARD",
        "GESTIONNAIRE_GED",
    }
    if not (user.get("is_admin") or role in allowed_roles):
        raise HTTPException(status_code=403, detail="Accès administrateur GED requis")
    return user


def clean_mongo(doc: Optional[dict]) -> Optional[dict]:
    if not doc:
        return None
    result = dict(doc)
    result.pop("_id", None)
    return result


def as_public_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=502, detail=str(exc))


async def record_bridge_sync(source: str, source_id: str, direction: str, status: str, payload: Dict[str, Any], response: Optional[Dict[str, Any]] = None):
    await db.ged_bridge_sync_events.insert_one({
        "id": f"gedsync-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
        "source": source,
        "source_id": source_id,
        "direction": direction,
        "status": status,
        "payload": payload,
        "response": response or {},
        "created_at": datetime.utcnow(),
    })


# ------------------------------------------------------------------
# Routes techniques
# ------------------------------------------------------------------

@ged_bridge_router.get("/health")
async def ged_bridge_health(_: dict = Depends(require_admin)):
    client = GedExternalClient()
    try:
        external = await client.health()
        return {"bridge": "OK", "external_ged": external}
    except GedExternalError as exc:
        raise as_public_error(exc)


@ged_bridge_router.get("/scopes")
async def ged_bridge_scopes(_: dict = Depends(require_admin)):
    client = GedExternalClient()
    try:
        return await client.list_scopes()
    except GedExternalError as exc:
        raise as_public_error(exc)


@ged_bridge_router.get("/sync-events")
async def ged_bridge_sync_events(
    source: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    _: dict = Depends(require_admin),
):
    query: Dict[str, Any] = {}
    if source:
        query["source"] = source
    if source_id:
        query["source_id"] = source_id
    docs = await db.ged_bridge_sync_events.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"events": docs}


# ------------------------------------------------------------------
# Routes de création directe GED externe
# ------------------------------------------------------------------

@ged_bridge_router.post("/documents")
async def create_external_ged_document(payload: GedBridgeCreateDocumentRequest, _: dict = Depends(require_admin)):
    # Resolve scope code (kept for logging / future routing — not yet used in body)
    resolve_scope_code(payload.source)
    body = payload.model_dump()
    body["business_metadata"] = {
        **payload.business_metadata,
        **build_ged_business_metadata(source=payload.source, source_id=payload.external_crm_id or payload.project_code or payload.title, payload=payload.business_metadata),
    }

    client = GedExternalClient()
    try:
        response = await client.create_document(body)
        await record_bridge_sync(payload.source, payload.external_crm_id or payload.project_code or response.get("id", "unknown"), "OUTBOUND", "SUCCESS", body, response)
        return response
    except GedExternalError as exc:
        await record_bridge_sync(payload.source, payload.external_crm_id or payload.project_code or payload.title, "OUTBOUND", "ERROR", body, {"error": str(exc)})
        raise as_public_error(exc)


@ged_bridge_router.post("/pdf/generate")
async def generate_external_ged_pdf(payload: GedBridgeGenerateRequest, _: dict = Depends(require_admin)):
    scope_code = resolve_scope_code(payload.source)
    template_code = payload.template_code or PDF_TEMPLATE_BY_SCOPE.get(scope_code, "GENERIQUE_ESS")

    body = payload.model_dump()
    body["template_code"] = template_code
    body["context"] = {
        **payload.context,
        "source_system": "KDM_MAIN_V2_PLUS_CRM_OSCOP",
        "source_scope": scope_code,
    }

    client = GedExternalClient()
    try:
        response = await client.generate_pdf(body)
        await record_bridge_sync(payload.source, payload.external_crm_id or payload.project_code or response.get("id", "unknown"), "OUTBOUND", "SUCCESS", body, response)
        return response
    except GedExternalError as exc:
        await record_bridge_sync(payload.source, payload.external_crm_id or payload.project_code or payload.title, "OUTBOUND", "ERROR", body, {"error": str(exc)})
        raise as_public_error(exc)


# ------------------------------------------------------------------
# Synchronisation CRM O'SCOP -> GED externe
# ------------------------------------------------------------------

@ged_bridge_router.post("/crm/dossiers/{dossier_id}/push")
async def push_crm_dossier_to_ged(
    dossier_id: str,
    entity_id: str = Query(..., description="ID entité microservice GED"),
    scope_id: str = Query(..., description="ID périmètre microservice GED"),
    generate_pdf: bool = Query(True),
    user: dict = Depends(require_admin),
):
    dossier = clean_mongo(await db.crm_dossiers.find_one({"id": dossier_id}))
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier CRM introuvable")

    organization = None
    if dossier.get("organization_id"):
        organization = clean_mongo(await db.crm_organizations.find_one({"id": dossier["organization_id"]}))

    contact = None
    if dossier.get("contact_id"):
        contact = clean_mongo(await db.crm_contacts.find_one({"id": dossier["contact_id"]}))

    title = f"Dossier CRM O'SCOP — {dossier.get('type_dossier', 'dossier')} — {dossier.get('objet_besoin') or dossier_id}"
    context = {
        "dossier": dossier,
        "organization": organization,
        "contact": contact,
        "operator": {"id": user.get("id"), "email": user.get("email"), "name": user.get("contact_name")},
    }

    client = GedExternalClient()
    try:
        if generate_pdf:
            body = {
                "template_code": "OSCOP_CONTRAT_COOPERATIF",
                "title": title,
                "entity_id": entity_id,
                "scope_id": scope_id,
                "family": "CONTRAT_COOPERATIF",
                "confidentiality": "INTERNE",
                "external_crm_id": dossier_id,
                "project_code": dossier.get("type_dossier"),
                "member_reference": dossier.get("organization_id") or dossier.get("contact_id"),
                "context": context,
            }
            response = await client.generate_pdf(body)
        else:
            body = {
                "title": title,
                "entity_id": entity_id,
                "scope_id": scope_id,
                "family": "DOSSIER_AO" if dossier.get("type_dossier") == "appel_offres" else "CONVENTION",
                "confidentiality": "INTERNE",
                "external_crm_id": dossier_id,
                "project_code": dossier.get("type_dossier"),
                "member_reference": dossier.get("organization_id") or dossier.get("contact_id"),
                "description": dossier.get("notes") or dossier.get("objet_besoin"),
                "business_metadata": build_ged_business_metadata(source="crm_dossier", source_id=dossier_id, payload=context),
            }
            response = await client.create_document(body)

        await db.crm_dossiers.update_one({"id": dossier_id}, {"$set": {
            "ged_external_document_id": response.get("id"),
            "ged_external_reference": response.get("reference"),
            "ged_synced_at": datetime.utcnow(),
        }})
        await record_bridge_sync("crm_dossier", dossier_id, "OUTBOUND", "SUCCESS", body, response)
        return {"status": "SYNCED", "dossier_id": dossier_id, "ged": response}
    except GedExternalError as exc:
        await record_bridge_sync("crm_dossier", dossier_id, "OUTBOUND", "ERROR", {"dossier_id": dossier_id}, {"error": str(exc)})
        raise as_public_error(exc)


# ------------------------------------------------------------------
# Synchronisation commandes LOLODRIVE/KDMARCHE -> GED externe
# ------------------------------------------------------------------

@ged_bridge_router.post("/lolodrive/orders/{order_id}/push")
async def push_lolodrive_order_to_ged(
    order_id: str,
    entity_id: str = Query(..., description="ID entité microservice GED"),
    scope_id: str = Query(..., description="ID périmètre microservice GED"),
    user: dict = Depends(require_admin),
):
    order = clean_mongo(await db.lolodrive_orders.find_one({"id": order_id}))
    if not order:
        raise HTTPException(status_code=404, detail="Commande LOLODRIVE introuvable")

    buyer = clean_mongo(await db.users.find_one({"id": order.get("user_id")}, {"password_hash": 0})) if order.get("user_id") else None
    title = f"KDMARCHE / LOLODRIVE — Appel à contribution / commande {order.get('order_number') or order_id}"

    context = {
        "order": order,
        "buyer": buyer,
        "holder_name": (buyer or {}).get("company_name") or (buyer or {}).get("contact_name") or order.get("user_id"),
        "amount": f"{(order.get('total_cents') or 0) / 100:.2f} EUR",
        "uc_amount": order.get("uc_amount") or order.get("credits_used") or order.get("uc_used"),
        "operator": {"id": user.get("id"), "email": user.get("email")},
    }

    body = {
        "template_code": "KDMARCHE_APPEL_CONTRIBUTION",
        "title": title,
        "entity_id": entity_id,
        "scope_id": scope_id,
        "family": "APPEL_CONTRIBUTION",
        "confidentiality": "INTERNE",
        "project_code": "LOLODRIVE_ORDER",
        "member_reference": order.get("user_id"),
        "external_crm_id": order_id,
        "context": context,
    }

    client = GedExternalClient()
    try:
        response = await client.generate_pdf(body)
        await db.lolodrive_orders.update_one({"id": order_id}, {"$set": {
            "ged_external_document_id": response.get("id"),
            "ged_external_reference": response.get("reference"),
            "ged_synced_at": datetime.utcnow(),
        }})
        await record_bridge_sync("lolodrive_order", order_id, "OUTBOUND", "SUCCESS", body, response)
        return {"status": "SYNCED", "order_id": order_id, "ged": response}
    except GedExternalError as exc:
        await record_bridge_sync("lolodrive_order", order_id, "OUTBOUND", "ERROR", body, {"error": str(exc)})
        raise as_public_error(exc)


# ------------------------------------------------------------------
# Indexes MongoDB du pont
# ------------------------------------------------------------------

async def ensure_ged_bridge_indexes(database):
    await database.ged_bridge_sync_events.create_index("id", unique=True)
    await database.ged_bridge_sync_events.create_index([("source", 1), ("source_id", 1), ("created_at", -1)])
    await database.ged_bridge_sync_events.create_index([("status", 1), ("created_at", -1)])
