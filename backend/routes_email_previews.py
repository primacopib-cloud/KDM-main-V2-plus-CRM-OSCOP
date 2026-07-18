"""Galerie d'aperçu des modèles d'emails de la plateforme (Super Admin)."""
import base64
import csv
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from admin_plans_common import get_current_admin_from_request
from brevo_service import _wrap_html

email_previews_router = APIRouter(prefix="/api/admin/email-previews")

_GOLD_BOX = 'style="background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;"'
_LABEL = 'style="margin:0 0 6px;color:#D9B35A;font-size:12px;text-transform:uppercase;letter-spacing:1px;"'

_TEMPLATES = [
    {"id": "payment-success", "category": "Paiements", "name": "Paiement réussi + Facture",
     "subject": "✓ Paiement réussi — Votre facture KDMARCHÉ (100 crédits)",
     "body": f"<p>Bonjour Sophie,</p><p>Merci pour votre achat ! <strong>100 crédits</strong> ont été ajoutés à votre solde CREDI&rsquo;SCOP pour <strong>50.00 €</strong>.</p><p>Vous trouverez votre facture en pièce jointe. Elle reste re-téléchargeable à tout moment depuis votre espace CREDI&rsquo;SCOP.</p>"},
    {"id": "payment-failed", "category": "Paiements", "name": "Échec / expiration du paiement",
     "subject": "✗ Échec du paiement — Achat de crédits KDMARCHÉ",
     "body": "<p>Bonjour Sophie,</p><p>Votre paiement par carte de <strong>50.00 €</strong> (100 crédits) n'a pas abouti : <strong>paiement expiré</strong>.</p><p>Aucun montant n'a été débité et aucun crédit n'a été ajouté.</p><p>Vous pouvez relancer l'achat à tout moment depuis votre espace CREDI&rsquo;SCOP.</p>"},
    {"id": "low-credits", "category": "Paiements", "name": "Solde de crédits faible",
     "subject": "⚠️ Solde de crédits faible (12 restants) — KDMARCHÉ",
     "body": f"<p>Bonjour,</p><p>Votre solde CREDI&rsquo;SCOP est passé sous le seuil d'alerte.</p><div {_GOLD_BOX}><p {_LABEL}>Solde restant</p><p style=\"margin:0;font-size:24px;font-weight:700;color:#D9B35A;\">12 crédits</p></div><p>Rechargez dès maintenant pour ne pas interrompre vos services.</p>"},
    {"id": "cart-price-alert", "category": "Panier & Commandes", "name": "Alerte prix panier",
     "subject": "⚠ Prix mis à jour dans votre panier KDMARCHÉ",
     "body": f"<p>Bonjour,</p><p>Le prix d'un article de votre panier a changé :</p><div {_GOLD_BOX}><p style=\"margin:0;\"><strong>Riz long grain 5kg</strong></p><p style=\"margin:6px 0 0;\">12,80 € → <strong style=\"color:#D9B35A;\">13,20 €</strong> HT</p></div><p>Validez votre commande pour figer les prix actuels.</p>"},
    {"id": "logiscop-mission", "category": "Panier & Commandes", "name": "Mission transporteur LOGI'SCOP",
     "subject": "[LOGI'SCOP] Mission de transport — commande CMD-2026-0042",
     "body": f"<p>Bonjour,</p><p>Une mission de transport vous a été assignée.</p><div {_GOLD_BOX}><p {_LABEL}>Commande</p><p style=\"margin:0;font-family:monospace;\">CMD-2026-0042</p><p style=\"margin:12px 0 0;\">Enlèvement : <strong>Fort-de-France</strong></p><p style=\"margin:6px 0 0;\">Livraison : <strong>Le Lamentin</strong></p></div><p style=\"text-align:center;\"><a href=\"#\" style=\"display:inline-block;background:#D4AF37;color:#1F0A33;font-weight:700;padding:12px 22px;border-radius:999px;text-decoration:none;\">Confirmer l'enlèvement</a></p>"},
    {"id": "vendor-invoice", "category": "Vendeurs", "name": "Facture crédits vendeur",
     "subject": "Votre facture KDMARCHÉ — Pack Pro (250 crédits)",
     "body": "<p>Bonjour,</p><p>Votre achat de crédits vendeur est confirmé. La facture PDF est jointe à cet email.</p><p>Crédités : <strong>250 crédits</strong> (+25 bonus)</p>"},
    {"id": "guarantee-restitution", "category": "Vendeurs", "name": "Restitution de garantie",
     "subject": "Restitution de garantie 125.00 € — contrat CTR-2026-011",
     "body": f"<p>Bonjour,</p><p>Une restitution de garantie a été effectuée sur votre contrat d'engagement de volume.</p><div {_GOLD_BOX}><p {_LABEL}>Montant restitué</p><p style=\"margin:0;font-size:24px;font-weight:700;color:#57D19A;\">125,00 €</p><p style=\"margin:10px 0 0;\">Contrat : <strong>CTR-2026-011</strong></p></div>"},
    {"id": "monthly-report", "category": "Vendeurs", "name": "Rapport mensuel vendeur",
     "subject": "📊 Votre rapport mensuel KDMARCHÉ — 2026-06",
     "body": "<p>Bonjour,</p><p>Votre rapport d'activité du mois est disponible : ventes, vues produits, crédits consommés et garanties retenues.</p><p>Le PDF détaillé est joint à cet email.</p>"},
    {"id": "video-spot", "category": "Vendeurs", "name": "Spot vidéo prêt",
     "subject": "🎬 Votre spot vidéo « Rhum blanc agricole AOC 1L » est prêt — KDMARCHÉ",
     "body": "<p>Bonjour,</p><p>Votre spot vidéo généré par IA est prêt ! Retrouvez-le dans votre espace vendeur, onglet <strong>Mes spots vidéo</strong>, et partagez-le sur vos réseaux.</p>"},
    {"id": "support-ticket", "category": "Support", "name": "Accusé de réception ticket",
     "subject": "Votre demande TCK-2026-0087 — Support Communityplace",
     "body": f"<p>Bonjour,</p><p>Nous avons bien reçu votre demande. Notre équipe vous répondra sous 24h ouvrées.</p><div {_GOLD_BOX}><p {_LABEL}>Ticket</p><p style=\"margin:0;font-family:monospace;\">TCK-2026-0087</p><p style=\"margin:10px 0 0;\">Catégorie : <strong>Facturation</strong></p></div>"},
    {"id": "support-reply", "category": "Support", "name": "Réponse du support",
     "subject": "Re: [TCK-2026-0087] Question sur ma facture",
     "body": "<p>Bonjour,</p><p>Le support a répondu à votre demande. Connectez-vous à votre espace pour consulter la réponse et poursuivre la conversation.</p>"},
    {"id": "welcome-access", "category": "Comptes", "name": "Accès à la plateforme",
     "subject": "Vos accès à la plateforme KDMARCHÉ × O'SCOP",
     "body": f"<p>Bonjour et bienvenue !</p><p>Votre compte a été créé. Voici vos identifiants de connexion :</p><div {_GOLD_BOX}><p {_LABEL}>Identifiant</p><p style=\"margin:0;font-family:monospace;\">prenom.nom@entreprise.fr</p></div><p>Nous vous conseillons de modifier votre mot de passe dès la première connexion.</p>"},
    {"id": "partnership", "category": "Comptes", "name": "Demande de partenariat",
     "subject": "[Partenariat PRT-2026-004] Coopérative Antilles Bois — Fournisseur",
     "body": "<p>Bonjour,</p><p>Une nouvelle demande de partenariat vient d'être déposée et attend votre traitement dans l'espace admin (onglet Conventions).</p>"},
    {"id": "guarantee-monthly", "category": "Administration", "name": "État mensuel des garanties (admins)",
     "subject": "[Communityplace] État des garanties — clôture 2026-06",
     "body": "<p>Bonjour,</p><p>Veuillez trouver ci-joint le rapport PDF mensuel des garanties vendeur retenues (rétention 5%) pour l'ensemble des contrats actifs.</p>"},
]


