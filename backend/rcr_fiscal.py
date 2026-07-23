"""Registre fiscal RCR continu (append-only avec extournes) + relevé annuel fiscal par fournisseur."""
import logging
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from attestation_nominative import compute_rcr_ledger
from core_deps import get_current_user, check_admin
from db import get_database

logger = logging.getLogger(__name__)
rcr_fiscal_router = APIRouter(prefix="/api/convention", tags=["convention"])

GOLD = colors.HexColor("#B8860B")
DARK = colors.HexColor("#1F2A3A")
GRID = colors.HexColor("#E5DCC8")
BG = colors.HexColor("#FBF6EE")
CANCELED_STATUSES = ["DRAFT", "CANCELED", "CANCELLED", "REFUSED", "REFUNDED"]


def _eur(cents) -> str:
    return f"{(cents or 0) / 100:,.2f} €".replace(",", " ").replace(".", ",")


async def sync_rcr_fiscal_register(db) -> dict:
    """Cron idempotent : matérialise en continu les écritures RCR (append-only, extournes si annulation)."""
    added, reversed_n = 0, 0
    now_iso = datetime.now(timezone.utc).isoformat()
    async for att in db.attestations_nominatives.find({}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        current_orders = {f["order_id"]: f for f in ledger["fractions"]}
        # Nouvelles constitutions
        for oid, f in current_orders.items():
            if f["fraction_cents"] <= 0:
                continue
            if await db.rcr_fiscal_register.find_one(
                    {"kind": "CONSTITUTION", "attestation_id": att["id"], "order_id": oid, "reversed_at": None}):
                continue
            await db.rcr_fiscal_register.insert_one({
                "id": str(uuid.uuid4()), "kind": "CONSTITUTION", "date": f["date"],
                "attestation_id": att["id"], "attestation_ref": att["ref"],
                "vendor_id": att["vendor_id"], "vendor_name": att.get("vendor_name"),
                "piece": f["order_ref"], "order_id": oid,
                "amount_cents": f["fraction_cents"],
                "debit_account": "401FOUR", "credit_account": "4671RCR",
                "label": f"Constitution fraction RCR {att['ref']} — commande {f['order_ref']}",
                "reversed_at": None, "recorded_at": now_iso})
            added += 1
        # Extournes : constitutions dont la commande a été annulée après coup
        async for entry in db.rcr_fiscal_register.find(
                {"kind": "CONSTITUTION", "attestation_id": att["id"], "reversed_at": None}, {"_id": 0}):
            if entry["order_id"] in current_orders:
                continue
            order = await db.orders.find_one({"id": entry["order_id"]}, {"_id": 0, "status": 1})
            status = (order or {}).get("status", "SUPPRIMÉE")
            await db.rcr_fiscal_register.insert_one({
                "id": str(uuid.uuid4()), "kind": "EXTOURNE", "date": now_iso[:10],
                "attestation_id": att["id"], "attestation_ref": att["ref"],
                "vendor_id": att["vendor_id"], "vendor_name": att.get("vendor_name"),
                "piece": entry["piece"], "order_id": entry["order_id"],
                "amount_cents": -entry["amount_cents"],
                "debit_account": "4671RCR", "credit_account": "401FOUR",
                "label": f"Extourne fraction RCR {att['ref']} — commande {entry['piece']} ({status})",
                "reverses_entry_id": entry["id"], "reversed_at": None, "recorded_at": now_iso})
            await db.rcr_fiscal_register.update_one({"id": entry["id"]}, {"$set": {"reversed_at": now_iso}})
            reversed_n += 1
    # Remboursements
    async for r in db.rcr_reimbursements.find({}, {"_id": 0}):
        if (r.get("amount_cents") or 0) <= 0:
            continue
        if await db.rcr_fiscal_register.find_one({"kind": "REMBOURSEMENT", "reimbursement_id": r["id"]}):
            continue
        await db.rcr_fiscal_register.insert_one({
            "id": str(uuid.uuid4()), "kind": "REMBOURSEMENT", "date": (r.get("created_at") or "")[:10],
            "attestation_id": r.get("attestation_id"), "attestation_ref": r.get("attestation_ref"),
            "vendor_id": r["vendor_id"], "vendor_name": r.get("vendor_name"),
            "piece": r["ref"], "reimbursement_id": r["id"],
            "amount_cents": r["amount_cents"],
            "debit_account": "4671RCR", "credit_account": "512OSC",
            "label": f"Remboursement RCR {r['ref']} — clôture {r.get('attestation_ref', '')}",
            "reversed_at": None, "recorded_at": now_iso})
        added += 1
    if added or reversed_n:
        logger.info("Registre fiscal RCR : %s écriture(s) ajoutée(s), %s extourne(s)", added, reversed_n)
    return {"added": added, "reversed": reversed_n}


@rcr_fiscal_router.get("/admin/rcr-fiscal-register")
async def get_rcr_fiscal_register(limit: int = 15, current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    db = get_database()
    entries = await db.rcr_fiscal_register.find({}, {"_id": 0}).sort("recorded_at", -1).to_list(500)
    totals = {"CONSTITUTION": 0, "EXTOURNE": 0, "REMBOURSEMENT": 0}
    for e in entries:
        totals[e["kind"]] = totals.get(e["kind"], 0) + e["amount_cents"]
    return {"count": len(entries), "totals": totals,
            "solde_cents": totals["CONSTITUTION"] + totals["EXTOURNE"] - totals["REMBOURSEMENT"],
            "entries": entries[:max(1, min(limit, 100))]}


@rcr_fiscal_router.post("/admin/rcr-fiscal-register/sync")
async def run_rcr_fiscal_sync(current_user: dict = Depends(get_current_user)):
    await check_admin(current_user)
    result = await sync_rcr_fiscal_register(get_database())
    return {"success": True, **result}


# ============== RELEVÉ ANNUEL FISCAL ==============

def build_annual_statement_pdf(vendor: dict, year: str, data: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=14 * mm, rightMargin=14 * mm)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=13)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GOLD, fontSize=10, spaceBefore=8)
    n = ParagraphStyle("n", parent=ss["Normal"], fontSize=8.5, leading=12)
    small = ParagraphStyle("sm", parent=ss["Normal"], fontSize=7.5, textColor=colors.grey)
    style = TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), BG),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), BG), ("FONTSIZE", (0, 0), (-1, -1), 7.6),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])
    rows = [["Mois", "Constitutions", "Extournes", "Remboursements", "Variation nette"]]
    for m in data["monthly"]:
        rows.append([m["month"], _eur(m["constitue"]), _eur(m["extourne"]), _eur(m["rembourse"]),
                     _eur(m["constitue"] + m["extourne"] - m["rembourse"])])
    t = data["totals"]
    rows.append(["TOTAL EXERCICE", _eur(t["constitue"]), _eur(t["extourne"]), _eur(t["rembourse"]),
                 _eur(t["constitue"] + t["extourne"] - t["rembourse"])])
    tab = Table(rows, colWidths=[32 * mm, 37 * mm, 37 * mm, 38 * mm, 38 * mm]); tab.setStyle(style)
    att_rows = [["Attestation", "Produit", "Statut", "Solde RCR au 31/12"]]
    labels = {"signed": "Active", "pending_countersign": "En attente", "closed": "Clôturée"}
    for s in data["soldes"]:
        att_rows.append([s["attestation_ref"], (s.get("product_name") or "")[:40],
                         labels.get(s["status"], s["status"]), _eur(s["solde_cents"])])
    att_rows.append(["TOTAL", "", "", _eur(sum(s["solde_cents"] for s in data["soldes"]))])
    tab2 = Table(att_rows, colWidths=[62 * mm, 62 * mm, 26 * mm, 32 * mm]); tab2.setStyle(style)
    doc.build([
        Paragraph(f"RELEVÉ ANNUEL FISCAL RCR — EXERCICE {year}", h1),
        Paragraph(f"Fournisseur : {vendor.get('company_name')} — SIRET {vendor.get('siret') or '—'} — "
                  f"édité le {datetime.now().strftime('%d/%m/%Y')} — FOGEDOM-SCIC / O'SCOP / KDMARCHÉ PRO", small),
        Spacer(1, 3 * mm),
        Paragraph(f"Écritures issues du registre fiscal RCR (append-only, extournes comprises) : "
                  f"<b>{data['entries_count']}</b> écriture(s) sur l'exercice.", n),
        Paragraph("1. MOUVEMENTS RCR PAR MOIS", h2), tab,
        Paragraph("2. SOLDES RCR PAR ATTESTATION (fin d'exercice)", h2), tab2,
        Spacer(1, 4 * mm),
        Paragraph("Comptes utilisés : 401FOUR (Fournisseur — retenue sur règlement), 4671RCR (RCR FOGEDOM-SCIC "
                  "individualisée), 512OSC (Banque O'SCOP — exécution monétaire). La RCR demeure une contribution "
                  "individualisée et remboursable ; le solde figure au passif du FOGEDOM-SCIC et à l'actif du "
                  "Fournisseur (créance). Document destiné aux déclarations comptables de fin d'exercice.", small),
        Paragraph("Généré automatiquement par le Dashboard KDMARCHÉ × O'SCOP — fait foi entre les Parties.", small),
    ])
    return buf.getvalue()


