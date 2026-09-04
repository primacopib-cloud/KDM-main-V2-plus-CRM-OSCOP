import asyncio, os, sys
sys.path.insert(0, '/app/backend')
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')
from motor.motor_asyncio import AsyncIOMotorClient
from unittest.mock import patch, MagicMock, AsyncMock

async def main():
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ['DB_NAME']]
    import db as db_registry
    db_registry.set_database(db)

    await db.admin_payment_links.delete_many({"email": "recu-test@example.com"})
    await db.notifications.delete_many({"type": "payment_link_paid"})
    await db.admin_payment_links.insert_one({
        "id": "recu-test-1", "email": "recu-test@example.com", "amount_cents": 15050,
        "account_type": "BUYER_PRO", "description": "Cotisation 2026", "stripe_payment_link_id": "plink_fake_recu",
        "url": "https://buy.stripe.com/fake", "status": "pending", "created_at": "2026-09-04T00:00:00+00:00",
    })

    paid_session = MagicMock(payment_status="paid", id="cs_recu_1")
    def fake_list(api_key=None, payment_link=None, limit=5):
        return MagicMock(data=[paid_session] if payment_link == "plink_fake_recu" else [])

    sent_emails = []
    async def fake_send_email(to_email, to_name, subject, html, text_content=None, tags=None, attachments=None):
        sent_emails.append({"to": to_email, "subject": subject, "html": html, "tags": tags})
        return {"messageId": "fake-1"}

    import brevo_service
    from routes_admin_payment_links import check_pending_payment_links
    with patch("stripe.checkout.Session.list", side_effect=fake_list), \
         patch.object(brevo_service, "send_email", new=AsyncMock(side_effect=fake_send_email)):
        await check_pending_payment_links(db)
        await check_pending_payment_links(db)  # idempotence

    link = await db.admin_payment_links.find_one({"id": "recu-test-1"}, {"_id": 0})
    assert link["status"] == "paid" and link["detected_by"] == "cron", link["status"]
    print("OK 1: lien payé détecté (seul le lien de test ciblé, autres liens intacts)")

    assert len(sent_emails) == 1, sent_emails
    m = sent_emails[0]
    assert m["to"] == "recu-test@example.com"
    assert "Reçu de paiement" in m["subject"] and "150,50" in m["subject"], m["subject"]
    for needle in ["150,50 €", "Adhésion Acheteur Pro", "Cotisation 2026", "RECU-TES"[:8], "bonne réception"]:
        assert needle in m["html"], needle
    print("OK 2: reçu client envoyé —", m["subject"])

    assert link.get("receipt_sent_at"), "receipt_sent_at absent"
    hist = link.get("send_history", [])
    assert any(h["by"] == "reçu automatique" and h["to"] == "recu-test@example.com" for h in hist), hist
    print("OK 3: receipt_sent_at + trace 'reçu automatique' dans l'historique")

    n = await db.notifications.count_documents({"type": "payment_link_paid"})
    assert n == 1, n
    print("OK 4: 1 notification admin, idempotent au 2e run (1 seul email envoyé)")

    # vérifier qu'aucun autre lien n'a été touché
    other = await db.admin_payment_links.count_documents({"detected_by": "cron", "id": {"$ne": "recu-test-1"}})
    assert other == 0, other
    print("OK 5: aucun autre lien contaminé")

    await db.admin_payment_links.delete_many({"email": "recu-test@example.com"})
    await db.notifications.delete_many({"type": "payment_link_paid"})
    print("ALL RECEIPT TESTS PASSED (nettoyé)")

asyncio.run(main())