_TAG_MAP = {
    "payment-success": ["wallet-credit-receipt"],
    "payment-failed": ["wallet-payment-failed"],
    "low-credits": ["low-credits"],
    "cart-price-alert": ["cart-price-alert"],
    "logiscop-mission": ["carrier-assignment"],
    "vendor-invoice": ["credit-invoice"],
    "guarantee-restitution": ["retention-release"],
    "monthly-report": ["monthly-report"],
    "video-spot": ["video-ready"],
    "support-ticket": ["support-confirmation", "support-contact"],
    "support-reply": ["support-reply", "support-reopen"],
    "welcome-access": ["team-invite"],
    "partnership": ["partnership-request"],
    "guarantee-monthly": ["guarantees-monthly-report"],
}

db = None


def set_email_previews_database(database):
    global db
    db = database


async def _email_stats() -> dict:
    tag_counts, tag_last = {}, {}
    async for row in db.email_logs.aggregate([
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}, "last": {"$max": "$sent_at"}}},
    ]):
        tag_counts[row["_id"]] = row["count"]
        tag_last[row["_id"]] = row["last"]
    stats = {}
    for tpl_id, tags in _TAG_MAP.items():
        stats[tpl_id] = {
            "count": sum(tag_counts.get(t, 0) for t in tags),
            "last_sent": max((tag_last.get(t) for t in tags if tag_last.get(t)), default=None),
        }
    return stats


