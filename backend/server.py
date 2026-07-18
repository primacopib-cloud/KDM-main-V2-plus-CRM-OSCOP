from fastapi import FastAPI
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from db import set_database as set_shared_database
import os
import logging
from pathlib import Path

from subscriptions import seed_subscription_plans

ROOT_DIR = Path(__file__).parent
# Load .env WITHOUT override: platform-injected vars (MONGO_URL, DB_NAME in production)
# must always win. Only Stripe keys are selectively overridden from .env because the
# preview pod injects a placeholder STRIPE_API_KEY=sk_test_emergent at pod level.
load_dotenv(ROOT_DIR / '.env')
from dotenv import dotenv_values  # noqa: E402
_env_file_values = dotenv_values(ROOT_DIR / '.env')
for _stripe_key in (
    "STRIPE_API_KEY", "STRIPE_LIVE_KEY", "STRIPE_KDMARCHE_API_KEY",
    "STRIPE_KDMARCHE_LIVE_KEY", "STRIPE_WEBHOOK_SECRETS_OSCOP",
    "STRIPE_WEBHOOK_SECRETS_KDMARCHE", "STRIPE_MODE",
):
    if _env_file_values.get(_stripe_key):
        os.environ[_stripe_key] = _env_file_values[_stripe_key]

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'b2b_ess_db')]
set_shared_database(db)

# Create the main app
app = FastAPI(title="Communityplace B2B ESS API")


@app.get("/health")
async def root_health():
    """Root health endpoint for deployment readiness probes."""
    return {"status": "ok"}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============== CORE ROUTES (split from this file into routes_core_*.py) ==============
from routes_core_auth import auth_core_router
from routes_core_users import users_core_router
from routes_core_admin import admin_core_router
from routes_core_notifications import notifications_core_router
from routes_core_orgs import orgs_core_router

app.include_router(auth_core_router)
app.include_router(users_core_router)
app.include_router(admin_core_router)
app.include_router(notifications_core_router)
app.include_router(orgs_core_router)

# Import and include v2 routes (applications & billing split into dedicated modules)
from routes_v2 import api_v2_router, set_database
from routes_v2_applications import applications_v2_router, set_applications_v2_database
from routes_v2_billing import billing_v2_router, set_billing_v2_database
set_database(db)
set_applications_v2_database(db)
set_billing_v2_database(db)
app.include_router(api_v2_router)
app.include_router(applications_v2_router)
app.include_router(billing_v2_router)

# Import and include catalog routes (cart & orders split into dedicated modules)
from routes_catalog import catalog_router, set_catalog_database
from routes_cart_v2 import cart_router, set_cart_database
from routes_orders_v2 import orders_router, set_orders_database
set_catalog_database(db)
set_cart_database(db)
set_orders_database(db)
app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(orders_router)

# Import and include GED (Document Management) routes
from routes_ged import ged_router, set_ged_database
from routes_ged_admin import ged_admin_router
set_ged_database(db)
app.include_router(ged_router)
app.include_router(ged_admin_router)

# Import and include Export routes
from routes_export import export_router, set_export_database
set_export_database(db)
app.include_router(export_router)

# Import and include Payment routes
from routes_payment import payment_router, set_payment_database
from routes_payment_sepa import payment_sepa_router
set_payment_database(db)
app.include_router(payment_router)
app.include_router(payment_sepa_router)

# Import and include SMS Signature routes
from routes_signature import signature_router, set_signature_database
from routes_signature_admin import signature_admin_router
set_signature_database(db)
app.include_router(signature_router)
app.include_router(signature_admin_router)

# Import and include Super Admin routes (activity & advanced stats split into modules)
from routes_superadmin import superadmin_router, set_superadmin_database
from routes_superadmin_activity import superadmin_activity_router, set_superadmin_activity_database
from routes_superadmin_stats import superadmin_stats_router, set_superadmin_stats_database
set_superadmin_database(db)
set_superadmin_activity_database(db)
set_superadmin_stats_database(db)
app.include_router(superadmin_router)
app.include_router(superadmin_activity_router)
app.include_router(superadmin_stats_router)

# Import and include Preparation routes (Zone-based preparation options)
from routes_preparation import preparation_router, set_preparation_database
set_preparation_database(db)
app.include_router(preparation_router)

