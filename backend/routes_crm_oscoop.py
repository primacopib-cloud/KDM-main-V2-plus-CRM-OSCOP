"""
CRM O'SCOP Bridge for KDMARCHÉ / LOLODRIVE by O'SCOP.

But: keep KDM V2 as the transactional source of truth (PASS, UC, orders, payments, POS).
This bridge provides the CRM layer for recruitment, follow-up, contracts and impact:
- Contacts
- Organizations
- Opportunities
- Dossiers
- Tasks / reminders
- CRM sync events from LOLODRIVE
- Impact reporting for cooperative board / investors

Namespace: /api/crm/*
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from auth import get_current_user_id

logger = logging.getLogger(__name__)
crm_router = APIRouter(prefix="/api/crm", tags=["CRM O'SCOP Bridge"])

db = None

def set_crm_database(database):
    global db
    db = database

# -----------------------
# Models
# -----------------------

class ContactCreate(BaseModel):
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    nom: str = ""
    prenom: str = ""
    type_acteur: str = "prospect"  # client, fournisseur, lolo_point, institutionnel, investisseur
    source_contact: Optional[str] = None
    statut_relation: str = "nouveau"
    organization_id: Optional[str] = None
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}

class OrganizationCreate(BaseModel):
    raison_sociale: str
    enseigne: Optional[str] = None
    type_structure: str = "prospect"  # entreprise, association, fournisseur, lolo_point, collectivité, partenaire
    email: Optional[str] = None
    telephone: Optional[str] = None
    ville: Optional[str] = None
    territoire: Optional[str] = "Guadeloupe"
    statut_ecosysteme: str = "prospect"
    college_cooperatif: Optional[str] = None
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}

class OpportunityCreate(BaseModel):
    titre: str
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    type_besoin: str = "partenariat"
    produit_vise: Optional[str] = None
    montant_estime_cents: Optional[int] = None
    pipeline_stage: str = "lead_entrant"
    probabilite_conversion: Optional[int] = None
    notes: Optional[str] = None
    tags: List[str] = []

class DossierCreate(BaseModel):
    type_dossier: str  # lolo_point, fournisseur, entreprise_relais, accession, investisseur
    organization_id: Optional[str] = None
    contact_id: Optional[str] = None
    objet_besoin: Optional[str] = None
    statut: str = "ouvert"
    etape_actuelle: str = "qualification"
    niveau_urgence: str = "normale"
    notes: Optional[str] = None
    custom_fields: Dict[str, Any] = {}

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_at: Optional[datetime] = None
    owner_user_id: Optional[str] = None
    related_type: Optional[str] = None
    related_id: Optional[str] = None
    status: str = "todo"
    priority: str = "normal"

class SyncEvent(BaseModel):
    event_type: str = Field(..., description="pass.activated | order.paid | lolo_point.created | partner.created | event.created | accession.submitted")
    payload: Dict[str, Any] = {}

# -----------------------
# Helpers
# -----------------------

async def get_current_user(user_id: str = Depends(get_current_user_id)) -> dict:
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    role = user.get("role") or user.get("user_role") or user.get("role_v2")
    if not (user.get("is_admin") or role in ["oscop_super_admin", "kdm_b2b_admin", "admin", "ADMIN", "SUPER_ADMIN", "COOP_BOARD"]):
        raise HTTPException(status_code=403, detail="Accès admin requis")
    return user

def clean(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    d.pop("_id", None)
    return d

def now() -> datetime:
    return datetime.utcnow()

def new_id() -> str:
    return str(uuid.uuid4())

async def upsert_contact_from_user(user: dict, source: str = "lolodrive") -> dict:
    email = user.get("email")
    phone = user.get("phone") or user.get("telephone")
    query = {"$or": []}
    if email: query["$or"].append({"email": email})
    if phone: query["$or"].append({"telephone": phone})
    if not query["$or"]:
        query = {"external_user_id": user.get("id")}

    existing = await db.crm_contacts.find_one(query)
    doc = {
        "external_user_id": user.get("id"),
        "email": email,
        "telephone": phone,
        "nom": user.get("last_name") or user.get("nom") or "",
        "prenom": user.get("first_name") or user.get("prenom") or user.get("contact_name") or "",
        "type_acteur": "client_pass",
        "source_contact": source,
        "statut_relation": "actif",
        "tags": list(set((existing or {}).get("tags", []) + ["PASS_VIE_CHERE", "KDMARCHE"])),
        "updated_at": now(),
    }
    if existing:
        await db.crm_contacts.update_one({"id": existing["id"]}, {"$set": doc})
        existing.update(doc)
        return clean(existing)
    doc.update({"id": new_id(), "created_at": now()})
    await db.crm_contacts.insert_one(doc)
    return clean(doc)

async def crm_record_event(database, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Public helper callable from transactional routes. Uses passed database to avoid circular state."""
    event_doc = {"id": new_id(), "event_type": event_type, "payload": payload, "created_at": now()}
    await database.crm_sync_events.insert_one(event_doc)

    # Lightweight CRM automation
    try:
        if event_type == "pass.activated":
            user_id = payload.get("user_id")
            user = await database.users.find_one({"id": user_id}) if user_id else None
            if user:
                # Upsert contact directly on passed database
                email = user.get("email")
                phone = user.get("phone") or user.get("telephone")
                q = {"external_user_id": user_id}
                existing = await database.crm_contacts.find_one(q)
                contact = {
                    "external_user_id": user_id,
                    "email": email,
                    "telephone": phone,
                    "nom": user.get("last_name") or user.get("nom") or "",
                    "prenom": user.get("first_name") or user.get("prenom") or user.get("contact_name") or "",
                    "type_acteur": "client_pass",
                    "source_contact": "pass.activated",
                    "statut_relation": "actif",
                    "tags": list(set((existing or {}).get("tags", []) + ["PASS_VIE_CHERE", "KDMARCHE"])),
                    "last_pass_activation_at": now(),
                    "updated_at": now(),
                }
                if existing:
                    await database.crm_contacts.update_one({"id": existing["id"]}, {"$set": contact})
                else:
                    contact.update({"id": new_id(), "created_at": now()})
                    await database.crm_contacts.insert_one(contact)

        elif event_type == "lolo_point.created":
            point = payload
            org = {
                "id": new_id(),
                "raison_sociale": point.get("name") or point.get("code") or "Lolo Point",
                "enseigne": point.get("name"),
                "type_structure": "lolo_point_cooperatif",
                "ville": point.get("city"),
                "territoire": "Guadeloupe",
                "statut_ecosysteme": "actif",
                "college_cooperatif": "Relais commerciaux coopératifs",
                "external_lolo_point_id": point.get("id"),
                "tags": ["LOLO_POINT", "COOPERATEUR", "KDMARCHE"],
                "created_at": now(), "updated_at": now(),
            }
            await database.crm_organizations.update_one({"external_lolo_point_id": point.get("id")}, {"$set": org, "$setOnInsert": {"id": org["id"], "created_at": org["created_at"]}}, upsert=True)
            dossier = {
                "id": new_id(), "type_dossier": "lolo_point_cooperatif", "objet_besoin": "Onboarding Lolo Point Coopératif",
                "statut": "ouvert", "etape_actuelle": "convention_a_signer", "external_lolo_point_id": point.get("id"),
                "created_at": now(), "updated_at": now(),
            }
            await database.crm_dossiers.insert_one(dossier)

        elif event_type == "partner.created":
            partner = payload
            await database.crm_organizations.update_one(
                {"external_partner_id": partner.get("id")},
                {"$set": {"raison_sociale": partner.get("name"), "enseigne": partner.get("name"), "type_structure": "fournisseur_partenaire", "statut_ecosysteme": "prospect", "external_partner_id": partner.get("id"), "tags": ["FOURNISSEUR", "LOLO_HOUR"], "updated_at": now()}, "$setOnInsert": {"id": new_id(), "created_at": now()}},
                upsert=True,
            )

        elif event_type == "event.created":
            ev = payload
            opp = {"id": new_id(), "titre": f"Sponsor / activation : {ev.get('title')}", "type_besoin": "sponsor_lolo_hour", "produit_vise": ev.get("title"), "pipeline_stage": "activation_planifiee", "external_event_id": ev.get("id"), "tags": ["LOLO_HOUR", "SPONSOR"], "created_at": now(), "updated_at": now()}
            await database.crm_opportunities.insert_one(opp)
    except Exception as e:
        logger.warning(f"CRM automation failed for {event_type}: {e}")

    event_doc.pop("_id", None)
    return event_doc

