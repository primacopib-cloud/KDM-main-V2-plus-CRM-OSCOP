"""Alerte super admin : produit dépassant le seuil de retours 'Défectueux' sur le mois courant."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def run_defective_alerts(db, now=None) -> int:
    now = now or datetime.utcnow()
    from routes_lolodrive_taxonomy import get_fees_config_doc
    threshold = int((await get_fees_config_doc()).get("defective_alert_threshold") or 0)
    if threshold <= 0:
        return 0
    month = now.strftime("%Y-%m")
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    agg = {}
    async for r in db.counter_refunds.find(
            {"reason": "DEFECTIVE", "created_at": {"$gte": month_start}},
            {"_id": 0, "items": 1, "point_id": 1}):
        for it in r.get("items", []):
            e = agg.setdefault(it["sku"], {"name": it.get("name", it["sku"]), "qty": 0, "points": {}})
            e["qty"] += it.get("qty", 0)
            e["points"][r.get("point_id")] = e["points"].get(r.get("point_id"), 0) + it.get("qty", 0)
    sent = 0
    for sku, e in agg.items():
        if e["qty"] < threshold:
            continue
        if await db.defective_alerts.find_one({"sku": sku, "month": month}):
            continue
        await db.defective_alerts.insert_one({"sku": sku, "month": month, "qty": e["qty"], "sent_at": now})
        try:
            await _notify_admins(db, sku, e, threshold, month)
            sent += 1
            logger.info("Alerte produit suspect envoyée : %s (%d retours défectueux)", sku, e["qty"])
        except Exception as exc:
            logger.warning("Alerte défectueux %s : %s", sku, exc)
    return sent


async def _notify_admins(db, sku, e, threshold, month):
    prod = await db.lolodrive_products.find_one({"sku": sku}, {"_id": 0, "supplier": 1})
    supplier = (prod or {}).get("supplier")
    admins = await db.users.find(
        {"$or": [{"is_admin": True}, {"role": {"$in": ["oscop_super_admin", "SUPER_ADMIN", "ADMIN", "admin"]}}],
         "email": {"$ne": None}}, {"_id": 0, "email": 1, "contact_name": 1}).to_list(20)
    if not admins:
        return
    pts = {p["id"]: p async for p in db.lolodrive_points.find(
        {"id": {"$in": [k for k in e["points"] if k]}}, {"_id": 0, "id": 1, "name": 1, "code": 1})}
    detail = "".join(
        f"<li>{pts.get(pid, {}).get('name', 'Relais inconnu')} ({pts.get(pid, {}).get('code', '—')}) : ×{q}</li>"
        for pid, q in sorted(e["points"].items(), key=lambda kv: -kv[1]))
    from brevo_service import send_email, _wrap_html
    subject = f"⚠️ Produit suspect — {e['name']} : {e['qty']} retours défectueux ce mois-ci"
    body = f"""
      <p>Le produit <strong>{e['name']}</strong> (SKU {sku}) a atteint
      <strong style='color:#dc2626'>{e['qty']} retour(s) « Défectueux »</strong> sur {month}
      (seuil d'alerte : {threshold}).</p>
      {f"<p>Fournisseur : <strong>{supplier}</strong></p>" if supplier else ""}
      <p>Répartition par relais :</p>
      <ul style='font-size:13px'>{detail}</ul>
      <p>Vérifiez le lot, le fournisseur ou retirez temporairement le produit du catalogue
      depuis <strong>/lolodrive → Fiches produits — TVA &amp; photos</strong> (bouton Retirer).</p>
      <p style='color:#999;font-size:11px;margin-top:12px'>Alerte automatique — Réseau LOLODRIVE by O'SCOP.</p>
    """
    for a in admins:
        await send_email(to_email=a["email"], to_name=a.get("contact_name"), subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"Produit suspect : {e['name']} — {e['qty']} retours defectueux sur {month}.",
                         tags=["defective_product_alert"])
