"""Abonnement Privilège « Spécial Investisseur » : packs de crédits coopératifs bonifiés
préfinançant les stocks et conteneurs LOGI'SCOP des acheteurs pro (programme FCRL)."""
import logging
import uuid
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from lolodrive_helpers import get_current_user, require_admin

logger = logging.getLogger(__name__)
privilege_router = APIRouter(prefix="/api/investor/privilege", tags=["investor-privilege"])

db = None


def set_privilege_database(database):
    global db
    db = database


def _now():
    return datetime.now(timezone.utc)


CONVENTION_VERSION = "1.0"

PACKS = {
    "BRONZE": {
        "id": "BRONZE", "tier": "Bronze", "name": "Pack Logistique « Relais »",
        "amount_eur": 50000, "bonus_pct": 15, "credits_eur": 57500,
        "cible": "PME locales ou commerçants installés souhaitant optimiser leurs prochains flux.",
        "destination": "Fléché sur le déblocage immédiat des lots de marchandises en attente de transit.",
        "privileges": [
            "Exonération des frais de dossier de groupage sur 2 conteneurs LOGI'SCOP",
            "Accès aux rapports de tendances de marché de la centrale",
            "Accès prioritaire aux nouveautés du catalogue KDMARCHÉ",
        ],
    },
    "ARGENT": {
        "id": "ARGENT", "tier": "Argent", "name": "Pack Fret « Booster »",
        "amount_eur": 150000, "bonus_pct": 20, "credits_eur": 180000,
        "cible": "Groupements d'achats, franchises ou investisseurs institutionnels de l'ESS.",
        "destination": "Financement amont d'un demi-conteneur de groupage sur les lignes maritimes stratégiques.",
        "privileges": [
            "Priorité de chargement « First-in, First-out » sur les lignes de fret maritime",
            "Priorisation automatique de traitement douanier (circuit coupe-file)",
            "Option de revente/transfert d'une partie des crédits à un autre acheteur pro (marché secondaire interne)",
        ],
    },
    "OR": {
        "id": "OR", "tier": "Or", "name": "Pack Structurel « Partenaire Majeur »",
        "amount_eur": 500000, "bonus_pct": 30, "credits_eur": 650000,
        "cible": "Fonds de capital-investissement à impact, grandes entreprises locales (RSE) ou mécènes industriels.",
        "destination": "Dotation du fonds de roulement global de la centrale pour sécuriser les contrats d'approvisionnement annuels.",
        "privileges": [
            "Siège au comité d'orientation stratégique de la SCIC (droit de vote consultatif)",
            "Indexation de la bonification sur les volumes globaux traités par la centrale",
            "Personnalisation des lignes de supply-chain dédiées",
        ],
    },
}

CONVENTION_PARTIES = (
    "La SCIC SAS OBJECTIF SCOP OUTREMER, immatriculée au RCS de Pointe-à-Pitre sous le numéro "
    "903 459 139, dont le siège social est situé aux Abymes (Guadeloupe), ci-après « La SCIC », "
    "ET l'Investisseur signataire identifié ci-dessous."
)

