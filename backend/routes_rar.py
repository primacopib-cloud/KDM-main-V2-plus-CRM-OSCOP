"""Règlement à Réception Pro (RàR) — éligibilité, plafond, options de paiement, paramètres produit."""
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from checkout_common import get_current_user_checkout
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)
rar_router = APIRouter(prefix="/api/rar", tags=["rar"])
db = None

RAR_STATUSES = [
    "Commande acceptée sous plafond", "Préparation fournisseur", "Expédiée",
    "En cours de livraison", "Livrée — réception à confirmer", "Réception confirmée",
    "Règlement déclenché", "Paiement en traitement", "Paiement encaissé",
    "Plafond rétabli", "Réserves en cours de traitement",
]

DEFAULT_OPTIONS = [
    {"code": "IMMEDIATE", "label": "Paiement immédiat",
     "description": "Réglez votre commande lors de sa validation.", "visible": True, "builtin": True, "sort": 1},
    {"code": "RAR", "label": "Règlement à Réception Pro",
     "description": "Aucun acompte sur les marchandises. Le paiement sera déclenché après confirmation de la livraison.",
     "visible": True, "builtin": True, "sort": 2},
]


def set_rar_database(database):
    global db
    db = database


async def _ensure_options_seed():
    if await db.payment_options.count_documents({}) == 0:
        await db.payment_options.insert_many([{**o} for o in DEFAULT_OPTIONS])


async def _org_id_for(user: dict):
    m = await db.org_memberships.find_one({"user_id": user["id"]})
    return m["org_id"] if m else None


async def get_rar_account(org_id: str):
    return await db.rar_accounts.find_one({"org_id": org_id}, {"_id": 0})


async def rar_usage(org_id: str) -> dict:
    """Montants mobilisés sur le plafond — rétablis uniquement après encaissement définitif."""
    buckets = {"preparation": 0, "delivery": 0, "processing": 0}
    async for o in db.orders.find(
            {"org_id": org_id, "payment_method": "cod",
             "payment_status": {"$in": ["cod_pending", "processing"]}},
            {"_id": 0, "status": 1, "payment_status": 1, "cod_amount_due_cents": 1,
             "total_ttc_cents": 1, "rar_reserved_cents": 1}):
        amount = o.get("rar_reserved_cents") or o.get("cod_amount_due_cents") or o.get("total_ttc_cents") or 0
        if o.get("payment_status") == "processing" or o.get("status") in ("PICKED_UP", "INVOICED"):
            buckets["processing"] += amount
        elif o.get("status") == "READY_FOR_PICKUP":
            buckets["delivery"] += amount
        else:
            buckets["preparation"] += amount
    buckets["in_use"] = sum(buckets.values())
    return buckets


async def rar_status_payload(org_id: str) -> dict:
    account = await get_rar_account(org_id)
    usage = await rar_usage(org_id)
    ceiling = (account or {}).get("ceiling_cents", 0)
    available = max(0, ceiling - usage["in_use"]) if account and account.get("status") == "APPROVED" else 0
    return {
        "status": (account or {}).get("status", "NONE"),
        "source": (account or {}).get("source"),
        "ceiling_cents": ceiling,
        "preparation_cents": usage["preparation"],
        "delivery_cents": usage["delivery"],
        "processing_cents": usage["processing"],
        "in_use_cents": usage["in_use"],
        "available_cents": available,
        "statuses": RAR_STATUSES,
        "notes": (account or {}).get("notes"),
    }


async def check_items_rar_eligible(order_or_cart: dict) -> list:
    """Retourne la liste des produits NON éligibles au RàR (nom + raison)."""
    zone = order_or_cart.get("zone_code")
    problems = []
    for it in order_or_cart.get("items", []):
        pid = it.get("product_id")
        p = await db.products.find_one({"id": pid}, {"_id": 0, "name": 1, "rar_eligible": 1, "rar_zones": 1})
        if not p or not p.get("rar_eligible"):
            problems.append({"name": (p or {}).get("name") or it.get("product_name", "?"),
                             "reason": "Produit non éligible (EXW — règlement à l'enlèvement)"})
        elif p.get("rar_zones") and zone and zone not in p["rar_zones"]:
            problems.append({"name": p["name"], "reason": f"Territoire {zone} non couvert"})
    return problems


