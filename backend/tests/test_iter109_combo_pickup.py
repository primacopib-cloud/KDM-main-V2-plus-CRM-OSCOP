"""Iter109 — Catalogue food_info, dépôt combo POP'S, cession, validation admin, fiche lot publique, retrait avec indisponibilité, étiquette PDF."""
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://oscop-platform-3.preview.emergentagent.com").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

POPS_EMAIL = "detaillant-test@kdmarche.fr"
POPS_PASSWORD = "Detaillant2026!"
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
INVESTOR_EMAIL = "invest.test.i@test.fr"
INVESTOR_PASSWORD = "InvestTest2026!"


@pytest.fixture(scope="module")
def mongo():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    yield db
    client.close()


def _login(session, email, password, portal=None):
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = session.post(f"{BASE_URL}/api/auth/login", json=body, timeout=20)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return data


@pytest.fixture(scope="module")
def pops_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, POPS_EMAIL, POPS_PASSWORD)
    return s


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    _login(s, ADMIN_EMAIL, ADMIN_PASSWORD, portal="admin")
    return s


@pytest.fixture(scope="module")
def pops_user_id(pops_session):
    r = pops_session.get(f"{BASE_URL}/api/profile", timeout=10)
    if r.status_code == 200:
        return r.json().get("id") or r.json().get("user", {}).get("id")
    # fallback via /auth/me
    r = pops_session.get(f"{BASE_URL}/api/auth/me", timeout=10)
    if r.status_code == 200:
        return r.json().get("id")
    return None


@pytest.fixture(scope="module")
def tracked(mongo):
    """Collect everything created so we can clean up at the end."""
    state = {"offer_ids": [], "auction_refs": [], "cession_ids": [], "credits_spent": 0,
             "lot_ids_test": [], "notif_ids": []}
    yield state
    # Teardown
    try:
        if state["offer_ids"]:
            # Get credits spent from offers before deleting
            spent = 0
            for oid in state["offer_ids"]:
                o = mongo.detaillant_offers.find_one({"id": oid}, {"cost_credits": 1, "user_id": 1})
                if o:
                    spent += int(o.get("cost_credits") or 0)
            if spent > 0:
                mongo.auction_accounts.update_one(
                    {"user_id": "user-detaillant-da978cfc"},
                    {"$inc": {"credits": spent}})
            mongo.detaillant_offers.delete_many({"id": {"$in": state["offer_ids"]}})
            mongo.detaillant_cessions.delete_many({"offer_id": {"$in": state["offer_ids"]}})
            mongo.auctions.delete_many({"detaillant_offer_id": {"$in": state["offer_ids"]}})
        if state["auction_refs"]:
            mongo.auctions.delete_many({"reference": {"$in": state["auction_refs"]}})
        if state["lot_ids_test"]:
            mongo.auctions.delete_many({"id": {"$in": state["lot_ids_test"]}})
        # Clean up any QA notifications
        mongo.notifications.delete_many({"data.reference": {"$regex": "^AUC-"}, "type": "AUCTION_PICKUP_INCIDENT",
                                         "created_at": {"$gte": "2026-01-01"}})
    except Exception as exc:
        print(f"Cleanup warning: {exc}")


# ============================================================
# P1 — Catalogue pré-rempli
# ============================================================

class TestCatalog:

    def test_catalog_has_food_info(self, pops_session):
        r = pops_session.get(f"{BASE_URL}/api/detaillant/catalog", timeout=15)
        assert r.status_code == 200, r.text
        products = r.json()["products"]
        by_sku = {p["sku"]: p for p in products}
        # At least 15 base products present
        required = ["CAFE-250G", "LAIT-1L", "THON-160G", "LP-CAP-CONFITURE-DE-GOYAV-53A0",
                    "RIZ-LONG-1KG", "PATES-500G", "FARINE-1KG", "HUILE-1L",
                    "SUCRE-CANNE-RE-1KG", "LENTILLES-500G", "HARICOTS-RGS-400G",
                    "POIS-ANGOLE-800G", "SARDINES-125G", "NECTAR-GOYAVE-1L", "SAUCE-TOMATE-400G"]
        for sku in required:
            assert sku in by_sku, f"SKU {sku} missing from catalogue"
            fi = by_sku[sku].get("food_info") or {}
            assert fi.get("format_label"), f"{sku} missing format_label"
            assert fi.get("ingredients"), f"{sku} missing ingredients"
            assert fi.get("allergens"), f"{sku} missing allergens"

    def test_catalog_specific_food_info(self, pops_session):
        r = pops_session.get(f"{BASE_URL}/api/detaillant/catalog", timeout=15)
        by_sku = {p["sku"]: p for p in r.json()["products"]}
        assert by_sku["CAFE-250G"]["food_info"]["format_label"] == "250 g"
        assert by_sku["CAFE-250G"]["food_info"]["allergens"] == "Aucun"
        assert by_sku["LAIT-1L"]["food_info"]["allergens"] == "Lait"
        assert by_sku["THON-160G"]["food_info"]["allergens"] == "Poisson"


