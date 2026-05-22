# Subscription plans data
#
# NOTE: Plans are now stored dynamically in MongoDB (`subscription_plans` collection)
# and can be managed by Super Admins through the admin UI.
# The hardcoded list below is used ONLY as a seed for first-time DB initialization
# and as a safe fallback if the DB is unavailable.

from datetime import datetime, timezone

SUBSCRIPTION_PLANS = [
    {
        "id": "ess-acces-pro",
        "slug": "ess-acces-pro",
        "name": "ESS ACCÈS PRO",
        "description": "Accès de base à la centrale d'achats KDMARCHE B2B",
        "price_cents": 14900,
        "price": 149,
        "period": "mois",
        "popular": False,
        "active": True,
        "sort_order": 1,
        "max_zones": 1,
        "max_users": 1,
        "default_credits": 100,
        "color": "#D9B35A",
        "features": [
            "Accès à la centrale d'achats KDMARCHE B2B",
            "1 zone géographique incluse",
            "Accès aux prix structurels mutualisés",
            "Wallet crédits de base",
            "Accès promos flash de la zone"
        ]
    },
    {
        "id": "ess-volume-pro",
        "slug": "ess-volume-pro",
        "name": "ESS VOLUME PRO",
        "description": "Pour les structures qui commandent en gros volumes",
        "price_cents": 34900,
        "price": 349,
        "period": "mois",
        "popular": True,
        "active": True,
        "sort_order": 2,
        "max_zones": 2,
        "max_users": 3,
        "default_credits": 200,
        "color": "#D9B35A",
        "features": [
            "Accès prioritaire aux volumes",
            "Accès élargi aux gammes KDMARCHE",
            "Wallet crédits renforcé",
            "Accès multi-catégories",
            "Reporting d'usage"
        ]
    },
    {
        "id": "ess-impact-pro",
        "slug": "ess-impact-pro",
        "name": "ESS IMPACT PRO",
        "description": "Pour les coopératives multi-zones et projets structurants",
        "price_cents": 74900,
        "price": 749,
        "period": "mois",
        "popular": False,
        "active": True,
        "sort_order": 3,
        "max_zones": 99,
        "max_users": 10,
        "default_credits": 500,
        "color": "#D9B35A",
        "features": [
            "Accès multi-zones",
            "Accès projets collectifs",
            "Reporting ESS / impact",
            "Appui structuration coopérative",
            "Accès fournisseurs stratégiques"
        ]
    }
]

# Default credits by plan (kept as fallback)
DEFAULT_CREDITS = {p["id"]: p["default_credits"] for p in SUBSCRIPTION_PLANS}


async def seed_subscription_plans(db) -> int:
    """
    Seed default subscription plans into MongoDB if collection is empty
    or if specific seed plans are missing. Idempotent.
    Returns the number of plans inserted.
    """
    inserted = 0
    now = datetime.now(timezone.utc).isoformat()
    for plan in SUBSCRIPTION_PLANS:
        existing = await db.subscription_plans.find_one({"id": plan["id"]})
        if not existing:
            doc = {
                "id": plan["id"],
                "slug": plan["slug"],
                "name": plan["name"],
                "description": plan.get("description"),
                "price_cents": plan["price_cents"],
                "period": plan["period"],
                "default_credits": plan["default_credits"],
                "features": plan["features"],
                "popular": plan["popular"],
                "active": plan["active"],
                "sort_order": plan["sort_order"],
                "max_zones": plan["max_zones"],
                "max_users": plan["max_users"],
                "color": plan["color"],
                "created_at": now,
                "updated_at": now,
                "created_by": "system_seed"
            }
            await db.subscription_plans.insert_one(doc)
            inserted += 1
    return inserted


async def get_active_plans_from_db(db) -> list:
    """Return active subscription plans from DB (fallback to hardcoded list)."""
    try:
        cursor = db.subscription_plans.find(
            {"active": True}, {"_id": 0}
        ).sort("sort_order", 1)
        plans = await cursor.to_list(100)
        if plans:
            # Normalize: provide both `price` (legacy, in EUR) and `price_cents`
            for p in plans:
                if "price" not in p and "price_cents" in p:
                    p["price"] = round(p["price_cents"] / 100)
            return plans
    except Exception as e:
        print(f"[subscriptions] Falling back to hardcoded plans: {e}")
    return SUBSCRIPTION_PLANS


async def get_plan_default_credits(db, plan_id: str) -> int:
    """Return default credits for a given plan id (DB first, fallback to hardcoded)."""
    try:
        plan = await db.subscription_plans.find_one({"id": plan_id}, {"_id": 0})
        if plan and plan.get("default_credits") is not None:
            return int(plan["default_credits"])
    except Exception:
        pass
    return DEFAULT_CREDITS.get(plan_id, 100)
