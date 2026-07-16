"""Seed idempotent : rattache le compte acheteur-pro à une organisation APPROVED
avec abonnement ACTIF, accès partenaire KDMARCHE, zones GUADELOUPE/MARTINIQUE et wallet.
Usage : python seed_buyer_org.py
"""
import os
import asyncio
import uuid
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
ORG_ID = "org-demo-achats"


async def seed():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    now = datetime.utcnow()

    user = await db.users.find_one({"email": BUYER_EMAIL})
    if not user:
        print(f"❌ Utilisateur {BUYER_EMAIL} introuvable — lancez d'abord seed_demo_personas.py")
        return

    await db.orgs.update_one(
        {"id": ORG_ID},
        {"$set": {
            "legal_name": "Demo Achats Antilles SARL",
            "registration_country": "FR",
            "registration_id": "12345678900012",
            "territory": "GUADELOUPE",
            "status": "APPROVED",
            "updated_at": now,
        }, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )

    await db.org_memberships.update_one(
        {"user_id": user["id"]},
        {"$set": {"org_id": ORG_ID, "role": "CUSTOMER_ORG_OWNER"},
         "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}},
        upsert=True,
    )

    plan = await db.plans.find_one({"code": "ESS_ACCES"})
    await db.subscriptions.update_one(
        {"org_id": ORG_ID},
        {"$set": {
            "plan_id": plan["id"] if plan else "plan-ess-acces",
            "status": "ACTIVE",
            "current_period_start": now,
            "current_period_end": now + timedelta(days=365),
            "cancel_at_period_end": False,
            "updated_at": now,
        }, "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}},
        upsert=True,
    )

    await db.partner_accounts.update_one(
        {"org_id": ORG_ID, "partner": "KDMARCHE"},
        {"$set": {"status": "ACCESS_ENABLED", "partner_org_ref": "KDM-DEMO-001", "updated_at": now},
         "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}},
        upsert=True,
    )

    zones = await db.zones_v2.find({"code": {"$in": ["GUADELOUPE", "MARTINIQUE"]}}).to_list(5)
    for z in zones:
        await db.org_zone_entitlements.update_one(
            {"org_id": ORG_ID, "zone_id": z["id"]},
            {"$set": {"source": "INCLUDED", "status": "ACTIVE", "starts_at": now},
             "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": now}},
            upsert=True,
        )

    gp = next((z for z in zones if z["code"] == "GUADELOUPE"), None)
    if gp:
        await db.org_runtime_preferences.update_one(
            {"org_id": ORG_ID},
            {"$set": {"org_id": ORG_ID, "selected_zone_id": gp["id"], "updated_at": now}},
            upsert=True,
        )

    await db.wallets.update_one(
        {"org_id": ORG_ID},
        {"$set": {"status": "ACTIVE", "updated_at": now},
         "$setOnInsert": {"balance_credits": 500}},
        upsert=True,
    )

    print(f"✅ Org {ORG_ID} APPROVED + membership OWNER + subscription ACTIVE + partner ACCESS_ENABLED + zones {[z['code'] for z in zones]} + wallet pour {BUYER_EMAIL}")


if __name__ == "__main__":
    asyncio.run(seed())
