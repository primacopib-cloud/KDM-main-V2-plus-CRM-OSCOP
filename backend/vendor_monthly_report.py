"""Rapport mensuel vendeur : vues des spots, meilleur spot, ventes — email Brevo."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from admin_guard import require_admin
from auth import get_current_user_id

logger = logging.getLogger(__name__)
vendor_reports_router = APIRouter(prefix="/api/admin/vendor-reports", tags=["Vendor Reports"])

db = None


def set_vendor_reports_database(database) -> None:
    global db
    db = database


async def _vendor_month_stats(vendor_id: str) -> dict:
    jobs = await db.ai_video_jobs.find(
        {"vendor_id": vendor_id, "status": "DONE"}, {"_id": 0, "product_id": 1}).to_list(200)
    product_ids = list({j["product_id"] for j in jobs})
    total_views, best = 0, None
    for pid in product_ids:
        p = await db.vendor_products.find_one({"id": pid}, {"_id": 0, "name": 1, "video_views": 1}) or {}
        views = int(p.get("video_views") or 0)
        total_views += views
        if best is None or views > best["views"]:
            best = {"name": p.get("name", "Produit"), "views": views}
    sales = await db.orders.aggregate([
        {"$unwind": "$items"},
        {"$match": {"items.vendor_id": vendor_id, "status": {"$nin": ["CANCELLED"]}}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$total_ht"}, "order_count": {"$sum": 1}}},
    ]).to_list(1)
    sales_data = sales[0] if sales else {}
    return {
        "spots": len(jobs), "total_views": total_views, "best": best,
        "revenue": round(float(sales_data.get("total_revenue") or 0), 2),
        "orders": int(sales_data.get("order_count") or 0),
    }


async def send_vendor_monthly_reports(force: bool = False) -> int:
    """Envoie le récap mensuel à chaque vendeur (idempotent par mois via monthly_report_sent)."""
    import os
    from brevo_service import is_brevo_configured, send_email, _wrap_html

    if not is_brevo_configured():
        logger.info("Rapport mensuel: Brevo non configuré — skip")
        return 0
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    base = os.environ.get("FRONTEND_URL", "")
    sent = 0
    async for vendor in db.vendors.find({"email": {"$ne": None}}, {"_id": 0}):
        if not force and vendor.get("monthly_report_sent") == month_key:
            continue
        stats = await _vendor_month_stats(vendor["id"])
        best_html = (
            f"<li>🏆 Meilleur spot : <strong>{stats['best']['name']}</strong> ({stats['best']['views']} vues)</li>"
            if stats["best"] else ""
        )
        body = (
            f"<p>Bonjour {vendor.get('contact_name', '')},</p>"
            f"<p>Voici votre récapitulatif KDMARCHÉ :</p>"
            "<ul>"
            f"<li>🎬 Spots vidéo publiés : <strong>{stats['spots']}</strong></li>"
            f"<li>👁 Vues cumulées de vos spots : <strong>{stats['total_views']}</strong></li>"
            f"{best_html}"
            f"<li>🛒 Commandes reçues : <strong>{stats['orders']}</strong></li>"
            f"<li>💶 Chiffre d'affaires HT : <strong>{stats['revenue']:.2f} €</strong></li>"
            "</ul>"
            f"<p>Retrouvez le détail dans votre <a href='{base}/espace-vendeur'>Espace Vendeur</a>. "
            "Pensez à créer de nouveaux spots pour booster votre visibilité !</p>"
        )
        try:
            await send_email(
                to_email=vendor["email"], to_name=vendor.get("contact_name"),
                subject=f"📊 Votre rapport mensuel KDMARCHÉ — {month_key}",
                html_content=_wrap_html("Votre rapport mensuel", body),
                tags=["monthly-report"],
            )
            await db.vendors.update_one({"id": vendor["id"]}, {"$set": {"monthly_report_sent": month_key}})
            sent += 1
        except Exception as exc:
            logger.warning("Rapport mensuel échoué pour %s: %s", vendor.get("email"), exc)
    if sent:
        logger.info("Rapport mensuel: %d email(s) envoyé(s)", sent)
    return sent


async def _admin(user_id: str = Depends(get_current_user_id)) -> dict:
    return await require_admin(user_id)


@vendor_reports_router.post("/send")
async def trigger_monthly_reports(force: bool = False, _: dict = Depends(_admin)):
    """Déclenche manuellement l'envoi des rapports mensuels vendeurs."""
    sent = await send_vendor_monthly_reports(force=force)
    return {"status": "DONE", "sent": sent}