@email_previews_router.get("")
async def list_email_previews(request: Request):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    stats = await _email_stats()
    total_sent = await db.email_logs.count_documents({})
    return {
        "templates": [
            {
                "id": t["id"],
                "category": t["category"],
                "name": t["name"],
                "subject": t["subject"],
                "html": _wrap_html(t["subject"], t["body"]),
                "stats": stats.get(t["id"], {"count": 0, "last_sent": None}),
            }
            for t in _TEMPLATES
        ],
        "admin_email": admin.get("email"),
        "total_sent": total_sent,
    }


@email_previews_router.get("/{template_id}/logs")
async def get_template_logs(request: Request, template_id: str, limit: int = 50, q: str = ""):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    tags = _TAG_MAP.get(template_id)
    if not tags:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    limit = max(1, min(limit, 200))
    query = {"tags": {"$in": tags}}
    if q.strip():
        query["to_email"] = {"$regex": re.escape(q.strip()), "$options": "i"}
    logs = await db.email_logs.find(
        query, {"_id": 0, "id": 1, "to_email": 1, "subject": 1, "sent_at": 1}
    ).sort("sent_at", -1).to_list(limit)
    return {"logs": logs}


@email_previews_router.post("/logs/{log_id}/resend")
async def resend_email_log(request: Request, log_id: str):
    """Renvoie l'email d'origine à son destinataire (contenu conservé, sans pièces jointes)."""
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    log = await db.email_logs.find_one({"id": log_id}, {"_id": 0})
    if not log:
        raise HTTPException(status_code=404, detail="Envoi introuvable dans le journal")
    from brevo_service import is_brevo_configured, send_email
    if not is_brevo_configured():
        raise HTTPException(status_code=503, detail="Brevo non configuré")
    html = log.get("html")
    if not html:
        tpl = next(
            (t for t in _TEMPLATES for tag in log.get("tags", []) if tag in _TAG_MAP.get(t["id"], [])),
            None,
        )
        if not tpl:
            raise HTTPException(status_code=409, detail="Contenu d'origine non conservé pour cet envoi")
        html = _wrap_html(tpl["subject"], tpl["body"])
    result = await send_email(
        to_email=log["to_email"], to_name=None,
        subject=log["subject"],
        html_content=html,
        tags=log.get("tags") or ["resend"],
    )
    if not result:
        raise HTTPException(status_code=502, detail="Échec de l'envoi Brevo")
    return {"sent": True, "to": log["to_email"], "message_id": result.get("messageId")}


def _template_name_for_tags(tags: list) -> str:
    for tpl_id, tpl_tags in _TAG_MAP.items():
        if any(t in tpl_tags for t in tags):
            return next((t["name"] for t in _TEMPLATES if t["id"] == tpl_id), tpl_id)
    return tags[0] if tags else ""