async def rar_gate(user: dict, amount_cents: int = 0, order_or_cart: dict = None) -> dict:
    """Vérification complète d'accès RàR — utilisée par le checkout et confirm-cod."""
    await _ensure_options_seed()
    opt = await db.payment_options.find_one({"code": "RAR"}, {"_id": 0})
    if not opt or not opt.get("visible"):
        return {"allowed": False, "reason": "Option désactivée par l'administration"}
    org_id = await _org_id_for(user)
    if not org_id:
        return {"allowed": False, "reason": "Aucune organisation associée"}
    payload = await rar_status_payload(org_id)
    if payload["status"] != "APPROVED":
        return {"allowed": False, "reason": "Accès sous réserve d'éligibilité et de plafond disponible — compte non validé",
                **payload}
    if amount_cents and amount_cents > payload["available_cents"]:
        return {"allowed": False, "reason": f"Plafond disponible insuffisant ({payload['available_cents'] / 100:.2f} €)",
                **payload}
    ineligible = await check_items_rar_eligible(order_or_cart) if order_or_cart else []
    if ineligible:
        return {"allowed": False, "reason": "Certains produits ne sont pas éligibles",
                "ineligible_items": ineligible, **payload}
    return {"allowed": True, "org_id": org_id, **payload}


# ================= PUBLIC / ACHETEUR =================

@rar_router.get("/payment-options")
async def public_payment_options():
    await _ensure_options_seed()
    opts = await db.payment_options.find({"visible": True}, {"_id": 0}).sort("sort", 1).to_list(20)
    return {"options": opts}


@rar_router.get("/my-status")
async def my_rar_status(user: dict = Depends(get_current_user_checkout)):
    org_id = await _org_id_for(user)
    if not org_id:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    return await rar_status_payload(org_id)


@rar_router.post("/request")
async def request_rar_access(body: dict = None, user: dict = Depends(get_current_user_checkout)):
    org_id = await _org_id_for(user)
    if not org_id:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    account = await get_rar_account(org_id)
    if account and account.get("status") in ("PENDING", "APPROVED"):
        raise HTTPException(status_code=409, detail="Demande déjà en cours ou compte déjà validé")
    await db.rar_accounts.update_one(
        {"org_id": org_id},
        {"$set": {"org_id": org_id, "status": "PENDING", "source": "REQUEST",
                  "message": ((body or {}).get("message") or "")[:500],
                  "requested_by": user["id"], "requested_at": datetime.utcnow(),
                  "updated_at": datetime.utcnow()}},
        upsert=True)
    logger.info("Demande RàR déposée par org %s", org_id)
    return {"ok": True, "status": "PENDING",
            "message": "Demande enregistrée — accès sous réserve d'éligibilité et de plafond disponible, après validation par KDMARCHÉ."}


@rar_router.post("/activate-via-pack")
async def activate_via_crediscop_pack(user: dict = Depends(get_current_user_checkout)):
    """Éligibilité immédiate (sans instruction de dossier) si un pack CREDI'SCOP a été acquis."""
    org_id = await _org_id_for(user)
    if not org_id:
        raise HTTPException(status_code=400, detail="Aucune organisation associée")
    account = await get_rar_account(org_id)
    if account and account.get("status") == "APPROVED":
        raise HTTPException(status_code=409, detail="Compte déjà validé")
    member_ids = [m["user_id"] async for m in db.org_memberships.find({"org_id": org_id}, {"user_id": 1})]
    tx = await db.payment_transactions.find_one(
        {"user_id": {"$in": member_ids}, "package_id": {"$exists": True},
         "payment_status": {"$in": ["paid", "succeeded", "complete", "completed"]}},
        {"_id": 0, "package_id": 1, "amount": 1})
    if not tx:
        raise HTTPException(status_code=403,
                            detail="Aucun pack CREDI'SCOP acquis — achetez un pack de crédits pour une éligibilité immédiate, ou déposez une demande classique.")
    cfg = await db.rar_config.find_one({}, {"_id": 0}) or {}
    ceiling = int(cfg.get("pack_ceiling_cents") or 200000)
    await db.rar_accounts.update_one(
        {"org_id": org_id},
        {"$set": {"org_id": org_id, "status": "APPROVED", "source": "CREDISCOP_PACK",
                  "ceiling_cents": ceiling, "decided_at": datetime.utcnow(),
                  "decided_by": "AUTO_CREDISCOP_PACK", "requested_by": user["id"],
                  "notes": f"Éligibilité automatique via pack CREDI'SCOP ({tx.get('package_id')})",
                  "updated_at": datetime.utcnow()}},
        upsert=True)
    logger.info("RàR activé via pack CREDI'SCOP pour org %s (plafond %s)", org_id, ceiling)
    return {"ok": True, "status": "APPROVED", "ceiling_cents": ceiling,
            "message": f"Éligibilité activée via votre pack CREDI'SCOP — plafond accordé : {ceiling / 100:.0f} €"}


