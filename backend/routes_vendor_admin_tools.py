"""Outils admin adhésions : entonnoir de conversion & export CSV comptable."""
import csv
import io
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from lolodrive_helpers import require_admin

vendor_admin_tools_router = APIRouter(prefix="/api/vendor-onboarding", tags=["vendor-admin-tools"])

db = None


def set_vendor_admin_tools_database(database):
    global db
    db = database


@vendor_admin_tools_router.get("/admin/funnel")
async def admin_funnel(days: int = 0, admin: dict = Depends(require_admin)):
    """Entonnoir de conversion : adhésions initiées → payées → signées → activées (période optionnelle)."""
    match = {}
    if days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        match = {"created_at": {"$gte": cutoff}}
    counts = {}
    async for d in db.vendor_onboarding.aggregate([{"$match": match}, {"$group": {"_id": "$status", "n": {"$sum": 1}}}]):
        counts[d["_id"]] = d["n"]
    started = sum(counts.values())
    paid = sum(v for k, v in counts.items() if k in ("PAID", "INFO_COMPLETED", "SIGNED", "ACTIVATED"))
    signed = counts.get("SIGNED", 0) + counts.get("ACTIVATED", 0)
    activated = counts.get("ACTIVATED", 0)
    return {"started": started, "paid": paid, "signed": signed, "activated": activated, "by_status": counts, "days": days}


@vendor_admin_tools_router.get("/admin/export.csv")
async def admin_export_csv(admin: dict = Depends(require_admin)):
    """Export comptable des adhésions : statuts, montants, TVA et historique des relances."""
    labels = {"activation": "Activation", "dunning": "Relance impayé", "warning": "Avertissement J+7",
              "suspended": "Suspension", "reactivated": "Réactivation", "sign_reminder": "Rappel signature",
              "resume": "Relance abandon", "resume2": "Rappel final abandon"}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["entreprise", "contact", "email", "telephone", "pays", "profil", "formule", "statut",
                "abonnement", "suspendu", "HT (EUR)", "TVA (EUR)", "TTC (EUR)", "taux TVA",
                "cree le", "paye le", "active le", "code convention", "relances"])
    async for ob in db.vendor_onboarding.find({}, {"_id": 0, "activation_token": 0, "signed_pdf_path": 0}).sort("created_at", -1):
        ttc = ob.get("amount_cents") or 0
        vatc = ob.get("vat_cents") or 0
        ht = ob.get("amount_ht_cents") or (ttc - vatc)
        rems = " | ".join(f"{labels.get(r['type'], r['type'])} {str(r.get('at'))[:10]}" for r in ob.get("reminders") or [])
        w.writerow([ob.get("company"), ob.get("contact_name"), ob.get("email"), ob.get("phone"),
                    ob.get("country") or "", ob.get("member_type"), ob.get("plan_name"), ob.get("status"),
                    ob.get("subscription_status") or "", "oui" if ob.get("access_suspended") else "",
                    f"{ht / 100:.2f}".replace(".", ","), f"{vatc / 100:.2f}".replace(".", ","),
                    f"{ttc / 100:.2f}".replace(".", ","), f"{ob.get('vat_rate') or 0}%",
                    str(ob.get("created_at"))[:10], str(ob.get("paid_at") or "")[:10],
                    str(ob.get("activated_at") or "")[:10],
                    (ob.get("signature") or {}).get("verification_code", ""), rems])
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="adhesions.csv"'})