async def _build_logs_csv(month: str | None = None) -> tuple[str, int]:
    """CSV complet du journal (ou d'un mois YYYY-MM)."""
    query = {"sent_at": {"$regex": f"^{re.escape(month)}"}} if month else {}
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["Date d'envoi", "Destinataire", "Objet", "Modèle", "Tags"])
    rows = 0
    async for log in db.email_logs.find(query, {"_id": 0, "html": 0}).sort("sent_at", -1):
        writer.writerow([
            log.get("sent_at", ""), log.get("to_email", ""), log.get("subject", ""),
            _template_name_for_tags(log.get("tags", [])), ",".join(log.get("tags", [])),
        ])
        rows += 1
    return buf.getvalue(), rows


async def archive_email_logs_to_ged(database, month: str, force: bool = False) -> dict:
    """Archive le journal du mois dans la GED ESS (idempotent par mois)."""
    global db
    if db is None:
        db = database
    existing = await db.email_archive_runs.find_one({"month": month, "status": "SUCCESS"})
    if existing and not force:
        return {"status": "ALREADY_ARCHIVED", "month": month}
    csv_content, rows = await _build_logs_csv(month)
    if rows == 0:
        return {"status": "EMPTY", "month": month, "rows": 0}
    from ged_external_client import GedExternalClient, build_ged_business_metadata
    client = GedExternalClient()
    if not client.config.enabled:
        return {"status": "GED_DISABLED", "month": month, "rows": rows}
    payload = {
        "title": f"Journal des emails transactionnels — {month}",
        "source": "kdmarche",
        "entity_id": f"EMAIL-JOURNAL-{month}",
        "scope_id": "KDMARCHE",
        "family": "CONFORMITE",
        "confidentiality": "INTERNE",
        "tags": "emails,journal,conformite,archive-mensuelle",
        "description": f"Archive mensuelle automatisée du journal des emails ({rows} envois) — Communityplace.",
        "business_metadata": build_ged_business_metadata(
            source="kdmarche", source_id=f"EMAIL-JOURNAL-{month}",
            payload={"month": month, "rows": rows, "csv_base64": base64.b64encode(csv_content.encode("utf-8-sig")).decode()},
        ),
    }
    run = {"month": month, "rows": rows, "archived_at": datetime.now(timezone.utc).isoformat()}
    try:
        response = await client.create_document(payload)
        run.update({"status": "SUCCESS", "ged_response": {k: response.get(k) for k in ("id", "reference", "status") if k in response}})
    except Exception as exc:
        run.update({"status": "ERROR", "error": str(exc)})
    await db.email_archive_runs.update_one({"month": month}, {"$set": run}, upsert=True)
    return run


@email_previews_router.get("/export/csv")
async def export_logs_csv(request: Request, month: str = ""):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    csv_content, _rows = await _build_logs_csv(month.strip() or None)
    suffix = month.strip() or datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=csv_content.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="journal-emails-{suffix}.csv"'},
    )


@email_previews_router.post("/archive-ged")
async def archive_to_ged(request: Request):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    month = (body.get("month") or datetime.now(timezone.utc).strftime("%Y-%m")).strip()
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise HTTPException(status_code=400, detail="Format de mois invalide (attendu YYYY-MM)")
    return await archive_email_logs_to_ged(db, month, force=bool(body.get("force")))


@email_previews_router.post("/{template_id}/send-test")
async def send_test_email(request: Request, template_id: str):
    admin = await get_current_admin_from_request(request)
    if not admin:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    template = next((t for t in _TEMPLATES if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    to_email = (body.get("email") or admin.get("email") or "").strip()
    if not to_email or "@" not in to_email:
        raise HTTPException(status_code=400, detail="Adresse email invalide")
    from brevo_service import is_brevo_configured, send_email
    if not is_brevo_configured():
        raise HTTPException(status_code=503, detail="Brevo non configuré")
    result = await send_email(
        to_email=to_email,
        to_name=admin.get("contact_name"),
        subject=f"[TEST] {template['subject']}",
        html_content=_wrap_html(template["subject"], template["body"]),
        tags=["email-preview-test"],
    )
    return {"sent": True, "to": to_email, "message_id": result.get("messageId")}
