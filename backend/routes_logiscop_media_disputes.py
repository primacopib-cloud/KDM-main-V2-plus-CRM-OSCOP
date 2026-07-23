"""Médias cargaison (photos/vidéos transporteur) + dossiers de litige LOGI'SCOP."""
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core_deps import get_current_user, check_admin, create_notification
from db import get_database

logger = logging.getLogger(__name__)
logiscop_media_router = APIRouter(prefix="/api", tags=["logiscop-transport"])

MEDIA_STAGES = ["PRISE_EN_CHARGE", "TRANSIT", "LIVRAISON"]
MEDIA_PROJECTION = {"_id": 0, "content_b64": 0}


class MediaBody(BaseModel):
    stage: str
    name: str = Field(min_length=3, max_length=150)
    mime: str = Field(min_length=3, max_length=80)
    content_b64: str = Field(min_length=10, max_length=14_000_000)


class DisputeUpdateBody(BaseModel):
    status: Optional[str] = None
    responsibility: Optional[str] = None
    resolution_note: Optional[str] = Field(default=None, max_length=1500)


class PieceBody(BaseModel):
    name: str = Field(min_length=3, max_length=150)
    mime: str = Field(min_length=3, max_length=80)
    content_b64: str = Field(min_length=10, max_length=14_000_000)


async def _operator_for_ot(db, user: dict, ot: dict):
    op = await db.logicoop_operators.find_one(
        {"email": (user.get("email") or "").lower(), "active": True}, {"_id": 0})
    if not op:
        return None
    if ((ot.get("pickup") or {}).get("zone_code") in set(op.get("exw_zones", []))
            or (ot.get("delivery") or {}).get("zone_code") in set(op.get("cif_zones", []))):
        return op
    return None


async def _can_access_ot(db, ot: dict, user: dict) -> bool:
    if user.get("is_admin") or ot["user_id"] == user["id"]:
        return True
    if await db.org_memberships.find_one({"user_id": user["id"], "org_id": ot["org_id"]}):
        return True
    return bool(await _operator_for_ot(db, user, ot))


async def _get_ot_or_404(db, ot_id: str) -> dict:
    ot = await db.logiscop_transport_orders.find_one({"id": ot_id}, {"_id": 0})
    if not ot:
        raise HTTPException(status_code=404, detail="Ordre de transport introuvable")
    return ot


# ---------- Médias cargaison ----------

@logiscop_media_router.post("/logicoop/transport-missions/{ot_id}/media")
async def upload_cargo_media(ot_id: str, body: MediaBody, current_user: dict = Depends(get_current_user)):
    """L'opérateur transmet photos/vidéos de la cargaison (prise en charge → livraison)."""
    if body.stage not in MEDIA_STAGES:
        raise HTTPException(status_code=400, detail=f"Étape invalide ({', '.join(MEDIA_STAGES)})")
    db = get_database()
    ot = await _get_ot_or_404(db, ot_id)
    op = await _operator_for_ot(db, current_user, ot)
    if not op:
        raise HTTPException(status_code=403, detail="Cet OT n'est pas dans vos zones opérateur")
    if ot["status"] not in ("ACCEPTE", "LIVRE_CONFORME", "LIVRE_AVEC_RESERVES", "PARTIEL", "REFUSE_LIVRAISON"):
        raise HTTPException(status_code=409, detail=f"OT non exécutable (statut : {ot['status']})")
    media = {"id": str(uuid.uuid4()), "ot_id": ot_id, "ot_ref": ot["ref"],
             "operator_id": op["id"], "operator_name": op["name"],
             "stage": body.stage, "name": body.name, "mime": body.mime,
             "size_bytes": len(body.content_b64) * 3 // 4, "ged_doc_id": None,
             "uploaded_at": datetime.now(timezone.utc).isoformat()}
    await db.logiscop_cargo_media.insert_one({**media, "content_b64": body.content_b64})
    await create_notification(
        "logiscop_cargo_media", "Média cargaison transmis",
        f"{op['name']} a transmis « {body.name} » ({body.stage.replace('_', ' ').lower()}) sur l'OT {ot['ref']}.",
        target_user_id=ot["user_id"], data={"ot_id": ot_id, "ref": ot["ref"], "stage": body.stage})
    return media