# Import and include Admin Zones routes (CRUD zones + options)
from routes_admin_zones import admin_zones_router, set_admin_zones_database
from routes_admin_zones_public import admin_zones_public_router
set_admin_zones_database(db)
app.include_router(admin_zones_router)
app.include_router(admin_zones_public_router)

# Import and include B2B routes (checkout + prep options)
from routes_b2b import b2b_router, set_b2b_database
set_b2b_database(db)
app.include_router(b2b_router)

# Import and include Vendor routes (admin endpoints split into routes_vendor_admin)
from routes_vendor import vendor_router, set_vendor_database
from routes_vendor_admin import vendor_admin_router, set_vendor_admin_database
set_vendor_database(db)
set_vendor_admin_database(db)
app.include_router(vendor_router)
app.include_router(vendor_admin_router)

# Import and include OPA Bundle routes
from routes_opa_bundle import opa_bundle_router, set_opa_bundle_database
set_opa_bundle_database(db)
app.include_router(opa_bundle_router)

# Import and include Catalog Admin routes
from routes_catalog_admin import catalog_admin_router, set_catalog_admin_database
set_catalog_admin_database(db)
app.include_router(catalog_admin_router)

# Import and include Invoices routes
from routes_invoices import invoices_router, set_invoices_database
set_invoices_database(db)
app.include_router(invoices_router)

# Import and include Checkout routes
from routes_checkout import checkout_router, set_checkout_database
set_checkout_database(db)
app.include_router(checkout_router)

# Import and include PDF routes
from routes_pdf import pdf_router, set_pdf_database
set_pdf_database(db)
app.include_router(pdf_router)

# Import and include WebSocket routes
from routes_websockets import websocket_router, set_websocket_database
set_websocket_database(db)
app.include_router(websocket_router)

# Import and include LOGI'SCOP routes
from routes_logiscop import logiscop_router, set_logiscop_database
set_logiscop_database(db)
app.include_router(logiscop_router)

# Import and include V1 LOGI'SCOP routes (OpenAPI v1 endpoints)
from routes_v1_logiscop import v1_logiscop_router, set_v1_logiscop_database
from routes_v1_logiscop_orders import v1_logiscop_orders_router
set_v1_logiscop_database(db)
app.include_router(v1_logiscop_router)
app.include_router(v1_logiscop_orders_router)

# Import and include Contracts routes
from routes_contracts import contracts_router, set_contracts_database
set_contracts_database(db)
app.include_router(contracts_router)

# Import and include POD (Proof of Delivery) routes
from routes_pod import pod_router, set_pod_database
from routes_pod_sign import pod_sign_router
set_pod_database(db)
app.include_router(pod_router)
app.include_router(pod_sign_router)

# Import and include ESS Route (Tournées Mutualisées) routes
from routes_ess import ess_router, set_ess_database
set_ess_database(db)
app.include_router(ess_router)

# Import and include Admin ESS Routes (CRUD policies, rules, capacity — split into 3 modules)
from routes_admin_ess import admin_ess_router, set_admin_ess_database
from routes_admin_ess_rules import admin_ess_rules_router, set_admin_ess_rules_database
from routes_admin_ess_capacity import admin_ess_capacity_router, set_admin_ess_capacity_database
set_admin_ess_database(db)
set_admin_ess_rules_database(db)
set_admin_ess_capacity_database(db)
app.include_router(admin_ess_router)
app.include_router(admin_ess_rules_router)
app.include_router(admin_ess_capacity_router)

# Import and include User Preferences Routes (shortcuts)
from routes_user_prefs import user_prefs_router, set_user_prefs_database
from routes_user_prefs_favorites import user_prefs_favorites_router
set_user_prefs_database(db)
app.include_router(user_prefs_router, prefix="/api")
app.include_router(user_prefs_favorites_router, prefix="/api")

# Import and include Notifications History Routes
from routes_notifications_history import notifications_history_router, set_notifications_history_database
set_notifications_history_database(db)
app.include_router(notifications_history_router, prefix="/api")

# Import and include Shopping Lists Routes
from routes_shopping_lists import shopping_lists_router, set_shopping_lists_database
from routes_shopping_lists_items import shopping_lists_items_router
set_shopping_lists_database(db)
app.include_router(shopping_lists_router, prefix="/api")
app.include_router(shopping_lists_items_router, prefix="/api")

