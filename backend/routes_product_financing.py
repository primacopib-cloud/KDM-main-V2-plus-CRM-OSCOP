"""Financement produits investisseurs : inscription superadmin (marge O'SCOP), paiement Stripe, mention « Vendu et facturé par O'SCOP »."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from lolodrive_helpers import require_admin
from auth import get_current_user_id

logger = logging.getLogger(__name__)
financing_router = APIRouter(prefix="/api", tags=["Financement produits"])
db = None


def set_product_financing_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _investor(user_id: str = Depends(get_current_user_id)):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur inconnu")
    role = (user.get("role") or "").upper()
    if not (user.get("is_investor") or user.get("is_admin") or role in {"SUPER_ADMIN", "ADMIN"}):
        raise HTTPException(status_code=403, detail="Réservé aux investisseurs")
    return user


class FinancingProductCreate(BaseModel):
    product_id: str | None = None
    name: str | None = None
    kind: str = "PRODUIT"
    base_price_eur: float = Field(gt=0, le=10_000_000)
    margin_percent: float = Field(ge=0, le=500)
    description: str | None = None
    # Option logistique LOGI'SCOP (coût + marge, soumise au financement)
    logistics_cost_eur: float | None = Field(default=None, ge=0, le=10_000_000)
    logistics_margin_percent: float | None = Field(default=None, ge=0, le=500)
    # Modalités de remboursement de l'investisseur
    repayment_amount_eur: float | None = Field(default=None, ge=0, le=10_000_000)
    repayment_duration_months: int | None = Field(default=None, ge=1, le=600)
    repayment_date: str | None = None


class FinancingProductUpdate(BaseModel):
    base_price_eur: float | None = Field(default=None, gt=0, le=10_000_000)
    margin_percent: float | None = Field(default=None, ge=0, le=500)
    logistics_cost_eur: float | None = Field(default=None, ge=0, le=10_000_000)
    logistics_margin_percent: float | None = Field(default=None, ge=0, le=500)
    repayment_amount_eur: float | None = Field(default=None, ge=0, le=10_000_000)
    repayment_duration_months: int | None = Field(default=None, ge=1, le=600)
    repayment_date: str | None = None


def _total(base: float, margin: float, logistics_cost: float = 0, logistics_margin: float = 0) -> float:
    """Total financé = produit (base + marge O'SCOP) + logistique (coût + marge LOGI'SCOP)."""
    return round(base * (1 + margin / 100) + (logistics_cost or 0) * (1 + (logistics_margin or 0) / 100), 2)


def _logi_total(cost, margin):
    return round((cost or 0) * (1 + (margin or 0) / 100), 2)


def build_repayment_schedule(fp: dict) -> list[dict]:
    """Échéancier mensuel : mensualités égales se terminant à repayment_date (dernière ajustée aux arrondis)."""
    amount = float(fp.get("repayment_amount_eur") or 0)
    months = int(fp.get("repayment_duration_months") or 0)
    end = fp.get("repayment_date")
    if not amount or not months or not end:
        return []
    from dateutil.relativedelta import relativedelta
    from datetime import date
    try:
        end_d = date.fromisoformat(str(end)[:10])
    except ValueError:
        return []
    monthly = round(amount / months, 2)
    done = set(fp.get("repayments_done") or [])
    schedule = []
    for i in range(months):
        due = end_d - relativedelta(months=months - 1 - i)
        amt = round(amount - monthly * (months - 1), 2) if i == months - 1 else monthly
        schedule.append({"due_date": due.isoformat(), "amount_eur": amt, "paid": due.isoformat() in done})
    return schedule


@financing_router.get("/admin/financing-products/catalog")
async def financing_catalog_products(_: dict = Depends(require_admin)):
    """Produits du catalogue sélectionnables pour le financement."""
    items = await db.products.find(
        {"status": "ACTIVE"}, {"_id": 0, "id": 1, "name": 1, "sku": 1}).sort("name", 1).to_list(200)
    return {"products": items}


@financing_router.post("/admin/financing-products")
async def create_financing_product(body: FinancingProductCreate, admin: dict = Depends(require_admin)):
    """Le superadmin inscrit un produit OU une prestation logistique au financement avec sa marge bénéficiaire."""
    kind = (body.kind or "PRODUIT").upper()
    if kind not in ("PRODUIT", "LOGISTIQUE"):
        raise HTTPException(status_code=400, detail="kind: PRODUIT ou LOGISTIQUE")
    name, sku = body.name, None
    if body.product_id and kind == "PRODUIT":
        prod = await db.products.find_one({"id": body.product_id}, {"_id": 0, "name": 1, "sku": 1})
        if not prod:
            raise HTTPException(status_code=404, detail="Produit catalogue introuvable")
        name, sku = prod["name"], prod.get("sku")
    if not name or len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Nom du produit requis")
    prefix = "LOG" if kind == "LOGISTIQUE" else "FIN"
    doc = {
        "id": str(uuid.uuid4()),
        "reference": f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:5].upper()}",
        "product_id": body.product_id if kind == "PRODUIT" else None,
        "name": name.strip(), "sku": sku, "kind": kind,
        "description": body.description,
        "base_price_eur": round(body.base_price_eur, 2),
        "margin_percent": round(body.margin_percent, 2),
        "logistics_cost_eur": round(body.logistics_cost_eur, 2) if body.logistics_cost_eur else None,
        "logistics_margin_percent": round(body.logistics_margin_percent, 2) if body.logistics_margin_percent is not None else None,
        "logistics_total_eur": _logi_total(body.logistics_cost_eur, body.logistics_margin_percent) if body.logistics_cost_eur else None,
        "repayment_amount_eur": round(body.repayment_amount_eur, 2) if body.repayment_amount_eur is not None else None,
        "repayment_duration_months": body.repayment_duration_months,
        "repayment_date": body.repayment_date,
        "total_price_eur": _total(body.base_price_eur, body.margin_percent, body.logistics_cost_eur, body.logistics_margin_percent),
        "sold_invoiced_by": "O'SCOP",
        "status": "OPEN", "created_by": admin.get("email"), "created_at": _now(),
    }
    await db.financing_products.insert_one(dict(doc))
    doc.pop("_id", None)
    # Investisseurs ayant déjà financé ce produit → notification de renouvellement dédiée
    renewal_payers = set()
    match_name = name.strip().lower()
    async for old in db.financing_products.find(
            {"status": "PAID", "id": {"$ne": doc["id"]}}, {"_id": 0, "paid_by": 1, "name": 1, "product_id": 1}):
        same = (body.product_id and old.get("product_id") == body.product_id) or \
               (old.get("name") or "").strip().lower() == match_name
        if same and old.get("paid_by"):
            renewal_payers.add(old["paid_by"].lower())
    # Alerte email à tous les investisseurs (nouveau produit au financement)
    try:
        from brevo_service import send_email, _wrap_html
        base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
        investors = await db.users.find(
            {"is_investor": True, "email": {"$exists": True}},
            {"_id": 0, "email": 1, "contact_name": 1}).to_list(500)
        kind_label = "logistique" if kind == "LOGISTIQUE" else "produit"
        for inv in investors:
            try:
                if (inv["email"] or "").lower() in renewal_payers:
                    await send_email(
                        to_email=inv["email"], to_name=inv.get("contact_name"),
                        subject=f"🔄 Le produit que vous aviez financé est de retour — {doc['name']} ({doc['reference']})",
                        html_content=_wrap_html("Renouvellement de financement", (
                            f"<p style='font-size:14px;'>Bonjour {inv.get('contact_name') or ''},</p>"
                            f"<p style='font-size:14px;'>Bonne nouvelle : le produit <b>{doc['name']}</b>, que vous aviez "
                            "déjà financé, vient d'être <b>réinscrit au financement</b> par la Centrale O'SCOP :</p>"
                            f"<p style='font-size:14px;'><b>{doc['reference']}</b> — Prix de base HT : <b>{doc['base_price_eur']:,.2f} €</b> · "
                            f"Marge O'SCOP : <b>{doc['margin_percent']:,.2f} %</b> · Total : <b>{doc['total_price_eur']:,.2f} €</b></p>"
                            f"<p style='text-align:center;'><a href='{base}/espace-investisseur' "
                            "style='display:inline-block;background:#8CC63E;color:#1F2A12;font-weight:bold;"
                            "padding:12px 26px;border-radius:12px;text-decoration:none;'>Financer à nouveau ce produit</a></p>").replace(",", " ")),
                        tags=["financing-renewal"])
                    continue
                await send_email(
                    to_email=inv["email"], to_name=inv.get("contact_name"),
                    subject=f"💰 Nouveau financement {kind_label} — {doc['name']} ({doc['reference']})",
                    html_content=_wrap_html("Nouvelle opportunité de financement", (
                        f"<p style='font-size:14px;'>Bonjour {inv.get('contact_name') or ''},</p>"
                        f"<p style='font-size:14px;'>La Centrale O'SCOP vient d'inscrire un financement {kind_label} :</p>"
                        f"<p style='font-size:14px;'><b>{doc['reference']} — {doc['name']}</b><br/>"
                        f"Prix de base HT : <b>{doc['base_price_eur']:,.2f} €</b> · Marge O'SCOP : <b>{doc['margin_percent']:,.2f} %</b><br/>"
                        f"Total à régler : <b>{doc['total_price_eur']:,.2f} €</b></p>"
                        f"<p style='text-align:center;'><a href='{base}/espace-investisseur' "
                        "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                        "padding:12px 26px;border-radius:12px;text-decoration:none;'>Voir dans mon espace investisseur</a></p>"
                        "<p style='font-size:12px;color:#888;'>Une fois payé, le produit est vendu et facturé par O'SCOP.</p>").replace(",", " ")),
                    tags=["financing-alert"])
            except Exception as e2:
                logger.warning("Alerte financement %s : %s", inv.get("email"), e2)
        doc["investors_notified"] = len(investors)
        doc["renewal_notified"] = len(renewal_payers)
    except Exception as exc:
        logger.warning("Alerte nouveau financement : %s", exc)
    return doc


@financing_router.get("/investor/financing-products/my")
async def my_financed_products(user: dict = Depends(_investor)):
    """Historique des produits financés par l'investisseur connecté (factures re-téléchargeables)."""
    me = (user.get("email") or "").lower()
    items = await db.financing_products.find(
        {"status": "PAID", "paid_by": me},
        {"_id": 0, "id": 1, "reference": 1, "name": 1, "base_price_eur": 1,
         "margin_percent": 1, "total_price_eur": 1, "paid_at": 1,
         "logistics_cost_eur": 1, "logistics_margin_percent": 1, "logistics_total_eur": 1,
         "repayment_amount_eur": 1, "repayment_duration_months": 1, "repayment_date": 1,
         "sold_invoiced_by": 1, "repayments_done": 1, "repayment_status": 1},
    ).sort("paid_at", -1).to_list(100)
    for i in items:
        i["repayment_schedule"] = build_repayment_schedule(i)
        i.pop("repayments_done", None)
    return {"products": items, "total_eur": sum(float(i.get("total_price_eur") or 0) for i in items)}


