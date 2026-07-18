"""Contrats automatisés d'engagement de volume avec rétention de garantie (5% plafonnée à 20 000 €)."""
import io
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from auth import get_current_user_id
from admin_guard import require_admin

logger = logging.getLogger(__name__)

contracts_router = APIRouter(prefix="/api/vendor/contracts", tags=["Contrats vendeurs"])

db = None

RETENTION_RATE = 5.0
RETENTION_CAP_CENTS = 2_000_000  # 20 000 €


def set_contracts_database(database) -> None:
    global db
    db = database


async def ensure_contract(database, vendor_id: str, product: dict) -> dict:
    """Crée le contrat d'engagement de volume s'il n'existe pas (idempotent)."""
    existing = await database.volume_contracts.find_one(
        {"vendor_id": vendor_id, "product_id": product["id"]}, {"_id": 0}
    )
    if existing:
        return existing
    doc = {
        "id": str(uuid.uuid4()),
        "contract_number": f"CTR-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}",
        "vendor_id": vendor_id,
        "product_id": product["id"],
        "product_name": product.get("name"),
        "volume_commitment": product.get("min_order_quantity") or 1,
        "unit": product.get("unit") or "unité",
        "price_cap_ht": product.get("price_ht"),
        "retention_rate": RETENTION_RATE,
        "retention_cap_cents": RETENTION_CAP_CENTS,
        "retained_cents": 0,
        "released_cents": 0,
        "retention_ledger": [],
        "status": "ACTIVE",
        "created_at": datetime.utcnow(),
    }
    await database.volume_contracts.insert_one({**doc})
    logger.info("Volume contract %s created for vendor %s / product %s", doc["contract_number"], vendor_id, product["id"])
    doc.pop("_id", None)
    return doc


async def apply_invoice_retention(database, order: dict) -> None:
    """Rétention 5% sur facture, par ligne produit vendeur, plafonnée à 20 000 € par contrat."""
    if order.get("retention_processed"):
        return
    for item in order.get("items", []):
        product = await database.products.find_one({"id": item["product_id"]}, {"_id": 0})
        vendor_id = (product or {}).get("vendor_id")
        if not vendor_id:
            continue
        vendor_product = await database.vendor_products.find_one({"id": item["product_id"]}, {"_id": 0}) or product
        contract = await ensure_contract(database, vendor_id, vendor_product)
        remaining = contract["retention_cap_cents"] - contract.get("retained_cents", 0)
        if remaining <= 0:
            continue
        retention = min(int(round(item["line_total_ht_cents"] * RETENTION_RATE / 100)), remaining)
        if retention <= 0:
            continue
        await database.volume_contracts.update_one(
            {"id": contract["id"]},
            {"$inc": {"retained_cents": retention},
             "$push": {"retention_ledger": {
                 "order_id": order["id"],
                 "order_number": order.get("order_number"),
                 "line_total_ht_cents": item["line_total_ht_cents"],
                 "retention_cents": retention,
                 "at": datetime.utcnow(),
             }}}
        )
        logger.info("Retention %s cents on contract %s (order %s)", retention, contract["contract_number"], order["id"])
    await database.orders.update_one({"id": order["id"]}, {"$set": {"retention_processed": True}})


COUNTRY_TERRITORY = {"GP": "Guadeloupe", "MQ": "Martinique", "GF": "Guyane", "RE": "La Réunion", "FR": "Hexagone"}