# Import and include Super Admin Plans & Credits Routes
from routes_admin_plans import admin_plans_router, set_admin_plans_database
from routes_admin_plans_credits import admin_plans_credits_router
set_admin_plans_database(db)
app.include_router(admin_plans_router, prefix="/api")
app.include_router(admin_plans_credits_router, prefix="/api")


# Import and include LOLODRIVE by O'SCOP routes (PASS Vie Chère, UC, Lolo Points, Events, POS)
from routes_lolodrive_oscoop import lolodrive_router, set_lolodrive_database
from routes_lolodrive_pos import lolodrive_pos_router
from routes_lolodrive_points import lolodrive_points_router
from routes_lolodrive_manager import lolodrive_manager_router
from routes_lolodrive_admin import lolodrive_admin_router, ensure_lolodrive_indexes
set_lolodrive_database(db)
app.include_router(lolodrive_router)
app.include_router(lolodrive_pos_router)
app.include_router(lolodrive_points_router)
app.include_router(lolodrive_manager_router)
app.include_router(lolodrive_admin_router)

# Import and include LOLODRIVE Stripe Checkout (hosted page) for PASS/Recharge/Order
from routes_lolodrive_checkout import (
    checkout_router as lolodrive_checkout_router,
    webhook_router as lolodrive_webhook_router,
    set_checkout_database as set_lolo_checkout_db,
    setup_checkout_indexes,
)
set_lolo_checkout_db(db)
app.include_router(lolodrive_checkout_router)
app.include_router(lolodrive_webhook_router)

# Import and include CRM O'SCOP Bridge routes (contacts, organisations, opportunités, dossiers, impact)
from routes_crm_oscoop import crm_router, set_crm_database, ensure_crm_indexes
set_crm_database(db)
app.include_router(crm_router)

# Import and include Emergent OAuth (Google social login via Emergent platform)
from routes_emergent_auth import router as emergent_auth_router, set_emergent_auth_database, setup_emergent_indexes
set_emergent_auth_database(db)
app.include_router(emergent_auth_router)

# Native Google OAuth (KDMARCHE own Google Cloud project — branding KDMARCHE)
from routes_google_auth import router as google_auth_router, set_google_auth_database, setup_google_auth_indexes
set_google_auth_database(db)
app.include_router(google_auth_router)

# Stripe Reconciliation (admin-only) — aggregated payments across KDMARCHE + O'SCOP accounts
from routes_stripe_reconciliation import (
    reconciliation_router as stripe_reconciliation_router,
    set_reconciliation_database,
)
set_reconciliation_database(db)
app.include_router(stripe_reconciliation_router)
from routes_stripe_health import stripe_health_router, set_stripe_health_database
set_stripe_health_database(db)
app.include_router(stripe_health_router)

# Brevo transactional webhooks (delivered/bounced metrics)
from routes_brevo_webhook import router as brevo_webhook_router, set_brevo_webhook_database, setup_brevo_webhook_indexes
set_brevo_webhook_database(db)
app.include_router(brevo_webhook_router)

# PASS lifecycle (auto-renew, referrals)
from routes_pass_lifecycle import router as pass_lifecycle_router, set_pass_lifecycle_database, setup_pass_lifecycle_indexes
set_pass_lifecycle_database(db)
app.include_router(pass_lifecycle_router)

# PASS Stripe Subscriptions (real recurring rebill)
from routes_pass_subscription import router as pass_subscription_router, set_pass_subscription_database, setup_pass_subscription_indexes
set_pass_subscription_database(db)
app.include_router(pass_subscription_router)

# GED ESS Bridge — connector to the external GED microservice (PostgreSQL/S3/audit)
# Does NOT replace the internal Mongo GED (/api/ged); namespace /api/ged-bridge/*
from routes_ged_bridge import (
    ged_bridge_router,
    set_ged_bridge_database,
    ensure_ged_bridge_indexes,
)
set_ged_bridge_database(db)
app.include_router(ged_bridge_router)

# Finance API Bridge — connector to the external finance-api microservice (PostgreSQL/ledger)
# Namespace /api/finance-bridge/* — admin-only
from routes_finance_bridge import (
    finance_bridge_router,
    set_finance_bridge_database,
    ensure_finance_bridge_indexes,
)
set_finance_bridge_database(db)
app.include_router(finance_bridge_router)