# ============================================================
# P1 — Dépôt offre combo + validations
# ============================================================

def _combo_offer_body(unit_prices, lot_price=12.0, discount_pct=20.0, descr=None):
    """Build a COMPOSED offer body."""
    skus_meta = {
        "CAFE-250G": {"name": "Café moulu 250g", "fmt": "250 g", "val": 250, "unit": "g",
                      "ing": "Café moulu 100 %", "all": "Aucun"},
        "LP-CAP-CONFITURE-DE-GOYAV-53A0": {"name": "Confiture", "fmt": "250 g", "val": 250, "unit": "g",
                                            "ing": "Goyave, sucre, pectine", "all": "Aucun"},
        "LAIT-1L": {"name": "Lait", "fmt": "1 L", "val": 1, "unit": "L",
                    "ing": "Lait demi-écrémé UHT", "all": "Lait"},
        "RIZ-LONG-1KG": {"name": "Riz", "fmt": "1 kg", "val": 1, "unit": "kg",
                         "ing": "Riz long grain", "all": "Aucun"},
        "PATES-500G": {"name": "Pâtes", "fmt": "500 g", "val": 500, "unit": "g",
                       "ing": "Semoule de blé dur", "all": "Gluten (blé)"},
        "FARINE-1KG": {"name": "Farine", "fmt": "1 kg", "val": 1, "unit": "kg",
                       "ing": "Farine T55", "all": "Gluten (blé)"},
        "SUCRE-CANNE-RE-1KG": {"name": "Sucre", "fmt": "1 kg", "val": 1, "unit": "kg",
                                "ing": "Sucre de canne", "all": "Aucun"},
        "HUILE-1L": {"name": "Huile", "fmt": "1 L", "val": 1, "unit": "L",
                     "ing": "Huile de tournesol", "all": "Aucun"},
        "LENTILLES-500G": {"name": "Lentilles", "fmt": "500 g", "val": 500, "unit": "g",
                           "ing": "Lentilles vertes", "all": "Aucun"},
        "THON-160G": {"name": "Thon", "fmt": "160 g net", "val": 160, "unit": "g",
                       "ing": "Thon, eau, sel", "all": "Poisson"},
        "SARDINES-125G": {"name": "Sardines", "fmt": "125 g net", "val": 125, "unit": "g",
                           "ing": "Sardines, huile, sel", "all": "Poisson"},
        "SAUCE-TOMATE-400G": {"name": "Sauce tomate", "fmt": "400 g", "val": 400, "unit": "g",
                               "ing": "Tomates, sel", "all": "Aucun"},
    }
    skus = list(unit_prices.keys())
    items = []
    for sku in skus:
        m = skus_meta[sku]
        items.append({"sku": sku, "brand": "Marque Test", "format_label": m["fmt"],
                      "unit_price_ttc": unit_prices[sku],
                      "net_qty_value": m["val"], "net_qty_unit": m["unit"],
                      "ingredients": m["ing"], "allergens": m["all"]})
    return {
        "product_sku": skus[0], "lot_type": "COMPOSED",
        "product_skus": skus[1:], "qty_lots": 1,
        "description": descr or "QA combo lot test iter109 — composition café+confiture+lait",
        "category": "epicerie", "items_detail": items,
        "lot_price": lot_price, "currency": "EUR",
        "discount_mode": "PERCENT", "discount_value": discount_pct,
        "photo_main": "https://example.com/photo.jpg", "photos": [],
        "condition": "NEW",
    }


