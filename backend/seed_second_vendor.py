"""Seed idempotent : second vendeur pro réel (Épices Karukera) avec produits, commandes et attestation RCR."""
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

load_dotenv("/app/backend/.env")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VENDOR_ID = "vendor-epices-karukera"
USER_ID = "user-vendor-karukera"
PRODUCTS = [
    {"id": "vp-karukera-colombo", "sku": "KAR-COLOMBO-500G", "name": "Poudre de colombo 500g",
     "category": "alimentaire", "price_ht_cents": 890, "stock_qty": 300,
     "description": "Mélange colombo traditionnel de Guadeloupe, moulu artisanalement."},
    {"id": "vp-karukera-vanille", "sku": "KAR-VANILLE-X10", "name": "Gousses de vanille Bourbon x10",
     "category": "alimentaire", "price_ht_cents": 2450, "stock_qty": 150,
     "description": "Gousses de vanille Bourbon premium, calibre 16-18 cm."},
]


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if not await db.users.find_one({"id": USER_ID}):
        await db.users.insert_one({
            "id": USER_ID, "email": "vendeur2@kdmarche.fr",
            "password_hash": pwd_context.hash("Demo2026!"),
            "contact_name": "Lucie Karukera", "company_name": "Épices Karukera SARL",
            "role": "vendor", "account_type": "vendor", "vendor_id": VENDOR_ID,
            "is_admin": False, "siret": "88877766600014", "phone": "+590690000002",
            "created_at": now_iso})
        print("User vendeur2@kdmarche.fr créé")

    if not await db.vendors.find_one({"id": VENDOR_ID}):
        await db.vendors.insert_one({
            "id": VENDOR_ID, "company_name": "Épices Karukera SARL",
            "contact_name": "Lucie Karukera", "email": "vendeur2@kdmarche.fr",
            "siret": "88877766600014", "status": "approved",
            "territory": "GUADELOUPE", "created_at": now_iso})
        print("Vendor Épices Karukera créé")

    for p in PRODUCTS:
        if not await db.vendor_products.find_one({"id": p["id"]}):
            await db.vendor_products.insert_one({
                **p, "vendor_id": VENDOR_ID, "status": "approved", "unit": "unit",
                "format": "lot", "min_order_qty": 6, "tva_rate": 5.5,
                "price_ttc_cents": int(p["price_ht_cents"] * 1.055),
                "zones": ["GUADELOUPE", "MARTINIQUE"],
                "created_at": now_iso, "updated_at": now_iso})
            print(f"Produit {p['name']} créé")

    # Attestation nominative V2.0 pour le colombo (via le flux réel + contre-signature)
    import sys
    sys.path.insert(0, "/app/backend")
    from db import set_database
    set_database(db)
    from attestation_nominative import create_attestation_for_product, countersign_attestation
    colombo = await db.vendor_products.find_one({"id": "vp-karukera-colombo"}, {"_id": 0})
    if not await db.attestations_nominatives.find_one({"product_id": "vp-karukera-colombo"}):
        vendor = await db.vendors.find_one({"id": VENDOR_ID}, {"_id": 0})
        att = await create_attestation_for_product(db, colombo, vendor)
        await countersign_attestation(db, "vp-karukera-colombo", "admin@kdmarche-oscop.fr")
        print(f"Attestation {att['ref']} créée et contre-signée")

    # Commandes B2B référençant le colombo (fractions RCR)
    for i, (qty, days_ago) in enumerate([(40, 20), (25, 6)], start=1):
        oid = f"seed-karukera-order-{i}"
        if await db.orders.find_one({"id": oid}):
            continue
        line = qty * colombo["price_ht_cents"]
        created = (now - timedelta(days=days_ago)).isoformat(sep=" ")
        await db.orders.insert_one({
            "id": oid, "order_number": f"KDM-KAR-{now.strftime('%Y%m%d')}-{i:02d}",
            "organization_id": "org-demo-achats", "zone_code": "GUADELOUPE",
            "status": "CONFIRMED",
            "items": [{"id": str(uuid.uuid4()), "product_id": "vp-karukera-colombo",
                       "product_name": colombo["name"], "product_sku": colombo["sku"],
                       "unit": "CARTON", "quantity": qty,
                       "price_ht_cents": colombo["price_ht_cents"], "line_total_ht_cents": line}],
            "subtotal_ht_cents": line, "total_ttc_cents": int(line * 1.055),
            "created_at": created})
        print(f"Commande {oid} créée ({qty} × colombo)")

    from rcr_fiscal import sync_rcr_fiscal_register
    result = await sync_rcr_fiscal_register(db)
    print(f"Registre fiscal synchronisé : {result}")
    print("Seed second vendeur terminé.")


if __name__ == "__main__":
    asyncio.run(main())
