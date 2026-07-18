"""Test manuel : facture PDF + email Brevo + alerte crédits faibles."""
import asyncio
import logging
import os
import sys

logging.basicConfig(level=logging.INFO)

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    import routes_credit_packs as rcp
    import vendor_credits as vc
    import credit_promotions as cp
    rcp.db = db
    vc.db = db
    cp.db = db

    print("=== 1. Génération PDF facture ===")
    from pdf_credit_invoice import generate_credit_invoice_pdf
    vendor = await db.vendors.find_one({"id": "vendor-demo-pro"}, {"_id": 0})
    pack = await db.credit_packs.find_one({"id": "starter"}, {"_id": 0})
    pdf = generate_credit_invoice_pdf(vendor, pack, 55, 5, 9.90, "cs_test_MANUALTEST1234")
    assert pdf[:5] == b"%PDF-", "PDF invalide"
    with open("/tmp/test_facture.pdf", "wb") as f:
        f.write(pdf)
    print(f"PDF OK — {len(pdf)} octets, header %PDF- valide")

    print("\n=== 2. Envoi email facture (Brevo) ===")
    fake_tx = {
        "vendor_id": "vendor-demo-pro", "pack_id": "starter",
        "amount_cents": 990, "session_id": "cs_test_MANUALTEST1234",
    }
    await rcp._send_invoice_email(fake_tx, 50, 5, 55)
    print("Email facture envoyé (voir logs Brevo ci-dessus)")

    print("\n=== 3. Alerte crédits faibles via consume_credits (franchissement < 10) ===")
    test_id = "vendor-test-lowcredit"
    await db.vendors.delete_one({"id": test_id})
    await db.vendors.insert_one({
        "id": test_id, "company_name": "Test Alerte SARL", "contact_name": "Testeur",
        "email": "test-lowcredit@kdmarche.fr", "credits": 12, "status": "approved",
    })
    cost = await vc.consume_credits(test_id, "ai_image_generation", "Test franchissement seuil")
    print(f"Consommation: {cost} crédits (12 -> {12 - cost})")
    await asyncio.sleep(6)
    v = await db.vendors.find_one({"id": test_id}, {"_id": 0, "credits": 1})
    print(f"Solde final test vendor: {v['credits']}")
    await db.vendors.delete_one({"id": test_id})
    await db.credit_transactions.delete_many({"vendor_id": test_id})
    print("Nettoyage OK")


asyncio.run(main())
