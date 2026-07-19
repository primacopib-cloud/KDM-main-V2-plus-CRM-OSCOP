"""Comptabilité analytique — journal de toutes les opérations avec ventilation HT / TVA / TTC."""
import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

accounting_router = APIRouter(prefix="/api/admin/accounting", tags=["accounting"])

db = None

KIND_LABELS = {
    "PASS": "PASS Vie Chère", "RECHARGE": "Recharge crédits", "ORDER": "Commande",
    "adhesion": "Adhésion (1er mois)", "renouvellement": "Renouvellement adhésion",
    "remboursement": "Remboursement", "CREDIT_PACK": "Pack crédits vendeur",
}


def set_accounting_database(database):
    global db
    db = database


def _entry(date, op_type, label, ht, vat, ttc, country="", email="", ref=""):
    return {"date": date or "", "type": op_type, "label": label,
            "ht_cents": int(ht or 0), "vat_cents": int(vat or 0), "ttc_cents": int(ttc or 0),
            "country": country or "", "email": email or "", "ref": ref or ""}


async def _collect_entries(date_from: str, date_to: str) -> list:
    entries = []
    # 1) Adhésions vendeur/acheteur (paiement initial + renouvellements, avec TVA si connue)
    async for ob in db.vendor_onboarding.find(
            {"status": {"$ne": "PAYMENT_PENDING"}}, {"_id": 0, "activation_token": 0, "signed_pdf_path": 0}):
        ttc = ob.get("amount_cents") or 0
        vat = ob.get("vat_cents") or 0
        ht = ob.get("amount_ht_cents") or (ttc - vat)
        paid_at = ob.get("paid_at") or ob.get("created_at") or ""
        entries.append(_entry(paid_at, "adhesion", f"Adhésion {ob.get('plan_name')} — {ob.get('company')}",
                              ht, vat, ttc, ob.get("country"), ob.get("email"), ob.get("id", "")[:8]))
        for r in ob.get("renewals") or []:
            r_ttc = r.get("amount_cents") or ttc
            r_vat = round(r_ttc - r_ttc / (1 + (ob.get("vat_rate") or 0) / 100)) if ob.get("vat_rate") else 0
            entries.append(_entry(r.get("at"), "renouvellement",
                                  f"Renouvellement {ob.get('plan_name')} — {ob.get('company')}",
                                  r_ttc - r_vat, r_vat, r_ttc, ob.get("country"), ob.get("email"),
                                  (r.get("invoice_id") or "")[:18]))
    # 2) Transactions Stripe (PASS, recharges, commandes, packs crédits) + remboursements
    async for tx in db.payment_transactions.find({"payment_status": "paid"}, {"_id": 0}):
        kind = tx.get("kind") or tx.get("type") or "ORDER"
        amount = tx.get("amount_cents") or 0
        date = str(tx.get("paid_at") or tx.get("created_at") or "")
        entries.append(_entry(date, kind, f"{KIND_LABELS.get(kind, kind)}",
                              amount, 0, amount, tx.get("country"), tx.get("user_email") or tx.get("email"),
                              (tx.get("session_id") or "")[:18]))
        if tx.get("refund_status"):
            r_amt = tx.get("refund_amount_cents") or amount
            entries.append(_entry(str(tx.get("refunded_at") or date), "remboursement",
                                  f"Remboursement {KIND_LABELS.get(kind, kind)}",
                                  -r_amt, 0, -r_amt, tx.get("country"), tx.get("user_email") or tx.get("email"),
                                  (tx.get("session_id") or "")[:18]))
    # 3) Packs CPC (services numériques O'SCOP — TVA réelle)
    async for p in db.cpc_purchases.find({"status": {"$in": ["SETTLED", "REVERSED"]}}, {"_id": 0}):
        date = str(p.get("settled_at") or p.get("created_at") or "")
        entries.append(_entry(date, "CPC_PACK", f"Pack CPC {p.get('pack_label')} ({p.get('credits')} CPC)",
                              p.get("price_ht_cents") or 0, p.get("vat_cents") or 0, p.get("ttc_cents") or 0,
                              p.get("country"), p.get("email"), (p.get("invoice_number") or p.get("id", ""))[:18]))
        if p.get("status") == "REVERSED":
            entries.append(_entry(str(p.get("reversed_at") or date), "remboursement",
                                  f"Remboursement pack CPC {p.get('pack_label')}",
                                  -(p.get("price_ht_cents") or 0), -(p.get("vat_cents") or 0),
                                  -(p.get("ttc_cents") or 0), p.get("country"), p.get("email"), (p.get("id", ""))[:18]))
    # Filtre période + tri
    def keep(e):
        d = e["date"][:10]
        return (not date_from or d >= date_from) and (not date_to or d <= date_to)
    entries = [e for e in entries if keep(e)]
    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def _totals(entries: list) -> dict:
    by_type, by_month = {}, {}
    tot = {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": len(entries)}
    for e in entries:
        tot["ht_cents"] += e["ht_cents"]; tot["vat_cents"] += e["vat_cents"]; tot["ttc_cents"] += e["ttc_cents"]
        t = by_type.setdefault(e["type"], {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": 0})
        t["ht_cents"] += e["ht_cents"]; t["vat_cents"] += e["vat_cents"]; t["ttc_cents"] += e["ttc_cents"]; t["count"] += 1
        month = e["date"][:7]
        m = by_month.setdefault(month, {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": 0})
        m["ht_cents"] += e["ht_cents"]; m["vat_cents"] += e["vat_cents"]; m["ttc_cents"] += e["ttc_cents"]; m["count"] += 1
    return {"totals": tot, "by_type": by_type, "by_month": dict(sorted(by_month.items(), reverse=True))}


@accounting_router.get("/journal")
async def accounting_journal(date_from: Optional[str] = None, date_to: Optional[str] = None,
                             op_type: Optional[str] = None, limit: int = 200,
                             admin: dict = Depends(require_admin)):
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    entries = await _collect_entries(date_from, date_to or "")
    agg = _totals(entries)
    if op_type and op_type != "all":
        entries = [e for e in entries if e["type"] == op_type]
    return {"entries": entries[:limit], "date_from": date_from, "date_to": date_to,
            "kind_labels": KIND_LABELS, **agg}


SOURCE_LABELS = {
    "adhesion": "Cotisations d'adhésion", "renouvellement": "Cotisations — renouvellements",
    "ORDER": "Ventes (commandes)", "PASS": "Contributions PASS Vie Chère",
    "RECHARGE": "Recharges de crédits", "CREDIT_PACK": "Packs crédits vendeurs",
    "CPC_PACK": "Packs CPC (consultations)",
    "remboursement": "Remboursements", "RCR": "Retenue contributive remboursable (RCR)",
}


@accounting_router.get("/fiscal-register")
async def fiscal_register(date_from: Optional[str] = None, date_to: Optional[str] = None,
                          admin: dict = Depends(require_admin)):
    """Registre fiscal : récapitulatif par source (taxes, cotisations, ventes, remboursements, RCR…)."""
    entries = await _collect_entries(date_from or "", date_to or "")
    by_source, vat_by_country = {}, {}
    for e in entries:
        s = by_source.setdefault(e["type"], {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": 0})
        s["ht_cents"] += e["ht_cents"]; s["vat_cents"] += e["vat_cents"]; s["ttc_cents"] += e["ttc_cents"]; s["count"] += 1
        if e["vat_cents"]:
            c = vat_by_country.setdefault(e["country"] or "??", {"vat_cents": 0, "count": 0})
            c["vat_cents"] += e["vat_cents"]; c["count"] += 1
    if "RCR" not in by_source:
        by_source["RCR"] = {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": 0}
    snapshots = await db.fiscal_register.find({}, {"_id": 0}).sort("month", -1).limit(12).to_list(12)
    return {"sources": by_source, "labels": SOURCE_LABELS, "vat_by_country": vat_by_country,
            "snapshots": snapshots, **_totals(entries)}


async def snapshot_fiscal_register(database):
    """Cron mensuel : fige le récapitulatif fiscal du mois précédent dans le registre."""
    global db
    if db is None:
        db = database
    now = datetime.now(timezone.utc)
    prev_last = now.replace(day=1) - timedelta(days=1)
    month = prev_last.strftime("%Y-%m")
    if await db.fiscal_register.find_one({"month": month}):
        return
    entries = [e for e in await _collect_entries(f"{month}-01", f"{month}-31") if e["date"][:7] == month]
    by_source = {}
    for e in entries:
        s = by_source.setdefault(e["type"], {"ht_cents": 0, "vat_cents": 0, "ttc_cents": 0, "count": 0})
        s["ht_cents"] += e["ht_cents"]; s["vat_cents"] += e["vat_cents"]; s["ttc_cents"] += e["ttc_cents"]; s["count"] += 1
    agg = _totals(entries)
    await db.fiscal_register.insert_one({
        "month": month, "sources": by_source, "totals": agg["totals"],
        "created_at": now.isoformat()})
    logger.info("Registre fiscal : snapshot %s enregistré (%d opérations)", month, agg["totals"]["count"])


@accounting_router.get("/fiscal-register/export.csv")
async def fiscal_register_export(date_from: Optional[str] = None, date_to: Optional[str] = None,
                                 admin: dict = Depends(require_admin)):
    entries = await _collect_entries(date_from or "", date_to or "")
    by_source = {}
    for e in entries:
        s = by_source.setdefault(e["type"], {"ht": 0, "vat": 0, "ttc": 0, "count": 0})
        s["ht"] += e["ht_cents"]; s["vat"] += e["vat_cents"]; s["ttc"] += e["ttc_cents"]; s["count"] += 1
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["source", "operations", "HT (EUR)", "TVA (EUR)", "TTC (EUR)"])
    for k, v in by_source.items():
        w.writerow([SOURCE_LABELS.get(k, k), v["count"],
                    f"{v['ht'] / 100:.2f}".replace(".", ","), f"{v['vat'] / 100:.2f}".replace(".", ","),
                    f"{v['ttc'] / 100:.2f}".replace(".", ",")])
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="registre-fiscal.csv"'})


@accounting_router.get("/export.csv")
async def accounting_export(date_from: Optional[str] = None, date_to: Optional[str] = None,
                            admin: dict = Depends(require_admin)):
    entries = await _collect_entries(date_from or "", date_to or "")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["date", "type", "libelle", "pays", "email", "reference", "HT (EUR)", "TVA (EUR)", "TTC (EUR)"])
    for e in entries:
        w.writerow([e["date"][:19], KIND_LABELS.get(e["type"], e["type"]), e["label"], e["country"],
                    e["email"], e["ref"],
                    f"{e['ht_cents'] / 100:.2f}".replace(".", ","),
                    f"{e['vat_cents'] / 100:.2f}".replace(".", ","),
                    f"{e['ttc_cents'] / 100:.2f}".replace(".", ",")])
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="journal-comptable.csv"'})