class TestOfferDeposit:

    def test_create_composed_offer_ok(self, pops_session, tracked):
        # lot_price=12, discount 20% -> final=9.60. Unit prices sum to 9.60.
        body = _combo_offer_body(
            unit_prices={"CAFE-250G": 5.00, "LP-CAP-CONFITURE-DE-GOYAV-53A0": 2.10, "LAIT-1L": 2.50},
            lot_price=12.0, discount_pct=20.0)
        r = pops_session.post(f"{BASE_URL}/api/detaillant/offers", json=body, timeout=20)
        assert r.status_code == 200, f"Expected 200 got {r.status_code}: {r.text}"
        offer = r.json()
        tracked["offer_ids"].append(offer["id"])
        tracked["credits_spent"] += int(offer.get("cost_credits") or 0)
        assert offer["lot_type"] == "COMPOSED"
        assert offer["final_price"] == 9.6
        # Check items_detail persisted with price_per_unit computed
        items = offer["items_detail"]
        assert len(items) == 3
        cafe = next(i for i in items if i["sku"] == "CAFE-250G")
        # 5.00 € / 0.25 kg = 20.00 €/kg
        assert cafe["price_per_unit"] == {"value": 20.0, "unit": "kg"}, cafe["price_per_unit"]

    def test_create_composed_offer_price_mismatch_400(self, pops_session):
        # Use different SKUs to avoid conflict with the OK offer still reserved
        body = _combo_offer_body(
            unit_prices={"RIZ-LONG-1KG": 5.00, "PATES-500G": 2.10, "FARINE-1KG": 5.00},
            lot_price=12.0, discount_pct=20.0,
            descr="QA mismatch sum != final price")
        r = pops_session.post(f"{BASE_URL}/api/detaillant/offers", json=body, timeout=15)
        assert r.status_code == 400, r.text
        assert "somme" in r.text.lower() or "égal" in r.text.lower() or "prix final" in r.text.lower()

    def test_create_composed_offer_missing_allergens_400(self, pops_session):
        body = _combo_offer_body(
            unit_prices={"THON-160G": 5.00, "SARDINES-125G": 2.10, "SAUCE-TOMATE-400G": 2.50},
            lot_price=12.0, discount_pct=20.0,
            descr="QA missing allergens")
        # Clear allergens on first item
        body["items_detail"][0]["allergens"] = ""
        r = pops_session.post(f"{BASE_URL}/api/detaillant/offers", json=body, timeout=15)
        assert r.status_code == 400, r.text
        assert "allerg" in r.text.lower() or "alimentair" in r.text.lower()

    def test_create_composed_offer_sku_conflict_409(self, pops_session, tracked):
        """Re-posting an offer with a SKU already reserved in another active lot → 409."""
        body = _combo_offer_body(
            unit_prices={"CAFE-250G": 5.00, "LP-CAP-CONFITURE-DE-GOYAV-53A0": 2.10, "LAIT-1L": 2.50},
            lot_price=12.0, discount_pct=20.0,
            descr="QA conflict re-deposit same sku")
        r = pops_session.post(f"{BASE_URL}/api/detaillant/offers", json=body, timeout=15)
        assert r.status_code == 409, f"Expected 409 got {r.status_code}: {r.text}"
        assert "réservée" in r.text.lower() or "reserv" in r.text.lower()


# ============================================================
# P1 — Cession signature + validation admin
# ============================================================