# -----------------------
# Health
# -----------------------

@crm_router.get("/health")
async def health():
    return {"status": "ok", "module": "crm_oscoop_bridge", "purpose": "relationnel/cooperatif/impact"}

# -----------------------
# Contacts
# -----------------------

@crm_router.post("/contacts")
async def create_contact(request: ContactCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": new_id(), "created_at": now(), "updated_at": now()})
    await db.crm_contacts.insert_one(doc)
    return clean(doc)

@crm_router.get("/contacts")
async def list_contacts(q: Optional[str] = None, type_acteur: Optional[str] = None, limit: int = 100, admin: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if type_acteur: query["type_acteur"] = type_acteur
    if q:
        query["$or"] = [{"email": {"$regex": q, "$options": "i"}}, {"nom": {"$regex": q, "$options": "i"}}, {"prenom": {"$regex": q, "$options": "i"}}, {"telephone": {"$regex": q, "$options": "i"}}]
    docs = await db.crm_contacts.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"contacts": docs}

@crm_router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str, admin: dict = Depends(require_admin)):
    doc = await db.crm_contacts.find_one({"id": contact_id}, {"_id": 0})
    if not doc: raise HTTPException(status_code=404, detail="Contact introuvable")
    return doc

# -----------------------
# Organizations
# -----------------------

