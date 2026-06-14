"""
Seed demo personas + journeys for KDMARCHE × O'SCOP demo.

Adds (on top of `seed_lolodrive.py`):
  • Vendor pro fictif  → `vendor-pro@kdmarche.fr` (espace vendeur opérationnel)
  • B2B Acheteur pro    → `acheteur-pro@kdmarche.fr` (parcours d'achat B2B EXW)
  • Une commande "Lolo Point achat" pour le gérant existant (parcours d'achat LP)
  • Activation GED interne : force-init des 4 documents de référence
    (convention, cg-oscop, cgv-kdmarche, note-preventive) si vides.

Idempotent : peut être ré-exécuté sans dupliquer.

Run: python /app/backend/seed_demo_personas.py
"""
import asyncio
import hashlib
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def main() -> None:
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "kdmarche_lolodrive")]
    now = datetime.now(timezone.utc)
    now_naive = datetime.utcnow()

    # =========================================================
    # 1) VENDOR PRO FICTIF — compte vendeur + produits approuvés
    # =========================================================
    vendor_id = "vendor-demo-pro"
    vendor_email = "vendor-pro@kdmarche.fr"
    # Demo seed password — overridable via env so prod-like environments inject their own.
    vendor_password = os.environ.get("DEMO_SEED_PASSWORD", "Demo2026!")

    # Côté table `users` (login app)
    vendor_user = {
        "id": "user-vendor-pro",
        "email": vendor_email,
        "password_hash": pwd_context.hash(vendor_password),
        "company_name": "Distillerie Damoiseau",
        "siret": "44444444444444",
        "contact_name": "Marc Damoiseau",
        "phone": "+590 590 44 44 44",
        "subscription": "ess-acces-pro",
        "credits": 0,
        "is_admin": False,
        "role": "vendor",
        "vendor_id": vendor_id,
        "created_at": now_naive,
        "updated_at": now_naive,
    }
    await db.users.update_one({"id": vendor_user["id"]}, {"$set": vendor_user}, upsert=True)

    # Côté table `vendors` (catalogue produits / dashboard vendor)
    vendor = {
        "id": vendor_id,
        "email": vendor_email,
        "password_hash": hashlib.sha256(vendor_password.encode()).hexdigest(),
        "company_name": "Distillerie Damoiseau",
        "siret": "44444444444444",
        "tva_intra": "FR12444444444",
        "address": "Bellevue Le Moule",
        "city": "Le Moule",
        "postal_code": "97160",
        "country": "GP",
        "phone": "+590 590 44 44 44",
        "contact_name": "Marc Damoiseau",
        "contact_title": "Responsable commercial",
        "description": "Distillerie agricole AOC Guadeloupe — rhums et produits dérivés.",
        "website": "https://damoiseau.fr",
        "status": "approved",
        "registration_method": "seed_demo",
        "product_count": 3,
        "total_sales": 0,
        "rating": 4.7,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "approved_at": now.isoformat(),
        "rejected_at": None,
        "rejection_reason": None,
    }
    await db.vendors.update_one({"id": vendor_id}, {"$set": vendor}, upsert=True)

    # 3 produits vendeur (1 brouillon, 1 en attente, 1 approuvé) — démo workflow complet
    vendor_products = [
        {
            "id": "vp-damoiseau-rhum-blanc", "vendor_id": vendor_id,
            "sku": "DAM-RHUM-BLANC-1L",
            "name": "Rhum blanc agricole AOC 1L",
            "category": "boissons",
            "description": "Rhum agricole blanc AOC Guadeloupe, 50% vol.",
            "unit": "unit", "format": "standard",
            "price_ttc_cents": 1990, "price_ht_cents": 1659,
            "tva_rate": 20.0, "min_order_qty": 6, "stock_qty": 240,
            "zones": ["GUADELOUPE", "MARTINIQUE"],
            "status": "approved", "approved_at": now.isoformat(),
            "created_at": now.isoformat(), "updated_at": now.isoformat(),
        },
        {
            "id": "vp-damoiseau-rhum-vsop", "vendor_id": vendor_id,
            "sku": "DAM-RHUM-VSOP-70CL",
            "name": "Rhum VSOP 8 ans 70cl",
            "category": "boissons",
            "description": "Rhum vieux AOC Guadeloupe, vieilli 8 ans en fût de chêne.",
            "unit": "unit", "format": "standard",
            "price_ttc_cents": 4990, "price_ht_cents": 4158,
            "tva_rate": 20.0, "min_order_qty": 3, "stock_qty": 60,
            "zones": ["GUADELOUPE", "MARTINIQUE", "REUNION"],
            "status": "approved", "approved_at": now.isoformat(),
            "created_at": now.isoformat(), "updated_at": now.isoformat(),
        },
        {
            "id": "vp-damoiseau-confiture", "vendor_id": vendor_id,
            "sku": "DAM-CONF-RHUM-300G",
            "name": "Confiture goyave-rhum 300g",
            "category": "alimentaire",
            "description": "Confiture artisanale goyave de Marie-Galante au rhum vieux.",
            "unit": "unit", "format": "lot",
            "price_ttc_cents": 690, "price_ht_cents": 627,
            "tva_rate": 5.5, "min_order_qty": 12, "stock_qty": 120,
            "zones": ["GUADELOUPE", "MARTINIQUE"],
            "status": "pending_approval",
            "created_at": now.isoformat(), "updated_at": now.isoformat(),
        },
    ]
    for p in vendor_products:
        await db.vendor_products.update_one(
            {"vendor_id": p["vendor_id"], "sku": p["sku"]}, {"$set": p}, upsert=True,
        )

    # =========================================================
    # 2) B2B ACHETEUR PRO FICTIF — distinct du titulaire PASS
    # =========================================================
    buyer = {
        "id": "user-buyer-pro",
        "email": "acheteur-pro@kdmarche.fr",
        "password_hash": pwd_context.hash("Demo2026!"),
        "company_name": "Restaurant La Caravelle",
        "siret": "55555555555555",
        "contact_name": "Sophie Verger",
        "phone": "+590 690 55 55 55",
        "subscription": "ess-acces-pro",
        "credits": 250,
        "is_admin": False,
        "role": "buyer",
        "created_at": now_naive,
        "updated_at": now_naive,
    }
    await db.users.update_one({"id": buyer["id"]}, {"$set": buyer}, upsert=True)

    # =========================================================
    # 3) GÉRANT LOLO POINT — parcours d'achat B2B (LP achète du stock)
    # =========================================================
    lp_purchase_order = {
        "id": "order-lp-gerant-1",
        "order_number": "LD-LP-20260518-J1K2L3",
        "user_id": "user-gerant-1",       # Gérant LP Capesterre
        "lolo_point_id": "lp-2",          # son propre LP
        "fulfillment_type": "B2B_RESTOCK",
        "status": "FULFILLED",
        "items": [
            {"sku": "RIZ-5KG", "name": "Riz long grain 5kg",
             "qty": 20, "catalog_type": "ESSENTIAL", "unit_cents": 490, "unit_uc": 0},
            {"sku": "LAIT-1L", "name": "Lait UHT 1L",
             "qty": 60, "catalog_type": "ESSENTIAL", "unit_cents": 110, "unit_uc": 0},
            {"sku": "HUILE-1L", "name": "Huile végétale 1L",
             "qty": 30, "catalog_type": "ESSENTIAL", "unit_cents": 320, "unit_uc": 0},
        ],
        "subtotal_cents": 26000,  # 20*490 + 60*110 + 30*320 = 9800+6600+9600
        "fees_cents": 0,
        "total_cents": 26000,
        "pay_with_uc": False,
        "stripe_payment_intent_id": "pi_demo_lp_restock",
        "stripe_account": "kdmarche",
        "created_at": now_naive - timedelta(days=4),
        "updated_at": now_naive - timedelta(days=3),
        "fulfilled_at": now_naive - timedelta(days=3),
    }
    await db.lolodrive_orders.update_one(
        {"id": lp_purchase_order["id"]}, {"$set": lp_purchase_order}, upsert=True,
    )

    # =========================================================
    # 4) ACTIVATION GED INTERNE — force l'initialisation des 4 docs
    # =========================================================
    existing = await db.ged_documents.count_documents({})
    if existing == 0:
        try:
            from routes_ged import initialize_default_documents
            await initialize_default_documents()
            new_count = await db.ged_documents.count_documents({})
            ged_msg = f"GED initialisée ({new_count} documents)"
        except Exception as e:
            ged_msg = f"GED init échouée: {e}"
    else:
        ged_msg = f"GED déjà active ({existing} documents)"

    client.close()

    # ========== RAPPORT ==========
    print("\n✅ SEED PERSONAS COMPLETE\n")
    print("Comptes ajoutés :")
    print("  Vendeur pro        : vendor-pro@kdmarche.fr / Demo2026!")
    print("                       → /vendor (Distillerie Damoiseau, 3 produits, 1 en attente)")
    print("  Acheteur B2B pro   : acheteur-pro@kdmarche.fr / Demo2026!")
    print("                       → /catalogue, /espace-acheteur (Restaurant La Caravelle, 250 crédits)")
    print("  Gérant LP (existant): gerant@lolopoint.fr / Demo2026!")
    print("                       → /lolo-point/dashboard + commande de réassort B2B FULFILLED")
    print()
    print(f"  {ged_msg}")


if __name__ == "__main__":
    asyncio.run(main())
