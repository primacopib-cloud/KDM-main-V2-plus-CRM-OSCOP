"""
Seed script for KDMARCHÉ / LOLODRIVE by O'SCOP demo data.
Creates: admin user, demo PASS holder, products ESSENTIAL/NORMAL, lolo_points,
events LOLO_HOUR, partners, demo orders, CRM contacts/orgs/opportunities/dossiers.

Run: python /app/backend/seed_lolodrive.py
"""
import asyncio
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ.get('DB_NAME', 'kdmarche_lolodrive')]

    now = datetime.utcnow()

    # ---- 1. USERS ----
    users = [
        {
            "id": "user-admin",
            "email": "admin@kdmarche-oscop.fr",
            "password": "AdminKDM2025!",
            "company_name": "O'SCOP HQ",
            "siret": "00000000000000",
            "contact_name": "Super Admin",
            "phone": "+590 590 00 00 00",
            "subscription": "ess-acces-pro",
            "credits": 1000,
            "is_admin": True,
            "role": "SUPER_ADMIN",
        },
        {
            "id": "user-titulaire-1",
            "email": "marie@example.com",
            "password": "Demo2026!",
            "company_name": "Marie Dupont",
            "siret": "11111111111111",
            "contact_name": "Marie Dupont",
            "phone": "+590 690 11 11 11",
            "subscription": "ess-acces-pro",
            "credits": 0,
            "is_admin": False,
            "role": "TITULAIRE_PASS",
        },
        {
            "id": "user-pos-1",
            "email": "pos@lolodrive.fr",
            "password": "Demo2026!",
            "company_name": "Lolodrive Pointe-à-Pitre",
            "siret": "22222222222222",
            "contact_name": "Opérateur POS",
            "phone": "+590 590 22 22 22",
            "subscription": "ess-acces-pro",
            "credits": 0,
            "is_admin": False,
            "role": "OPERATEUR_POS",
        },
        {
            "id": "user-gerant-1",
            "email": "gerant@lolopoint.fr",
            "password": "Demo2026!",
            "company_name": "Lolo Point Capesterre",
            "siret": "33333333333333",
            "contact_name": "Jean Bernard",
            "phone": "+590 690 33 33 33",
            "subscription": "ess-acces-pro",
            "credits": 0,
            "is_admin": False,
            "role": "GERANT_LOLO_POINT",
        },
    ]

    for u in users:
        password = u.pop("password")
        u["password_hash"] = pwd_context.hash(password)
        u["created_at"] = now
        u["updated_at"] = now
        await db.users.update_one({"id": u["id"]}, {"$set": u}, upsert=True)
    print(f"  ✔ {len(users)} users seeded")

    # ---- 2. PRODUITS (avec affinage par territoires) ----
    # Convention : `territories=[]` → disponible partout. Sinon liste explicite des codes DOM.
    products = [
        # ESSENTIELS (prix PASS) — disponibles dans les 4 DOM
        {"sku": "RIZ-5KG", "name": "Riz long grain 5kg", "category": "Épicerie", "brand": "Saveurs Caraïbes", "catalog_type": "ESSENTIAL", "price_public_cents": 650, "price_pass_cents": 490, "territories": ["GP", "MQ", "GF"], "image_url": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400"},
        {"sku": "LAIT-1L", "name": "Lait UHT 1L", "category": "Épicerie", "brand": "Candia", "catalog_type": "ESSENTIAL", "price_public_cents": 140, "price_pass_cents": 110, "territories": [], "image_url": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=400"},
        {"sku": "HUILE-1L", "name": "Huile végétale 1L", "category": "Épicerie", "brand": "Lesieur", "catalog_type": "ESSENTIAL", "price_public_cents": 450, "price_pass_cents": 320, "territories": [], "image_url": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400"},
        {"sku": "FARINE-1KG", "name": "Farine de blé T45 1kg", "category": "Épicerie", "brand": "Francine", "catalog_type": "ESSENTIAL", "price_public_cents": 200, "price_pass_cents": 160, "territories": [], "image_url": "https://images.unsplash.com/photo-1568254183919-78a4f43a2877?w=400"},
        {"sku": "PATES-500G", "name": "Pâtes 500g", "category": "Épicerie", "brand": "Barilla", "catalog_type": "ESSENTIAL", "price_public_cents": 180, "price_pass_cents": 140, "territories": [], "image_url": "https://images.unsplash.com/photo-1551462147-37885acc36f1?w=400"},
        {"sku": "SUCRE-1KG", "name": "Sucre blanc 1kg", "category": "Épicerie", "brand": "Daddy", "catalog_type": "ESSENTIAL", "price_public_cents": 180, "price_pass_cents": 140, "territories": [], "image_url": "https://images.unsplash.com/photo-1582049165166-77fd35d56167?w=400"},
        {"sku": "OEUFS-12", "name": "Œufs frais x12", "category": "Frais", "brand": "Local", "catalog_type": "ESSENTIAL", "price_public_cents": 380, "price_pass_cents": 290, "territories": ["GP", "MQ"], "image_url": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400"},
        {"sku": "POULET-1KG", "name": "Poulet entier 1kg", "category": "Frais", "brand": "Volailles Antilles", "catalog_type": "ESSENTIAL", "price_public_cents": 850, "price_pass_cents": 650, "territories": ["GP", "MQ"], "image_url": "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=400"},
        # NORMAL / HORS25
        {"sku": "TOMACOULI-500G", "name": "Tomacouli 500g", "category": "Cuisine", "brand": "Panzani", "catalog_type": "NORMAL", "price_public_cents": 220, "price_pass_cents": None, "territories": [], "image_url": "https://images.unsplash.com/photo-1604908554007-3f88f54fa0aa?w=400"},
        {"sku": "NUTELLA-400G", "name": "Pâte à tartiner 400g", "category": "Épicerie", "brand": "Nutella", "catalog_type": "NORMAL", "price_public_cents": 380, "price_pass_cents": None, "territories": [], "image_url": "https://images.unsplash.com/photo-1610725664338-5f25c3a23bb1?w=400"},
        {"sku": "JUS-MANGUE-1L", "name": "Jus de mangue 1L", "category": "Boissons", "brand": "Caraïbes", "catalog_type": "NORMAL", "price_public_cents": 320, "price_pass_cents": None, "territories": ["GP", "MQ", "GF"], "image_url": "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?w=400"},
        {"sku": "CAFE-250G", "name": "Café moulu 250g", "category": "Épicerie", "brand": "Carte Noire", "catalog_type": "NORMAL", "price_public_cents": 480, "price_pass_cents": None, "territories": [], "image_url": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400"},
        # PRODUITS LOCAUX SPÉCIFIQUES — différenciation par territoire
        # Antilles (Guadeloupe + Martinique)
        {"sku": "RHUM-AGRICOLE-70CL", "name": "Rhum agricole AOC 70cl", "category": "Boissons", "brand": "Distillerie Damoiseau", "catalog_type": "NORMAL", "price_public_cents": 1850, "price_pass_cents": None, "territories": ["GP", "MQ"], "image_url": "https://images.unsplash.com/photo-1568708030267-8a4cd1b86d3a?w=400"},
        {"sku": "BANANE-1KG", "name": "Banane locale 1kg", "category": "Frais", "brand": "Coopérative Banane Caraïbe", "catalog_type": "ESSENTIAL", "price_public_cents": 220, "price_pass_cents": 170, "territories": ["GP", "MQ"], "image_url": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400"},
        # Guyane
        {"sku": "MANIOC-500G", "name": "Farine de manioc 500g", "category": "Épicerie", "brand": "Yana Wassaï", "catalog_type": "ESSENTIAL", "price_public_cents": 280, "price_pass_cents": 210, "territories": ["GF"], "image_url": "https://images.unsplash.com/photo-1604908554007-3f88f54fa0aa?w=400"},
        {"sku": "CACHIRI-1L", "name": "Cachiri (boisson amérindienne) 1L", "category": "Boissons", "brand": "Coop Wayampi", "catalog_type": "NORMAL", "price_public_cents": 450, "price_pass_cents": None, "territories": ["GF"], "image_url": "https://images.unsplash.com/photo-1601924994987-69e26d50dc26?w=400"},
        # La Réunion
        {"sku": "VANILLE-BOURBON-3G", "name": "Gousse de vanille Bourbon (3g)", "category": "Épicerie", "brand": "Vanilleraie Provanille", "catalog_type": "NORMAL", "price_public_cents": 590, "price_pass_cents": None, "territories": ["RE"], "image_url": "https://images.unsplash.com/photo-1606914469333-9c7e9e1b2c5c?w=400"},
        {"sku": "ACHARDS-LEGUMES-200G", "name": "Achards de légumes 200g", "category": "Épicerie", "brand": "La Reine du Cari", "catalog_type": "NORMAL", "price_public_cents": 320, "price_pass_cents": None, "territories": ["RE"], "image_url": "https://images.unsplash.com/photo-1604908554007-3f88f54fa0aa?w=400"},
        {"sku": "SUCRE-CANNE-RE-1KG", "name": "Sucre de canne La Réunion 1kg", "category": "Épicerie", "brand": "Tereos Sucre Réunion", "catalog_type": "ESSENTIAL", "price_public_cents": 220, "price_pass_cents": 170, "territories": ["RE"], "image_url": "https://images.unsplash.com/photo-1582049165166-77fd35d56167?w=400"},
    ]

    for p in products:
        p["id"] = str(uuid.uuid4())
        p["is_active"] = True
        p["stock_qty"] = 100
        p["created_at"] = now
        p["updated_at"] = now
        await db.lolodrive_products.update_one({"sku": p["sku"]}, {"$set": p}, upsert=True)
    print(f"  ✔ {len(products)} produits seeded")

    # ---- 3. ZONES LIVRAISON ----
    zones = [
        {"id": "zone-gt", "name": "Grande-Terre", "days": "MON,WED,FRI", "slots": [
            {"id": "gt-am", "label": "Matin 9h–12h30", "start": "09:00", "end": "12:30"},
            {"id": "gt-pm", "label": "Après-midi 14h–18h", "start": "14:00", "end": "18:00"},
        ]},
        {"id": "zone-bt", "name": "Basse-Terre", "days": "TUE,THU,FRI", "slots": [
            {"id": "bt-am", "label": "Matin 9h–12h30", "start": "09:00", "end": "12:30"},
            {"id": "bt-pm", "label": "Après-midi 14h–18h", "start": "14:00", "end": "18:00"},
        ]},
    ]
    for z in zones:
        await db.lolodrive_delivery_zones.update_one({"id": z["id"]}, {"$set": z}, upsert=True)
    print(f"  ✔ {len(zones)} zones seeded")

    # ---- 4. LOLO POINTS (multi-territoires DOM) ----
    lolo_points = [
        # Guadeloupe (GP)
        {"id": "lp-1", "name": "Lolo Point Pointe-à-Pitre", "code": "LP-PAP", "territory": "GP", "city": "Pointe-à-Pitre", "address": "12 rue Schoelcher", "zone_name": "Grande-Terre", "lat": 16.2418, "lng": -61.5331, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-2", "name": "Lolo Point Capesterre", "code": "LP-CAP", "territory": "GP", "city": "Capesterre-Belle-Eau", "address": "Place de la Mairie", "zone_name": "Basse-Terre", "lat": 16.0476, "lng": -61.5644, "status": "ACTIVE", "manager_user_id": "user-gerant-1", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-3", "name": "Lolo Point Le Gosier", "code": "LP-GOS", "territory": "GP", "city": "Le Gosier", "address": "Rue Principale", "zone_name": "Grande-Terre", "lat": 16.2078, "lng": -61.4910, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-4", "name": "Lolo Point Saint-François", "code": "LP-STF", "territory": "GP", "city": "Saint-François", "address": "Marina", "zone_name": "Grande-Terre", "lat": 16.2520, "lng": -61.2790, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        # Martinique (MQ)
        {"id": "lp-5", "name": "Lolo Point Fort-de-France", "code": "LP-FDF", "territory": "MQ", "city": "Fort-de-France", "address": "Rue Schoelcher", "zone_name": "Centre", "lat": 14.6160, "lng": -61.0588, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-6", "name": "Lolo Point Le Lamentin", "code": "LP-LAM", "territory": "MQ", "city": "Le Lamentin", "address": "Centre commercial", "zone_name": "Centre", "lat": 14.6094, "lng": -60.9990, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        # Guyane (GF)
        {"id": "lp-7", "name": "Lolo Point Cayenne", "code": "LP-CAY", "territory": "GF", "city": "Cayenne", "address": "Place des Palmistes", "zone_name": "Littoral", "lat": 4.9333, "lng": -52.3270, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-8", "name": "Lolo Point Kourou", "code": "LP-KOU", "territory": "GF", "city": "Kourou", "address": "Avenue de l'Espace", "zone_name": "Littoral", "lat": 5.1599, "lng": -52.6500, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        # La Réunion (RE)
        {"id": "lp-9", "name": "Lolo Point Saint-Denis", "code": "LP-STD", "territory": "RE", "city": "Saint-Denis", "address": "Rue Maréchal Leclerc", "zone_name": "Nord", "lat": -20.8823, "lng": 55.4504, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
        {"id": "lp-10", "name": "Lolo Point Saint-Pierre", "code": "LP-STP", "territory": "RE", "city": "Saint-Pierre", "address": "Boulevard Hubert Delisle", "zone_name": "Sud", "lat": -21.3393, "lng": 55.4781, "status": "ACTIVE", "payout_cap_cents_monthly": 120000, "payout_cap_percent_bps": 600, "withdrawal_commission_cents": 70, "pass_activation_commission_cents": 400, "essential_volume_bps": 200},
    ]
    for lp in lolo_points:
        lp["created_at"] = now
        lp["updated_at"] = now
        await db.lolodrive_points.update_one({"code": lp["code"]}, {"$set": lp}, upsert=True)
    print(f"  ✔ {len(lolo_points)} lolo points seeded")

    # ---- 5. PARTENAIRES ----
    partners = [
        {"id": "p-1", "name": "Brasserie Antillaise", "type": "fournisseur", "contact_email": "contact@brasserie-antillaise.fr", "contact_phone": "+590 590 11 22 33"},
        {"id": "p-2", "name": "Crédit Mutuel Antilles", "type": "sponsor_financier", "contact_email": "partenariats@cmag.fr", "contact_phone": "+590 590 44 55 66"},
        {"id": "p-3", "name": "Région Guadeloupe", "type": "institutionnel", "contact_email": "ess@regionguadeloupe.fr", "contact_phone": "+590 590 77 88 99"},
        {"id": "p-4", "name": "Coopérative Banane Caraïbe", "type": "fournisseur", "contact_email": "coop@bananecaraibes.com", "contact_phone": "+590 590 12 34 56"},
    ]
    for p in partners:
        p["created_at"] = now
        await db.lolodrive_partners.update_one({"id": p["id"]}, {"$set": p}, upsert=True)
    print(f"  ✔ {len(partners)} partners seeded")

    # ---- 6. ÉVÉNEMENTS LOLO HOUR ----
    events = [
        {"id": "ev-1", "type": "LOLO_HOUR", "title": "LOLO HOUR Vendredi - 30% Riz & Lait", "starts_at": now + timedelta(days=2), "ends_at": now + timedelta(days=2, hours=2), "is_pass_only": True, "drive_only": True, "per_user_limit": 2, "stock_limit": 50, "is_active": True},
        {"id": "ev-2", "type": "FLASH_PASS", "title": "Flash PASS - Huile 1L à -25%", "starts_at": now + timedelta(hours=4), "ends_at": now + timedelta(hours=8), "is_pass_only": True, "drive_only": False, "per_user_limit": 1, "stock_limit": 100, "is_active": True},
        {"id": "ev-3", "type": "LOLO_BIG_DEAL", "title": "BIG DEAL Mensuel - Panier essentiels 30€", "starts_at": now + timedelta(days=5), "ends_at": now + timedelta(days=7), "is_pass_only": True, "drive_only": True, "per_user_limit": 1, "stock_limit": 200, "is_active": True},
        {"id": "ev-4", "type": "PARTNER", "title": "Action partenaire Crédit Mutuel - Activation PASS offerte", "starts_at": now + timedelta(days=10), "ends_at": now + timedelta(days=17), "partner_id": "p-2", "sponsor_pack": "GOLD", "is_pass_only": False, "drive_only": False, "per_user_limit": 1, "stock_limit": 50, "is_active": True},
    ]
    for ev in events:
        ev["created_at"] = now
        await db.lolodrive_events.update_one({"id": ev["id"]}, {"$set": ev}, upsert=True)
    print(f"  ✔ {len(events)} events seeded")

    # ---- 7. DEMO PASS + WALLET pour user-titulaire-1 ----
    pass_doc = {
        "id": "pass-demo-1",
        "user_id": "user-titulaire-1",
        "status": "ACTIVE",
        "starts_at": now - timedelta(days=5),
        "ends_at": now + timedelta(days=25),
        "price_cents": 6000,
        "uc_granted": 600,
        "is_auto_renew": False,
        "source_lolo_point_id": "lp-1",
        "created_at": now - timedelta(days=5),
        "updated_at": now,
    }
    await db.lolodrive_passes.update_one({"user_id": "user-titulaire-1"}, {"$set": pass_doc}, upsert=True)

    wallet_doc = {
        "id": "wallet-demo-1",
        "user_id": "user-titulaire-1",
        "balance_uc": 450,
        "created_at": now - timedelta(days=5),
        "updated_at": now,
    }
    await db.lolodrive_wallets.update_one({"user_id": "user-titulaire-1"}, {"$set": wallet_doc}, upsert=True)

    # Wallet ledger
    ledger_entries = [
        {"id": str(uuid.uuid4()), "wallet_id": "wallet-demo-1", "type": "CREDIT", "amount_uc": 600, "reason": "PASS_ACTIVATION", "created_at": now - timedelta(days=5)},
        {"id": str(uuid.uuid4()), "wallet_id": "wallet-demo-1", "type": "DEBIT", "amount_uc": 100, "reason": "ORDER_PAY_UC", "order_id": "order-demo-1", "created_at": now - timedelta(days=3)},
        {"id": str(uuid.uuid4()), "wallet_id": "wallet-demo-1", "type": "DEBIT", "amount_uc": 50, "reason": "ORDER_PAY_UC", "order_id": "order-demo-2", "created_at": now - timedelta(days=1)},
    ]
    await db.lolodrive_wallet_ledger.delete_many({"wallet_id": "wallet-demo-1"})
    await db.lolodrive_wallet_ledger.insert_many(ledger_entries)
    print("  ✔ PASS, wallet et ledger seeded pour Marie Dupont")

    # ---- 8. COMMANDES DEMO ----
    demo_orders = [
        {
            "id": "order-demo-1", "order_number": "LD-20260520-A1B2C3", "user_id": "user-titulaire-1",
            "lolo_point_id": "lp-1", "fulfillment_type": "LOLO_POINT", "status": "FULFILLED",
            "items": [{"sku": "RIZ-5KG", "name": "Riz long grain 5kg", "qty": 1, "catalog_type": "ESSENTIAL", "unit_cents": 490, "unit_uc": 49},
                      {"sku": "LAIT-1L", "name": "Lait UHT 1L", "qty": 2, "catalog_type": "ESSENTIAL", "unit_cents": 110, "unit_uc": 11}],
            "subtotal_cents": 710, "fees_cents": 200, "total_cents": 910,
            "subtotal_uc": 71, "fees_uc": 20, "total_uc": 91, "pay_with_uc": True,
            "created_at": now - timedelta(days=3), "updated_at": now - timedelta(days=3), "fulfilled_at": now - timedelta(days=2, hours=20),
        },
        {
            "id": "order-demo-2", "order_number": "LD-20260521-D4E5F6", "user_id": "user-titulaire-1",
            "lolo_point_id": "lp-2", "fulfillment_type": "DRIVE", "status": "READY",
            "items": [{"sku": "HUILE-1L", "name": "Huile végétale 1L", "qty": 1, "catalog_type": "ESSENTIAL", "unit_cents": 320, "unit_uc": 32},
                      {"sku": "PATES-500G", "name": "Pâtes 500g", "qty": 2, "catalog_type": "ESSENTIAL", "unit_cents": 140, "unit_uc": 14}],
            "subtotal_cents": 600, "fees_cents": 200, "total_cents": 800,
            "subtotal_uc": 60, "fees_uc": 20, "total_uc": 80, "pay_with_uc": True,
            "created_at": now - timedelta(days=1), "updated_at": now - timedelta(hours=2),
        },
        {
            "id": "order-demo-3", "order_number": "LD-20260522-G7H8I9", "user_id": "user-titulaire-1",
            "lolo_point_id": "lp-1", "fulfillment_type": "DRIVE", "status": "PREPARING",
            "items": [{"sku": "FARINE-1KG", "name": "Farine de blé T45 1kg", "qty": 1, "catalog_type": "ESSENTIAL", "unit_cents": 160, "unit_uc": 16},
                      {"sku": "OEUFS-12", "name": "Œufs frais x12", "qty": 1, "catalog_type": "ESSENTIAL", "unit_cents": 290, "unit_uc": 29}],
            "subtotal_cents": 450, "fees_cents": 200, "total_cents": 650,
            "subtotal_uc": 45, "fees_uc": 20, "total_uc": 65, "pay_with_uc": False,
            "stripe_payment_intent_id": "pi_demo_3",
            "created_at": now - timedelta(hours=5), "updated_at": now - timedelta(hours=1), "prepared_at": now - timedelta(hours=1),
        },
    ]
    for o in demo_orders:
        await db.lolodrive_orders.update_one({"id": o["id"]}, {"$set": o}, upsert=True)
    print(f"  ✔ {len(demo_orders)} commandes seeded")

    # ---- 9. CRM Contacts, Orgs, Opportunities, Dossiers ----
    crm_contacts = [
        {"id": "ct-1", "external_user_id": "user-titulaire-1", "email": "marie@example.com", "telephone": "+590 690 11 11 11", "nom": "Dupont", "prenom": "Marie", "type_acteur": "client_pass", "source_contact": "pass.activated", "statut_relation": "actif", "tags": ["PASS_VIE_CHERE", "KDMARCHE", "FIDELE"], "created_at": now, "updated_at": now},
        {"id": "ct-2", "email": "jean.bernard@lolopoint.fr", "telephone": "+590 690 33 33 33", "nom": "Bernard", "prenom": "Jean", "type_acteur": "lolo_point", "source_contact": "onboarding", "statut_relation": "actif", "tags": ["LOLO_POINT", "COOPERATEUR"], "created_at": now, "updated_at": now},
        {"id": "ct-3", "email": "contact@brasserie-antillaise.fr", "telephone": "+590 590 11 22 33", "nom": "Antillaise", "prenom": "Brasserie", "type_acteur": "fournisseur", "source_contact": "prospection", "statut_relation": "prospect", "tags": ["FOURNISSEUR", "ARTISAN"], "created_at": now, "updated_at": now},
        {"id": "ct-4", "email": "ess@regionguadeloupe.fr", "telephone": "+590 590 77 88 99", "nom": "Région", "prenom": "Guadeloupe", "type_acteur": "institutionnel", "source_contact": "rencontre", "statut_relation": "actif", "tags": ["INSTITUTION", "FINANCEUR"], "created_at": now, "updated_at": now},
    ]
    for c in crm_contacts:
        await db.crm_contacts.update_one({"id": c["id"]}, {"$set": c}, upsert=True)

    crm_orgs = [
        {"id": "org-1", "raison_sociale": "Lolo Point Pointe-à-Pitre", "enseigne": "LP-PAP", "type_structure": "lolo_point_cooperatif", "ville": "Pointe-à-Pitre", "territoire": "Guadeloupe", "statut_ecosysteme": "actif", "college_cooperatif": "Relais commerciaux coopératifs", "external_lolo_point_id": "lp-1", "tags": ["LOLO_POINT", "COOPERATEUR"], "created_at": now, "updated_at": now},
        {"id": "org-2", "raison_sociale": "Lolo Point Capesterre", "enseigne": "LP-CAP", "type_structure": "lolo_point_cooperatif", "ville": "Capesterre-Belle-Eau", "territoire": "Guadeloupe", "statut_ecosysteme": "actif", "college_cooperatif": "Relais commerciaux coopératifs", "external_lolo_point_id": "lp-2", "tags": ["LOLO_POINT"], "created_at": now, "updated_at": now},
        {"id": "org-3", "raison_sociale": "Brasserie Antillaise", "enseigne": "Brasserie Antillaise", "type_structure": "fournisseur_partenaire", "ville": "Pointe-à-Pitre", "territoire": "Guadeloupe", "statut_ecosysteme": "prospect", "external_partner_id": "p-1", "tags": ["FOURNISSEUR"], "created_at": now, "updated_at": now},
        {"id": "org-4", "raison_sociale": "Crédit Mutuel Antilles", "enseigne": "CMAG", "type_structure": "sponsor_financier", "ville": "Pointe-à-Pitre", "territoire": "Guadeloupe", "statut_ecosysteme": "actif", "external_partner_id": "p-2", "tags": ["SPONSOR", "BANQUE"], "created_at": now, "updated_at": now},
        {"id": "org-5", "raison_sociale": "Région Guadeloupe", "enseigne": "Région", "type_structure": "institutionnel", "ville": "Basse-Terre", "territoire": "Guadeloupe", "statut_ecosysteme": "actif", "external_partner_id": "p-3", "tags": ["INSTITUTION"], "created_at": now, "updated_at": now},
    ]
    for o in crm_orgs:
        await db.crm_organizations.update_one({"id": o["id"]}, {"$set": o}, upsert=True)

    crm_opps = [
        {"id": "opp-1", "titre": "Sponsoring LOLO HOUR Q1 2026 - Crédit Mutuel", "organization_id": "org-4", "type_besoin": "sponsor_lolo_hour", "produit_vise": "LOLO HOUR Vendredi", "montant_estime_cents": 500000, "pipeline_stage": "negociation", "probabilite_conversion": 75, "tags": ["SPONSOR", "LOLO_HOUR"], "created_at": now, "updated_at": now},
        {"id": "opp-2", "titre": "Référencement Brasserie Antillaise", "organization_id": "org-3", "type_besoin": "partenariat_fournisseur", "produit_vise": "Bières artisanales", "pipeline_stage": "qualification", "probabilite_conversion": 40, "tags": ["FOURNISSEUR"], "created_at": now, "updated_at": now},
        {"id": "opp-3", "titre": "Subvention Région ESS 2026", "organization_id": "org-5", "type_besoin": "financement_ess", "montant_estime_cents": 5000000, "pipeline_stage": "dossier_depose", "probabilite_conversion": 60, "tags": ["FINANCEMENT", "ESS"], "created_at": now, "updated_at": now},
        {"id": "opp-4", "titre": "Nouveau Lolo Point Marie-Galante", "type_besoin": "ouverture_lolo_point", "pipeline_stage": "lead_entrant", "probabilite_conversion": 20, "tags": ["LOLO_POINT", "EXPANSION"], "created_at": now, "updated_at": now},
    ]
    for o in crm_opps:
        await db.crm_opportunities.update_one({"id": o["id"]}, {"$set": o}, upsert=True)

    crm_dossiers = [
        {"id": "dos-1", "type_dossier": "lolo_point_cooperatif", "organization_id": "org-2", "objet_besoin": "Onboarding gérant Capesterre", "statut": "ouvert", "etape_actuelle": "convention_a_signer", "niveau_urgence": "haute", "created_at": now, "updated_at": now},
        {"id": "dos-2", "type_dossier": "fournisseur", "organization_id": "org-3", "objet_besoin": "Référencement catalogue ESSENTIELS", "statut": "ouvert", "etape_actuelle": "qualification", "niveau_urgence": "normale", "created_at": now, "updated_at": now},
        {"id": "dos-3", "type_dossier": "investisseur", "organization_id": "org-4", "objet_besoin": "Pacte sponsor 2026", "statut": "ouvert", "etape_actuelle": "negociation", "niveau_urgence": "haute", "created_at": now, "updated_at": now},
    ]
    for d in crm_dossiers:
        await db.crm_dossiers.update_one({"id": d["id"]}, {"$set": d}, upsert=True)

    crm_tasks = [
        {"id": "task-1", "title": "Relancer Crédit Mutuel sponsoring", "description": "Envoyer proposition GOLD pack LOLO HOUR Q1", "due_at": now + timedelta(days=2), "related_type": "opportunity", "related_id": "opp-1", "status": "todo", "priority": "high", "created_at": now, "updated_at": now},
        {"id": "task-2", "title": "Visiter Brasserie Antillaise", "description": "Rencontre référencement", "due_at": now + timedelta(days=5), "related_type": "opportunity", "related_id": "opp-2", "status": "todo", "priority": "normal", "created_at": now, "updated_at": now},
        {"id": "task-3", "title": "Dossier subvention Région à compléter", "due_at": now + timedelta(days=7), "related_type": "opportunity", "related_id": "opp-3", "status": "in_progress", "priority": "high", "created_at": now, "updated_at": now},
    ]
    for t in crm_tasks:
        await db.crm_tasks.update_one({"id": t["id"]}, {"$set": t}, upsert=True)

    print(f"  ✔ CRM: {len(crm_contacts)} contacts, {len(crm_orgs)} orgs, {len(crm_opps)} opportunities, {len(crm_dossiers)} dossiers, {len(crm_tasks)} tasks")

    # ---- 10. CONTRIBUTIONS COOPERATIVES ----
    contribs = [
        {"id": "co-1", "lolo_point_id": "lp-1", "type": "BENEVOLAT", "title": "Aide installation rayonnage", "description": "10h de bénévolat équipe Lolo Point PAP", "estimated_value_cents": 30000, "created_at": now},
        {"id": "co-2", "lolo_point_id": "lp-2", "type": "FORMATION", "title": "Formation gestion caisse", "description": "Formation par O'SCOP", "estimated_value_cents": 50000, "created_at": now},
    ]
    for c in contribs:
        await db.lolodrive_contributions.update_one({"id": c["id"]}, {"$set": c}, upsert=True)
    print(f"  ✔ {len(contribs)} contributions")

    print("\n✅ SEED COMPLETE\n")
    print("Comptes démo :")
    print("  Super Admin   : admin@kdmarche-oscop.fr / AdminKDM2025!")
    print("  Titulaire PASS: marie@example.com / Demo2026!")
    print("  POS Operator  : pos@lolodrive.fr / Demo2026!")
    print("  Gérant LP     : gerant@lolopoint.fr / Demo2026!")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
