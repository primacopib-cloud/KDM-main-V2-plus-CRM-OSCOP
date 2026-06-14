"""
KDMARCHE × O'SCOP - B2B API Routes
Endpoints publics B2B pour le checkout avec options de préparation
Conforme OpenAPI 3.0 - Contrôlé par ABAC Policy
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from abac_policy import (
    PrepOptionsPolicy, KDMarcheAccessPolicyV2,
    build_zones_config_from_db
)

logger = logging.getLogger(__name__)

# Router
b2b_router = APIRouter(prefix="/api/v1/b2b")

# Database reference
db = None


def set_b2b_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== PYDANTIC MODELS (OpenAPI aligned) ==============

class ZoneSummary(BaseModel):
    code: str
    label: str
    kind: str
    currency: str = "EUR"
    vat_rate: float
    exw_only: bool = True
    pickup_required: bool = True


class PrepOptionSLA(BaseModel):
    lead_time_hours: int = 0


class PrepOptionPublic(BaseModel):
    enabled: bool
    pricing_mode: str
    unit_price_ht: float
    unit_label: str
    min_qty: int = 1
    max_qty: int = 999999
    includes: List[str] = []
    excludes: List[str] = []
    sla: PrepOptionSLA = PrepOptionSLA()
    description: Optional[str] = None


class ZonePrepOptionsResponse(BaseModel):
    zone: ZoneSummary
    prep_options: Dict[str, PrepOptionPublic]


class PrepSelection(BaseModel):
    code: str
    qty: int = Field(..., ge=1)


class ApplyPrepOptionsRequest(BaseModel):
    zone_code: str
    selections: List[PrepSelection]
    org_id: Optional[str] = None
    roles: List[str] = ["CUSTOMER_ORG_BUYER"]


class AppliedPrepLine(BaseModel):
    code: str
    label: str
    qty: int
    unit_price_ht: float
    total_ht: float


class ApplyPrepOptionsResponse(BaseModel):
    zone_code: str
    lines: List[AppliedPrepLine]
    fees_subtotal_ht: float
    policy_result: Optional[Dict] = None


class CheckoutQuoteRequest(BaseModel):
    zone_code: str
    goods_subtotal_ht: float
    prep_lines: List[AppliedPrepLine] = []


class CheckoutQuoteResponse(BaseModel):
    zone_code: str
    vat_rate: float
    vat_exonerated: bool = False
    goods_subtotal_ht: float
    fees_subtotal_ht: float
    total_ht: float
    vat_amount: float
    total_ttc: float


# ============== OPA CACHE MANAGEMENT ==============

async def regenerate_opa_cache():
    """
    Régénère le cache OPA zones_config depuis la DB.
    Appelé après chaque modification de zone/option.
    """
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    options = await db.zone_preparation_options.find({"is_active": True}, {"_id": 0}).to_list(500)
    
    zones_config = build_zones_config_from_db(zones, options)
    
    # OPA bundle format (minimal: enabled + bornes + mode)
    opa_bundle = {"zones_config": {}}
    
    for zone_code, zone_data in zones_config.items():
        opa_bundle["zones_config"][zone_code] = {
            "prep_options": {}
        }
        for opt_code, opt_data in zone_data.get("prep_options", {}).items():
            opa_bundle["zones_config"][zone_code]["prep_options"][opt_code] = {
                "enabled": opt_data.get("enabled", False),
                "min_qty": opt_data.get("min_qty", 1),
                "max_qty": opt_data.get("max_qty", 999999),
                "pricing_mode": opt_data.get("pricing_mode", "ORDER")
            }
    
    # Store in cache collection
    await db.kdm_opa_cache.update_one(
        {"cache_key": "zones_config"},
        {
            "$set": {
                "payload": opa_bundle,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {
                "cache_key": "zones_config",
                "created_at": datetime.utcnow()
            }
        },
        upsert=True
    )
    
    logger.info("OPA cache regenerated")
    return opa_bundle


async def get_opa_cache():
    """Récupère le cache OPA ou le régénère si absent."""
    cache = await db.kdm_opa_cache.find_one({"cache_key": "zones_config"}, {"_id": 0})
    if not cache:
        return await regenerate_opa_cache()
    return cache.get("payload", {})


# ============== B2B ENDPOINTS ==============

@b2b_router.get("/zones", tags=["ZonesB2B"])
async def list_b2b_zones():
    """
    Liste des zones actives B2B.
    
    GET /v1/b2b/zones
    """
    zones = await db.kdm_zones.find(
        {"is_active": True},
        {"_id": 0, "id": 0, "created_at": 0, "updated_at": 0}
    ).sort("code", 1).to_list(100)
    
    return {
        "zones": [
            ZoneSummary(
                code=z["code"],
                label=z["label"],
                kind=z.get("kind", "OM"),
                currency=z.get("currency", "EUR"),
                vat_rate=z.get("vat_rate", 0),
                exw_only=z.get("exw_only", True),
                pickup_required=z.get("pickup_required", True)
            ).dict()
            for z in zones
        ]
    }


@b2b_router.get("/zones/{zone_code}/prep-options", response_model=ZonePrepOptionsResponse, tags=["PrepOptionsB2B"])
async def get_zone_prep_options_b2b(zone_code: str):
    """
    Options de préparation disponibles (enabled=true) pour une zone.
    
    GET /v1/b2b/zones/{zone_code}/prep-options
    """
    zone_code = zone_code.upper()
    
    # Get zone
    zone = await db.kdm_zones.find_one(
        {"code": zone_code, "is_active": True},
        {"_id": 0}
    )
    if not zone:
        raise HTTPException(
            status_code=404,
            detail={"error": "ZONE_NOT_FOUND", "details": [f"Zone {zone_code} non trouvée"]}
        )
    
    # Get enabled options
    options = await db.zone_preparation_options.find(
        {"zone_code": zone_code, "is_active": True, "enabled": True},
        {"_id": 0}
    ).sort("sort_order", 1).to_list(50)
    
    # Build response
    zone_summary = ZoneSummary(
        code=zone["code"],
        label=zone["label"],
        kind=zone.get("kind", "OM"),
        currency=zone.get("currency", "EUR"),
        vat_rate=zone.get("vat_rate", 0),
        exw_only=zone.get("exw_only", True),
        pickup_required=zone.get("pickup_required", True)
    )
    
    prep_options = {}
    for opt in options:
        code = opt.get("code", opt.get("preparation_type"))
        prep_options[code] = PrepOptionPublic(
            enabled=opt.get("enabled", False),
            pricing_mode=opt.get("pricing_mode", "ORDER"),
            unit_price_ht=opt.get("price_ht_cents", 0) / 100.0,
            unit_label=opt.get("unit_label", "unité"),
            min_qty=opt.get("min_qty", 1),
            max_qty=opt.get("max_qty", 999999),
            includes=opt.get("includes", []),
            excludes=opt.get("excludes", []),
            sla=PrepOptionSLA(lead_time_hours=opt.get("sla_lead_time_hours", 0)),
            description=opt.get("description")
        )
    
    return ZonePrepOptionsResponse(zone=zone_summary, prep_options=prep_options)


@b2b_router.post("/cart/prep-options/apply", response_model=ApplyPrepOptionsResponse, tags=["PrepOptionsB2B"])
async def apply_prep_options_b2b(request: ApplyPrepOptionsRequest):
    """
    Appliquer des options de préparation au panier.
    Contrôlé par OPA policy: kdm.prep_options.apply
    
    POST /v1/b2b/cart/prep-options/apply
    """
    zone_code = request.zone_code.upper()
    
    # Get OPA cache for policy evaluation (zones_config currently unused — see build_zones_config_from_db below).
    await get_opa_cache()
    
    # Build full config for policy (with detailed options)
    zones = await db.kdm_zones.find({"is_active": True}, {"_id": 0}).to_list(100)
    options = await db.zone_preparation_options.find({"is_active": True}, {"_id": 0}).to_list(500)
    full_config = build_zones_config_from_db(zones, options)
    
    # Evaluate ABAC policy
    policy = KDMarcheAccessPolicyV2(full_config)
    policy_result = policy.evaluate(
        action="kdm.prep_options.apply",
        resource={
            "org_id": request.org_id,
            "zone_id": zone_code,
            "selections": [{"code": s.code, "qty": s.qty} for s in request.selections]
        },
        subject={
            "org_id": request.org_id,
            "roles": request.roles
        }
    )
    
    if not policy_result.get("allow"):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "POLICY_DENIED",
                "deny": policy_result.get("deny_reasons", []),
                "details": policy_result.get("deny_reasons", [])
            }
        )
    
    # Calculate lines
    lines = []
    fees_subtotal_ht = 0.0
    
    for selection in request.selections:
        opt = await db.zone_preparation_options.find_one({
            "zone_code": zone_code,
            "code": selection.code,
            "enabled": True
        }, {"_id": 0})
        
        if opt:
            unit_price_ht = opt.get("price_ht_cents", 0) / 100.0
            total_ht = unit_price_ht * selection.qty
            
            lines.append(AppliedPrepLine(
                code=selection.code,
                label=opt.get("name", selection.code),
                qty=selection.qty,
                unit_price_ht=unit_price_ht,
                total_ht=total_ht
            ))
            
            fees_subtotal_ht += total_ht
    
    return ApplyPrepOptionsResponse(
        zone_code=zone_code,
        lines=lines,
        fees_subtotal_ht=round(fees_subtotal_ht, 2),
        policy_result=policy_result
    )


@b2b_router.post("/checkout/quote", response_model=CheckoutQuoteResponse, tags=["CheckoutB2B"])
async def checkout_quote_b2b(request: CheckoutQuoteRequest):
    """
    Calculer un devis checkout (HT/TVA/TTC).
    
    POST /v1/b2b/checkout/quote
    """
    zone_code = request.zone_code.upper()
    
    # Get zone for VAT rate
    zone = await db.kdm_zones.find_one(
        {"code": zone_code, "is_active": True},
        {"_id": 0}
    )
    if not zone:
        raise HTTPException(
            status_code=400,
            detail={"error": "ZONE_NOT_FOUND", "details": [f"Zone {zone_code} non trouvée"]}
        )
    
    vat_rate = zone.get("vat_rate", 0) / 100.0  # Convert from percentage
    vat_exonerated = vat_rate == 0
    
    # Calculate fees subtotal
    fees_subtotal_ht = sum(line.total_ht for line in request.prep_lines)
    
    # Calculate totals
    total_ht = request.goods_subtotal_ht + fees_subtotal_ht
    vat_amount = 0 if vat_exonerated else round(total_ht * vat_rate, 2)
    total_ttc = round(total_ht + vat_amount, 2)
    
    return CheckoutQuoteResponse(
        zone_code=zone_code,
        vat_rate=zone.get("vat_rate", 0),
        vat_exonerated=vat_exonerated,
        goods_subtotal_ht=round(request.goods_subtotal_ht, 2),
        fees_subtotal_ht=round(fees_subtotal_ht, 2),
        total_ht=round(total_ht, 2),
        vat_amount=vat_amount,
        total_ttc=total_ttc
    )


# ============== OPA CACHE ENDPOINTS ==============

@b2b_router.get("/opa/cache", tags=["OPA"])
async def get_opa_cache_endpoint():
    """
    Récupère le cache OPA zones_config.
    Utilisé par OPA pour charger les données.
    
    GET /v1/b2b/opa/cache
    """
    cache = await get_opa_cache()
    return cache


@b2b_router.post("/opa/regenerate", tags=["OPA"])
async def regenerate_opa_cache_endpoint():
    """
    Force la régénération du cache OPA.
    Appelé manuellement ou par cron.
    
    POST /v1/b2b/opa/regenerate
    """
    bundle = await regenerate_opa_cache()
    return {
        "message": "OPA cache regenerated",
        "zones_count": len(bundle.get("zones_config", {})),
        "regenerated_at": datetime.utcnow().isoformat()
    }


# ============== INTERNAL: Auto-regenerate OPA cache on zone/option changes ==============

async def trigger_opa_cache_regen():
    """
    Trigger pour régénérer le cache OPA.
    À appeler après INSERT/UPDATE/DELETE sur zones ou options.
    """
    try:
        await regenerate_opa_cache()
    except Exception as e:
        logger.error(f"Failed to regenerate OPA cache: {e}")