@contracts_router.get("/admin/all")
async def admin_list_contracts(user_id: str = Depends(get_current_user_id)):
    """Vue Super Admin : tous les contrats + total des garanties retenues par territoire."""
    await require_admin(user_id)
    contracts = await db.volume_contracts.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    by_territory = {}
    for c in contracts:
        vendor = await db.vendors.find_one({"id": c["vendor_id"]}, {"_id": 0, "company_name": 1, "country": 1})
        c["vendor_name"] = (vendor or {}).get("company_name") or c["vendor_id"]
        country = (vendor or {}).get("country")
        c["territory"] = COUNTRY_TERRITORY.get(country, country or "Autre")
        net = c.get("retained_cents", 0) - c.get("released_cents", 0)
        t = by_territory.setdefault(c["territory"], {"contracts": 0, "retained_cents": 0, "released_cents": 0, "net_cents": 0})
        t["contracts"] += 1
        t["retained_cents"] += c.get("retained_cents", 0)
        t["released_cents"] += c.get("released_cents", 0)
        t["net_cents"] += net
    return {
        "contracts": contracts,
        "by_territory": by_territory,
        "total_net_cents": sum(t["net_cents"] for t in by_territory.values()),
    }


class ReleasePayload(BaseModel):
    amount_cents: int = Field(..., gt=0)
    note: str = Field(..., min_length=3, max_length=1000)


@contracts_router.post("/admin/{contract_id}/release")
async def release_retention(
    contract_id: str,
    payload: ReleasePayload,
    user_id: str = Depends(get_current_user_id),
):
    """Restitution totale ou partielle de la garantie, tracée au registre du contrat."""
    admin = await require_admin(user_id)
    contract = await db.volume_contracts.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    available = contract.get("retained_cents", 0) - contract.get("released_cents", 0)
    if payload.amount_cents > available:
        raise HTTPException(status_code=400, detail=f"Montant supérieur à la garantie disponible ({available / 100:.2f} €)")
    await db.volume_contracts.update_one(
        {"id": contract_id},
        {"$inc": {"released_cents": payload.amount_cents},
         "$push": {"retention_ledger": {
             "type": "RELEASE",
             "release_cents": payload.amount_cents,
             "note": payload.note.strip(),
             "by": admin.get("email"),
             "at": datetime.utcnow(),
         }}}
    )
    logger.info("Release %s cents on contract %s by %s", payload.amount_cents, contract["contract_number"], admin.get("email"))

    # Email Brevo au vendeur
    vendor = await db.vendors.find_one({"id": contract["vendor_id"]}, {"_id": 0, "email": 1, "company_name": 1, "contact_name": 1})
    if vendor and vendor.get("email"):
        try:
            import brevo_service
            from brevo_service import _wrap_html
            remaining = available - payload.amount_cents
            body = f"""
              <h2 style=\"color:#D9B35A;margin:0 0 12px;font-size:18px;\">Restitution de garantie — {contract['contract_number']}</h2>
              <p style=\"color:rgba(255,255,255,0.8);font-size:14px;\">
                Bonjour {vendor.get('contact_name') or vendor.get('company_name')},<br/><br/>
                Une restitution de garantie a été effectuée sur votre contrat d'engagement de volume
                relatif au produit <strong>{contract['product_name']}</strong> :
              </p>
              <div style=\"background:rgba(255,255,255,0.05);border-radius:12px;padding:16px;color:rgba(255,255,255,0.85);font-size:14px;\">
                <strong>Montant restitué :</strong> {payload.amount_cents / 100:.2f} €<br/>
                <strong>Solde de garantie restant :</strong> {remaining / 100:.2f} €<br/>
                <strong>Motif :</strong> {payload.note.strip()}
              </div>
              <p style=\"color:rgba(255,255,255,0.55);font-size:12px;margin-top:14px;\">
                Le détail complet est disponible dans votre espace vendeur, onglet Contrats.
              </p>
            """
            await brevo_service.send_email(
                to_email=vendor["email"], to_name=vendor.get("contact_name") or vendor.get("company_name"),
                subject=f"Restitution de garantie {payload.amount_cents / 100:.2f} € — contrat {contract['contract_number']}",
                html_content=_wrap_html("Restitution de garantie", body),
                tags=["retention-release"],
            )
            logger.info("Release notification sent to %s", vendor["email"])
        except Exception as e:
            logger.error("Release notification failed: %s", e)

    return {"ok": True, "released_cents": payload.amount_cents, "remaining_cents": available - payload.amount_cents}


