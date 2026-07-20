"""Consultations compétitives — machine à états, double validation, verrouillage à la publication.
BROUILLON → EN_VALIDATION → VALIDEE → PUBLIEE → INSCRIPTIONS_OUVERTES → EN_COURS → CLOTUREE
→ EN_EVALUATION → ATTRIBUEE → ARCHIVEE (+ SANS_SUITE, ANNULEE avec recrédit CPC automatique)."""
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin
from consultation_audit import audit

logger = logging.getLogger(__name__)

consultations_router = APIRouter(prefix="/api/admin/consultations", tags=["consultations"])

db = None

DEFAULT_CRITERIA = [
    {"key": "prix", "label": "Prix total rendu", "weight": 35},
    {"key": "qualite", "label": "Qualité et conformité", "weight": 20},
    {"key": "disponibilite", "label": "Disponibilité", "weight": 15},
    {"key": "logistique", "label": "Performance logistique", "weight": 15},
    {"key": "impact", "label": "Impact territorial et ESS", "weight": 10},
    {"key": "tracabilite", "label": "Traçabilité", "weight": 5},
]

TRANSITIONS = {
    "BROUILLON": ["EN_VALIDATION"],
    "EN_VALIDATION": ["VALIDEE", "BROUILLON"],
    "VALIDEE": ["PUBLIEE"],
    "PUBLIEE": ["INSCRIPTIONS_OUVERTES", "ANNULEE"],
    "INSCRIPTIONS_OUVERTES": ["EN_COURS", "ANNULEE"],
    "EN_COURS": ["CLOTUREE", "ANNULEE"],
    "CLOTUREE": ["EN_EVALUATION", "SANS_SUITE"],
    "EN_EVALUATION": ["ATTRIBUEE", "SANS_SUITE"],
    "ATTRIBUEE": ["ARCHIVEE"],
}
LOCKED_AFTER_PUBLISH = ["type", "procedure", "category", "sku_ean", "products", "volumes",
                        "territories", "opens_at", "closes_at", "criteria", "cpc_cost",
                        "max_rounds", "specs", "tie_break_order"]


def set_consultations_database(database):
    global db
    db = database


async def _next_ref() -> str:
    from pymongo import ReturnDocument
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"consultation_{year}"}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER)
    return f"CONS-{year}-{doc['seq']:04d}"


async def _get(cid: str) -> dict:
    c = await db.consultations.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Consultation introuvable")
    return c


class ConsultationBody(BaseModel):
    title: str
    type: str = "STANDARD"  # STANDARD | INTERTERRITORIALE
    procedure: str = "SCELLEE"  # SCELLEE | ENCHERE_INVERSEE
    category: str
    sku_ean: Optional[str] = None
    products: List[dict] = []
    territories: List[str] = []
    specs: str = ""
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    max_rounds: int = 3
    criteria: Optional[List[dict]] = None


