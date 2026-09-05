"""Seed idempotent: catégories BTP & Agriculture + 6 produits + prix par zone."""
import os
import uuid
from datetime import datetime, timezone
import pymongo
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
db = pymongo.MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
now = datetime.now(timezone.utc).isoformat()
IMG = "https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/"

CATS = [
    ("BTP", "BTP & Matériaux", "Matériaux de construction et équipements BTP", 7),
    ("AGRICULTURE", "Agriculture & Végétal", "Intrants, semences et équipements agricoles", 8),
]
cat_ids = {}
for code, name, desc, order in CATS:
    existing = db.categories.find_one({"code": code})
    if existing:
        cat_ids[code] = existing["id"]
    else:
        cid = str(uuid.uuid4())
        db.categories.insert_one({"id": cid, "code": code, "name": name, "description": desc,
                                  "parent_id": None, "image_url": None, "sort_order": order,
                                  "product_count": 0, "is_active": True, "created_at": now})
        cat_ids[code] = cid
        print("catégorie créée:", name)

ZONES = ["GUADELOUPE", "MARTINIQUE", "GUYANE", "REUNION"]
PRODUCTS = [
    ("BTP-CIM-001", "BTP", "Ciment gris 25 kg (palette 56 sacs)",
     "Ciment CEM II 32,5 R en sacs de 25 kg, palette filmée de 56 sacs. Usage maçonnerie générale.",
     "PALETTE", 42000, "6b396532ea3c49e1ce5b516808a0047d33aad690e1c1e62d5c2201a0f43af67c.jpeg", 1400.0, 1.2),
    ("BTP-FER-001", "BTP", "Fer à béton HA10 — botte de 50 barres 6 m",
     "Acier haute adhérence HA10, barres de 6 m, botte cerclée de 50 unités.",
     "BOTTE", 28500, "35c165ee4e335d380cd55bb725eaff32fb5be534fe7a251f25071c8afc0ad47d.jpeg", 185.0, 0.5),
    ("BTP-TOL-001", "BTP", "Tôles ondulées galvanisées 2 m (lot de 20)",
     "Tôles de couverture ondulées galvanisées 2 m, épaisseur 0,4 mm, lot de 20 plaques.",
     "LOT", 19800, "9aead258be1e317f1cae0d7a3c67ae9bbe0bbc2f88824b3cc704616e91c4375a.jpeg", 96.0, 0.4),
    ("AGR-ENG-001", "AGRICULTURE", "Engrais organique 20 kg (palette 40 sacs)",
     "Engrais organique NPK utilisable en agriculture biologique, sacs de 20 kg, palette de 40.",
     "PALETTE", 68000, "3962e6ecfee956db71b2d7854778d5ee55e36a60de423317a38ad95553a0fbe5.jpeg", 800.0, 1.0),
    ("AGR-SEM-001", "AGRICULTURE", "Assortiment semences maraîchères tropicales (100 sachets)",
     "Sélection de semences adaptées aux climats tropicaux : tomate, gombo, piment, concombre…",
     "CARTON", 24500, "5691475a9551d61245f841a94689aab41e7991cdb50740d4ec55f1c70e9579ea.jpeg", 6.0, 0.05),
    ("AGR-IRR-001", "AGRICULTURE", "Kit irrigation goutte-à-goutte 100 m",
     "Gaine goutte-à-goutte 100 m avec raccords, goutteurs et piquets — cultures maraîchères.",
     "KIT", 15900, "60eba864fe96f603ea1946f5adb9d9c5b7f013d06ccb3c1df5393ff4a85c030a.jpeg", 12.0, 0.08),
]

created = 0
for sku, cat, name, desc, unit, price, img, weight, vol in PRODUCTS:
    if db.products.find_one({"sku": sku}):
        continue
    pid = str(uuid.uuid4())
    db.products.insert_one({
        "id": pid, "sku": sku, "name": name, "description": desc,
        "category_id": cat_ids[cat], "unit": unit, "unit_quantity": 1,
        "min_order_qty": 1, "max_order_qty": 50, "status": "ACTIVE",
        "image_url": IMG + img, "incoterms": {z: ["CIF", "DAP"] for z in ZONES},
        "sale_model": "OSCOP_DIRECT_RESALE", "financing_eligible": True,
        "is_featured": False, "tags": [], "translations": {},
        "rating_avg": 0, "rating_count": 0,
        "weight_kg": weight, "volume_m3": vol, "supplier_id": None,
        "created_at": now, "updated_at": now,
    })
    for i, z in enumerate(ZONES):
        db.zone_prices.insert_one({
            "id": str(uuid.uuid4()), "product_id": pid, "zone_code": z,
            "price_ht_cents": price + i * 500, "price_type": "STANDARD",
            "original_price_ht_cents": None, "promo_start": None, "promo_end": None,
            "is_active": True, "created_at": now, "updated_at": now,
        })
    created += 1
    print("produit créé:", sku, name)

for code in cat_ids:
    db.categories.update_one({"code": code}, {"$set": {
        "product_count": db.products.count_documents({"category_id": cat_ids[code], "status": "ACTIVE"})}})
print(f"Terminé — {created} produits créés")
