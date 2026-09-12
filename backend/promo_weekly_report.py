"""Rapport hebdomadaire des promotions envoyé aux superadmins chaque lundi."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_promo_weekly_report(db, now=None) -> bool:
    now = now or datetime.utcnow()
    if now.weekday() != 0:
        return False
    week_tag = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    flag = await db.system_flags.find_one({"key": "promo_report_week"}, {"_id": 0, "value": 1})
    if flag and flag.get("value") == week_tag:
        return False
    await db.system_flags.update_one(
        {"key": "promo_report_week"}, {"$set": {"value": week_tag}}, upsert=True)

    horizon = now + timedelta(days=7)
    active, expiring = [], []
    async for zp in db.zone_prices.find({"is_active": True, "promo_end": {"$gt": now}}, {"_id": 0}):
        product = await db.products.find_one({"id": zp["product_id"]}, {"_id": 0, "name": 1, "sku": 1})
        row = {"name": (product or {}).get("name", zp["product_id"]),
               "sku": (product or {}).get("sku", ""),
               "zone": zp["zone_code"], "end": zp["promo_end"],
               "price": zp.get("price_ht_cents"), "original": zp.get("original_price_ht_cents")}
        active.append(row)
        if zp["promo_end"] <= horizon:
            expiring.append(row)

    def _table(rows):
        if not rows:
            return "<p style='color:#777;'>Aucune.</p>"
        cells = "".join(
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee;'>{r['name']}<br>"
            f"<span style='color:#999;font-size:11px;'>{r['sku']}</span></td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{r['zone']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>"
            f"{(r['price'] or 0) / 100:.2f} €" + (f" <s style='color:#999;'>{r['original'] / 100:.2f} €</s>" if r.get("original") else "") + "</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid #eee;'>{r['end'].strftime('%d/%m/%Y')}</td></tr>"
            for r in sorted(rows, key=lambda x: x["end"]))
        return ("<table style='border-collapse:collapse;width:100%;font-size:13px;'>"
                "<tr style='background:#f5f0e6;'><th style='padding:6px 10px;text-align:left;'>Produit</th>"
                "<th style='padding:6px 10px;text-align:left;'>Zone</th>"
                "<th style='padding:6px 10px;text-align:left;'>Prix HT</th>"
                "<th style='padding:6px 10px;text-align:left;'>Fin</th></tr>" + cells + "</table>")

    html = (f"<h2>📊 Rapport promos — semaine {week_tag}</h2>"
            f"<h3>⏳ Expirent sous 7 jours ({len(expiring)})</h3>{_table(expiring)}"
            f"<h3 style='margin-top:24px;'>✅ Toutes les promos actives ({len(active)})</h3>{_table(active)}"
            "<p style='color:#777;font-size:12px;margin-top:24px;'>Rapport automatique du lundi — CommunityPlace, O'SCOP × KDMARCHÉ</p>")

    from brevo_service import send_email
    sent = 0
    async for u in db.users.find({"is_admin": True}, {"_id": 0, "email": 1}):
        if not u.get("email"):
            continue
        try:
            await send_email(to_email=u["email"], to_name=None,
                             subject=f"📊 Rapport promos hebdo — {len(expiring)} expirent sous 7 j, {len(active)} actives",
                             html_content=html, tags=["promo-weekly-report"])
            sent += 1
        except Exception as exc:
            logger.warning("Rapport promos %s : %s", u["email"], exc)
    logger.info("Rapport promos hebdo envoyé à %d admin(s)", sent)
    return sent > 0
