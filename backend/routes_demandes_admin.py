"""Super Admin KDMARCHÉ — gestion des coûts/conditions de Communityplace Demandes (plateforme O'SCOP distante)."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

demandes_admin_router = APIRouter(prefix="/api/admin/demandes", tags=["demandes-admin"])

db = None


def set_demandes_admin_database(database):
    global db
    db = database


@demandes_admin_router.get("/remote-tarifs")
async def list_remote_tarifs(admin: dict = Depends(require_admin)):
    from oscop_demandes_client import is_oscop_configured, get_remote_tarifs
    if not is_oscop_configured():
        raise HTTPException(status_code=503, detail="Plateforme O'SCOP non configurée")
    try:
        return await get_remote_tarifs()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Plateforme O'SCOP injoignable : {exc}")


@demandes_admin_router.put("/remote-tarifs/{tarif_id}")
async def update_remote(tarif_id: str, payload: dict, admin: dict = Depends(require_admin)):
    from oscop_demandes_client import update_remote_tarif
    try:
        result = await update_remote_tarif(tarif_id, payload)
        logger.info("Tarif Communityplace Demandes %s mis à jour par %s", tarif_id, admin.get("email"))
        return result
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Mise à jour distante échouée : {exc}")


@demandes_admin_router.patch("/remote-tarifs/{tarif_id}/toggle")
async def toggle_remote(tarif_id: str, payload: dict, admin: dict = Depends(require_admin)):
    from oscop_demandes_client import toggle_remote_tarif
    try:
        return await toggle_remote_tarif(tarif_id, bool(payload.get("is_active")))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Bascule distante échouée : {exc}")


@demandes_admin_router.get("/pushes")
async def list_pushes(admin: dict = Depends(require_admin)):
    """Journal des demandes de devis poussées vers Communityplace Demandes."""
    quotes = await db.quote_requests.find(
        {}, {"_id": 0, "id": 1, "company": 1, "contact_name": 1, "first_name": 1, "last_name": 1,
             "legal_status": 1, "email": 1, "phone": 1, "phone_country": 1, "lang": 1, "status": 1,
             "created_at": 1, "oscop_status": 1, "oscop_demande_id": 1, "oscop_error": 1, "oscop_pushed_at": 1, "message": 1,
             "internal_note": 1, "note_by": 1, "followup_sent_at": 1, "status_history": 1,
             "converted_user_id": 1, "converted_role": 1, "last_manual_reminder_at": 1, "manual_reminders": 1}
    ).sort("created_at", -1).limit(50).to_list(50)
    for q in quotes:
        if isinstance(q.get("created_at"), object) and hasattr(q["created_at"], "isoformat"):
            q["created_at"] = q["created_at"].isoformat()
    return {"quotes": quotes}


@demandes_admin_router.post("/pushes/{quote_id}/retry")
async def retry_push(quote_id: str, admin: dict = Depends(require_admin)):
    from oscop_demandes_client import push_quote_to_oscop
    await push_quote_to_oscop(db, quote_id)
    quote = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0, "oscop_status": 1, "oscop_error": 1, "oscop_demande_id": 1})
    if not quote:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return quote
