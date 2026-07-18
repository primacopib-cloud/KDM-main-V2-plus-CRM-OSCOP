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
    return {"ok": True, "released_cents": payload.amount_cents, "remaining_cents": available - payload.amount_cents}


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