@crm_router.post("/organizations")
async def create_org(request: OrganizationCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": new_id(), "created_at": now(), "updated_at": now()})
    await db.crm_organizations.insert_one(doc)
    return clean(doc)

@crm_router.get("/organizations")
async def list_orgs(q: Optional[str] = None, type_structure: Optional[str] = None, limit: int = 100, admin: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if type_structure: query["type_structure"] = type_structure
    if q:
        query["$or"] = [{"raison_sociale": {"$regex": q, "$options": "i"}}, {"enseigne": {"$regex": q, "$options": "i"}}, {"email": {"$regex": q, "$options": "i"}}]
    docs = await db.crm_organizations.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"organizations": docs}

# -----------------------
# Opportunities
# -----------------------

@crm_router.post("/opportunities")
async def create_opp(request: OpportunityCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": new_id(), "created_at": now(), "updated_at": now()})
    await db.crm_opportunities.insert_one(doc)
    return clean(doc)

@crm_router.get("/opportunities")
async def list_opps(stage: Optional[str] = None, type_besoin: Optional[str] = None, limit: int = 100, admin: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if stage: query["pipeline_stage"] = stage
    if type_besoin: query["type_besoin"] = type_besoin
    docs = await db.crm_opportunities.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"opportunities": docs}


@crm_router.patch("/opportunities/{opp_id}/stage")
async def update_opp_stage(opp_id: str, payload: dict, admin: dict = Depends(require_admin)):
    stage = (payload or {}).get("stage")
    if not stage:
        raise HTTPException(status_code=400, detail="stage requis")
    r = await db.crm_opportunities.update_one({"id": opp_id}, {"$set": {"pipeline_stage": stage, "updated_at": now()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Opportunité introuvable")
    return {"ok": True, "opp_id": opp_id, "stage": stage}

# -----------------------
# Dossiers
# -----------------------

@crm_router.post("/dossiers")
async def create_dossier(request: DossierCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": new_id(), "created_at": now(), "updated_at": now()})
    await db.crm_dossiers.insert_one(doc)
    return clean(doc)

@crm_router.get("/dossiers")
async def list_dossiers(type_dossier: Optional[str] = None, statut: Optional[str] = None, limit: int = 100, admin: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if type_dossier: query["type_dossier"] = type_dossier
    if statut: query["statut"] = statut
    docs = await db.crm_dossiers.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return {"dossiers": docs}

# -----------------------
# Tasks / reminders
# -----------------------

@crm_router.post("/tasks")
async def create_task(request: TaskCreate, admin: dict = Depends(require_admin)):
    doc = request.dict()
    doc.update({"id": new_id(), "created_at": now(), "updated_at": now()})
    await db.crm_tasks.insert_one(doc)
    return clean(doc)

@crm_router.get("/tasks")
async def list_tasks(status: Optional[str] = None, due_only: bool = False, admin: dict = Depends(require_admin)):
    query: Dict[str, Any] = {}
    if status: query["status"] = status
    if due_only: query["due_at"] = {"$lte": now() + timedelta(days=7)}
    docs = await db.crm_tasks.find(query, {"_id": 0}).sort("due_at", 1).limit(200).to_list(200)
    return {"tasks": docs}


@crm_router.patch("/tasks/{task_id}/status")
async def update_task_status(task_id: str, payload: dict, admin: dict = Depends(require_admin)):
    status_v = (payload or {}).get("status")
    if status_v not in ("todo", "in_progress", "done", "cancelled"):
        raise HTTPException(status_code=400, detail="status invalide")
    r = await db.crm_tasks.update_one({"id": task_id}, {"$set": {"status": status_v, "updated_at": now()}})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return {"ok": True, "task_id": task_id, "status": status_v}


@crm_router.patch("/dossiers/{dossier_id}/status")
async def update_dossier_status(dossier_id: str, payload: dict, admin: dict = Depends(require_admin)):
    statut = (payload or {}).get("statut")
    if not statut:
        raise HTTPException(status_code=400, detail="statut requis")
    upd = {"statut": statut, "updated_at": now()}
    if (payload or {}).get("etape_actuelle"):
        upd["etape_actuelle"] = payload["etape_actuelle"]
    r = await db.crm_dossiers.update_one({"id": dossier_id}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dossier introuvable")
    return {"ok": True, "dossier_id": dossier_id, "statut": statut}

# -----------------------
# Sync / Events bridge
# -----------------------

@crm_router.post("/sync/event")
async def sync_event(request: SyncEvent, admin: dict = Depends(require_admin)):
    return await crm_record_event(db, request.event_type, request.payload)

@crm_router.post("/sync/rebuild-from-lolodrive")
async def rebuild_from_lolodrive(admin: dict = Depends(require_admin)):
    created = {"contacts": 0, "organizations": 0, "opportunities": 0}

    passes = await db.lolodrive_passes.find({"status": "ACTIVE"}).to_list(50000)
    for p in passes:
        user = await db.users.find_one({"id": p.get("user_id")})
        if user:
            await upsert_contact_from_user(user, source="rebuild.pass")
            created["contacts"] += 1

    points = await db.lolodrive_points.find({}).to_list(50000)
    for point in points:
        await crm_record_event(db, "lolo_point.created", point)
        created["organizations"] += 1

    partners = await db.lolodrive_partners.find({}).to_list(50000)
    for partner in partners:
        await crm_record_event(db, "partner.created", partner)
        created["organizations"] += 1

    events = await db.lolodrive_events.find({}).to_list(50000)
    for ev in events:
        await crm_record_event(db, "event.created", ev)
        created["opportunities"] += 1

    return {"ok": True, "rebuilt": created}

# -----------------------
# Impact / KPI CRM
# -----------------------

@crm_router.get("/impact/summary")
async def impact_summary(admin: dict = Depends(require_admin)):
    pass_active = await db.lolodrive_passes.count_documents({"status": "ACTIVE", "ends_at": {"$gt": now()}})
    lolo_points = await db.lolodrive_points.count_documents({"status": "ACTIVE"})
    partners = await db.lolodrive_partners.count_documents({})
    opportunities = await db.crm_opportunities.count_documents({})
    dossiers = await db.crm_dossiers.count_documents({})
    contacts = await db.crm_contacts.count_documents({})
    orders = await db.lolodrive_orders.find({"status": {"$in": ["PAID", "PREPARING", "READY", "FULFILLED"]}}).to_list(100000)
    revenue = sum(o.get("total_cents", 0) for o in orders)
    uc_paid_orders = len([o for o in orders if o.get("pay_with_uc")])
    return {
        "pass_active": pass_active,
        "lolo_points_active": lolo_points,
        "partners": partners,
        "crm_contacts": contacts,
        "crm_opportunities": opportunities,
        "crm_dossiers": dossiers,
        "orders_paid": len(orders),
        "revenue_cents": revenue,
        "orders_paid_uc": uc_paid_orders,
        "impact_positioning": "V2 vend/encaisse/livre/pilote les UC ; CRM recrute/suit/contractualise/prouve l’impact.",
    }

# -----------------------
# Indexes
# -----------------------

async def ensure_crm_indexes(database):
    await database.crm_contacts.create_index("id", unique=True)
    await database.crm_contacts.create_index("email")
    await database.crm_contacts.create_index("external_user_id")
    await database.crm_contacts.create_index("type_acteur")
    await database.crm_organizations.create_index("id", unique=True)
    await database.crm_organizations.create_index("external_lolo_point_id")
    await database.crm_organizations.create_index("external_partner_id")
    await database.crm_organizations.create_index("type_structure")
    await database.crm_opportunities.create_index("id", unique=True)
    await database.crm_opportunities.create_index("pipeline_stage")
    await database.crm_dossiers.create_index("id", unique=True)
    await database.crm_dossiers.create_index("type_dossier")
    await database.crm_tasks.create_index("id", unique=True)
    await database.crm_tasks.create_index("due_at")
    await database.crm_sync_events.create_index("id", unique=True)
    await database.crm_sync_events.create_index("event_type")
    await database.crm_sync_events.create_index("created_at")