class RepaymentToggle(BaseModel):
    due_date: str


@financing_router.get("/investor/financing-products/{fp_id}/repayment-certificate.pdf")
async def repayment_certificate(fp_id: str, user: dict = Depends(_investor)):
    """Attestation PDF de remboursement intégral (réservée à l'investisseur payeur, financement REPAID)."""
    me = (user.get("email") or "").lower()
    fp = await db.financing_products.find_one({"id": fp_id, "paid_by": me}, {"_id": 0})
    if not fp:
        raise HTTPException(status_code=404, detail="Financement introuvable")
    if fp.get("repayment_status") != "REPAID":
        raise HTTPException(status_code=409, detail="Le remboursement intégral n'est pas encore constaté")
    import io as _io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as _canvas
    buf = _io.BytesIO()
    c = _canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFillColorRGB(0.16, 0.05, 0.28)
    c.rect(0, h - 32 * mm, w, 32 * mm, stroke=0, fill=1)
    c.setFillColorRGB(0.85, 0.7, 0.35)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(16 * mm, h - 17 * mm, "O'SCOP — Centrale coopérative")
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 10)
    c.drawString(16 * mm, h - 25 * mm, "Attestation de remboursement intégral — financement investisseur")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(w / 2, h - 55 * mm, "ATTESTATION DE REMBOURSEMENT INTÉGRAL")
    c.setFont("Helvetica", 11)
    y = h - 72 * mm
    schedule = build_repayment_schedule(fp)
    lines = [
        "La SCIC SAS OBJECTIF SCOP OUTREMER atteste que le financement suivant a été",
        "intégralement remboursé à l'investisseur :",
        "",
        f"Investisseur : {me}",
        f"Référence : {fp['reference']} — {fp['name']}",
        f"Montant financé : {float(fp.get('total_price_eur') or 0):,.2f} €",
        f"Remboursement : {float(fp.get('repayment_amount_eur') or 0):,.2f} € sur {fp.get('repayment_duration_months')} mois",
        f"Dernière échéance honorée le : {str(fp.get('repayment_updated_at') or '')[:10]}",
        "",
        "Détail des échéances honorées :",
    ] + [f"   • {s['due_date']} — {s['amount_eur']:,.2f} € ✓" for s in schedule] + [
        "",
        f"Fait le {datetime.now(timezone.utc).strftime('%d/%m/%Y')} — vendu et facturé par O'SCOP.",
    ]
    for line in lines:
        c.drawString(20 * mm, y, line)
        y -= 7 * mm
    c.setFillColorRGB(0.16, 0.05, 0.28)
    c.rect(0, 0, w, 16 * mm, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 8)
    c.drawCentredString(w / 2, 9 * mm, "SCIC SAS OBJECTIF SCOP OUTREMER — contact@objectifscopoutremer.com · centrale.objectifscopoutremer.com")
    c.showPage()
    c.save()
    from fastapi.responses import Response
    return Response(content=buf.getvalue(), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=attestation-remboursement-{fp['reference']}.pdf"})


@financing_router.post("/admin/financing-products/{fp_id}/repayments/toggle")
async def toggle_repayment(fp_id: str, body: RepaymentToggle, admin: dict = Depends(require_admin)):
    """Marque/démarque une échéance « Remboursé » ; statut global REPAID quand tout est honoré (investisseur notifié)."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    schedule = build_repayment_schedule(fp)
    if body.due_date not in [s["due_date"] for s in schedule]:
        raise HTTPException(status_code=400, detail="Échéance inconnue de l'échéancier")
    done = set(fp.get("repayments_done") or [])
    if body.due_date in done:
        done.discard(body.due_date)
    else:
        done.add(body.due_date)
    all_done = done >= {s["due_date"] for s in schedule}
    was_repaid = fp.get("repayment_status") == "REPAID"
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "repayments_done": sorted(done),
        "repayment_status": "REPAID" if all_done else ("IN_PROGRESS" if done else None),
        "repayment_updated_by": admin.get("email"), "repayment_updated_at": _now()}})
    if all_done and not was_repaid and fp.get("paid_by"):
        try:
            from brevo_service import send_email, _wrap_html
            await send_email(
                to_email=fp["paid_by"], to_name=None,
                subject=f"✅ Remboursement intégral — {fp['reference']} · {fp['name']}",
                html_content=_wrap_html("Financement intégralement remboursé", (
                    f"<p style='font-size:14px;'>Bonjour,</p>"
                    f"<p style='font-size:14px;'>Toutes les échéances de votre financement <b>{fp['reference']} — "
                    f"{fp['name']}</b> ({fp.get('repayment_amount_eur', 0):,.2f} € sur "
                    f"{fp.get('repayment_duration_months')} mois) ont été honorées par O'SCOP. "
                    f"Merci de votre confiance !</p>")),
                tags=["financing-repaid"])
        except Exception as exc:
            logger.warning("Email remboursement intégral %s : %s", fp_id, exc)
    out = await db.financing_products.find_one({"id": fp_id}, {"_id": 0})
    out["repayment_schedule"] = build_repayment_schedule(out)
    return out


@financing_router.get("/investor/financing-products/{fp_id}/invoice.pdf")
async def download_financing_invoice(fp_id: str, user: dict = Depends(_investor)):
    """Re-téléchargement de la facture acquittée (propriétaire du financement ou admin)."""
    fp = await db.financing_products.find_one({"id": fp_id, "status": "PAID"}, {"_id": 0})
    if not fp:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    me = (user.get("email") or "").lower()
    is_admin = user.get("is_admin") or (user.get("role") or "").upper() in {"SUPER_ADMIN", "ADMIN"}
    if (fp.get("paid_by") or "").lower() != me and not is_admin:
        raise HTTPException(status_code=403, detail="Facture réservée à l'acheteur")
    from fastapi.responses import Response
    from communityplace_invoice import build_financing_invoice_pdf
    pdf = build_financing_invoice_pdf(fp)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=facture-{fp['reference']}.pdf"})


TRACKING_STEPS = ["CONFIRMEE", "PREPARATION", "EXPEDITION", "TRANSIT", "LIVREE"]
TRACKING_LABELS = {"CONFIRMEE": "Commande confirmée", "PREPARATION": "Préparation",
                   "EXPEDITION": "Expédiée", "TRANSIT": "En transit", "LIVREE": "Livrée"}


class TrackingUpdate(BaseModel):
    step: str | None = None
    eta_delivery: str | None = None


@financing_router.put("/admin/financing-products/{fp_id}/tracking")
async def update_financing_tracking(fp_id: str, body: TrackingUpdate, admin: dict = Depends(require_admin)):
    """Étape logistique et/ou date de livraison estimée d'un financement payé (suivi investisseur)."""
    step = (body.step or "").upper() or None
    if step is not None and step not in TRACKING_STEPS:
        raise HTTPException(status_code=400, detail=f"Étape invalide. Choix : {', '.join(TRACKING_STEPS)}")
    eta = None
    if body.eta_delivery:
        try:
            eta = datetime.strptime(body.eta_delivery.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Date de livraison estimée au format AAAA-MM-JJ") from None
    if not step and not eta:
        raise HTTPException(status_code=400, detail="Étape ou date de livraison estimée requise")
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Financement introuvable")
    if fp.get("status") != "PAID":
        raise HTTPException(status_code=409, detail="Le suivi n'est disponible qu'après paiement")
    updates = {"tracking_updated_at": _now(), "tracking_updated_by": admin.get("email")}
    if step:
        updates["tracking_status"] = step
    if eta:
        updates["eta_delivery"] = eta
    op = {"$set": updates}
    if step:
        op["$push"] = {"tracking_history": {"step": step, "label": TRACKING_LABELS[step], "at": _now()}}
    await db.financing_products.update_one({"id": fp_id}, op)
    if fp.get("paid_by"):
        try:
            from brevo_service import send_email, _wrap_html
            base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
            cur_step = step or fp.get("tracking_status") or "CONFIRMEE"
            done = TRACKING_STEPS.index(cur_step) + 1
            bar = " → ".join(("<b style='color:#4c8a2f;'>" + TRACKING_LABELS[s] + "</b>") if i < done else TRACKING_LABELS[s]
                             for i, s in enumerate(TRACKING_STEPS))
            eta_line = (f"<p style='font-size:14px;'>📅 Livraison estimée : <b>{eta[8:10]}/{eta[5:7]}/{eta[:4]}</b></p>" if eta else "")
            subject_step = TRACKING_LABELS[cur_step]
            await send_email(
                to_email=fp["paid_by"], to_name=None,
                subject=f"🚚 Suivi de votre financement {fp['reference']} — {subject_step}" + (" · date de livraison annoncée" if eta else ""),
                html_content=_wrap_html("Suivi logistique", (
                    f"<p style='font-size:14px;'>Votre financement <b>{fp['reference']} — {fp['name']}</b> "
                    f"passe à l'étape : <b style='font-size:16px;'>{subject_step}</b>"
                    f"{' 🎉 Livraison effectuée !' if cur_step == 'LIVREE' else ''}</p>"
                    + eta_line
                    + f"<p style='font-size:12px;color:#666;'>{bar}</p>"
                    f"<p style='text-align:center;'><a href='{base}/espace-investisseur' "
                    "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                    "padding:12px 26px;border-radius:12px;text-decoration:none;'>Suivre dans mon espace</a></p>")),
                tags=["financing-tracking"])
        except Exception as exc:
            logger.warning("Email suivi financement : %s", exc)
    return await db.financing_products.find_one({"id": fp_id}, {"_id": 0, "stripe_session_id": 0})


@financing_router.post("/admin/financing-products/{fp_id}/delivery-proof")
async def upload_delivery_proof(fp_id: str, file: UploadFile = File(...), admin: dict = Depends(require_admin)):
    """Preuve de livraison (photo ou bon signé PDF) jointe à un financement payé."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Financement introuvable")
    if fp.get("status") != "PAID":
        raise HTTPException(status_code=409, detail="Preuve de livraison possible uniquement après paiement")
    allowed = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "application/pdf": "pdf"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Format accepté : PNG, JPG, WEBP ou PDF")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Fichier trop lourd (max 5 Mo)")
    from upload_storage import save_upload
    url = await save_upload(f"financing/proof-{uuid.uuid4().hex[:10]}.{allowed[file.content_type]}", content, file.content_type)
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "delivery_proof": url, "delivery_proof_at": _now(), "delivery_proof_by": admin.get("email")}})
    return {"ok": True, "url": url}


@financing_router.get("/admin/financing-products/stats")
async def financing_products_stats(_: dict = Depends(require_admin)):
    """Statistiques financements : total financé, marge cumulée O'SCOP, top investisseurs."""
    paid = await db.financing_products.find({"status": "PAID"}, {"_id": 0}).to_list(1000)
    all_items = await db.financing_products.find({}, {"_id": 0, "status": 1}).to_list(1000)
    total_paid = round(sum(float(i.get("total_price_eur") or 0) for i in paid), 2)
    margin_cumul = round(sum(float(i.get("total_price_eur") or 0) - float(i.get("base_price_eur") or 0) for i in paid), 2)
    by_investor = {}
    for i in paid:
        email = (i.get("paid_by") or "").lower() or "inconnu"
        e = by_investor.setdefault(email, {"email": email, "products_count": 0, "total_eur": 0.0})
        e["products_count"] += 1
        e["total_eur"] = round(e["total_eur"] + float(i.get("total_price_eur") or 0), 2)
    top = sorted(by_investor.values(), key=lambda x: -x["total_eur"])[:5]
    monthly_map = {}
    for i in paid:
        m = str(i.get("paid_at") or "")[:7]
        if m:
            monthly_map[m] = round(monthly_map.get(m, 0) + float(i.get("total_price_eur") or 0), 2)
    monthly = [{"month": m, "total_eur": v} for m, v in sorted(monthly_map.items())][-12:]
    # Trésorerie : remboursements à venir (échéances non honorées) agrégés par mois
    upcoming_map = {}
    today = datetime.now(timezone.utc).date().isoformat()
    for i in paid:
        for step in build_repayment_schedule(i):
            if not step["paid"] and step["due_date"] >= today[:10]:
                m = step["due_date"][:7]
                upcoming_map[m] = round(upcoming_map.get(m, 0) + step["amount_eur"], 2)
    upcoming = [{"month": m, "total_eur": v} for m, v in sorted(upcoming_map.items())][:12]
    return {
        "total_financed_eur": total_paid,
        "margin_cumul_eur": margin_cumul,
        "paid_count": len(paid),
        "open_count": sum(1 for i in all_items if i.get("status") == "OPEN"),
        "pending_count": sum(1 for i in all_items if i.get("status") == "PENDING_PAYMENT"),
        "top_investors": top,
        "monthly": monthly,
        "upcoming_repayments": upcoming,
        "upcoming_repayments_total_eur": round(sum(upcoming_map.values()), 2),
    }


@financing_router.get("/admin/financing-products")
async def list_financing_products_admin(_: dict = Depends(require_admin)):
    items = await db.financing_products.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    for i in items:
        i["repayment_schedule"] = build_repayment_schedule(i)
    pending = [i for i in items if i.get("status") == "PENDING_PAYMENT" and i.get("stripe_session_id")][:10]
    if pending:
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        for i in pending:
            try:
                s = stripe.checkout.Session.retrieve(i["stripe_session_id"])
                if s.payment_status == "paid":
                    await _mark_paid(i["id"], i.get("pending_by"))
                    i["status"] = "PAID"
            except Exception as exc:
                logger.warning("Check paiement financement %s : %s", i["id"], exc)
    return {"products": items}


@financing_router.put("/admin/financing-products/{fp_id}")
async def update_financing_product(fp_id: str, body: FinancingProductUpdate, admin: dict = Depends(require_admin)):
    """Ajuste prix / marge bénéficiaire / logistique — avant paiement ; modalités de remboursement à tout moment."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    updates = {}
    if fp.get("status") == "PAID":
        if body.base_price_eur is not None or body.margin_percent is not None \
                or body.logistics_cost_eur is not None or body.logistics_margin_percent is not None:
            raise HTTPException(status_code=409, detail="Déjà payé — seules les modalités de remboursement restent modifiables")
    else:
        base = body.base_price_eur if body.base_price_eur is not None else fp["base_price_eur"]
        margin = body.margin_percent if body.margin_percent is not None else fp["margin_percent"]
        logi_c = body.logistics_cost_eur if body.logistics_cost_eur is not None else fp.get("logistics_cost_eur")
        logi_m = body.logistics_margin_percent if body.logistics_margin_percent is not None else fp.get("logistics_margin_percent")
        updates = {
            "base_price_eur": round(base, 2), "margin_percent": round(margin, 2),
            "logistics_cost_eur": round(logi_c, 2) if logi_c else None,
            "logistics_margin_percent": round(logi_m, 2) if logi_m is not None else None,
            "logistics_total_eur": _logi_total(logi_c, logi_m) if logi_c else None,
            "total_price_eur": _total(base, margin, logi_c, logi_m),
        }
    # Modalités de remboursement : enregistrables/modifiables même après paiement
    for f in ("repayment_amount_eur", "repayment_duration_months", "repayment_date"):
        v = getattr(body, f)
        if v is not None:
            updates[f] = v
    if not updates:
        raise HTTPException(status_code=400, detail="Aucune modification fournie")
    updates["updated_by"] = admin.get("email")
    updates["updated_at"] = _now()
    await db.financing_products.update_one({"id": fp_id}, {"$set": updates})
    return await db.financing_products.find_one({"id": fp_id}, {"_id": 0})


@financing_router.delete("/admin/financing-products/{fp_id}")
async def delete_financing_product(fp_id: str, _: dict = Depends(require_admin)):
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if fp.get("status") == "PAID":
        raise HTTPException(status_code=409, detail="Déjà payé — suppression impossible")
    await db.financing_products.delete_one({"id": fp_id})
    return {"ok": True}


@financing_router.get("/investor/financing-products")
async def list_financing_products_investor(user: dict = Depends(_investor)):
    items = await db.financing_products.find(
        {}, {"_id": 0, "created_by": 0, "stripe_session_id": 0}).sort("created_at", -1).to_list(200)
    me = (user.get("email") or "").lower()
    for i in items:
        i["is_mine"] = (i.get("paid_by") or i.get("pending_by") or "").lower() == me
        if i["is_mine"] and i.get("status") == "PAID" and not i.get("tracking_token"):
            i["tracking_token"] = uuid.uuid4().hex
            await db.financing_products.update_one({"id": i["id"]}, {"$set": {"tracking_token": i["tracking_token"]}})
        if i.get("status") != "PAID":
            i.pop("paid_by", None)
            i.pop("tracking_token", None)
        if not i["is_mine"]:
            i.pop("tracking_token", None)
        i.pop("pending_by", None)
    return {"products": items}


@financing_router.post("/investor/financing-products/{fp_id}/pay")
async def pay_financing_product(fp_id: str, user: dict = Depends(_investor)):
    """L'investisseur paie le produit inscrit au financement (Stripe)."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    if fp.get("status") == "PAID":
        raise HTTPException(status_code=409, detail="Produit déjà payé — vendu et facturé par O'SCOP")
    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")
    base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
    session = stripe.checkout.Session.create(
        mode="payment",
        customer_email=user.get("email"),
        line_items=[{"price_data": {"currency": "eur", "unit_amount": int(round(fp["total_price_eur"] * 100)),
                     "product_data": {"name": f"Financement {'logistique' if fp.get('kind') == 'LOGISTIQUE' else 'produit'} — {fp['reference']} {fp['name']}"}},
                     "quantity": 1}],
        metadata={"financing_product_id": fp_id, "investor_email": user.get("email") or "", "kind": "PRODUCT_FINANCING"},
        success_url=f"{base}/espace-investisseur?finprod_session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}/espace-investisseur?finprod_cancelled=1",
    )
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "status": "PENDING_PAYMENT", "stripe_session_id": session.id,
        "pending_by": (user.get("email") or "").lower(), "pending_at": _now()}})
    return {"checkout_url": session.url, "session_id": session.id, "total_price_eur": fp["total_price_eur"]}


async def _mark_paid(fp_id: str, investor_email: str | None):
    """Marque payé (idempotent) + facture acquittée O'SCOP par email."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp or fp.get("status") == "PAID":
        return
    email = (investor_email or fp.get("pending_by") or "").lower()
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "status": "PAID", "paid_at": _now(), "paid_by": email,
        "tracking_status": "CONFIRMEE", "tracking_token": uuid.uuid4().hex,
        "tracking_history": [{"step": "CONFIRMEE", "label": "Commande confirmée", "at": _now()}]}})
    if not email:
        return
    try:
        from communityplace_invoice import build_financing_invoice_pdf
        from brevo_service import send_email, _wrap_html
        import base64
        fp = await db.financing_products.find_one({"id": fp_id}, {"_id": 0})
        pdf = build_financing_invoice_pdf(fp)
        await send_email(
            to_email=email, to_name=None,
            subject=f"🧾 Facture acquittée O'SCOP — financement {fp['reference']} ({fp['name']})",
            html_content=_wrap_html("Facture acquittée", (
                "<p style='font-size:14px;'>Bonjour,</p>"
                f"<p>Votre paiement du financement <b>{fp['reference']} — {fp['name']}</b> "
                f"({fp['total_price_eur']:.2f} €) est confirmé. Ce produit est désormais "
                "<b>vendu et facturé par O'SCOP</b>.</p>"
                "<p>Vous trouverez ci-joint votre <b>facture acquittée</b>. Merci de votre confiance 🤝</p>")),
            attachments=[{"content": base64.b64encode(pdf).decode(), "name": f"facture-{fp['reference']}.pdf"}],
            tags=["financing-invoice"])
    except Exception as e:
        logger.warning("Facture financement non envoyée : %s", e)


@financing_router.post("/investor/financing-products/{fp_id}/confirm-receipt")
async def confirm_receipt(fp_id: str, user: dict = Depends(_investor)):
    """L'investisseur confirme lui-même la réception → clôture du suivi."""
    fp = await db.financing_products.find_one({"id": fp_id})
    if not fp:
        raise HTTPException(status_code=404, detail="Financement introuvable")
    if (fp.get("paid_by") or "").lower() != (user.get("email") or "").lower():
        raise HTTPException(status_code=403, detail="Réservé à l'investisseur payeur")
    if fp.get("status") != "PAID":
        raise HTTPException(status_code=409, detail="Financement non payé")
    if fp.get("tracking_status") != "LIVREE":
        raise HTTPException(status_code=409, detail="La livraison n'est pas encore marquée « Livrée » par la Centrale")
    if fp.get("receipt_confirmed_at"):
        return {"ok": True, "receipt_confirmed_at": fp["receipt_confirmed_at"], "already": True}
    now = _now()
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "receipt_confirmed_at": now, "receipt_confirmed_by": (user.get("email") or "").lower()}})
    try:
        from brevo_service import send_email, _wrap_html
        team = os.environ.get("QUOTE_NOTIFY_EMAIL", "contact@objectifscopoutremer.com")
        await send_email(
            to_email=team, to_name=None,
            subject=f"✅ Réception confirmée par l'investisseur — {fp['reference']} ({fp['name']})",
            html_content=_wrap_html("Réception confirmée", (
                f"<p style='font-size:14px;'>L'investisseur <b>{user.get('email')}</b> a confirmé la réception du financement "
                f"<b>{fp['reference']} — {fp['name']}</b> ({fp['total_price_eur']:.2f} €) le {now[:10]}. "
                "Le suivi est clôturé.</p>")),
            tags=["financing-receipt"])
    except Exception as exc:
        logger.warning("Email confirmation réception : %s", exc)
    return {"ok": True, "receipt_confirmed_at": now, "already": False}