CONVENTION_ARTICLES = [
    ("Article 1 — Objet de la convention",
     "La présente convention définit les conditions dans lesquelles l'Investisseur préfinance les flux "
     "logistiques amont et d'achats de marchandises de la centrale KDMARCHÉ × O'SCOP (programme "
     "« Fonds Coopératif de Roulement Logistique » — FCRL), en contrepartie d'une bonification de son "
     "pouvoir d'achat professionnel au sein du réseau."),
    ("Article 2 — Montant de l'apport et sélection du pack",
     "L'Investisseur s'engage à verser à la SCIC la somme globale et définitive correspondant au pack "
     "sélectionné : 50 000 € (Pack Bronze — bonification +15 %), 150 000 € (Pack Argent — bonification "
     "+20 %) ou 500 000 € et plus (Pack Or — bonification +30 %). Les fonds sont libérés par carte via la "
     "passerelle sécurisée de la plateforme ou par virement bancaire sur le compte de la SCIC dans un délai "
     "de 8 jours ouvrés à compter de la signature des présentes."),
    ("Article 3 — Affectation des fonds et collatéral",
     "La SCIC s'engage formellement à affecter 100 % des fonds versés au compte d'exploitation exclusif des "
     "branches KDMARCHÉ (achats de stocks de marchandises) et LOGI'SCOP (fret et transit maritime). Les "
     "marchandises acquises et en transit logistique constituent le gage collatéral de l'apport de "
     "l'Investisseur. Les fonds ne sont jamais placés sur des marchés spéculatifs."),
    ("Article 4 — Créditation et modalités des bonifications",
     "Dès réception des fonds, la SCIC crédite le compte numérique professionnel de l'Investisseur "
     "(système CREDI'SCOP) de la valeur convertie et bonifiée : 57 500 € de crédits (Pack Bronze), "
     "180 000 € de crédits (Pack Argent) ou 650 000 € de crédits (Pack Or). Ces crédits sont valables 24 "
     "mois sur l'ensemble du catalogue de la centrale et ne sont pas directement remboursables en "
     "numéraire, sauf défaillance de livraison constatée et non résolue sous 90 jours par LOGI'SCOP."),
    ("Article 5 — Force majeure et aléas climatiques (spécificité Outre-mer)",
     "Outre les cas habituellement retenus par la jurisprudence, sont expressément considérés comme cas de "
     "force majeure : les phénomènes cycloniques majeurs (alerte rouge ou violette Météo-France) entraînant "
     "la fermeture des ports de départ ou d'arrivée ; les catastrophes naturelles reconnues par arrêté "
     "interministériel impactant les infrastructures de stockage de la SCIC ou du transporteur LOGI'SCOP. "
     "La survenance d'un tel événement suspend les obligations de livraison et de mise à disposition des "
     "crédits pendant toute la durée du blocage, sans pénalité ni dommages et intérêts."),
    ("Article 6 — Extension et gestion des retards maritimes exceptionnels",
     "En cas de retard de livraison supérieur à 45 jours ouvrés par rapport à l'ETA du conteneur "
     "préfinancé, la SCIC s'engage à informer l'Investisseur par écrit sous 48 heures ouvrées (justificatif "
     "de transport maritime à l'appui) et à proposer un déblocage d'un crédit d'urgence équivalent à 20 % "
     "de la valeur de l'apport initial, prélevé sur les stocks immédiatement disponibles de la centrale "
     "KDMARCHÉ, afin de ne pas paralyser l'activité de l'acheteur professionnel."),
    ("Article 7 — Conditions de résiliation anticipée",
     "Par l'Investisseur : si le retard maritime dépasse 90 jours calendaires hors force majeure (Article "
     "5) sans solution de substitution ni compensation de stock, les sommes versées et non encore "
     "converties en marchandises livrées sont intégralement remboursées sous 30 jours, entraînant "
     "l'annulation des bonifications associées. Par la SCIC : en cas de non-libération des fonds dans le "
     "délai prévu à l'Article 2, résiliation immédiate sans mise en demeure préalable."),
]


@privilege_router.get("/packs")
async def list_packs():
    return {"packs": [PACKS["BRONZE"], PACKS["ARGENT"], PACKS["OR"]],
            "convention": {"version": CONVENTION_VERSION, "parties": CONVENTION_PARTIES,
                           "articles": [{"title": t, "text": x} for t, x in CONVENTION_ARTICLES]}}


class SubscribeBody(BaseModel):
    pack_id: str
    payment_method: str  # STRIPE | TRANSFER
    signer_name: str
    company_name: str
    siret: str = ""
    accept: bool
    origin_url: str = ""


