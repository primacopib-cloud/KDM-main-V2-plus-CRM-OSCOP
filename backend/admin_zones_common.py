"""KDMARCHE Admin Zones — Helpers partagés (split from routes_admin_zones.py)."""
import logging

from schema_preparation import DEFAULT_ZONES, DEFAULT_ZONE_PREPARATION_OPTIONS, ZoneInDB, ZonePreparationOptionInDB

logger = logging.getLogger(__name__)

db = None

def set_admin_zones_common_database(database):
    global db
    db = database

_regen_opa_cache = None


def set_opa_cache_regen_callback(callback):
    """Set callback for OPA cache regeneration"""
    global _regen_opa_cache
    _regen_opa_cache = callback


async def trigger_opa_cache_regen():
    """Trigger OPA cache regeneration after zone/option changes"""
    global _regen_opa_cache
    if _regen_opa_cache:
        await _regen_opa_cache()
    else:
        # Fallback: regenerate directly
        from routes_b2b import regenerate_opa_cache
        await regenerate_opa_cache()


# ============== INITIALIZATION ==============

async def init_zones_and_options():
    """Initialize zones and options if not exist"""
    # Initialize zones
    zones_count = await db.kdm_zones.count_documents({})
    if zones_count == 0:
        logger.info("Initializing default zones...")
        for zone_data in DEFAULT_ZONES:
            zone = ZoneInDB(**zone_data)
            await db.kdm_zones.insert_one(zone.dict())
        logger.info(f"Initialized {len(DEFAULT_ZONES)} zones")
    
    # Initialize options
    options_count = await db.zone_preparation_options.count_documents({})
    if options_count == 0:
        logger.info("Initializing default preparation options...")
        for opt_data in DEFAULT_ZONE_PREPARATION_OPTIONS:
            opt = ZonePreparationOptionInDB(**opt_data)
            if opt.tva_exonerated:
                opt.price_ttc_cents = opt.price_ht_cents
            else:
                opt.price_ttc_cents = int(opt.price_ht_cents * (1 + opt.tva_rate / 100))
            await db.zone_preparation_options.insert_one(opt.dict())
        logger.info(f"Initialized {len(DEFAULT_ZONE_PREPARATION_OPTIONS)} preparation options")