@consultations_router.post("")
async def create_consultation(body: ConsultationBody, admin: dict = Depends(require_admin)):
    from routes_cpc_admin import get_cpc_settings
    from routes_legal_matrix import resolve_legal_status
    settings = await get_cpc_settings()
    legal = await resolve_legal_status(body.category, body.sku_ean)
    procedure = "SCELLEE" if legal["status"] == "ROUGE" else body.procedure
    doc = {
        "id": str(uuid.uuid4()), "ref": await _next_ref(), "version": 1,
        "title": body.title.strip(), "type": body.type, "procedure": procedure,
        "category": body.category.strip().lower(), "sku_ean": body.sku_ean,
        "legal_status": legal["status"], "legal_matrix_id": legal.get("id"),
        "legal_matrix_version": legal.get("version"), "orange_validation": None,
        "products": body.products, "territories": body.territories, "specs": body.specs,
        "cpc_cost": settings["interterritorial_cost"] if body.type == "INTERTERRITORIALE" else settings["standard_cost"],
        "max_rounds": body.max_rounds, "criteria": body.criteria or DEFAULT_CRITERIA,
        "tie_break_order": ["qualite", "logistique", "disponibilite", "tracabilite", "first_timestamp"],
        "opens_at": body.opens_at, "closes_at": body.closes_at,
        "status": "BROUILLON", "validations": {},
        "published_snapshot_hash": None,
        "created_by": admin.get("email"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.consultations.insert_one({**doc})
    await audit("LOT_CREATED", admin.get("email"), doc["id"],
                {"ref": doc["ref"], "legal_status": legal["status"], "procedure": procedure})
    return doc


@consultations_router.get("")
async def list_consultations(status: Optional[str] = None, admin: dict = Depends(require_admin)):
    q = {"status": status} if status else {}
    items = await db.consultations.find(q, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"items": items}


@consultations_router.get("/{cid}")
async def get_consultation(cid: str, admin: dict = Depends(require_admin)):
    return await _get(cid)


@consultations_router.put("/{cid}")
async def update_consultation(cid: str, body: dict, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    published = c["status"] not in ("BROUILLON", "EN_VALIDATION", "VALIDEE")
    allowed = {k: v for k, v in body.items()
               if k in ("title", "type", "procedure", "category", "sku_ean", "products", "territories",
                        "specs", "opens_at", "closes_at", "max_rounds", "criteria", "cpc_cost")}
    if published:
        locked = [k for k in allowed if k in LOCKED_AFTER_PUBLISH]
        if locked:
            raise HTTPException(status_code=409, detail=f"Champs verrouillés après publication : {', '.join(locked)}. "
                                                        "Annulez la consultation (recrédit auto) et créez une nouvelle version.")
    if "category" in allowed or "sku_ean" in allowed:
        from routes_legal_matrix import resolve_legal_status
        legal = await resolve_legal_status(allowed.get("category", c["category"]), allowed.get("sku_ean", c.get("sku_ean")))
        allowed["legal_status"] = legal["status"]
        allowed["legal_matrix_id"] = legal.get("id")
        allowed["legal_matrix_version"] = legal.get("version")
        allowed["orange_validation"] = None
    if c["legal_status"] == "ROUGE" and allowed.get("procedure") == "ENCHERE_INVERSEE":
        raise HTTPException(status_code=409, detail="Lot ROUGE : enchère inversée interdite (art. L.442-8) — offres scellées uniquement")
    if allowed.get("legal_status") == "ROUGE":
        allowed["procedure"] = "SCELLEE"
    allowed["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.consultations.update_one({"id": cid}, {"$set": allowed})
    await audit("LOT_UPDATED", admin.get("email"), cid, {"fields": list(allowed.keys())})
    return await _get(cid)


@consultations_router.get("/{cid}/liquidity")
async def liquidity_score(cid: str, admin: dict = Depends(require_admin)):
    """Score de liquidité avant publication : fournisseurs éligibles → procédure recommandée."""
    c = await _get(cid)
    vendor_ids = await db.vendor_products.distinct("vendor_id", {"category": c.get("category")})
    emails = set()
    if vendor_ids:
        async for v in db.vendors.find({"id": {"$in": vendor_ids}}, {"_id": 0, "email": 1}):
            if v.get("email"):
                emails.add(v["email"].lower())
    eligible = len(emails)
    past_ids = [p["id"] async for p in db.consultations.find(
        {"category": c["category"], "id": {"$ne": cid}}, {"_id": 0, "id": 1})]
    hist = len(await db.consultation_entries.distinct(
        "vendor_user_id", {"consultation_id": {"$in": past_ids}})) if past_ids else 0
    if eligible <= 1:
        reco, msg = "NEGOCIATION_DIRECTE", f"{eligible} fournisseur éligible — négociation directe recommandée"
    elif eligible == 2:
        reco, msg = "SCELLEE", "2 fournisseurs éligibles — offre scellée comparative recommandée"
    else:
        reco, msg = "ENCHERE_POSSIBLE", f"{eligible} fournisseurs éligibles — enchère envisageable"
    return {"eligible_vendors": eligible, "historical_participants": hist,
            "recommendation": reco, "message": msg}


@consultations_router.post("/{cid}/duplicate")
async def duplicate_consultation(cid: str, admin: dict = Depends(require_admin)):
    """Relance la même consultation en deux clics : copie en BROUILLON, statut juridique re-résolu, dates recalées."""
    c = await _get(cid)
    from routes_legal_matrix import resolve_legal_status
    from routes_cpc_admin import get_cpc_settings
    settings = await get_cpc_settings()
    legal = await resolve_legal_status(c["category"], c.get("sku_ean"))
    procedure = "SCELLEE" if legal["status"] == "ROUGE" else c["procedure"]
    now = datetime.now(timezone.utc)
    try:
        duration = datetime.fromisoformat(c["closes_at"]) - datetime.fromisoformat(c["opens_at"])
    except (ValueError, TypeError, KeyError):
        duration = timedelta(days=7)
    doc = {
        "id": str(uuid.uuid4()), "ref": await _next_ref(), "version": 1,
        "title": c["title"], "type": c["type"], "procedure": procedure,
        "category": c["category"], "sku_ean": c.get("sku_ean"),
        "legal_status": legal["status"], "legal_matrix_id": legal.get("id"),
        "legal_matrix_version": legal.get("version"), "orange_validation": None,
        "products": c.get("products") or [], "territories": c.get("territories") or [],
        "specs": c.get("specs", ""),
        "cpc_cost": settings["interterritorial_cost"] if c["type"] == "INTERTERRITORIALE" else settings["standard_cost"],
        "max_rounds": c.get("max_rounds", 3), "criteria": c.get("criteria") or DEFAULT_CRITERIA,
        "tie_break_order": c.get("tie_break_order") or ["qualite", "logistique", "disponibilite", "tracabilite", "first_timestamp"],
        "opens_at": now.isoformat(), "closes_at": (now + duration).isoformat(),
        "status": "BROUILLON", "validations": {}, "published_snapshot_hash": None,
        "duplicated_from": cid, "created_by": admin.get("email"),
        "created_at": now.isoformat(), "updated_at": now.isoformat(),
    }
    await db.consultations.insert_one({**doc})
    await audit("LOT_CREATED", admin.get("email"), doc["id"],
                {"ref": doc["ref"], "duplicated_from": c["ref"], "legal_status": legal["status"], "procedure": procedure})
    return doc


class OrangeValidationBody(BaseModel):
    reason: str
    allow_auction: bool = False


@consultations_router.post("/{cid}/validate-orange")
async def validate_orange(cid: str, body: OrangeValidationBody, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    if c["legal_status"] != "ORANGE":
        raise HTTPException(status_code=400, detail="Cette consultation n'est pas classée ORANGE")
    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="Motivation juridique obligatoire")
    val = {"author": admin.get("email"), "date": datetime.now(timezone.utc).isoformat(),
           "reason": body.reason.strip(), "allow_auction": body.allow_auction}
    upd = {"orange_validation": val}
    if not body.allow_auction:
        upd["procedure"] = "SCELLEE"
    await db.consultations.update_one({"id": cid}, {"$set": upd})
    await audit("LEGAL_VALIDATED_ORANGE", admin.get("email"), cid, val)
    return {"ok": True, "orange_validation": val}


@consultations_router.post("/{cid}/validate/{kind}")
async def validate_consultation(cid: str, kind: str, admin: dict = Depends(require_admin)):
    """kind = commercial (KDMARCHE) | platform (O'SCOP)."""
    if kind not in ("commercial", "platform"):
        raise HTTPException(status_code=400, detail="Type de validation invalide")
    c = await _get(cid)
    if c["status"] not in ("EN_VALIDATION",):
        raise HTTPException(status_code=409, detail=f"Validation impossible au statut {c['status']}")
    val = {"by": admin.get("email"), "at": datetime.now(timezone.utc).isoformat()}
    await db.consultations.update_one({"id": cid}, {"$set": {f"validations.{kind}": val}})
    await audit("VALIDATION_COMMERCIAL" if kind == "commercial" else "VALIDATION_PLATFORM",
                admin.get("email"), cid, val)
    c = await _get(cid)
    needs_double = c["legal_status"] == "ORANGE" or c["type"] == "INTERTERRITORIALE"
    have = c.get("validations", {})
    if (needs_double and have.get("commercial") and have.get("platform")) or (not needs_double and (have.get("commercial") or have.get("platform"))):
        await db.consultations.update_one({"id": cid}, {"$set": {"status": "VALIDEE"}})
        return {"ok": True, "status": "VALIDEE"}
    return {"ok": True, "status": c["status"], "waiting_for": "platform" if have.get("commercial") else "commercial"}


def _publish_guards(c: dict) -> List[str]:
    errors = []
    if c["legal_status"] == "NON_CLASSE":
        errors.append("Catégorie non classée dans la matrice juridique")
    if c["legal_status"] == "ORANGE" and not c.get("orange_validation"):
        errors.append("Validation juridique nominative du lot ORANGE requise")
    if c["legal_status"] == "ROUGE" and c["procedure"] != "SCELLEE":
        errors.append("Lot ROUGE : offres scellées obligatoires")
    total = sum(cr.get("weight", 0) for cr in c.get("criteria", []))
    if total != 100:
        errors.append(f"Les pondérations des critères totalisent {total} % (100 % requis)")
    if not c.get("cpc_cost"):
        errors.append("Coût CPC non fixé")
    if not c.get("opens_at") or not c.get("closes_at"):
        errors.append("Dates d'ouverture et de clôture requises")
    elif c["closes_at"] <= c["opens_at"]:
        errors.append("La clôture doit être postérieure à l'ouverture")
    elif c["closes_at"] <= datetime.now(timezone.utc).isoformat():
        errors.append("La clôture est déjà passée")
    if not c.get("products"):
        errors.append("Aucun produit défini")
    needs_double = c["legal_status"] == "ORANGE" or c["type"] == "INTERTERRITORIALE"
    have = c.get("validations", {})
    if needs_double and not (have.get("commercial") and have.get("platform")):
        errors.append("Double validation requise (commerciale KDMARCHE + plateforme O'SCOP)")
    return errors


@consultations_router.post("/{cid}/publish")
async def publish_consultation(cid: str, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    if c["status"] != "VALIDEE":
        raise HTTPException(status_code=409, detail=f"Publication impossible au statut {c['status']}")
    errors = _publish_guards(c)
    if errors:
        raise HTTPException(status_code=409, detail=" · ".join(errors))
    snapshot = {k: c.get(k) for k in LOCKED_AFTER_PUBLISH + ["legal_status", "legal_matrix_version", "title", "ref", "version"]}
    snap_hash = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
    await db.consultations.update_one({"id": cid}, {"$set": {
        "status": "PUBLIEE", "published_snapshot": snapshot, "published_snapshot_hash": snap_hash,
        "published_at": datetime.now(timezone.utc).isoformat(), "published_by": admin.get("email")}})
    await audit("PUBLISHED", admin.get("email"), cid, {"snapshot_hash": snap_hash})
    return {"ok": True, "status": "PUBLIEE", "snapshot_hash": snap_hash}


class TransitionBody(BaseModel):
    to: str
    reason: Optional[str] = None


@consultations_router.post("/{cid}/transition")
async def transition(cid: str, body: TransitionBody, admin: dict = Depends(require_admin)):
    c = await _get(cid)
    allowed = TRANSITIONS.get(c["status"], [])
    if body.to not in allowed:
        raise HTTPException(status_code=409, detail=f"Transition {c['status']} → {body.to} interdite (autorisées : {', '.join(allowed) or 'aucune'})")
    if body.to == "PUBLIEE":
        raise HTTPException(status_code=409, detail="Utilisez l'action Publier (contrôles obligatoires)")
    if body.to in ("ANNULEE", "SANS_SUITE") and not (body.reason or "").strip():
        raise HTTPException(status_code=400, detail="Motif obligatoire")
    upd = {"status": body.to, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.reason:
        upd["status_reason"] = body.reason.strip()
    await db.consultations.update_one({"id": cid}, {"$set": upd})
    if body.to == "CLOTUREE" and c["procedure"] == "SCELLEE":
        from routes_bids import open_sealed_bids
        await open_sealed_bids(cid)
    if body.to == "CLOTUREE":
        import asyncio
        from consultation_notify import notify_report_available
        asyncio.create_task(notify_report_available(cid))
    event = {"ANNULEE": "CANCELLED", "SANS_SUITE": "NO_FOLLOW_UP", "CLOTUREE": "CLOSED"}.get(body.to, f"STATUS_{body.to}")
    await audit(event, admin.get("email"), cid, {"from": c["status"], "to": body.to, "reason": body.reason})
    refunded = 0
    if body.to == "ANNULEE":
        refunded = await _refund_entries(c)
    if body.to == "INSCRIPTIONS_OUVERTES":
        import asyncio
        asyncio.create_task(_notify_vendors_opening({**c, "status": body.to}))
    return {"ok": True, "status": body.to, "cpc_refunded_entries": refunded}


async def _notify_vendors_opening(c: dict):
    """Email ciblé : vendeurs dont les produits correspondent à la catégorie du lot (repli : tous les vendeurs actifs)."""
    try:
        from brevo_service import send_email
        base = os.environ.get("FRONTEND_PUBLIC_URL", "")
        # Ciblage par catégorie de produits
        vendor_ids = await db.vendor_products.distinct("vendor_id", {"category": c.get("category")})
        emails = set()
        if vendor_ids:
            async for v in db.vendors.find({"id": {"$in": vendor_ids}}, {"_id": 0, "email": 1}):
                if v.get("email"):
                    emails.add(v["email"].lower())
        targeted = bool(emails)
        q = {"role": "vendor", "suspended": {"$ne": True}}
        if targeted:
            q["email"] = {"$in": list(emails)}
        sent = 0
        async for u in db.users.find(q, {"_id": 0, "email": 1, "full_name": 1, "name": 1}).limit(200):
            if not u.get("email"):
                continue
            try:
                await send_email(
                    to_email=u["email"], to_name=u.get("full_name") or u.get("name"),
                    subject=f"Nouvelle consultation ouverte : {c['title']} ({c['ref']})",
                    html_content=f"""<h2 style="color:#451F6B;">Consultation {c['ref']} — inscriptions ouvertes</h2>
                    <p>Bonjour,</p>
                    <p><strong>{c['title']}</strong> — catégorie <strong>{c['category']}</strong>{' (correspondant à vos produits)' if targeted else ''} ·
                    procédure {'offres scellées' if c['procedure'] == 'SCELLEE' else 'enchère inversée'} ·
                    accès {c['cpc_cost']} CPC ({c.get('max_rounds', 3)} tours inclus) ·
                    clôture le {str(c.get('closes_at', ''))[:16].replace('T', ' ')} (heure serveur).</p>
                    <p style="margin:24px 0;"><a href="{base}/vendor?tab=consultations"
                    style="background:#D4AF37;color:#1F0A33;padding:12px 24px;border-radius:10px;text-decoration:none;font-weight:bold;">Voir la consultation</a></p>
                    <p style="color:#777;font-size:12px;">Les offres sont exprimées en euros HT. Les CPC n'interviennent jamais dans le classement.</p>""",
                    tags=["consultation-opening"])
                sent += 1
            except Exception as exc:
                logger.warning("Notif consultation %s → %s : %s", c["ref"], u["email"], exc)
        await audit("NOTIFICATION_SENT", "system", c["id"],
                    {"kind": "opening", "sent": sent, "targeted_by_category": targeted, "category": c.get("category")})
        logger.info("Consultation %s : %d vendeurs notifiés (ciblage catégorie : %s)", c["ref"], sent, targeted)
    except Exception as exc:
        logger.warning("Notification ouverture %s : %s", c.get("ref"), exc)


async def _refund_entries(c: dict) -> int:
    """Recrédit automatique et idempotent de tous les inscrits (annulation imputable à l'organisateur)."""
    from cpc_ledger import add_cpc_movement
    count = 0
    async for e in db.consultation_entries.find({"consultation_id": c["id"], "status": "INSCRIT"}, {"_id": 0}):
        entry = await add_cpc_movement(
            e["vendor_user_id"], "REFUND_CANCELLATION", c["cpc_cost"],
            idempotency_key=f"refund:{c['id']}:{e['id']}",
            reason=f"Annulation consultation {c['ref']} — recrédit automatique",
            consultation_id=c["id"], allow_frozen=True)
        if entry:
            count += 1
            await audit("CPC_CREDIT", "system", c["id"], {"user_id": e["vendor_user_id"], "qty": c["cpc_cost"]})
    return count
