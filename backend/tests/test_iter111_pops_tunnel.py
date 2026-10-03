"""Iter111 — Régression TUNNEL DE DÉPÔT POP'S (COOP'ACT) :
- cancel J+30 (409 avant, OK après, re-cancel 409)
- modèles réutilisables (save-template APPROVED ok, PENDING 409, list, delete)
- brouillon serveur multi-appareils (PUT/GET/DELETE)
- contrôle photo IA négatif (fail-open accepté)
Pas de POST /api/detaillant/offers (coût crédits + LLM) — seed direct en DB.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

POPS_EMAIL = "detaillant-test@kdmarche.fr"
POPS_PASSWORD = "Detaillant2026!"
POPS_USER_ID = "user-detaillant-da978cfc"

OFFER_CANCEL = "qa-off-tun1"
OFFER_CANCEL_UI = "qa-off-tun2"
OFFER_TPL = "qa-off-tun3"


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def pops():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": POPS_EMAIL, "password": POPS_PASSWORD}, timeout=20)
    assert r.status_code == 200, f"login POPS: {r.status_code} {r.text}"
    tok = r.json().get("access_token") or r.json().get("token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module", autouse=True)
def cleanup(db):
    """Pre + post cleanup : offres QA, templates, draft, 3 crédits remboursés."""
    def _wipe():
        db.detaillant_offers.delete_many({"id": {"$in": [OFFER_CANCEL, OFFER_CANCEL_UI, OFFER_TPL]}})
        db.detaillant_offer_templates.delete_many({"user_id": POPS_USER_ID})
        db.detaillant_offer_drafts.delete_many({"user_id": POPS_USER_ID})
    _wipe()
    yield
    _wipe()
    # Décrément des 3 crédits remboursés par le test cancel (si cycle OK a tourné)
    db.auction_accounts.update_one(
        {"user_id": POPS_USER_ID}, {"$inc": {"credits": -3}}, upsert=False)


def _seed_offer(db, oid: str, status: str, created_at_iso: str, extra: dict = None):
    doc = {
        "id": oid, "user_id": POPS_USER_ID, "status": status,
        "created_at": created_at_iso, "cost_credits": 3,
        "product_name": "QA tunnel", "product_sku": "CAFE-250G",
        "lot_type": "SAME", "qty_lots": 1, "lot_price": 10, "currency": "EUR",
        "discount_mode": "PERCENT", "discount_value": 15, "condition": "NEW",
        "description": "desc QA tunnel", "photo_main": "https://via.placeholder.com/300",
        "photos": [], "product_skus": [],
    }
    if extra:
        doc.update(extra)
    db.detaillant_offers.update_one({"id": oid}, {"$set": doc}, upsert=True)


# ---------- P1 — Annulation J+30 ----------

class TestCancelJ30:
    def test_cancel_fresh_offer_409(self, db, pops):
        _seed_offer(db, OFFER_CANCEL, "PENDING", datetime.now(timezone.utc).isoformat())
        r = pops.post(f"{BASE_URL}/api/detaillant/offers/{OFFER_CANCEL}/cancel", timeout=20)
        assert r.status_code == 409, f"attendu 409, got {r.status_code} {r.text}"
        assert "J+30" in r.text or "30" in r.text

    def test_cancel_backdated_ok_refund_3(self, db, pops):
        backdated = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        db.detaillant_offers.update_one(
            {"id": OFFER_CANCEL}, {"$set": {"created_at": backdated, "status": "PENDING"}})
        before = db.auction_accounts.find_one({"user_id": POPS_USER_ID}) or {}
        credits_before = int(before.get("credits") or 0)
        r = pops.post(f"{BASE_URL}/api/detaillant/offers/{OFFER_CANCEL}/cancel", timeout=20)
        assert r.status_code == 200, f"attendu 200, got {r.status_code} {r.text}"
        data = r.json()
        assert data.get("ok") is True
        assert data.get("refunded_credits") == 3
        after = db.auction_accounts.find_one({"user_id": POPS_USER_ID}) or {}
        assert int(after.get("credits") or 0) == credits_before + 3

    def test_recancel_409_already_cancelled(self, pops):
        r = pops.post(f"{BASE_URL}/api/detaillant/offers/{OFFER_CANCEL}/cancel", timeout=20)
        assert r.status_code == 409
        assert "attente" in r.text.lower()


# ---------- P2 — Modèles réutilisables ----------

class TestTemplates:
    def test_save_template_pending_409(self, db, pops):
        _seed_offer(db, OFFER_TPL, "PENDING", datetime.now(timezone.utc).isoformat())
        r = pops.post(f"{BASE_URL}/api/detaillant/offers/{OFFER_TPL}/save-template", timeout=20)
        assert r.status_code == 409

    def test_save_template_approved_ok(self, db, pops):
        items = [{"sku": "CAFE-250G", "name": "Café moulu 250g", "brand": "X",
                  "format_label": "250 g", "unit_price_ttc": None, "price_per_unit": None,
                  "ingredients": "café", "allergens": "Aucun"}]
        db.detaillant_offers.update_one(
            {"id": OFFER_TPL},
            {"$set": {"status": "APPROVED", "product_name": "Combo QA modèle",
                      "items_detail": items}})
        r = pops.post(f"{BASE_URL}/api/detaillant/offers/{OFFER_TPL}/save-template", timeout=20)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        assert r.json().get("ok") is True

    def test_list_templates_contains(self, pops):
        r = pops.get(f"{BASE_URL}/api/detaillant/templates", timeout=20)
        assert r.status_code == 200
        items = r.json().get("templates") or []
        names = [t.get("name") for t in items]
        assert "Combo QA modèle" in names

    def test_delete_template(self, pops):
        r = pops.get(f"{BASE_URL}/api/detaillant/templates", timeout=20)
        tpls = [t for t in r.json().get("templates") or [] if t.get("name") == "Combo QA modèle"]
        assert tpls, "modèle non trouvé"
        tid = tpls[0]["id"]
        r2 = pops.delete(f"{BASE_URL}/api/detaillant/templates/{tid}", timeout=20)
        assert r2.status_code == 200
        assert r2.json().get("ok") is True


# ---------- P2 — Brouillon serveur multi-appareils ----------

class TestServerDraft:
    def test_put_draft(self, pops):
        payload = {"draft": {"f": {"product_sku": "CAFE-250G"},
                             "saved_at": "2099-01-01T00:00:00"}}
        r = pops.put(f"{BASE_URL}/api/detaillant/offer-draft", json=payload, timeout=20)
        assert r.status_code == 200
        assert r.json().get("ok") is True
        assert r.json().get("updated_at")

    def test_get_draft(self, pops):
        r = pops.get(f"{BASE_URL}/api/detaillant/offer-draft", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert data.get("draft") is not None
        assert data["draft"]["f"]["product_sku"] == "CAFE-250G"
        assert data.get("updated_at")

    def test_delete_draft(self, pops):
        r = pops.delete(f"{BASE_URL}/api/detaillant/offer-draft", timeout=20)
        assert r.status_code == 200
        r2 = pops.get(f"{BASE_URL}/api/detaillant/offer-draft", timeout=20)
        assert r2.status_code == 200
        assert r2.json().get("draft") is None


# ---------- P2 — Seed UI cancel button disabled < J+30 ----------

class TestUICancelSeed:
    def test_seed_pending_fresh_for_ui(self, db):
        _seed_offer(db, OFFER_CANCEL_UI, "PENDING", datetime.now(timezone.utc).isoformat())
        assert db.detaillant_offers.find_one({"id": OFFER_CANCEL_UI})


# ---------- P3 — Contrôle photo IA (1 seul appel LLM) ----------

class TestPhotoAI:
    def test_check_photo_ai_off_topic(self):
        """Image hors sujet (og-image) vs 'Café moulu 250g' → ok=False (ou skipped=fail-open)."""
        # charger EMERGENT_LLM_KEY depuis backend/.env si manquant
        if not os.environ.get("EMERGENT_LLM_KEY"):
            try:
                with open("/app/backend/.env") as fh:
                    for line in fh:
                        if line.startswith("EMERGENT_LLM_KEY="):
                            os.environ["EMERGENT_LLM_KEY"] = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass
        sys.path.insert(0, "/app/backend")
        from routes_detaillant import _check_photo_ai
        result = asyncio.get_event_loop().run_until_complete(
            _check_photo_ai("https://oscop-platform-3.preview.emergentagent.com/og-image.jpg",
                            ["Café moulu 250g"]))
        print(f"PHOTO AI VERDICT: {result}")
        if result.get("skipped"):
            pytest.skip(f"fail-open (réseau/LLM indispo): {result.get('skipped')}")
        assert result.get("ok") is False, f"attendu ok=False, got {result}"
        assert result.get("reason"), "reason doit être non vide"