@privilege_router.post("/subscribe")
async def subscribe_pack(body: SubscribeBody, user: dict = Depends(get_current_user)):
    pack = PACKS.get(body.pack_id.upper())
    if not pack:
        raise HTTPException(status_code=400, detail="Pack invalide")
    if not body.accept or not body.signer_name.strip() or not body.company_name.strip():
        raise HTTPException(status_code=400,
                            detail="Signature de la convention d'investissement requise (nom, société, acceptation)")
    if body.payment_method not in ("STRIPE", "TRANSFER"):
        raise HTTPException(status_code=400, detail="Mode de paiement invalide")
    if await db.investor_privilege_subs.find_one(
            {"user_id": user["id"], "status": {"$in": ["ACTIVE", "PENDING_TRANSFER"]}}):
        raise HTTPException(status_code=409,
                            detail="Vous avez déjà un pack Privilège actif ou en attente d'activation")
    reference = f"FCRL-{_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    sub = {
        "id": str(uuid.uuid4()), "reference": reference, "user_id": user["id"],
        "email": user.get("email"), "pack_id": pack["id"], "pack_name": pack["name"],
        "tier": pack["tier"], "amount_eur": pack["amount_eur"], "bonus_pct": pack["bonus_pct"],
        "credits_eur": pack["credits_eur"], "payment_method": body.payment_method,
        "convention": {"version": CONVENTION_VERSION, "signer_name": body.signer_name.strip(),
                       "company_name": body.company_name.strip(), "siret": body.siret.strip(),
                       "signed_at": _now().isoformat()},
        "created_at": _now().isoformat(),
    }
    if body.payment_method == "TRANSFER":
        sub["status"] = "PENDING_TRANSFER"
        await db.investor_privilege_subs.insert_one({**sub})
        return {"ok": True, "status": "PENDING_TRANSFER", "reference": reference,
                "instructions": ("Effectuez votre virement sur le compte séquestre de la SCIC OBJECTIF SCOP "
                                 f"OUTREMER en indiquant la référence {reference}. Votre pack sera activé par "
                                 "la direction financière dès réception des fonds (délai contractuel : 8 jours "
                                 "ouvrés, Article 2 de la convention). IBAN communiqué par retour d'email à "
                                 f"{user.get('email')}.")}
    from routes_cpc import _stripe_key
    origin = (body.origin_url or "").rstrip("/")
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.create(
        api_key=_stripe_key(), mode="payment", payment_method_types=["card"],
        line_items=[{
            "price_data": {"currency": "eur", "unit_amount": pack["amount_eur"] * 100,
                           "product_data": {
                               "name": f"Abonnement Privilège Investisseur — {pack['name']} "
                                       f"(+{pack['bonus_pct']} % · {pack['credits_eur']:,} € de crédits)".replace(",", " ")}},
            "quantity": 1}],
        customer_email=user.get("email"),
        success_url=f"{origin}/espace-investisseur?priv_session={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{origin}/investisseurs-privilege?cancelled=1",
        metadata={"kind": "INVESTOR_PRIVILEGE", "user_id": user["id"], "pack_id": pack["id"]})
    sub["status"] = "PENDING"
    sub["stripe_session_id"] = session.id
    await db.investor_privilege_subs.insert_one({**sub})
    return {"ok": True, "status": "PENDING", "checkout_url": session.url, "reference": reference}


class ActivateBody(BaseModel):
    session_id: str


async def _activate(sub: dict):
    await db.investor_privilege_subs.update_one(
        {"id": sub["id"]}, {"$set": {"status": "ACTIVE", "activated_at": _now().isoformat()}})
    await db.users.update_one({"id": sub["user_id"]}, {"$set": {"is_investor": True}})
    await db.privilege_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": sub["user_id"], "sub_id": sub["id"],
        "sub_reference": sub["reference"], "type": "CREDIT", "amount_eur": sub["credits_eur"],
        "label": f"Créditation {sub['pack_name']} (+{sub['bonus_pct']} % de bonification)",
        "created_at": _now().isoformat()})
    try:
        from brevo_service import send_email, _wrap_html
        html = _wrap_html(
            "Abonnement Privilège Investisseur activé",
            f"<p>Votre <b>{sub['pack_name']}</b> ({sub['tier']}) est actif.</p>"
            f"<p>Apport : <b>{sub['amount_eur']:,} €</b> — Crédits CREDI'SCOP bonifiés crédités : "
            f"<b>{sub['credits_eur']:,} €</b> (+{sub['bonus_pct']} %), valables 24 mois.</p>"
            f"<p>Référence : {sub['reference']}. Votre convention signée est téléchargeable depuis votre "
            "espace investisseur.</p>".replace(",", " "))
        await send_email(sub["email"], "👑 Votre Abonnement Privilège Investisseur est actif", html)
    except Exception as exc:
        logger.warning("Email activation pack privilège : %s", exc)