@rar_router.get("/checkout-context")
async def rar_checkout_context(user: dict = Depends(get_current_user_checkout)):
    """Contexte panier : options visibles + état RàR + montants plafond pour l'écran de paiement."""
    await _ensure_options_seed()
    opts = await db.payment_options.find({"visible": True}, {"_id": 0}).sort("sort", 1).to_list(20)
    org_id = await _org_id_for(user)
    cart = None
    if org_id:
        carts = await db.carts.find({"org_id": org_id, "status": "ACTIVE"}).sort("updated_at", -1).to_list(5)
        cart = next((c for c in carts if c.get("items")), carts[0] if carts else None)
    total = (cart or {}).get("total_ttc_cents", 0)
    gate = await rar_gate(user, amount_cents=total, order_or_cart=cart)
    return {
        "options": opts,
        "rar": {**{k: v for k, v in gate.items() if k != "org_id"},
                "order_total_ttc_cents": total,
                "remaining_after_cents": max(0, gate.get("available_cents", 0) - total)},
    }


# ================= ADMIN =================

@rar_router.get("/admin/accounts")
async def admin_rar_accounts(admin: dict = Depends(require_admin)):
    accounts = await db.rar_accounts.find({}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    org_ids = [a["org_id"] for a in accounts]
    orgs = {o["id"]: o.get("legal_name") or o.get("name") for o in
            await db.organizations.find({"id": {"$in": org_ids}}, {"id": 1, "legal_name": 1, "name": 1}).to_list(200)}
    for a in accounts:
        a["org_name"] = orgs.get(a["org_id"], a["org_id"])
        usage = await rar_usage(a["org_id"])
        a["in_use_cents"] = usage["in_use"]
        a["available_cents"] = max(0, a.get("ceiling_cents", 0) - usage["in_use"]) if a.get("status") == "APPROVED" else 0
    return {"accounts": accounts, "pending_count": sum(1 for a in accounts if a["status"] == "PENDING")}


@rar_router.post("/admin/decide")
async def admin_rar_decide(body: dict, admin: dict = Depends(require_admin)):
    org_id = (body or {}).get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id requis")
    approve = bool(body.get("approve"))
    update = {"status": "APPROVED" if approve else "REJECTED",
              "decided_at": datetime.utcnow(), "decided_by": admin.get("email"),
              "notes": (body.get("notes") or "")[:500], "updated_at": datetime.utcnow()}
    if approve:
        ceiling = int(body.get("ceiling_cents") or 0)
        if ceiling <= 0:
            raise HTTPException(status_code=400, detail="Plafond requis pour valider (ceiling_cents)")
        update["ceiling_cents"] = ceiling
    r = await db.rar_accounts.update_one({"org_id": org_id}, {"$set": update}, upsert=True)
    logger.info("RàR %s pour org %s par %s", update["status"], org_id, admin.get("email"))
    # Email de décision à l'acheteur
    account = await db.rar_accounts.find_one({"org_id": org_id}, {"_id": 0, "requested_by": 1})
    requester = await db.users.find_one({"id": (account or {}).get("requested_by")},
                                        {"_id": 0, "email": 1, "contact_name": 1}) if account else None
    if requester and requester.get("email"):
        try:
            from brevo_service import send_email, _wrap_html
            if approve:
                subject = "✅ Règlement à Réception Pro — votre accès est validé"
                body_html = (f"<p>Bonjour,</p><p>Votre demande d'accès au dispositif <b>Règlement à Réception Pro</b> "
                             f"a été validée par KDMARCHÉ.</p><p>Plafond accordé : "
                             f"<b style='font-size:18px'>{update['ceiling_cents'] / 100:.2f} €</b></p>"
                             f"<p>Vous pouvez désormais commander les marchandises éligibles sans acompte — "
                             f"le règlement sera déclenché après validation électronique de la réception.</p>"
                             f"<p style='font-size:11px;color:#888'>Accès personnel et révocable, sous réserve du plafond disponible.</p>")
            else:
                subject = "Règlement à Réception Pro — décision sur votre demande"
                body_html = (f"<p>Bonjour,</p><p>Après instruction, votre demande d'accès au dispositif "
                             f"Règlement à Réception Pro n'a pas été retenue à ce stade."
                             f"{('<p>Motif : ' + update['notes'] + '</p>') if update.get('notes') else ''}"
                             f"<p>Vous pouvez renouveler votre demande ultérieurement ou obtenir une éligibilité "
                             f"immédiate via l'acquisition d'un pack CREDI'SCOP.</p>")
            await send_email(to_email=requester["email"], to_name=requester.get("contact_name"),
                             subject=subject, html_content=_wrap_html(subject, body_html),
                             text_content=subject, tags=["rar_decision"])
        except Exception as exc:
            logger.warning("Email décision RàR non envoyé : %s", exc)
    return {"ok": True, "status": update["status"], "matched": r.matched_count}


@rar_router.post("/admin/update")
async def admin_rar_update(body: dict, admin: dict = Depends(require_admin)):
    """Ajuste plafond ou statut (SUSPENDED / APPROVED)."""
    org_id = (body or {}).get("org_id")
    if not org_id:
        raise HTTPException(status_code=400, detail="org_id requis")
    update = {"updated_at": datetime.utcnow()}
    if body.get("ceiling_cents") is not None:
        update["ceiling_cents"] = max(0, int(body["ceiling_cents"]))
    if body.get("status") in ("APPROVED", "SUSPENDED", "REJECTED"):
        update["status"] = body["status"]
    r = await db.rar_accounts.update_one({"org_id": org_id}, {"$set": update})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    return {"ok": True}


# ----- Options de paiement (configurables super admin) -----

@rar_router.get("/admin/payment-options")
async def admin_payment_options(admin: dict = Depends(require_admin)):
    await _ensure_options_seed()
    return {"options": await db.payment_options.find({}, {"_id": 0}).sort("sort", 1).to_list(50)}


@rar_router.post("/admin/payment-options")
async def admin_add_payment_option(body: dict, admin: dict = Depends(require_admin)):
    label = ((body or {}).get("label") or "").strip()
    if not label:
        raise HTTPException(status_code=400, detail="label requis")
    code = (body.get("code") or f"OPT-{uuid.uuid4().hex[:6].upper()}").upper()
    if await db.payment_options.find_one({"code": code}):
        raise HTTPException(status_code=409, detail="Code déjà utilisé")
    await db.payment_options.insert_one({
        "code": code, "label": label[:80], "description": (body.get("description") or "")[:300],
        "visible": bool(body.get("visible", True)), "builtin": False,
        "sort": int(body.get("sort") or 99)})
    return {"ok": True, "code": code}


@rar_router.put("/admin/payment-options/{code}")
async def admin_update_payment_option(code: str, body: dict, admin: dict = Depends(require_admin)):
    update = {}
    for f in ("label", "description"):
        if body.get(f) is not None:
            update[f] = str(body[f])[:300]
    if body.get("visible") is not None:
        update["visible"] = bool(body["visible"])
    if body.get("sort") is not None:
        update["sort"] = int(body["sort"])
    r = await db.payment_options.update_one({"code": code.upper()}, {"$set": update})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Option introuvable")
    return {"ok": True}


@rar_router.delete("/admin/payment-options/{code}")
async def admin_delete_payment_option(code: str, admin: dict = Depends(require_admin)):
    opt = await db.payment_options.find_one({"code": code.upper()})
    if not opt:
        raise HTTPException(status_code=404, detail="Option introuvable")
    if opt.get("builtin"):
        raise HTTPException(status_code=400, detail="Option native : utilisez le masquage (visible=false)")
    await db.payment_options.delete_one({"code": code.upper()})
    return {"ok": True}


# ----- Paramètres produit RàR (Lot B) -----

RAR_PRODUCT_FIELDS = ("rar_eligible", "rar_zones", "rar_min_ceiling_cents", "rar_delay",
                      "rar_trigger", "rar_logistics_fees", "rar_customs", "rar_delivery_mode")


@rar_router.get("/admin/products")
async def admin_rar_products(admin: dict = Depends(require_admin)):
    prods = await db.products.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "sku": 1, "name": 1, **{f: 1 for f in RAR_PRODUCT_FIELDS}},
    ).sort("name", 1).to_list(300)
    return {"products": prods}


@rar_router.put("/admin/products/{product_id}")
async def admin_set_product_rar(product_id: str, body: dict, admin: dict = Depends(require_admin)):
    update = {}
    b = body or {}
    if b.get("rar_eligible") is not None:
        update["rar_eligible"] = bool(b["rar_eligible"])
    if b.get("rar_zones") is not None:
        update["rar_zones"] = [str(z).upper() for z in (b["rar_zones"] or [])][:20]
    if b.get("rar_min_ceiling_cents") is not None:
        update["rar_min_ceiling_cents"] = max(0, int(b["rar_min_ceiling_cents"]))
    for f in ("rar_delay", "rar_trigger", "rar_logistics_fees", "rar_customs", "rar_delivery_mode"):
        if b.get(f) is not None:
            update[f] = str(b[f])[:200]
    if not update:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    if update.get("rar_eligible"):
        update.setdefault("rar_delivery_mode", "LOGI'SCOP")
        update.setdefault("rar_trigger", "Validation du bon de livraison")
    r = await db.products.update_one({"id": product_id}, {"$set": update})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return {"ok": True, "updated": list(update)}
