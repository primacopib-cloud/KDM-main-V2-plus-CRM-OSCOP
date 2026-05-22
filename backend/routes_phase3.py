"""Phase 3 endpoints: Brevo emails, Notifications, Multi-territoires,
Google OAuth (stub), Mapbox config, Manager LP étendu, Lolo Points avec coords."""
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_user_id

logger = logging.getLogger(__name__)
phase3_router = APIRouter(prefix="/api/lolodrive", tags=["LOLODRIVE Phase 3"])
notif_router = APIRouter(prefix="/api/notifications", tags=["Notifications"])
oauth_router = APIRouter(prefix="/api/auth/google", tags=["Google OAuth"])
config_router = APIRouter(prefix="/api/config", tags=["Public Config"])

db = None
TERRITORIES = ["Guadeloupe", "Martinique", "Guyane", "Réunion"]


def set_phase3_database(database):
    global db
    db = database


async def get_current_user(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


async def require_admin(user: dict = Depends(get_current_user)):
    role = user.get("role")
    if user.get("is_admin") or role in ("SUPER_ADMIN", "ADMIN", "oscop_super_admin", "kdm_b2b_admin"):
        return user
    raise HTTPException(status_code=403, detail="Accès admin requis")


# ============================================================
# BREVO Email service
# ============================================================
async def send_brevo_email(to_email: str, subject: str, html: str, text: str = "") -> dict:
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        logger.warning("BREVO_API_KEY non défini, email non envoyé")
        return {"sent": False, "reason": "no_api_key"}
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "no_reply@kdmarche-oscop.fr")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "KDMARCHE x O'SCOP")
    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
        "textContent": text or _strip_html(html),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": api_key, "content-type": "application/json", "accept": "application/json"},
                json=payload,
            )
        if r.status_code in (200, 201):
            return {"sent": True, "message_id": r.json().get("messageId")}
        logger.warning(f"Brevo error {r.status_code}: {r.text[:200]}")
        return {"sent": False, "reason": f"brevo_{r.status_code}", "body": r.text[:200]}
    except Exception as e:
        logger.warning(f"Brevo network error: {e}")
        return {"sent": False, "reason": "network_error"}


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()


# ============================================================
# NOTIFICATIONS (in-app + email via Brevo)
# ============================================================
class CreateNotif(BaseModel):
    user_id: str
    title: str
    message: str
    severity: str = "info"
    send_email: bool = False


async def create_notification(user_id: str, title: str, message: str, severity: str = "info", send_email: bool = False) -> dict:
    notif = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "message": message,
        "severity": severity,
        "read": False,
        "created_at": datetime.utcnow(),
    }
    await db.notifications.insert_one(notif)
    notif.pop("_id", None)
    # Send email if requested and brevo configured
    if send_email:
        user = await db.users.find_one({"id": user_id})
        if user and user.get("email"):
            html = f"""<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;background:#0a0a0f;color:#fff;border-radius:12px">
<h2 style="color:#D9B35A">{title}</h2><p style="color:#ccc;line-height:1.6">{message}</p>
<hr style="border-color:#333"><p style="font-size:11px;color:#888">KDMARCHÉ × O'SCOP — coopérative ESS Outre-Mer</p></div>"""
            result = await send_brevo_email(user["email"], title, html)
            notif["email_sent"] = result.get("sent", False)
            await db.notifications.update_one({"id": notif["id"]}, {"$set": {"email_sent": result.get("sent", False)}})
    return notif


@notif_router.get("/me")
async def my_notifications(user: dict = Depends(get_current_user)):
    docs = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return {"notifications": docs, "unread": sum(1 for n in docs if not n.get("read"))}


