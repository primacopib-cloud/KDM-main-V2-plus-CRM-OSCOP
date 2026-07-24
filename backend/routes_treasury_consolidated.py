"""Trésorerie consolidée : RCR détenue + transport LOGI'SCOP + adhésions, projection 30/60/90 jours."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from attestation_nominative import compute_rcr_ledger
from convention_settings import get_convention_settings
from core_deps import get_current_user, check_admin
from db import get_database

treasury_consolidated_router = APIRouter(prefix="/api/admin/treasury", tags=["treasury"])

BUCKETS = [("0-30 j", 0, 30), ("31-60 j", 31, 60), ("61-90 j", 61, 90)]


class ThresholdBody(BaseModel):
    threshold_eur: float


async def get_alert_threshold_cents(db) -> int:
    doc = await db.treasury_settings.find_one({"key": "alert_threshold_cents"}, {"_id": 0})
    return int(doc["value"]) if doc else 0


@treasury_consolidated_router.get("/alert-threshold")
async def get_alert_threshold(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    cents = await get_alert_threshold_cents(get_database())
    return {"threshold_eur": cents / 100}


@treasury_consolidated_router.post("/alert-threshold")
async def set_alert_threshold(body: ThresholdBody, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    await get_database().treasury_settings.update_one(
        {"key": "alert_threshold_cents"},
        {"$set": {"value": round(body.threshold_eur * 100)}}, upsert=True)
    return {"ok": True, "threshold_eur": body.threshold_eur}


def _bucket_index(days: float) -> int | None:
    for i, (_, lo, hi) in enumerate(BUCKETS):
        if lo <= days <= hi:
            return i
    return None


@treasury_consolidated_router.get("/consolidated")
async def consolidated_treasury(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    data = await compute_consolidated_treasury(db)
    data["history"] = await compute_treasury_history(db)
    return data


async def compute_consolidated_treasury(db) -> dict:
    now = datetime.now(timezone.utc)
    buckets = [{"label": b[0], "transport_in_cents": 0, "memberships_in_cents": 0,
                "rcr_out_cents": 0} for b in BUCKETS]

    # 1) Transport : encours impayé (net d'avoir), échéance = émission + 30 j
    transport = {"outstanding_cents": 0, "overdue_cents": 0, "overdue_count": 0,
                 "collected_cents": 0, "unpaid_count": 0}
    async for inv in db.logiscop_transport_invoices.find({}, {"_id": 0}):
        ttc = inv.get("total_ttc_cents") or 0
        if inv.get("status") == "PAID":
            transport["collected_cents"] += ttc
            continue
        credit = await db.logiscop_transport_credits.find_one(
            {"invoice_id": inv["id"]}, {"_id": 0, "total_ttc_cents": 1})
        net = max(0, ttc - ((credit or {}).get("total_ttc_cents") or 0))
        transport["outstanding_cents"] += net
        transport["unpaid_count"] += 1
        try:
            due = datetime.fromisoformat(inv["issued_at"]) + timedelta(days=30)
        except ValueError:
            continue
        days = (due - now).total_seconds() / 86400
        if days < 0:
            transport["overdue_cents"] += net
            transport["overdue_count"] += 1
            buckets[0]["transport_in_cents"] += net
        else:
            idx = _bucket_index(days)
            if idx is not None:
                buckets[idx]["transport_in_cents"] += net

    # 2) Adhésions : revenu mensuel récurrent des membres actifs (1 renouvellement / fenêtre 30 j)
    memberships = {"mrr_cents": 0, "active_count": 0}
    async for ob in db.vendor_onboarding.find(
            {"status": "ACTIVATED", "access_suspended": {"$ne": True}}, {"_id": 0, "amount_cents": 1}):
        memberships["mrr_cents"] += ob.get("amount_cents") or 0
        memberships["active_count"] += 1
    for b in buckets:
        b["memberships_in_cents"] = memberships["mrr_cents"]

    # 3) RCR : trésorerie détenue + décaissements prévus (expiration + délai réglementaire)
    settings = await get_convention_settings(db)
    reimb_days = int(settings.get("reimbursement_days", 45))
    rcr = {"held_cents": 0, "projected_out_cents": 0}
    async for e in db.rcr_fiscal_register.find({}, {"_id": 0, "kind": 1, "amount_cents": 1}):
        sign = -1 if e["kind"] == "REMBOURSEMENT" else 1
        rcr["held_cents"] += sign * e["amount_cents"]
    async for att in db.attestations_nominatives.find({"status": {"$ne": "closed"}}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        solde = ledger.get("solde_cents") or 0
        if solde <= 0:
            continue
        try:
            exp = datetime.fromisoformat(att["date_expiration"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        days = (exp + timedelta(days=reimb_days) - now).total_seconds() / 86400
        idx = _bucket_index(max(0, days))
        if idx is not None:
            buckets[idx]["rcr_out_cents"] += solde
            rcr["projected_out_cents"] += solde

    cumulative = 0
    for b in buckets:
        b["net_cents"] = b["transport_in_cents"] + b["memberships_in_cents"] - b["rcr_out_cents"]
        cumulative += b["net_cents"]
        b["cumulative_cents"] = cumulative
    return {"as_of": now.isoformat(), "buckets": buckets, "transport": transport,
            "memberships": memberships, "rcr": rcr,
            "projected_net_90d_cents": cumulative}


async def compute_treasury_history(db, months: int = 12) -> list:
    """Évolution mensuelle réelle : encaissements transport + adhésions + mouvements RCR nets, cumulés."""
    series = {}

    def bump(month, key, cents):
        if not month:
            return
        m = series.setdefault(month, {"month": month, "transport_cents": 0,
                                      "memberships_cents": 0, "rcr_net_cents": 0})
        m[key] += cents

    async for inv in db.logiscop_transport_invoices.find({"status": "PAID"}, {"_id": 0}):
        bump((inv.get("paid_at") or inv.get("issued_at") or "")[:7], "transport_cents",
             inv.get("total_ttc_cents") or 0)
    async for ob in db.vendor_onboarding.find({"status": {"$ne": "PAYMENT_PENDING"}}, {"_id": 0}):
        bump((str(ob.get("paid_at") or ob.get("activated_at") or ob.get("created_at") or ""))[:7],
             "memberships_cents", ob.get("amount_cents") or 0)
        for r in ob.get("renewals") or []:
            bump((str(r.get("at") or ""))[:7], "memberships_cents",
                 r.get("amount_cents") or ob.get("amount_cents") or 0)
    async for e in db.rcr_fiscal_register.find({}, {"_id": 0, "kind": 1, "amount_cents": 1, "date": 1}):
        sign = -1 if e["kind"] == "REMBOURSEMENT" else 1
        bump((e.get("date") or "")[:7], "rcr_net_cents", sign * e["amount_cents"])
    out = [series[k] for k in sorted(series)][-months:]
    cumulative = 0
    for m in out:
        m["total_cents"] = m["transport_cents"] + m["memberships_cents"] + m["rcr_net_cents"]
        cumulative += m["total_cents"]
        m["cumulative_cents"] = cumulative
    return out


async def check_treasury_alert(db) -> bool:
    """Alerte email quand le net cumulé projeté à 90 j passe sous le seuil réglable (1 envoi max / jour)."""
    import logging
    import os
    logger = logging.getLogger(__name__)
    data = await compute_consolidated_treasury(db)
    net = data["projected_net_90d_cents"]
    threshold = await get_alert_threshold_cents(db)
    if net >= threshold:
        return False
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if await db.system_flags.find_one({"key": "treasury_low_alert", "date": today}):
        return False
    from brevo_service import send_email, is_brevo_configured
    if not is_brevo_configured():
        return False

    def eur(c):
        return f"{c / 100:,.2f} €".replace(",", " ").replace(".", ",")

    rows = "".join(
        f"<tr><td style='padding:4px 10px'>{b['label']}</td>"
        f"<td style='padding:4px 10px;text-align:right'>{eur(b['transport_in_cents'])}</td>"
        f"<td style='padding:4px 10px;text-align:right'>{eur(b['memberships_in_cents'])}</td>"
        f"<td style='padding:4px 10px;text-align:right'>-{eur(b['rcr_out_cents'])}</td>"
        f"<td style='padding:4px 10px;text-align:right'><b>{eur(b['cumulative_cents'])}</b></td></tr>"
        for b in data["buckets"])
    html = (
        f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#B91C1C'>ALERTE TRÉSORERIE — projection 90 jours sous le seuil</h2>"
        f"<p>Le net cumulé projeté à 90 jours est de <b style='color:#B91C1C'>{eur(net)}</b> "
        f"(seuil d'alerte : {eur(threshold)}).</p>"
        "<table style='border-collapse:collapse;font-size:13px'><tr style='background:#FBF6EE'>"
        "<th style='padding:4px 10px'>Période</th><th style='padding:4px 10px'>Transport</th>"
        "<th style='padding:4px 10px'>Adhésions</th><th style='padding:4px 10px'>Sorties RCR</th>"
        f"<th style='padding:4px 10px'>Net cumulé</th></tr>{rows}</table>"
        f"<p>Encours transport impayé : <b>{eur(data['transport']['outstanding_cents'])}</b> "
        f"(dont échu {eur(data['transport']['overdue_cents'])}) — RCR détenue : {eur(data['rcr']['held_cents'])}.</p>"
        "<p>Consultez le tableau Trésorerie consolidée (onglet Comptabilité) pour le détail.</p>"
        "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP</b></p></div>")
    report_email = os.environ.get("ADMIN_ALERT_EMAIL") or os.environ.get("WEEKLY_REPORT_EMAIL") \
        or os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
    await send_email(to_email=report_email, to_name="Administration KDMARCHÉ × O'SCOP",
                     subject=f"[ALERTE] Trésorerie projetée à 90 j sous le seuil : {eur(net)}",
                     html_content=html, tags=["treasury-low-alert"])
    from core_deps import create_notification
    try:
        await create_notification(
            "treasury_low_alert", "Alerte trésorerie basse",
            f"Le net cumulé projeté à 90 jours ({eur(net)}) est sous le seuil d'alerte ({eur(threshold)}).",
            target_roles=["oscop_super_admin", "kdm_b2b_admin"], data={"net_90d_cents": net})
    except Exception as exc:
        logger.warning("Notification alerte trésorerie échouée : %s", exc)
    await db.system_flags.insert_one({"key": "treasury_low_alert", "date": today,
                                      "net_90d_cents": net,
                                      "sent_at": datetime.now(timezone.utc).isoformat()})
    logger.info("Alerte trésorerie basse envoyée (%s)", eur(net))
    return True
