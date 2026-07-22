"""Alertes recherches : email à l'acheteur quand un nouveau produit correspond à une recherche récente."""
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
search_alerts_router = APIRouter(prefix="/api/admin/search-alerts", tags=["search-alerts"])


async def record_user_search(db, user: dict, term: str):
    """Journalise une recherche catalogue (dédupliquée par user+terme)."""
    t = (term or "").strip().lower()
    if len(t) < 2 or len(t) > 60 or not user:
        return
    await db.user_recent_searches.update_one(
        {"user_id": user.get("id"), "term": t},
        {"$set": {"email": user.get("email"),
                  "name": user.get("contact_name") or user.get("company_name") or "",
                  "at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)


def _to_dt(v):
    if hasattr(v, "tzinfo"):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    try:
        d = datetime.fromisoformat(str(v))
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
    except (TypeError, ValueError):
        return None


def _product_matches(term: str, p: dict) -> bool:
    hay = [p.get("name") or "", p.get("description") or "", p.get("short_description") or ""]
    for tr in (p.get("translations") or {}).values():
        if isinstance(tr, dict):
            hay += [tr.get("name") or "", tr.get("description") or "", tr.get("short_description") or ""]
    t = term.lower()
    return any(t in h.lower() for h in hay if h)


def _alert_html(name: str, items_html: str, base: str) -> str:
    return (
        "<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto'>"
        "<div style='background:#2A1045;border-radius:14px;padding:28px;color:#fff'>"
        "<h2 style='color:#D4AF37;margin-top:0'>Du nouveau au catalogue KDMARCHÉ</h2>"
        f"<p>Bonjour <b>{name}</b>,</p>"
        "<p>De nouveaux produits correspondant à vos recherches récentes viennent d'arriver "
        "au catalogue mutualisé :</p>"
        f"<ul style='color:#eee;line-height:1.8'>{items_html}</ul>"
        f"<p style='text-align:center;margin:24px 0'><a href='{base}/catalogue' "
        "style='background:#D4AF37;color:#1F0A33;padding:12px 26px;border-radius:999px;"
        "text-decoration:none;font-weight:bold'>Voir le catalogue</a></p>"
        "</div>"
        "<p style='color:#999;font-size:11px;text-align:center;margin-top:14px'>"
        "KDMARCHÉ × O'SCOP — alerte basée sur vos dernières recherches catalogue</p></div>"
    )


async def check_search_alerts(db) -> dict:
    """Scanne les nouveaux produits ACTIFS et alerte les membres dont une recherche récente matche."""
    now = datetime.now(timezone.utc)
    flag = await db.system_flags.find_one({"key": "search_alerts_last_run"}) or {}
    cutoff = _to_dt(flag.get("at")) or (now - timedelta(hours=24))

    new_products = []
    async for p in db.products.find({"status": "ACTIVE"}, {
            "_id": 0, "id": 1, "name": 1, "description": 1, "short_description": 1,
            "translations": 1, "created_at": 1}):
        c = _to_dt(p.get("created_at"))
        if c and c > cutoff:
            new_products.append(p)

    users = {}
    if new_products:
        since30 = (now - timedelta(days=30)).isoformat()
        async for s in db.user_recent_searches.find({"at": {"$gte": since30}}, {"_id": 0}):
            u = users.setdefault(s["user_id"], {"email": s.get("email"), "name": s.get("name"), "terms": []})
            u["terms"].append(s["term"])

    emails_sent = 0
    base = (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")
    for u in users.values():
        if not u.get("email"):
            continue
        matches = []
        for p in new_products:
            hit = next((t for t in u["terms"] if _product_matches(t, p)), None)
            if hit:
                matches.append((p, hit))
        if not matches:
            continue
        items = "".join(
            f"<li><b>{p.get('name')}</b> — correspond à votre recherche « {t} »</li>"
            for p, t in matches[:10])
        try:
            from brevo_service import send_email
            await send_email(to_email=u["email"], to_name=u.get("name") or u["email"],
                             subject="🆕 De nouveaux produits correspondent à vos recherches — KDMARCHÉ",
                             html_content=_alert_html(u.get("name") or u["email"], items, base),
                             tags=["search-alert"])
            emails_sent += 1
        except Exception as e:
            logger.warning("Alerte recherche non envoyée à %s: %s", u["email"], e)

    await db.system_flags.update_one(
        {"key": "search_alerts_last_run"},
        {"$set": {"at": now.isoformat(), "new_products": len(new_products),
                  "emails_sent": emails_sent}}, upsert=True)
    if emails_sent:
        logger.info("Alertes recherches : %s email(s) envoyé(s) pour %s nouveau(x) produit(s)",
                    emails_sent, len(new_products))
    return {"new_products": len(new_products), "users_scanned": len(users), "emails_sent": emails_sent}


@search_alerts_router.post("/run")
async def run_search_alerts(current_user: dict = Depends(get_current_user)):
    """Déclenchement manuel du scan (admin)."""
    await check_admin(current_user)
    return await check_search_alerts(get_database())