@logiscop_media_router.get("/logiscop-transport/orders/{ot_id}/media")
async def list_cargo_media(ot_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    ot = await _get_ot_or_404(db, ot_id)
    if not await _can_access_ot(db, ot, current_user):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return await db.logiscop_cargo_media.find({"ot_id": ot_id}, MEDIA_PROJECTION).sort("uploaded_at", 1).to_list(50)


@logiscop_media_router.get("/logiscop-transport/media/{media_id}/download")
async def download_cargo_media(media_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    m = await db.logiscop_cargo_media.find_one({"id": media_id}, {"_id": 0})
    if not m:
        raise HTTPException(status_code=404, detail="Média introuvable")
    ot = await _get_ot_or_404(db, m["ot_id"])
    if not await _can_access_ot(db, ot, current_user):
        raise HTTPException(status_code=403, detail="Accès refusé")
    return Response(content=base64.b64decode(m["content_b64"]), media_type=m["mime"],
                    headers={"Content-Disposition": f"attachment; filename={m['name']}"})


# ---------- Litiges ----------

DISPUTE_STATUSES = ["OPEN", "UNDER_REVIEW", "RESOLVED"]
RESPONSIBILITIES = ["INDETERMINEE", "TRANSPORTEUR", "DONNEUR_ORDRE", "PARTAGEE"]


@logiscop_media_router.get("/logiscop-transport/disputes")
async def my_disputes(current_user: dict = Depends(get_current_user)):
    db = get_database()
    m = await db.org_memberships.find_one({"user_id": current_user["id"]}, {"_id": 0, "org_id": 1})
    org_id = current_user.get("organization_id") or (m or {}).get("org_id")
    if not org_id:
        return []
    return await db.logiscop_disputes.find({"org_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(100)


@logiscop_media_router.get("/logiscop-transport/admin/disputes")
async def admin_disputes(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    return await db.logiscop_disputes.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@logiscop_media_router.patch("/logiscop-transport/admin/disputes/{dispute_id}")
async def update_dispute(dispute_id: str, body: DisputeUpdateBody, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    d = await db.logiscop_disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Litige introuvable")
    update, actions = {}, []
    if body.status:
        if body.status not in DISPUTE_STATUSES:
            raise HTTPException(status_code=400, detail="Statut invalide")
        update["status"] = body.status
        actions.append(f"Statut → {body.status}")
    if body.responsibility:
        if body.responsibility not in RESPONSIBILITIES:
            raise HTTPException(status_code=400, detail="Responsabilité invalide")
        update["responsibility"] = body.responsibility
        actions.append(f"Responsabilité → {body.responsibility}")
    if body.resolution_note is not None:
        update["resolution_note"] = body.resolution_note.strip() or None
        actions.append("Note de résolution mise à jour")
    if not update:
        raise HTTPException(status_code=400, detail="Aucune modification")
    if update.get("status") == "RESOLVED":
        update["resolved_at"] = datetime.now(timezone.utc).isoformat()
    entry = {"at": datetime.now(timezone.utc).isoformat(),
             "by": current_user.get("email"), "action": " ; ".join(actions)}
    await db.logiscop_disputes.update_one({"id": dispute_id}, {"$set": update, "$push": {"timeline": entry}})
    if update.get("status"):
        await create_notification(
            "logiscop_dispute_update", f"Litige {d['ref']} — mise à jour",
            f"Litige {d['ref']} (OT {d['ot_ref']}) : {' ; '.join(actions)}.",
            target_user_id=d["user_id"], data={"dispute_id": dispute_id, "ref": d["ref"]})
    return await db.logiscop_disputes.find_one({"id": dispute_id}, {"_id": 0})


@logiscop_media_router.post("/logiscop-transport/disputes/{dispute_id}/pieces")
async def add_dispute_piece(dispute_id: str, body: PieceBody, current_user: dict = Depends(get_current_user)):
    """Ajout d'une pièce au dossier (acheteur concerné ou admin)."""
    db = get_database()
    d = await db.logiscop_disputes.find_one({"id": dispute_id}, {"_id": 0})
    if not d:
        raise HTTPException(status_code=404, detail="Litige introuvable")
    if not current_user.get("is_admin") and d["user_id"] != current_user["id"]:
        m = await db.org_memberships.find_one({"user_id": current_user["id"], "org_id": d["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    now_iso = datetime.now(timezone.utc).isoformat()
    file_id = str(uuid.uuid4())
    await db.logiscop_dispute_files.insert_one({
        "id": file_id, "dispute_id": dispute_id, "name": body.name, "mime": body.mime,
        "content_b64": body.content_b64, "uploaded_by": current_user.get("email"), "uploaded_at": now_iso})
    piece = {"id": file_id, "name": body.name, "by": current_user.get("email"), "at": now_iso}
    await db.logiscop_disputes.update_one(
        {"id": dispute_id},
        {"$push": {"pieces": piece,
                   "timeline": {"at": now_iso, "by": current_user.get("email"),
                                "action": f"Pièce ajoutée : {body.name}"}}})
    return piece


@logiscop_media_router.get("/logiscop-transport/disputes/pieces/{file_id}/download")
async def download_dispute_piece(file_id: str, current_user: dict = Depends(get_current_user)):
    db = get_database()
    f = await db.logiscop_dispute_files.find_one({"id": file_id}, {"_id": 0})
    if not f:
        raise HTTPException(status_code=404, detail="Pièce introuvable")
    d = await db.logiscop_disputes.find_one({"id": f["dispute_id"]}, {"_id": 0})
    if not current_user.get("is_admin") and d["user_id"] != current_user["id"]:
        m = await db.org_memberships.find_one({"user_id": current_user["id"], "org_id": d["org_id"]})
        if not m:
            raise HTTPException(status_code=403, detail="Accès refusé")
    return Response(content=base64.b64decode(f["content_b64"]), media_type=f["mime"],
                    headers={"Content-Disposition": f"attachment; filename={f['name']}"})