# Socle Connecteurs unifiés (multi-apps) — /api/connectors/*
from admin_guard import set_admin_guard_database
from connectors.base import set_connectors_database, ensure_connectors_indexes
from connectors.auto_sync import set_auto_sync_database
from routes_connectors import connectors_router, set_connectors_routes_database
set_admin_guard_database(db)
set_connectors_database(db)
set_auto_sync_database(db)
set_connectors_routes_database(db)
app.include_router(connectors_router)
from connectors.iabois_sync import set_iabois_sync_database
set_iabois_sync_database(db)
from connectors.iabois_quotes import set_iabois_quotes_database
from connectors.health_watch import set_health_watch_database
set_iabois_quotes_database(db)
set_health_watch_database(db)
from routes_team_roles import team_router, set_team_roles_database
set_team_roles_database(db)
app.include_router(team_router)
from routes_taxonomy import taxonomy_router, set_taxonomy_database, seed_taxonomy
set_taxonomy_database(db)
app.include_router(taxonomy_router)
from routes_team_space import team_space_router, admin_buyers_router, set_team_space_database
set_team_space_database(db)
app.include_router(team_space_router)
app.include_router(admin_buyers_router)
from fastapi.staticfiles import StaticFiles
_uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(os.path.join(_uploads_dir, "products"), exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

# Alertes favoris (restock/promo) + routes admin stock & prix
from favorites_alerts import set_favorites_alerts_database
from routes_stock_admin import stock_admin_router, set_stock_admin_database
set_favorites_alerts_database(db)
set_stock_admin_database(db)
app.include_router(stock_admin_router)

# Centre d'alertes favoris (préférences par produit + historique)
from routes_favorites_alerts_center import favorites_alerts_center_router, set_favorites_alerts_center_database
set_favorites_alerts_center_database(db)
app.include_router(favorites_alerts_center_router, prefix="/api")

# Background scheduler (PASS J-3 reminders every 6h)
from scheduler import set_scheduler_database, start_scheduler, stop_scheduler
set_scheduler_database(db)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_db_client():
    """Create indexes on startup."""
    # Create unique index on email
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.quote_requests.create_index("id", unique=True)
    # Phase 1 & 2: Additional indexes
    await db.notifications.create_index("id", unique=True)
    await db.notifications.create_index("created_at")
    await db.organizations.create_index("id", unique=True)
    await db.organizations.create_index("siret", unique=True)
    await db.zones.create_index("id", unique=True)
    await db.zones.create_index("code", unique=True)

    # v2 Schema indexes
    await db.orgs.create_index("id", unique=True)
    await db.orgs.create_index([("registration_country", 1), ("registration_id", 1)], unique=True)
    await db.users_v2.create_index("id", unique=True)
    await db.users_v2.create_index("email", unique=True)
    await db.org_memberships.create_index("id", unique=True)
    await db.org_memberships.create_index([("org_id", 1), ("user_id", 1)], unique=True)
    await db.b2b_applications.create_index("id", unique=True)
    await db.b2b_applications.create_index("org_id")
    await db.application_documents.create_index("id", unique=True)
    await db.plans.create_index("id", unique=True)
    await db.plans.create_index("code", unique=True)
    await db.subscriptions.create_index("id", unique=True)
    await db.subscriptions.create_index("org_id")
    await db.billing_invoices.create_index("id", unique=True)
    await db.wallets.create_index("org_id", unique=True)
    await db.wallet_ledger.create_index("id", unique=True)
    await db.wallet_ledger.create_index([("org_id", 1), ("correlation_id", 1)], unique=True)
    await db.zones_v2.create_index("id", unique=True)
    await db.zones_v2.create_index("code", unique=True)
    await db.org_zone_entitlements.create_index("id", unique=True)
    await db.org_zone_entitlements.create_index([("org_id", 1), ("zone_id", 1)], unique=True)
    await db.partner_accounts.create_index("id", unique=True)
    await db.partner_accounts.create_index([("org_id", 1), ("partner", 1)], unique=True)
    await db.audit_log.create_index("id", unique=True)
    await db.audit_log.create_index([("org_id", 1), ("created_at", -1)])
    await db.outbox_events.create_index("id", unique=True)

    # Catalog indexes
    await db.categories.create_index("id", unique=True)
    await db.categories.create_index("code", unique=True)
    await db.products.create_index("id", unique=True)
    await db.products.create_index("sku", unique=True)
    await db.products.create_index("category_id")
    await db.products.create_index([("name", "text"), ("description", "text")])
    await db.zone_prices.create_index("id", unique=True)
    await db.zone_prices.create_index([("product_id", 1), ("zone_code", 1)], unique=True)
    await db.zone_stocks.create_index("id", unique=True)
    await db.zone_stocks.create_index([("product_id", 1), ("zone_code", 1)], unique=True)
    await db.pickup_locations.create_index("id", unique=True)
    await db.pickup_locations.create_index("zone_code")
    await db.carts.create_index("id", unique=True)
    await db.carts.create_index([("org_id", 1), ("zone_code", 1), ("status", 1)])
    await db.orders.create_index("id", unique=True)
    await db.orders.create_index("order_number", unique=True)
    await db.orders.create_index("org_id")

    # Preparation options indexes
    await db.zone_preparation_options.create_index("id", unique=True)
    await db.zone_preparation_options.create_index([("zone_code", 1), ("preparation_type", 1)])
    await db.zone_preparation_options.create_index([("zone_code", 1), ("code", 1)])

    # OPA cache index
    await db.kdm_opa_cache.create_index("cache_key", unique=True)

    # Vendor indexes
    await db.vendors.create_index("id", unique=True)
    await db.vendors.create_index("email", unique=True)
    await db.vendors.create_index("siret", unique=True)
    await db.vendor_products.create_index("id", unique=True)
    await db.vendor_products.create_index([("vendor_id", 1), ("sku", 1)], unique=True)

    # Super Admin: subscription plans, options, credits
    await db.subscription_plans.create_index("id", unique=True)
    await db.subscription_plans.create_index("slug", unique=True)
    await db.plan_options.create_index("id", unique=True)
    await db.credit_history.create_index("id", unique=True)
    await db.credit_history.create_index([("user_id", 1), ("created_at", -1)])

    # LOLODRIVE by O'SCOP indexes
    try:
        await ensure_lolodrive_indexes(db)
        logger.info("LOLODRIVE indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create LOLODRIVE indexes: {e}")

    # Stripe Checkout indexes (payment_transactions)
    try:
        await setup_checkout_indexes(db)
        logger.info("LOLODRIVE Checkout indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create LOLODRIVE Checkout indexes: {e}")

    # CRM O'SCOP Bridge indexes
    try:
        await ensure_crm_indexes(db)
        logger.info("CRM O'SCOP indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create CRM O'SCOP indexes: {e}")

    # Emergent OAuth indexes + start background scheduler
    try:
        await setup_emergent_indexes(db)
        logger.info("Emergent OAuth indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Emergent OAuth indexes: {e}")
    try:
        await setup_google_auth_indexes(db)
        logger.info("Native Google OAuth indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Google OAuth indexes: {e}")
    try:
        await setup_brevo_webhook_indexes(db)
        logger.info("Brevo webhook indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Brevo webhook indexes: {e}")
    try:
        await setup_pass_lifecycle_indexes(db)
        logger.info("PASS lifecycle indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create PASS lifecycle indexes: {e}")
    try:
        await setup_pass_subscription_indexes(db)
        logger.info("PASS subscription indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create PASS subscription indexes: {e}")
    try:
        await ensure_ged_bridge_indexes(db)
        logger.info("GED ESS Bridge indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create GED bridge indexes: {e}")
    try:
        await ensure_finance_bridge_indexes(db)
        logger.info("Finance API Bridge indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create Finance bridge indexes: {e}")
    try:
        await ensure_connectors_indexes(db)
        logger.info("Connectors indexes ensured")
    except Exception as e:
        logger.warning(f"Could not create connectors indexes: {e}")
    try:
        start_scheduler()
    except Exception as e:
        logger.warning(f"Could not start scheduler: {e}")
    try:
        await seed_taxonomy()
    except Exception as e:
        logger.warning(f"Could not seed taxonomy: {e}")

    # Seed default subscription plans if missing
    try:
        seeded = await seed_subscription_plans(db)
        if seeded:
            logger.info(f"Seeded {seeded} default subscription plan(s)")
    except Exception as e:
        logger.warning(f"Could not seed default subscription plans: {e}")

    logger.info("Database indexes created (v1 + v2 + catalog + preparation + vendor + OPA + admin_plans)")


@app.on_event("shutdown")
async def shutdown_db_client():
    try:
        stop_scheduler()
    except Exception:
        pass
    client.close()