async def build_annual_data(db, vendor_id: str, year: str) -> dict:
    """Données du relevé annuel fiscal (mensuel + soldes par attestation)."""
    entries = await db.rcr_fiscal_register.find(
        {"vendor_id": vendor_id, "date": {"$regex": f"^{year}"}}, {"_id": 0}).to_list(2000)
    monthly = {f"{year}-{m:02d}": {"constitue": 0, "extourne": 0, "rembourse": 0} for m in range(1, 13)}
    for e in entries:
        k = e["date"][:7]
        if k not in monthly:
            continue
        if e["kind"] == "CONSTITUTION":
            monthly[k]["constitue"] += e["amount_cents"]
        elif e["kind"] == "EXTOURNE":
            monthly[k]["extourne"] += e["amount_cents"]
        else:
            monthly[k]["rembourse"] += e["amount_cents"]
    totals = {"constitue": sum(m["constitue"] for m in monthly.values()),
              "extourne": sum(m["extourne"] for m in monthly.values()),
              "rembourse": sum(m["rembourse"] for m in monthly.values())}
    soldes = []
    async for att in db.attestations_nominatives.find({"vendor_id": vendor_id}, {"_id": 0, "ai_text": 0}):
        ledger = await compute_rcr_ledger(db, att)
        solde = 0 if att.get("status") == "closed" else ledger["solde_cents"]
        soldes.append({"attestation_ref": att["ref"], "product_name": att.get("product_name"),
                       "status": att.get("status"), "solde_cents": solde})
    return {"monthly": [{"month": k, **v} for k, v in sorted(monthly.items())],
            "totals": totals, "soldes": soldes, "entries_count": len(entries)}


@rcr_fiscal_router.get("/rcr-annual/{vendor_id}/{year}/pdf")
async def annual_statement_pdf(vendor_id: str, year: str, current_user: dict = Depends(get_current_user)):
    """Relevé annuel fiscal RCR — admin ou fournisseur propriétaire."""
    if not current_user.get("is_admin") and current_user.get("vendor_id") != vendor_id:
        raise HTTPException(status_code=403, detail="Accès refusé")
    if not (year.isdigit() and len(year) == 4):
        raise HTTPException(status_code=400, detail="Année invalide")
    db = get_database()
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0})
    if not vendor:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable")
    await sync_rcr_fiscal_register(db)
    data = await build_annual_data(db, vendor_id, year)
    pdf = build_annual_statement_pdf(vendor, year, data)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=releve-annuel-rcr-{year}-{vendor_id[:8]}.pdf"})