@financing_router.get("/public/financing-products/track/{token}")
async def public_tracking(token: str):
    """Suivi logistique en lecture seule, partageable sans connexion (aucune donnée personnelle)."""
    fp = await db.financing_products.find_one(
        {"tracking_token": token},
        {"_id": 0, "reference": 1, "name": 1, "kind": 1, "status": 1, "tracking_status": 1,
         "tracking_history": 1, "eta_delivery": 1, "receipt_confirmed_at": 1})
    if not fp:
        raise HTTPException(status_code=404, detail="Lien de suivi invalide")
    return fp


@financing_router.get("/investor/financing-products/checkout-status/{session_id}")
async def financing_checkout_status(session_id: str, user: dict = Depends(_investor)):
    fp = await db.financing_products.find_one({"stripe_session_id": session_id}, {"_id": 0})
    if not fp:
        raise HTTPException(status_code=404, detail="Session inconnue")
    if fp.get("status") != "PAID":
        import stripe
        stripe.api_key = os.environ.get("STRIPE_API_KEY")
        try:
            s = stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid":
                await _mark_paid(fp["id"], (s.get("metadata") or {}).get("investor_email"))
                fp = await db.financing_products.find_one({"stripe_session_id": session_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("Statut checkout financement : %s", exc)
    return {"status": fp.get("status"), "reference": fp.get("reference"), "name": fp.get("name"),
            "total_price_eur": fp.get("total_price_eur")}


@financing_router.post("/public/financing-products/webhook")
async def financing_webhook(payload: dict):
    """Webhook Stripe : checkout.session.completed → produit payé + facture acquittée."""
    if payload.get("type") != "checkout.session.completed":
        return {"received": True}
    obj = (payload.get("data") or {}).get("object") or {}
    fp_id = (obj.get("metadata") or {}).get("financing_product_id")
    if fp_id and obj.get("payment_status") == "paid":
        await _mark_paid(fp_id, (obj.get("metadata") or {}).get("investor_email"))
    return {"received": True}
