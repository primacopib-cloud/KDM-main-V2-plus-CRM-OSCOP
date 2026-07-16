"""
KDMARCHE × O'SCOP - Préparation de Commande API Routes
Options de préparation conditionnelles par zone géographique
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from schema_preparation import (
    PreparationType, PricingMode,
    ZonePreparationOptionCreate, ZonePreparationOptionUpdate,
    ZonePreparationOptionResponse, ZonePreparationOptionInDB,
    OrderCalculationRequest, OrderCalculationResponse,
    PreparationSelectionItem,
    DEFAULT_ZONE_PREPARATION_OPTIONS
)

logger = logging.getLogger(__name__)

# Router
preparation_router = APIRouter(prefix="/api/v2/preparation")

# Database reference
db = None


def set_preparation_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== HELPER FUNCTIONS ==============

async def init_default_options():
    """Initialize default preparation options if not exist"""
    count = await db.zone_preparation_options.count_documents({})
    if count == 0:
        logger.info("Initializing default zone preparation options...")
        for opt_data in DEFAULT_ZONE_PREPARATION_OPTIONS:
            opt = ZonePreparationOptionInDB(**opt_data)
            # Calculate TTC
            opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
            await db.zone_preparation_options.insert_one(opt.dict())
        logger.info(f"Initialized {len(DEFAULT_ZONE_PREPARATION_OPTIONS)} preparation options")


async def get_current_user_prep(request):
    """Get current user from token"""
    from auth import decode_token, extract_user_id_from_request
    
    user_id = extract_user_id_from_request(request)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    
    return user


# ============== PUBLIC ENDPOINTS ==============

@preparation_router.get("/options", response_model=List[ZonePreparationOptionResponse])
async def list_preparation_options(
    zone_code: Optional[str] = Query(None, description="Filtrer par code zone"),
    preparation_type: Optional[PreparationType] = Query(None, description="Filtrer par type"),
):
    """
    Liste les options de préparation disponibles.
    Filtrage possible par zone et/ou type.
    """
    # Init defaults if needed
    await init_default_options()
    
    query = {"is_active": True}
    
    if zone_code:
        query["zone_code"] = zone_code
    
    if preparation_type:
        query["preparation_type"] = preparation_type.value
    
    options = await db.zone_preparation_options.find(
        query, {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    
    return [ZonePreparationOptionResponse(**opt) for opt in options]


@preparation_router.get("/options/{zone_code}", response_model=List[ZonePreparationOptionResponse])
async def get_zone_options(zone_code: str):
    """
    Récupère toutes les options de préparation pour une zone spécifique.
    Utile pour afficher les options conditionnelles dans le bon de commande.
    """
    await init_default_options()
    
    options = await db.zone_preparation_options.find(
        {"zone_code": zone_code, "is_active": True},
        {"_id": 0}
    ).sort("sort_order", 1).to_list(100)
    
    if not options:
        raise HTTPException(
            status_code=404, 
            detail=f"Aucune option de préparation pour la zone {zone_code}"
        )
    
    return [ZonePreparationOptionResponse(**opt) for opt in options]


@preparation_router.post("/calculate", response_model=OrderCalculationResponse)
async def calculate_order_total(request: OrderCalculationRequest):
    """
    Calcule le total d'une commande avec les frais de préparation sélectionnés.
    
    - Valide les options sélectionnées pour la zone
    - Calcule les totaux HT/TTC
    - Retourne un récapitulatif complet pour validation serveur
    """
    await init_default_options()
    
    zone_code = request.zone_code
    
    # Validate zone has options
    zone_options = await db.zone_preparation_options.find(
        {"zone_code": zone_code, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    if not zone_options:
        raise HTTPException(
            status_code=400,
            detail=f"Zone {zone_code} non configurée pour la préparation"
        )
    
    options_map = {opt["id"]: opt for opt in zone_options}
    
    # Calculate preparation fees
    preparation_details = []
    preparation_subtotal_ht = 0
    preparation_tva = 0
    
    for selection in request.preparation_selections:
        option_id = selection.get("option_id")
        quantity = selection.get("quantity", 1)
        
        if not option_id:
            continue
        
        if option_id not in options_map:
            raise HTTPException(
                status_code=400,
                detail=f"Option {option_id} non disponible pour la zone {zone_code}"
            )
        
        opt = options_map[option_id]
        
        # Calculate based on pricing mode
        pricing_mode = opt["pricing_mode"]
        unit_price_ht = opt["price_ht_cents"]
        
        if pricing_mode == PricingMode.FIXED.value:
            total_ht = unit_price_ht
        elif pricing_mode == PricingMode.PER_UNIT.value:
            total_ht = unit_price_ht * quantity
        elif pricing_mode == PricingMode.PER_KG.value:
            total_ht = unit_price_ht * quantity
        elif pricing_mode == PricingMode.PERCENTAGE.value:
            # For percentage, price_ht_cents represents the percentage * 100
            # e.g., 1500 = 15%
            percentage = unit_price_ht / 10000  # Convert to decimal
            total_ht = int(request.products_subtotal_ht_cents * percentage)
            unit_price_ht = total_ht  # For display purposes
        else:
            total_ht = unit_price_ht
        
        # Calculate TVA
        tva_rate = opt["tva_rate"]
        item_tva = int(total_ht * tva_rate / 100)
        total_ttc = total_ht + item_tva
        
        preparation_details.append(PreparationSelectionItem(
            option_id=option_id,
            option_name=opt["name"],
            preparation_type=opt["preparation_type"],
            pricing_mode=pricing_mode,
            quantity=quantity,
            unit_price_ht_cents=unit_price_ht,
            total_ht_cents=total_ht,
            tva_rate=tva_rate,
            total_tva_cents=item_tva,
            total_ttc_cents=total_ttc
        ))
        
        preparation_subtotal_ht += total_ht
        preparation_tva += item_tva
    
    preparation_total_ttc = preparation_subtotal_ht + preparation_tva
    
    # Products totals
    products_total_ttc = request.products_subtotal_ht_cents + request.products_tva_cents
    
    # Grand totals
    grand_total_ht = request.products_subtotal_ht_cents + preparation_subtotal_ht
    grand_total_tva = request.products_tva_cents + preparation_tva
    grand_total_ttc = grand_total_ht + grand_total_tva
    
    return OrderCalculationResponse(
        products_subtotal_ht_cents=request.products_subtotal_ht_cents,
        products_tva_cents=request.products_tva_cents,
        products_total_ttc_cents=products_total_ttc,
        preparation_subtotal_ht_cents=preparation_subtotal_ht,
        preparation_tva_cents=preparation_tva,
        preparation_total_ttc_cents=preparation_total_ttc,
        preparation_details=preparation_details,
        grand_total_ht_cents=grand_total_ht,
        grand_total_tva_cents=grand_total_tva,
        grand_total_ttc_cents=grand_total_ttc,
        zone_code=zone_code,
        calculation_timestamp=datetime.utcnow()
    )


# ============== ADMIN ENDPOINTS ==============

@preparation_router.post("/options", response_model=ZonePreparationOptionResponse, status_code=201)
async def create_preparation_option(
    option: ZonePreparationOptionCreate,
    request = None
):
    """Créer une nouvelle option de préparation (admin)"""
    from fastapi import Request
    
    # Check admin (simplified - in production, use proper dependency)
    # user = await get_current_user_prep(request)
    # if not user.get("is_admin"):
    #     raise HTTPException(status_code=403, detail="Admin requis")
    
    opt = ZonePreparationOptionInDB(**option.dict())
    opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
    
    await db.zone_preparation_options.insert_one(opt.dict())
    
    logger.info(f"Created preparation option: {opt.id} for zone {opt.zone_code}")
    
    return ZonePreparationOptionResponse(**opt.dict())


@preparation_router.put("/options/{option_id}", response_model=ZonePreparationOptionResponse)
async def update_preparation_option(
    option_id: str,
    update: ZonePreparationOptionUpdate
):
    """Mettre à jour une option de préparation (admin)"""
    existing = await db.zone_preparation_options.find_one({"id": option_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    
    # Recalculate TTC if price or TVA changed
    if "price_ht_cents" in update_data or "tva_rate" in update_data:
        price_ht = update_data.get("price_ht_cents", existing["price_ht_cents"])
        tva_rate = update_data.get("tva_rate", existing["tva_rate"])
        update_data["price_ttc_cents"] = int(price_ht * (1 + tva_rate / 100))
    
    update_data["updated_at"] = datetime.utcnow()
    
    await db.zone_preparation_options.update_one(
        {"id": option_id},
        {"$set": update_data}
    )
    
    updated = await db.zone_preparation_options.find_one({"id": option_id}, {"_id": 0})
    return ZonePreparationOptionResponse(**updated)


@preparation_router.delete("/options/{option_id}")
async def delete_preparation_option(option_id: str):
    """Désactiver une option de préparation (soft delete)"""
    result = await db.zone_preparation_options.update_one(
        {"id": option_id},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Option non trouvée")
    
    return {"message": "Option désactivée", "option_id": option_id}


@preparation_router.get("/admin/all", response_model=List[ZonePreparationOptionResponse])
async def admin_list_all_options(
    include_inactive: bool = Query(False, description="Inclure les options désactivées")
):
    """Liste toutes les options (admin), y compris les inactives"""
    query = {} if include_inactive else {"is_active": True}
    
    options = await db.zone_preparation_options.find(
        query, {"_id": 0}
    ).sort([("zone_code", 1), ("sort_order", 1)]).to_list(500)
    
    return [ZonePreparationOptionResponse(**opt) for opt in options]


@preparation_router.post("/admin/init-defaults")
async def admin_reinit_defaults():
    """Réinitialiser les options par défaut (admin)"""
    # Delete all existing
    await db.zone_preparation_options.delete_many({})
    
    # Reinit
    for opt_data in DEFAULT_ZONE_PREPARATION_OPTIONS:
        opt = ZonePreparationOptionInDB(**opt_data)
        opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
        await db.zone_preparation_options.insert_one(opt.dict())
    
    return {
        "message": "Options réinitialisées",
        "count": len(DEFAULT_ZONE_PREPARATION_OPTIONS)
    }