@contracts_router.get("/admin/report-pdf")
async def guarantees_report_pdf(user_id: str = Depends(get_current_user_id)):
    """État PDF des garanties par territoire (assemblées / commissaire aux comptes)."""
    await require_admin(user_id)
    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    contracts = await db.volume_contracts.find({}, {"_id": 0}).sort("created_at", 1).to_list(2000)
    grouped = {}
    for c in contracts:
        vendor = await db.vendors.find_one({"id": c["vendor_id"]}, {"_id": 0, "company_name": 1, "country": 1})
        terr = COUNTRY_TERRITORY.get((vendor or {}).get("country"), (vendor or {}).get("country") or "Autre")
        c["vendor_name"] = (vendor or {}).get("company_name") or c["vendor_id"]
        grouped.setdefault(terr, []).append(c)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=styles["Heading2"], textColor=colors.HexColor("#4C2A6E"))
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8.5, textColor=colors.HexColor("#5C4B36"))
    date_str = datetime.utcnow().strftime("%d/%m/%Y")
    elements = [
        Paragraph("ÉTAT DES GARANTIES DE RÉTENTION — CONTRATS D'ENGAGEMENT DE VOLUME", styles["Title"]),
        Paragraph(f"Coopérative Communityplace / KDMARCHÉ × O'SCOP — édité le {date_str} — "
                  f"document destiné aux assemblées et au commissaire aux comptes", small),
        Spacer(1, 6 * mm),
    ]
    tbl_style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4C2A6E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9B35A")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FBF6EC")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#F3E9D2")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ])
    grand = {"retained": 0, "released": 0, "net": 0}
    for terr in sorted(grouped):
        rows = [["Contrat", "Fournisseur", "Produit", "Signé le", "Retenu (€)", "Restitué (€)", "Solde net (€)"]]
        sub = {"retained": 0, "released": 0}
        for c in grouped[terr]:
            ret, rel = c.get("retained_cents", 0), c.get("released_cents", 0)
            sub["retained"] += ret
            sub["released"] += rel
            rows.append([
                c["contract_number"], c["vendor_name"], (c.get("product_name") or "")[:40],
                c["created_at"].strftime("%d/%m/%Y") if c.get("created_at") else "",
                f"{ret / 100:,.2f}", f"{rel / 100:,.2f}", f"{(ret - rel) / 100:,.2f}",
            ])
        rows.append(["", "", "", f"Sous-total {terr}", f"{sub['retained'] / 100:,.2f}",
                     f"{sub['released'] / 100:,.2f}", f"{(sub['retained'] - sub['released']) / 100:,.2f}"])
        grand["retained"] += sub["retained"]
        grand["released"] += sub["released"]
        table = Table(rows, repeatRows=1)
        table.setStyle(tbl_style)
        elements += [Paragraph(f"Territoire : {terr} — {len(grouped[terr])} contrat(s)", h), table, Spacer(1, 6 * mm)]
    grand["net"] = grand["retained"] - grand["released"]
    elements.append(Paragraph(
        f"<b>TOTAL GÉNÉRAL — Retenu : {grand['retained'] / 100:,.2f} € · "
        f"Restitué : {grand['released'] / 100:,.2f} € · Garanties nettes détenues : {grand['net'] / 100:,.2f} €</b>",
        ParagraphStyle("total", parent=styles["Normal"], fontSize=11, textColor=colors.HexColor("#4C2A6E"))))
    doc.build(elements)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": f'attachment; filename="etat-garanties-{datetime.utcnow().strftime("%Y%m%d")}.pdf"'})