@privilege_router.post("/activate")
async def activate_stripe(body: ActivateBody, user: dict = Depends(get_current_user)):
    sub = await db.investor_privilege_subs.find_one(
        {"stripe_session_id": body.session_id, "user_id": user["id"]}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Souscription introuvable")
    if sub["status"] == "ACTIVE":
        return {"ok": True, "already": True, "sub": sub}
    from routes_cpc import _stripe_key
    stripe.api_base = "https://api.stripe.com"
    session = stripe.checkout.Session.retrieve(body.session_id, api_key=_stripe_key())
    if session.get("payment_status") != "paid":
        raise HTTPException(status_code=402, detail="Paiement non confirmé")
    await _activate(sub)
    sub["status"] = "ACTIVE"
    return {"ok": True, "sub": sub}


@privilege_router.get("/me")
async def my_privilege(user: dict = Depends(get_current_user)):
    subs = await db.investor_privilege_subs.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(10)
    consumed = {}
    async for e in db.privilege_credit_ledger.find(
            {"user_id": user["id"], "type": "CONSUMPTION"}, {"_id": 0, "sub_id": 1, "amount_eur": 1}):
        consumed[e["sub_id"]] = consumed.get(e["sub_id"], 0.0) + abs(float(e["amount_eur"]))
    for s in subs:
        s["privileges"] = PACKS.get(s["pack_id"], {}).get("privileges", [])
        s["consumed_eur"] = round(consumed.get(s["id"], 0.0), 2)
        s["remaining_eur"] = (round(s["credits_eur"] - s["consumed_eur"], 2)
                              if s["status"] == "ACTIVE" else 0.0)
    credits = sum(s["remaining_eur"] for s in subs if s["status"] == "ACTIVE")
    return {"subscriptions": subs, "credits_eur": round(credits, 2)}


def _convention_pdf(sub: dict) -> bytes:
    from routes_detaillant import _pdf_doc, _fmt_ts
    c = sub["convention"]
    blocks = [("Entre les parties", CONVENTION_PARTIES),
              ("Investisseur signataire",
               f"{c['company_name']} · SIREN/SIRET : {c.get('siret') or '—'} — représenté par {c['signer_name']}"),
              ("Pack souscrit",
               f"{sub['pack_name']} ({sub['tier']}) — Apport : {sub['amount_eur']:,} € — Bonification : "
               f"+{sub['bonus_pct']} % — Crédits CREDI'SCOP : {sub['credits_eur']:,} € — "
               f"Référence : {sub['reference']} — Paiement : "
               f"{'Carte (Stripe)' if sub['payment_method'] == 'STRIPE' else 'Virement bancaire'}".replace(",", " "))]
    blocks += list(CONVENTION_ARTICLES)
    blocks.append(("Signature électronique",
                   f"Signée par {c['signer_name']} le {_fmt_ts(c['signed_at'])} — version {c['version']} — "
                   "horodatage plateforme KDMARCHÉ × O'SCOP."))
    return _pdf_doc(f"Convention de préfinancement logistique et d'achats coopératifs — v{CONVENTION_VERSION}",
                    blocks)


@privilege_router.get("/convention/pdf")
async def my_convention_pdf(user: dict = Depends(get_current_user)):
    sub = await db.investor_privilege_subs.find_one(
        {"user_id": user["id"]}, {"_id": 0}, sort=[("created_at", -1)])
    if not sub:
        raise HTTPException(status_code=404, detail="Aucune convention signée")
    return Response(_convention_pdf(sub), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=convention-fcrl-{sub['reference']}.pdf"})


@privilege_router.get("/admin/registry")
async def admin_registry(q: str = "", status: str = "", admin: dict = Depends(require_admin)):
    query: dict = {}
    if status:
        query["status"] = status.upper()
    if q.strip():
        rx = {"$regex": q.strip(), "$options": "i"}
        query["$or"] = [{"reference": rx}, {"email": rx}, {"convention.company_name": rx},
                        {"convention.signer_name": rx}]
    subs = await db.investor_privilege_subs.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    all_subs = await db.investor_privilege_subs.find({}, {"_id": 0, "status": 1, "amount_eur": 1,
                                                          "credits_eur": 1}).to_list(1000)
    active = [s for s in all_subs if s["status"] == "ACTIVE"]
    stats = {"total": len(all_subs), "active": len(active),
             "pending_transfer": sum(1 for s in all_subs if s["status"] == "PENDING_TRANSFER"),
             "collected_eur": sum(s["amount_eur"] for s in active),
             "credits_issued_eur": sum(s["credits_eur"] for s in active)}
    return {"subscriptions": subs, "stats": stats}


@privilege_router.post("/admin/{sub_id}/activate")
async def admin_activate_transfer(sub_id: str, admin: dict = Depends(require_admin)):
    sub = await db.investor_privilege_subs.find_one({"id": sub_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Souscription introuvable")
    if sub["status"] == "ACTIVE":
        return {"ok": True, "already": True}
    if sub["status"] != "PENDING_TRANSFER":
        raise HTTPException(status_code=409, detail="Seuls les virements en attente peuvent être activés manuellement")
    await _activate(sub)
    return {"ok": True}


@privilege_router.get("/admin/{sub_id}/convention/pdf")
async def admin_convention_pdf(sub_id: str, admin: dict = Depends(require_admin)):
    sub = await db.investor_privilege_subs.find_one({"id": sub_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Souscription introuvable")
    return Response(_convention_pdf(sub), media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=convention-fcrl-{sub['reference']}.pdf"})


class ConsumeBody(BaseModel):
    amount_eur: float
    label: str


async def _ledger_entries(user_id: str):
    return await db.privilege_credit_ledger.find(
        {"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(1000)


def _monthly_statement(entries: list, month: str):
    sel = [e for e in entries if str(e["created_at"])[:7] == month]
    credited = sum(e["amount_eur"] for e in sel if e["amount_eur"] > 0)
    consumed = sum(-e["amount_eur"] for e in sel if e["amount_eur"] < 0)
    opening = sum(e["amount_eur"] for e in entries if str(e["created_at"])[:7] < month)
    return {"month": month, "entries": sel, "credited_eur": round(credited, 2),
            "consumed_eur": round(consumed, 2), "opening_eur": round(opening, 2),
            "closing_eur": round(opening + credited - consumed, 2)}


@privilege_router.get("/statement")
async def privilege_statement(month: str = "", user: dict = Depends(get_current_user)):
    """Relevé mensuel des crédits bonifiés FCRL : chaque créditation et consommation."""
    entries = await _ledger_entries(user["id"])
    months = sorted({str(e["created_at"])[:7] for e in entries}, reverse=True)
    if not month:
        month = months[0] if months else _now().strftime("%Y-%m")
    return {**_monthly_statement(entries, month), "months": months}


@privilege_router.get("/statement/pdf")
async def privilege_statement_pdf(month: str, user: dict = Depends(get_current_user)):
    entries = await _ledger_entries(user["id"])
    st = _monthly_statement(entries, month)
    from routes_detaillant import _pdf_doc, _fmt_ts
    label_month = datetime.strptime(month, "%Y-%m").strftime("%m/%Y")
    blocks = [("Période", f"Relevé du mois {label_month} — programme FCRL (crédits bonifiés CREDI'SCOP)"),
              ("Solde d'ouverture", f"{st['opening_eur']:,.2f} €".replace(",", " "))]
    if not st["entries"]:
        blocks.append(("Mouvements", "Aucun mouvement sur la période."))
    for e in st["entries"]:
        sign = "+" if e["amount_eur"] > 0 else "−"
        blocks.append((f"{_fmt_ts(e['created_at'])} — {e.get('sub_reference', '')}",
                       f"{e['label']} : {sign}{abs(e['amount_eur']):,.2f} €".replace(",", " ")))
    blocks.append(("Totaux du mois",
                   f"Crédité : +{st['credited_eur']:,.2f} € — Consommé : −{st['consumed_eur']:,.2f} € — "
                   f"Solde de clôture : {st['closing_eur']:,.2f} €".replace(",", " ")))
    pdf = _pdf_doc(f"Relevé mensuel des crédits FCRL — {label_month}", blocks)
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=releve-fcrl-{month}.pdf"})


@privilege_router.post("/admin/{sub_id}/consume")
async def admin_consume_credits(sub_id: str, body: ConsumeBody, admin: dict = Depends(require_admin)):
    """Impute une consommation de crédits bonifiés sur un pack actif (en euros)."""
    sub = await db.investor_privilege_subs.find_one({"id": sub_id}, {"_id": 0})
    if not sub:
        raise HTTPException(status_code=404, detail="Souscription introuvable")
    if sub["status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="Seul un pack actif peut être consommé")
    amount = round(float(body.amount_eur), 2)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Montant positif requis")
    used = 0.0
    async for e in db.privilege_credit_ledger.find(
            {"sub_id": sub_id, "type": "CONSUMPTION"}, {"_id": 0, "amount_eur": 1}):
        used += float(e["amount_eur"])
    remaining = round(sub["credits_eur"] - used, 2)
    if amount > remaining:
        raise HTTPException(status_code=400,
                            detail=f"Solde insuffisant : {remaining:,.2f} € restants".replace(",", " "))
    await db.privilege_credit_ledger.insert_one({
        "id": str(uuid.uuid4()), "user_id": sub["user_id"], "sub_id": sub_id,
        "sub_reference": sub["reference"], "type": "CONSUMPTION", "amount_eur": -amount,
        "label": body.label.strip() or "Consommation de crédits bonifiés",
        "recorded_by": admin.get("email"), "created_at": _now().isoformat()})
    return {"ok": True, "remaining_eur": round(remaining - amount, 2)}
