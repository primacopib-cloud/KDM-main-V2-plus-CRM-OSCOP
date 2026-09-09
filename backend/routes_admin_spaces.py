"""Registres & gestion des espaces (vendeur, investisseur, relais, PASS) pour le superadmin."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from lolodrive_helpers import require_admin

admin_spaces_router = APIRouter(prefix="/api/admin/spaces", tags=["Admin Spaces"])

db = None


def set_admin_spaces_database(database):
    global db
    db = database


async def notify_admin_signup(title: str, message: str, category: str = "inscription"):
    await db.admin_notifications.insert_one({
        "id": str(uuid.uuid4()), "title": title, "message": message,
        "type": "info", "category": category, "target_user_id": None,
        "action_url": "/superadmin", "metadata": {}, "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()})


def _iso(v):
    if isinstance(v, datetime):
        return v.isoformat()
    return v


async def _vendors_registry():
    items = []
    async for v in db.vendors.find({}, {"_id": 0, "password_hash": 0}):
        items.append({
            "id": v.get("id"),
            "name": v.get("company_name") or v.get("contact_name"),
            "contact": v.get("contact_name"),
            "email": v.get("email"),
            "phone": v.get("phone"),
            "country": v.get("country") or v.get("city"),
            "status": (v.get("status") or "pending").upper(),
            "detail": f"{v.get('product_count', 0)} produit(s)",
            "created_at": _iso(v.get("created_at")),
            "account_connected": True,
        })
    return items


async def _investors_registry():
    items = []
    async for acc in db.investor_accounts.find({}, {"_id": 0}):
        user = await db.users.find_one({"id": acc.get("user_id")}, {"_id": 0, "password_hash": 0})
        items.append({
            "id": acc.get("id"),
            "name": (user or {}).get("contact_name") or (user or {}).get("company_name") or "—",
            "email": (user or {}).get("email"),
            "phone": (user or {}).get("phone"),
            "country": None,
            "status": (acc.get("status") or "ACTIVE").upper(),
            "detail": f"Plan {acc.get('plan_code', '—')} · {round((acc.get('monthly_invest_uc') or 0) / 100)} UC/mois",
            "created_at": _iso(acc.get("created_at")),
            "account_connected": bool(user),
        })
    return items


async def _relays_registry():
    gerants = {}
    async for u in db.users.find({"role": "GERANT_LOLO_POINT"}, {"_id": 0, "password_hash": 0}):
        if u.get("email"):
            gerants[u["email"].lower()] = u
    items = []
    async for p in db.lolodrive_points.find({}, {"_id": 0}):
        manager = gerants.get((p.get("contact_email") or "").lower())
        items.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "contact": (manager or {}).get("contact_name"),
            "email": p.get("contact_email"),
            "country": p.get("territory"),
            "status": (p.get("status") or "ACTIVE").upper(),
            "detail": f"{p.get('code', '')} · {p.get('city', '')}",
            "created_at": _iso(p.get("created_at")),
            "account_connected": bool(manager),
        })
    return items


async def _pass_registry():
    items = []
    async for u in db.users.find({"role": "TITULAIRE_PASS"}, {"_id": 0, "password_hash": 0}):
        p = await db.lolodrive_passes.find_one({"user_id": u.get("id")}, {"_id": 0}, sort=[("created_at", -1)])
        ends = _iso((p or {}).get("ends_at")) or ""
        items.append({
            "id": u.get("id"),
            "name": u.get("contact_name") or u.get("company_name") or "—",
            "email": u.get("email"),
            "phone": u.get("phone"),
            "country": None,
            "status": ((p or {}).get("status") or "SANS_PASS").upper(),
            "detail": f"PASS jusqu'au {str(ends)[:10]}" if p else "Aucun PASS actif",
            "created_at": _iso(u.get("created_at")),
            "account_connected": True,
        })
    return items


async def _coopers_registry():
    items = []
    async for u in db.users.find({"role": "COOPER"}, {"_id": 0, "password_hash": 0}):
        items.append({"id": u.get("id"), "name": u.get("contact_name") or u.get("company_name"),
                      "email": u.get("email"), "phone": u.get("phone"), "country": u.get("country"),
                      "status": "SUSPENDED" if u.get("suspended") else "ACTIVE",
                      "created_at": _iso(u.get("created_at")), "account_connected": True})
    async for a in db.cooper_applications.find({"status": "PENDING"}, {"_id": 0}):
        items.append({"id": a.get("id"), "name": a.get("name"), "email": a.get("email"),
                      "phone": a.get("phone"), "country": a.get("country"), "status": "CANDIDATURE",
                      "detail": (a.get("motivation") or "")[:80],
                      "created_at": _iso(a.get("created_at")), "account_connected": False})
    return items


@admin_spaces_router.get("/registries")
async def get_registries(admin: dict = Depends(require_admin)):
    return {
        "vendors": await _vendors_registry(),
        "investors": await _investors_registry(),
        "relays": await _relays_registry(),
        "pass_members": await _pass_registry(),
        "coopers": await _coopers_registry(),
    }


class StatusBody(BaseModel):
    status: str


class ManagerBody(BaseModel):
    email: str


@admin_spaces_router.get("/relays/managers")
async def list_relay_managers(admin: dict = Depends(require_admin)):
    items = []
    async for u in db.users.find({"role": "GERANT_LOLO_POINT"}, {"_id": 0, "password_hash": 0}):
        items.append({"id": u.get("id"), "name": u.get("contact_name") or u.get("company_name"), "email": u.get("email")})
    return {"managers": items}


@admin_spaces_router.patch("/relays/{item_id}/manager")
async def link_relay_manager(item_id: str, body: ManagerBody, admin: dict = Depends(require_admin)):
    email = body.email.strip().lower()
    manager = await db.users.find_one({"email": email, "role": "GERANT_LOLO_POINT"}, {"_id": 0, "id": 1, "contact_name": 1})
    if not manager:
        raise HTTPException(status_code=404, detail="Aucun compte gérant avec cet email")
    res = await db.lolodrive_points.update_one(
        {"id": item_id},
        {"$set": {"contact_email": email, "manager_user_id": manager["id"],
                  "updated_at": datetime.now(timezone.utc).isoformat()}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Relais introuvable")
    return {"ok": True, "manager": manager.get("contact_name"), "email": email}


@admin_spaces_router.get("/assignees")
async def list_assignees(admin: dict = Depends(require_admin)):
    """Vendeurs et COOPER'S assignables aux besoins d'achat."""
    vendors, coopers = [], []
    async for v in db.vendors.find({}, {"_id": 0, "company_name": 1, "email": 1}):
        if v.get("email"):
            vendors.append({"name": v.get("company_name"), "email": v["email"]})
    async for u in db.users.find({"role": "COOPER"}, {"_id": 0, "contact_name": 1, "company_name": 1, "email": 1}):
        coopers.append({"name": u.get("contact_name") or u.get("company_name"), "email": u.get("email")})
    return {"vendors": vendors, "coopers": coopers}


class CooperCreate(BaseModel):
    name: str
    email: str
    phone: str | None = None
    country: str | None = None
    password: str | None = None


@admin_spaces_router.get("/coopers")
async def list_coopers(admin: dict = Depends(require_admin)):
    return {"coopers": await _coopers_registry()}


@admin_spaces_router.post("/coopers")
async def create_cooper(body: CooperCreate, admin: dict = Depends(require_admin)):
    """Crée un espace COOPER'S (compte utilisateur rôle COOPER)."""
    import secrets
    from auth import get_password_hash
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet email")
    password = body.password or secrets.token_urlsafe(9)
    user = {
        "id": f"user-cooper-{secrets.token_hex(4)}", "email": email,
        "password_hash": get_password_hash(password), "role": "COOPER",
        "contact_name": body.name, "company_name": body.name,
        "phone": body.phone, "country": body.country,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.cooper_applications.update_many({"email": email}, {"$set": {"status": "ACCEPTED"}})
    try:
        from brevo_service import send_email, _wrap_html
        import os
        base = os.environ.get("FRONTEND_URL") or "https://centrale.objectifscopoutremer.com"
        await send_email(
            to_email=email, to_name=body.name,
            subject="🤝 Votre espace COOPER'S est ouvert — Centrale O'SCOP",
            html_content=_wrap_html("Bienvenue COOPER'S", (
                f"<p style='font-size:14px;'>Bonjour {body.name},</p>"
                f"<p>Votre espace COOPER'S est créé. Identifiant : <b>{email}</b><br/>"
                f"Mot de passe provisoire : <b>{password}</b> (à changer à la première connexion)</p>"
                f"<p style='text-align:center;'><a href='{base}/connexion' "
                "style='display:inline-block;background:#D9B35A;color:#1F0A33;font-weight:bold;"
                "padding:12px 26px;border-radius:12px;text-decoration:none;'>Accéder à mon espace COOPER'S</a></p>")),
            tags=["cooper"])
    except Exception:
        pass
    return {"ok": True, "id": user["id"], "email": email, "temp_password": None if body.password else password}


class CooperApplication(BaseModel):
    name: str
    email: str
    phone: str | None = None
    country: str | None = None
    motivation: str | None = None


cooper_public_router = APIRouter(prefix="/api/public", tags=["Public COOPER"])


@cooper_public_router.post("/cooper-applications")
async def apply_cooper(body: CooperApplication):
    """Inscription publique en tant que COOPER'S (pied de page d'accueil)."""
    import uuid as _uuid
    email = body.email.strip().lower()
    doc = {
        "id": str(_uuid.uuid4()), "name": body.name.strip(), "email": email,
        "phone": body.phone, "country": body.country, "motivation": (body.motivation or "").strip()[:800],
        "status": "PENDING", "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.cooper_applications.insert_one(dict(doc))
    await notify_admin_signup("Nouvelle candidature COOPER'S",
                              f"{doc['name']} ({email}) souhaite devenir COOPER'S.", "cooper")
    try:
        from brevo_service import send_email, _wrap_html
        await send_email(
            to_email=email, to_name=doc["name"],
            subject="🤝 Candidature COOPER'S bien reçue — Centrale O'SCOP",
            html_content=_wrap_html("Candidature reçue", (
                f"<p style='font-size:14px;'>Bonjour {doc['name']},</p>"
                "<p>Votre candidature pour devenir <b>COOPER'S</b> de la Centrale O'SCOP est bien enregistrée. "
                "Notre équipe l'étudie et vous recontacte rapidement pour ouvrir votre espace.</p>")),
            tags=["cooper"])
    except Exception:
        pass
    return {"received": True, "id": doc["id"]}


def _fmt_order(o):
    return {
        "order_number": o.get("order_number"),
        "date": _iso(o.get("created_at")),
        "total_cents": o.get("total_cents") or o.get("total_ttc_cents") or 0,
        "status": o.get("status"),
    }


@admin_spaces_router.get("/{kind}/{item_id}/detail")
async def get_space_detail(kind: str, item_id: str, admin: dict = Depends(require_admin)):
    profile, orders, passes, activity, extra = {}, [], [], [], []
    if kind == "vendors":
        v = await db.vendors.find_one({"id": item_id}, {"_id": 0, "password_hash": 0})
        if not v:
            raise HTTPException(status_code=404, detail="Vendeur introuvable")
        profile = {"name": v.get("company_name"), "contact": v.get("contact_name"), "email": v.get("email"),
                   "phone": v.get("phone"), "country": v.get("country"), "status": (v.get("status") or "").upper(),
                   "created_at": _iso(v.get("created_at"))}
        async for p in db.vendor_products.find({"vendor_id": item_id}, {"_id": 0}).sort("created_at", -1).limit(10):
            extra.append({"label": p.get("name"), "value": f"{(p.get('price_ttc_cents') or 0) / 100:.2f} € · {p.get('status', '')}"})
        activity.append({"date": _iso(v.get("created_at")), "label": "Inscription vendeur"})
        if v.get("approved_at"):
            activity.append({"date": _iso(v.get("approved_at")), "label": "Compte approuvé"})
    elif kind == "investors":
        acc = await db.investor_accounts.find_one({"id": item_id}, {"_id": 0})
        if not acc:
            raise HTTPException(status_code=404, detail="Investisseur introuvable")
        user = await db.users.find_one({"id": acc.get("user_id")}, {"_id": 0, "password_hash": 0}) or {}
        profile = {"name": user.get("contact_name") or user.get("company_name"), "email": user.get("email"),
                   "phone": user.get("phone"), "country": user.get("country"),
                   "status": (acc.get("status") or "").upper(), "created_at": _iso(acc.get("created_at")),
                   "detail": f"Plan {acc.get('plan_code')} · {round((acc.get('monthly_invest_uc') or 0) / 100)} UC/mois"}
        async for l in db.invest_credit_ledger.find({"user_id": acc.get("user_id")}, {"_id": 0}).sort("created_at", -1).limit(10):
            activity.append({"date": _iso(l.get("created_at")), "label": f"{l.get('label')} ({round((l.get('amount_uc') or 0) / 100)} UC)"})
        activity.append({"date": _iso(acc.get("created_at")), "label": "Ouverture du compte investisseur"})
        if user.get("last_login_at"):
            activity.insert(0, {"date": _iso(user.get("last_login_at")), "label": "Dernière connexion"})
    elif kind == "relays":
        p = await db.lolodrive_points.find_one({"id": item_id}, {"_id": 0})
        if not p:
            raise HTTPException(status_code=404, detail="Relais introuvable")
        profile = {"name": p.get("name"), "email": p.get("contact_email"), "country": p.get("territory"),
                   "status": (p.get("status") or "").upper(), "created_at": _iso(p.get("created_at")),
                   "detail": f"{p.get('code', '')} · {p.get('city', '')}"}
        async for o in db.lolodrive_orders.find({"lolo_point_id": item_id}, {"_id": 0}).sort("created_at", -1).limit(10):
            orders.append(_fmt_order(o))
        n_act = await db.lolodrive_passes.count_documents({"source_lolo_point_id": item_id})
        extra.append({"label": "PASS activés via ce relais", "value": str(n_act)})
        activity.append({"date": _iso(p.get("created_at")), "label": "Création du relais"})
    elif kind == "pass-members":
        user = await db.users.find_one({"id": item_id}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=404, detail="Membre introuvable")
        profile = {"name": user.get("contact_name") or user.get("company_name"), "email": user.get("email"),
                   "phone": user.get("phone"), "country": user.get("country"),
                   "status": "MEMBRE PASS", "created_at": _iso(user.get("created_at"))}
        async for pa in db.lolodrive_passes.find({"user_id": item_id}, {"_id": 0}).sort("created_at", -1).limit(5):
            passes.append({"status": (pa.get("status") or "").upper(), "starts_at": _iso(pa.get("starts_at")),
                           "ends_at": _iso(pa.get("ends_at")), "uc_granted": pa.get("uc_granted")})
        async for o in db.lolodrive_orders.find({"user_id": item_id}, {"_id": 0}).sort("created_at", -1).limit(10):
            orders.append(_fmt_order(o))
        activity.append({"date": _iso(user.get("created_at")), "label": "Création du compte"})
        if user.get("last_login_at"):
            activity.insert(0, {"date": _iso(user.get("last_login_at")), "label": "Dernière connexion"})
    elif kind == "coopers":
        user = await db.users.find_one({"id": item_id, "role": "COOPER"}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=404, detail="COOPER'S introuvable")
        profile = {"name": user.get("contact_name") or user.get("company_name"), "email": user.get("email"),
                   "phone": user.get("phone"), "country": user.get("country"),
                   "status": "SUSPENDED" if user.get("suspended") else "ACTIVE",
                   "created_at": _iso(user.get("created_at"))}
        async for n in db.purchase_needs.find({"assigned_vendor": (user.get("email") or "").lower()}, {"_id": 0}).sort("created_at", -1).limit(10):
            extra.append({"label": f"{n.get('reference')} — {n.get('product')}", "value": n.get("status")})
        activity.append({"date": _iso(user.get("created_at")), "label": "Ouverture de l'espace COOPER'S"})
        if user.get("last_login_at"):
            activity.insert(0, {"date": _iso(user.get("last_login_at")), "label": "Dernière connexion"})
    else:
        raise HTTPException(status_code=404, detail="Type d'espace inconnu")
    activity = [a for a in activity if a.get("date")]
    return {"profile": profile, "orders": orders, "passes": passes, "activity": activity, "extra": extra}


_KINDS = {
    "vendors": ("vendors", "id"),
    "investors": ("investor_accounts", "id"),
    "relays": ("lolodrive_points", "id"),
}


@admin_spaces_router.patch("/{kind}/{item_id}/status")
async def update_space_status(kind: str, item_id: str, body: StatusBody, admin: dict = Depends(require_admin)):
    status = body.status.strip().upper()
    if not status:
        raise HTTPException(status_code=400, detail="Statut requis")
    now = datetime.now(timezone.utc).isoformat()
    if kind == "pass-members":
        res = await db.lolodrive_passes.update_one(
            {"user_id": item_id}, {"$set": {"status": status, "updated_at": now}}, upsert=False)
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Aucun PASS pour ce membre")
        return {"ok": True, "status": status}
    if kind == "coopers":
        res = await db.users.update_one(
            {"id": item_id, "role": "COOPER"},
            {"$set": {"suspended": status == "SUSPENDED", "updated_at": now}})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="COOPER'S introuvable")
        return {"ok": True, "status": status}
    if kind not in _KINDS:
        raise HTTPException(status_code=404, detail="Type d'espace inconnu")
    coll, key = _KINDS[kind]
    if kind == "vendors":
        status = status.lower()
    res = await db[coll].update_one({key: item_id}, {"$set": {"status": status, "updated_at": now}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Élément introuvable")
    return {"ok": True, "status": status}