class TestCessionAndValidation:

    def test_sign_cession_and_approve(self, pops_session, admin_session, tracked, mongo):
        assert tracked["offer_ids"], "need offer from previous test"
        offer_id = tracked["offer_ids"][0]
        # GET cession
        r = pops_session.get(f"{BASE_URL}/api/detaillant/offers/{offer_id}/cession", timeout=10)
        assert r.status_code == 200, r.text
        cession = r.json()
        decls = cession["declarations"]
        assert len(decls) >= 1
        # Sign
        r = pops_session.post(
            f"{BASE_URL}/api/detaillant/offers/{offer_id}/cession/sign",
            json={"signer_name": "QA Signer Test", "declarations_checked": decls},
            timeout=10)
        assert r.status_code == 200, r.text
        assert r.json().get("status") == "SIGNED"

        # Admin approve
        r = admin_session.post(
            f"{BASE_URL}/api/admin/detaillant/offers/{offer_id}/review",
            json={"action": "APPROVE"}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        refs = data.get("auction_refs") or []
        assert len(refs) >= 1, data
        tracked["auction_refs"].extend(refs)

        # Verify auction created in DB with combo_items + lot_type + lot_price_ttc
        auc = mongo.auctions.find_one({"reference": refs[0]})
        assert auc is not None
        assert auc.get("lot_type") == "COMPOSED"
        assert auc.get("lot_price_ttc") == 9.6
        assert len(auc.get("combo_items") or []) == 3


# ============================================================
# P1 — Fiche lot publique
# ============================================================

class TestPublicLot:

    def test_public_lot_exposes_combo(self, tracked):
        assert tracked["auction_refs"], "need auction from approval"
        ref = tracked["auction_refs"][0]
        r = requests.get(f"{BASE_URL}/api/auctions/public/lot/{ref}", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["lot_type"] == "COMPOSED"
        assert data["lot_price_ttc"] == 9.6
        items = data["combo_items"]
        assert len(items) == 3
        skus = {i["sku"] for i in items}
        assert "CAFE-250G" in skus and "LAIT-1L" in skus
        cafe = next(i for i in items if i["sku"] == "CAFE-250G")
        assert cafe.get("unit_price_ttc") == 5.0
        assert cafe.get("ingredients")
        assert cafe.get("allergens")
        # price_per_unit present
        assert cafe.get("price_per_unit", {}).get("value") == 20.0


# ============================================================
# P1 — Retrait avec indisponibilité (pickup-scan)
# ============================================================

class TestPickupScanIncident:

    @pytest.fixture(scope="class")
    def forced_winner(self, mongo, tracked):
        """Force the auction into ENDED/WON with a known pickup token."""
        assert tracked["auction_refs"], "need auction"
        ref = tracked["auction_refs"][0]
        token = f"qa-token-combo-{uuid.uuid4().hex[:6]}"
        now = "2026-01-15T10:00:00+00:00"
        mongo.auctions.update_one(
            {"reference": ref},
            {"$set": {"status": "WON",
                      "winner": {"user_id": "qa-user-winner-iter109", "name": "QA Winner",
                                 "email": "qa.winner.iter109@example.com",
                                 "price_eur": 12.0, "pickup_token": token,
                                 "won_at": now}}})
        return ref, token

    def test_scan_preview_returns_combo(self, admin_session, forced_winner):
        ref, token = forced_winner
        r = admin_session.post(f"{BASE_URL}/api/admin/auctions/pickup-scan",
                               json={"code": token, "confirm": False}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["reference"] == ref
        assert data["lot_type"] == "COMPOSED"
        assert len(data["combo_items"]) == 3

    def test_scan_unknown_sku_400(self, admin_session, forced_winner):
        _, token = forced_winner
        r = admin_session.post(f"{BASE_URL}/api/admin/auctions/pickup-scan",
                               json={"code": token, "confirm": True,
                                     "missing_skus": ["SKU-FAKE-999"]}, timeout=15)
        assert r.status_code == 400, r.text

    def test_scan_all_missing_400(self, admin_session, forced_winner):
        _, token = forced_winner
        r = admin_session.post(f"{BASE_URL}/api/admin/auctions/pickup-scan",
                               json={"code": token, "confirm": True,
                                     "missing_skus": ["CAFE-250G", "LP-CAP-CONFITURE-DE-GOYAV-53A0", "LAIT-1L"]},
                               timeout=15)
        assert r.status_code == 400, r.text

    def test_scan_confirm_with_missing_lait(self, admin_session, forced_winner, mongo):
        ref, token = forced_winner
        r = admin_session.post(f"{BASE_URL}/api/admin/auctions/pickup-scan",
                               json={"code": token, "confirm": True,
                                     "missing_skus": ["LAIT-1L"]}, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        inc = data.get("pickup_incident")
        assert inc, data
        # lait 2.50 / lot 9.60 * paid 12.0 = 3.125 → but formula uses lot_price_ttc=9.60
        # 2.50/9.60 * 12.0 = 3.125 → round(,2) = 3.12 or 3.13
        assert 3.0 <= inc["credit_eur"] <= 3.2, inc["credit_eur"]
        # Verify notification created
        notif = mongo.notifications.find_one(
            {"type": "AUCTION_PICKUP_INCIDENT", "data.reference": ref})
        assert notif is not None, "notification not created"
        # Verify lot marked picked up
        auc = mongo.auctions.find_one({"reference": ref}, {"pickup_confirmed_at": 1, "pickup_incident": 1})
        assert auc.get("pickup_confirmed_at")

    def test_scan_reconfirm_409(self, admin_session, forced_winner):
        _, token = forced_winner
        r = admin_session.post(f"{BASE_URL}/api/admin/auctions/pickup-scan",
                               json={"code": token, "confirm": True,
                                     "missing_skus": ["CAFE-250G"]}, timeout=15)
        assert r.status_code == 409, r.text


# ============================================================
# P2 — Étiquette PDF
# ============================================================

class TestLabelPDF:

    def test_label_pdf_owner_200(self, pops_session, tracked):
        assert tracked["offer_ids"]
        offer_id = tracked["offer_ids"][0]
        r = pops_session.get(f"{BASE_URL}/api/detaillant/offers/{offer_id}/label.pdf", timeout=20)
        assert r.status_code == 200, r.text[:200]
        assert "application/pdf" in r.headers.get("content-type", "")
        assert len(r.content) > 1024, f"PDF too small: {len(r.content)}"

    def test_label_pdf_stranger_404(self, tracked):
        """Another member must not access the PDF."""
        assert tracked["offer_ids"]
        offer_id = tracked["offer_ids"][0]
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        _login(s, INVESTOR_EMAIL, INVESTOR_PASSWORD)
        r = s.get(f"{BASE_URL}/api/detaillant/offers/{offer_id}/label.pdf", timeout=15)
        assert r.status_code == 404, f"Expected 404 got {r.status_code}"
