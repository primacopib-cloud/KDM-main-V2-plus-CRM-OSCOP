"""Relance des dossiers d'adhésion incomplets — déclenchement manuel admin."""
from fastapi import APIRouter, HTTPException, Depends

adhesion_reminders_router = APIRouter(prefix="/api/v2")

db = None


def set_adhesion_reminders_database(database):
    global db
    db = database


from routes_v2 import get_current_user_v2


@adhesion_reminders_router.post("/admin/adhesion-reminders/run")
async def run_reminders_now(current_user: dict = Depends(get_current_user_v2)):
    """Envoie immédiatement les relances des dossiers DRAFT bloqués depuis 48 h+ (admin)."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    from adhesion_emails import run_adhesion_reminders
    sent = await run_adhesion_reminders(db)
    return {"ok": True, "reminders_sent": sent}


@adhesion_reminders_router.post("/admin/applications/{app_id}/remind")
async def remind_single_application(app_id: str, current_user: dict = Depends(get_current_user_v2)):
    """Relance immédiate d'un dossier précis, même déjà relancé (admin)."""
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    app = await db.b2b_applications.find_one({"id": app_id})
    if not app:
        raise HTTPException(status_code=404, detail="Demande non trouvée")
    if app["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Seuls les dossiers en brouillon peuvent être relancés")
    from adhesion_emails import run_adhesion_reminders
    sent = await run_adhesion_reminders(db, only_app_id=app_id, force=True)
    return {"ok": True, "reminders_sent": sent}