@notif_router.post("/me/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@notif_router.post("/admin/check-expiring-pass")
async def check_expiring_pass(admin: dict = Depends(require_admin)):
    """Trigger J-3 reminder emails for PASS expiring soon."""
    j3 = datetime.utcnow() + timedelta(days=3)
    soon = await db.lolodrive_passes.find({"status": "ACTIVE", "ends_at": {"$lte": j3, "$gte": datetime.utcnow()}}, {"_id": 0}).to_list(500)
    sent = 0
    for p in soon:
        days_left = max(1, (p["ends_at"] - datetime.utcnow()).days)
        await create_notification(
            user_id=p["user_id"],
            title=f"Votre PASS expire dans {days_left} jour(s)",
            message=f"Votre PASS Vie Chère expire le {p['ends_at'].strftime('%d/%m/%Y')}. Pensez à le renouveler pour conserver vos prix PASS sur les ESSENTIELS et continuer à payer en UC.",
            severity="warning",
            send_email=True,
        )
        sent += 1
    return {"checked": len(soon), "notifications_sent": sent}


@notif_router.post("/admin/test-email")
async def admin_test_email(payload: dict, admin: dict = Depends(require_admin)):
    to = payload.get("to") or admin["email"]
    r = await send_brevo_email(to, "Test KDMARCHE x O'SCOP", "<h1>Test Brevo OK</h1><p>Email transactionnel envoyé depuis le backend FastAPI via l'API Brevo.</p>")
    return r


# ============================================================
# MULTI-TERRITOIRES
# ============================================================
@phase3_router.get("/territories")
async def list_territories():
    """Liste des territoires + comptes de produits/points par territoire."""
    out = []
    for t in TERRITORIES:
        product_count = await db.lolodrive_products.count_documents({"is_active": True, "territory": t})
        point_count = await db.lolodrive_points.count_documents({"status": "ACTIVE", "territory": t})
        out.append({"name": t, "products": product_count, "lolo_points": point_count})
    return {"territories": out}


# ============================================================
# MANAGER LP étendu : timeseries + classement réseau
# ============================================================
@phase3_router.get("/manager/timeseries")
async def manager_timeseries(metric: str = "revenue", days: int = 30, user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    days = min(max(days, 7), 365)
    from_date = datetime.utcnow() - timedelta(days=days)
    paid = ["PAID", "PREPARING", "READY", "FULFILLED"]
    if metric == "revenue":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"lolo_point_id": point["id"], "created_at": {"$gte": from_date}, "status": {"$in": paid}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": "$total_cents"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
    elif metric == "orders":
        rows = await db.lolodrive_orders.aggregate([
            {"$match": {"lolo_point_id": point["id"], "created_at": {"$gte": from_date}, "status": {"$in": paid}}},
            {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "value": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(400)
    else:
        raise HTTPException(status_code=400, detail="metric invalide (revenue|orders)")
    return {"metric": metric, "days": days, "points": [{"date": r["_id"], "value": r["value"]} for r in rows]}


@phase3_router.get("/manager/network-ranking")
async def manager_network_ranking(user: dict = Depends(get_current_user)):
    point = await db.lolodrive_points.find_one({"manager_user_id": user["id"]})
    if not point:
        raise HTTPException(status_code=404, detail="Aucun Lolo Point assigné")
    from_date = datetime.utcnow() - timedelta(days=30)
    paid = ["PAID", "PREPARING", "READY", "FULFILLED"]
    rows = await db.lolodrive_orders.aggregate([
        {"$match": {"created_at": {"$gte": from_date}, "status": {"$in": paid}, "lolo_point_id": {"$ne": None}}},
        {"$group": {"_id": "$lolo_point_id", "orders": {"$sum": 1}, "revenue": {"$sum": "$total_cents"}}},
        {"$sort": {"revenue": -1}},
        {"$limit": 50},
    ]).to_list(50)
    point_ids = [r["_id"] for r in rows]
    points = await db.lolodrive_points.find({"id": {"$in": point_ids}}, {"_id": 0}).to_list(100)
    by_id = {p["id"]: p for p in points}
    ranking = []
    my_rank = None
    for i, r in enumerate(rows):
        p = by_id.get(r["_id"], {})
        entry = {"rank": i + 1, "lolo_point_id": r["_id"], "name": p.get("name", "?"), "city": p.get("city"), "code": p.get("code"), "orders": r["orders"], "revenue_cents": r["revenue"]}
        if r["_id"] == point["id"]:
            my_rank = entry
        ranking.append(entry)
    return {"ranking": ranking, "my_rank": my_rank, "my_point_id": point["id"]}


# ============================================================
# CARTE — Lolo Points avec coords
# ============================================================
@phase3_router.get("/lolo-points/with-coords")
async def list_points_with_coords():
    points = await db.lolodrive_points.find({"status": "ACTIVE"}, {"_id": 0}).to_list(500)
    return {"points": [p for p in points if p.get("latitude") is not None and p.get("longitude") is not None]}


# ============================================================
# CONFIG public (Mapbox + Google)
# ============================================================
@config_router.get("/public")
async def public_config():
    return {
        "mapbox_token": os.environ.get("MAPBOX_TOKEN", ""),
        "google_login_enabled": bool(os.environ.get("GOOGLE_CLIENT_ID")),
    }


# ============================================================
# GOOGLE OAUTH (structure prête)
# ============================================================
@oauth_router.get("/login")
async def google_login_url():
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI", "")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google OAuth non configuré (GOOGLE_CLIENT_ID manquant). Voir README.")
    state = str(uuid.uuid4())
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}&redirect_uri={redirect_uri}"
        f"&response_type=code&scope=openid+email+profile&state={state}"
    )
    return {"login_url": url, "state": state}


@oauth_router.get("/callback")
async def google_callback(code: str = Query(...), state: Optional[str] = None):
    """Stub : échange du code contre tokens. À compléter quand GOOGLE_CLIENT_ID/SECRET fournis."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not (client_id and client_secret):
        raise HTTPException(status_code=503, detail="Google OAuth non configuré côté serveur")
    # Real implementation would exchange code -> id_token via Google,
    # decode id_token, find/create user, return JWT.
    raise HTTPException(status_code=501, detail="Implémentation à finaliser quand les clés Google seront fournies")


async def setup_phase3_indexes(database):
    await database.notifications.create_index([("user_id", 1), ("created_at", -1)])
    await database.notifications.create_index("read")