@contracts_router.get("/{vendor_id}")
async def list_vendor_contracts(vendor_id: str):
    """Liste les contrats du vendeur ; auto-crée ceux des produits approuvés (idempotent)."""
    approved = await db.vendor_products.find(
        {"vendor_id": vendor_id, "status": {"$in": ["APPROVED", "approved"]}}, {"_id": 0}
    ).to_list(500)
    for p in approved:
        await ensure_contract(db, vendor_id, p)
    contracts = await db.volume_contracts.find({"vendor_id": vendor_id}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return {"contracts": contracts, "count": len(contracts)}


@contracts_router.get("/{vendor_id}/{contract_id}/pdf")
async def contract_pdf(vendor_id: str, contract_id: str):
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    contract = await db.volume_contracts.find_one({"id": contract_id, "vendor_id": vendor_id}, {"_id": 0})
    if not contract:
        raise HTTPException(status_code=404, detail="Contrat introuvable")
    vendor = await db.vendors.find_one({"id": vendor_id}, {"_id": 0}) or {}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=9.5, leading=14)
    h = ParagraphStyle("h", parent=styles["Heading3"], textColor=colors.HexColor("#4C2A6E"))
    cap_eur = contract["retention_cap_cents"] / 100
    retained_eur = contract.get("retained_cents", 0) / 100
    elements = [
        Paragraph("CONTRAT CADRE D'APPROVISIONNEMENT — ENGAGEMENT DE VOLUME", styles["Title"]),
        Paragraph(f"N° {contract['contract_number']} — édité le {datetime.utcnow().strftime('%d/%m/%Y')}", styles["Normal"]),
        Spacer(1, 6 * mm),
        Paragraph("Entre les soussignés", h),
        Paragraph(f"<b>KDMARCHÉ × O'SCOP</b> (la Centrale coopérative), d'une part, et<br/>"
                  f"<b>{vendor.get('company_name') or vendor_id}</b> (le Fournisseur), "
                  f"{('SIRET ' + vendor.get('siret')) if vendor.get('siret') else ''}, d'autre part.", body),
        Spacer(1, 4 * mm),
        Paragraph("Article 1 — Objet et engagement de volume", h),
        Paragraph(f"Le Fournisseur s'engage à maintenir disponible pour la Centrale le produit référencé "
                  f"<b>{contract['product_name']}</b>, à hauteur d'un volume minimum de "
                  f"<b>{contract['volume_commitment']} {contract['unit']}</b> par commande, avec la capacité logistique associée "
                  f"et un délai de mise à disposition conforme aux conditions du catalogue B2B.", body),
        Spacer(1, 3 * mm),
        Paragraph("Article 2 — Prix", h),
        Paragraph(f"Le prix plafond convenu est de <b>{contract['price_cap_ht']} € HT / {contract['unit']}</b>"
                  if contract.get("price_cap_ht") else
                  "Le prix suit la formule de prix négociée au catalogue coopératif du territoire.", body),
        Spacer(1, 3 * mm),
        Paragraph("Article 3 — Rétention de garantie sur factures", h),
        Paragraph(f"La Centrale retient <b>{contract['retention_rate']} %</b> du montant HT de chaque facture relative au produit, "
                  f"jusqu'à constitution d'un plafond de garantie de <b>{cap_eur:,.0f} €</b>. "
                  f"Les sommes retenues sont <b>restituables</b> au Fournisseur sous réserve de la bonne exécution "
                  f"de ses engagements de volume, de capacité logistique et de délais.", body),
        Spacer(1, 3 * mm),
        Paragraph("Article 4 — État de la garantie", h),
    ]
    table = Table([
        ["Taux de rétention", f"{contract['retention_rate']} %"],
        ["Plafond de garantie", f"{cap_eur:,.2f} €"],
        ["Montant retenu à date", f"{retained_eur:,.2f} €"],
        ["Montant restitué", f"{contract.get('released_cents', 0) / 100:,.2f} €"],
        ["Statut du contrat", contract["status"]],
    ], colWidths=[70 * mm, 60 * mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9B35A")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FBF6EC")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements += [table, Spacer(1, 5 * mm),
                 Paragraph("Contrat généré automatiquement à la validation du référencement du produit — "
                           "fait foi entre les parties dans le cadre du règlement intérieur coopératif.", body)]
    doc.build(elements)
    buf.seek(0)
    from fastapi.responses import StreamingResponse as SR
    return SR(buf, media_type="application/pdf",
              headers={"Content-Disposition": f'attachment; filename="{contract["contract_number"]}.pdf"'})
