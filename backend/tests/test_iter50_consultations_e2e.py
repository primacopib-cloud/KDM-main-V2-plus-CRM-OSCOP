"""
Iter 50 — Consultations Compétitives KDMARCHÉ/O'SCOP.
Tests E2E complet : CPC, matrice juridique, workflow consultation ENCHERE_INVERSEE, offres SCELLEES, gardes, exports/PV.
Stripe LIVE — jamais payer, on s'arrête à la vérification de l'URL checkout.stripe.com.
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://coop-dashboard-8.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASS = "AdminKDM2025!"
VENDOR_EMAIL = "vendor-pro@kdmarche.fr"
VENDOR_PASS = "Demo2026!"

TEST_CAT_GREEN = f"test-emballages-{uuid.uuid4().hex[:6]}"
TEST_CAT_RED = f"test-riz-{uuid.uuid4().hex[:6]}"

STATE = {}  # partagé entre tests


def _login(email, password, portal=None):
    body = {"email": email, "password": password}
    if portal:
        body["portal"] = portal
    r = requests.post(f"{BASE}/api/auth/login", json=body, timeout=30)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def admin_token():
    return _login(ADMIN_EMAIL, ADMIN_PASS, "admin")


@pytest.fixture(scope="module")
def vendor_token():
    return _login(VENDOR_EMAIL, VENDOR_PASS)


def H(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------------- CPC regression ----------------

class TestCPC:
    def test_packs(self):
        r = requests.get(f"{BASE}/api/cpc/packs", timeout=30)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 3
        by_credits = {p["credits"]: p["price_ht_cents"] for p in items}
        assert by_credits == {50: 2500, 150: 6000, 500: 15000}, f"packs unexpected: {by_credits}"

    def test_vendor_cpc_me(self, vendor_token):
        r = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "balance" in d and "status" in d
        STATE["initial_balance"] = d["balance"]

    def test_vendor_checkout_returns_stripe_url(self, vendor_token):
        r = requests.post(f"{BASE}/api/cpc/checkout",
                          json={"pack_id": "cpc-pack-50", "origin_url": BASE},
                          headers=H(vendor_token), timeout=60)
        assert r.status_code == 200, r.text
        url = r.json().get("checkout_url", "")
        assert "checkout.stripe.com" in url, f"expected Stripe checkout URL got {url}"
        STATE["stripe_session_id"] = r.json().get("session_id")

    def test_admin_cpc_settings(self, admin_token):
        r = requests.get(f"{BASE}/api/admin/cpc/settings", headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["standard_cost"] == 20
        assert d["interterritorial_cost"] == 40
        assert d["report_cost"] == 10

    def test_admin_grant_requires_reason(self, admin_token):
        r = requests.post(f"{BASE}/api/admin/cpc/grant",
                          json={"user_email": VENDOR_EMAIL, "credits": 10, "reason": ""},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 400, r.text


# ---------------- E2E Enchère inversée VERT ----------------

class TestEnchereInverseeE2E:
    def test_01_classify_green(self, admin_token):
        r = requests.post(f"{BASE}/api/admin/legal-matrix",
                          json={"scope": "category", "category": TEST_CAT_GREEN,
                                "status": "VERT",
                                "legal_reason": "Produit non essentiel — test iter50"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "VERT"

    def test_02_create_consultation(self, admin_token):
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter50 enchère verte",
                                "category": TEST_CAT_GREEN,
                                "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "Produit X"}],
                                "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["procedure"] == "ENCHERE_INVERSEE"
        assert d["legal_status"] == "VERT"
        assert d["status"] == "BROUILLON"
        assert d["cpc_cost"] == 20
        STATE["cid_green"] = d["id"]
        STATE["ref_green"] = d["ref"]

    def test_03_transition_en_validation(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "EN_VALIDATION"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_04_validate_commercial(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/validate/commercial",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "VALIDEE"

    def test_05_publish(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/publish",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "PUBLIEE"
        assert d.get("snapshot_hash")

    def test_06_transition_inscriptions_puis_encours(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "INSCRIPTIONS_OUVERTES"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "EN_COURS"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_07_admin_grant_cpc(self, admin_token):
        r = requests.post(f"{BASE}/api/admin/cpc/grant",
                          json={"user_email": VENDOR_EMAIL, "credits": 50, "reason": "test iter50"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        STATE["balance_after_grant"] = r.json()["balance"]

    def test_08_vendor_lists_consultation(self, vendor_token):
        r = requests.get(f"{BASE}/api/consultations", headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        cids = [c["id"] for c in r.json()["items"]]
        assert STATE["cid_green"] in cids

    def test_09_register_reject_no_accept(self, vendor_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": False}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 400, r.text

    def test_10_register_ok(self, vendor_token):
        cid = STATE["cid_green"]
        before = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": True}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        after = r.json()["balance"]
        assert before - after == 20, f"expected -20 CPC, got {before}->{after}"

    def test_11_register_duplicate_409(self, vendor_token):
        cid = STATE["cid_green"]
        before = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": True}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 409, r.text
        after = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        assert before == after, "duplicate registration must not debit"

    def test_12_bids_3_rounds(self, vendor_token):
        cid = STATE["cid_green"]
        for i, amt in enumerate([10000, 9000, 8000], start=1):
            r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                              json={"amount_ht_cents": amt}, headers=H(vendor_token), timeout=30)
            assert r.status_code == 200, f"round {i}: {r.text}"
            d = r.json()
            assert d["round"] == i
            assert d["rank"] == 1

    def test_13_bid_higher_rejected(self, vendor_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                          json={"amount_ht_cents": 8500}, headers=H(vendor_token), timeout=30)
        assert r.status_code in (400, 409), r.text

    def test_14_bid_4th_round_rejected(self, vendor_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                          json={"amount_ht_cents": 7000}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 409, r.text

    def test_15_my_status(self, vendor_token):
        cid = STATE["cid_green"]
        r = requests.get(f"{BASE}/api/consultations/{cid}/my-status", headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["rank"] == 1
        assert d["participants"] == 1
        assert d["gap_to_best_cents"] == 0

    def test_16_close_and_evaluate(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "CLOTUREE"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "EN_EVALUATION"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text

    def test_17_scores(self, admin_token):
        cid = STATE["cid_green"]
        # récupérer entry_id via admin bids
        r = requests.get(f"{BASE}/api/admin/consultations/{cid}/bids", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        entries = r.json()["entries"]
        assert len(entries) == 1
        entry_id = entries[0]["id"]
        STATE["entry_id_green"] = entry_id
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/scores",
                          json={"scores": [{"entry_id": entry_id,
                                            "criteria": {"qualite": 80, "disponibilite": 70,
                                                         "logistique": 60, "impact": 50,
                                                         "tracabilite": 90}}]},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        ranking = r.json()["ranking"]
        assert len(ranking) == 1
        top = ranking[0]
        # expected: prix=100*35% + qual80*20% + dispo70*15% + logi60*15% + impact50*10% + trac90*5%
        # = 35 + 16 + 10.5 + 9 + 5 + 4.5 = 80.0
        assert top["scores"]["prix"] == 100
        assert abs(top["total"] - 80.0) < 0.01, f"expected total 80.0, got {top['total']}"

    def test_18_award_and_attestation(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/award",
                          json={}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] == "ATTRIBUEE"
        assert d.get("attestation_id")
        STATE["attestation_id"] = d["attestation_id"]

    def test_19_winner_identity(self, vendor_token):
        cid = STATE["cid_green"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/winner-identity",
                          headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("winner")

    def test_20_pv_pdf(self, admin_token):
        cid = STATE["cid_green"]
        r = requests.get(f"{BASE}/api/admin/consultations/{cid}/pv.pdf",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
        assert r.status_code == 200, r.text[:500]
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert len(r.content) > 500
        assert r.content[:4] == b"%PDF"

    def test_21_export_csv_json(self, admin_token):
        cid = STATE["cid_green"]
        for kind in ("export.csv", "export.json"):
            r = requests.get(f"{BASE}/api/admin/consultations/{cid}/{kind}",
                             headers={"Authorization": f"Bearer {admin_token}"}, timeout=30)
            assert r.status_code == 200, f"{kind}: {r.text[:200]}"
            assert len(r.content) > 20

    def test_22_audit_verify(self, admin_token):
        r = requests.get(f"{BASE}/api/admin/cpc/audit/verify", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("valid") is True


# ---------------- Offres SCELLEES (catégorie ROUGE) ----------------

class TestSealedRed:
    def test_01_classify_red(self, admin_token):
        r = requests.post(f"{BASE}/api/admin/legal-matrix",
                          json={"scope": "category", "category": TEST_CAT_RED,
                                "status": "ROUGE",
                                "legal_reason": "Produit essentiel L.442-8 III — test iter50"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        assert r.json()["status"] == "ROUGE"

    def test_02_create_forces_sealed(self, admin_token):
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter50 scellée rouge",
                                "category": TEST_CAT_RED,
                                "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "Riz local"}],
                                "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["legal_status"] == "ROUGE"
        assert d["procedure"] == "SCELLEE", f"ROUGE must force SCELLEE, got {d['procedure']}"
        STATE["cid_red"] = d["id"]

    def test_03_workflow_to_en_cours(self, admin_token):
        cid = STATE["cid_red"]
        for target in ("EN_VALIDATION",):
            requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": target}, headers=H(admin_token), timeout=30)
        requests.post(f"{BASE}/api/admin/consultations/{cid}/validate/commercial",
                      headers=H(admin_token), timeout=30)
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/publish",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        for target in ("INSCRIPTIONS_OUVERTES", "EN_COURS"):
            r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                              json={"to": target}, headers=H(admin_token), timeout=30)
            assert r.status_code == 200, r.text

    def test_04_register_and_seal_bid(self, vendor_token):
        cid = STATE["cid_red"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": True}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                          json={"amount_ht_cents": 12000}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("sealed") is True
        assert d.get("fingerprint")
        STATE["fp1"] = d["fingerprint"]

    def test_05_admin_bids_403_before_close(self, admin_token):
        cid = STATE["cid_red"]
        r = requests.get(f"{BASE}/api/admin/consultations/{cid}/bids",
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code} {r.text[:200]}"

    def test_06_replace_bid(self, vendor_token):
        cid = STATE["cid_red"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/bid",
                          json={"amount_ht_cents": 11000}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("sealed") is True
        assert r.json().get("fingerprint") != STATE["fp1"]

    def test_07_close_manual_and_bids_visible(self, admin_token):
        cid = STATE["cid_red"]
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "CLOTUREE"}, headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        r = requests.get(f"{BASE}/api/admin/consultations/{cid}/bids",
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        entries = r.json()["entries"]
        assert len(entries) == 1
        latest_bid = entries[0].get("bid")
        # NOTE: la review précise que la clôture MANUELLE peut laisser les scellées non ouvertes → BUG à signaler
        if latest_bid is None or latest_bid.get("amount_ht_cents") is None:
            pytest.fail("BUG SIGNALÉ (review): après clôture MANUELLE, les offres scellées ne sont pas déchiffrées automatiquement. amount_ht_cents=None")
        assert latest_bid["amount_ht_cents"] == 11000, f"expected replacement amount 11000, got {latest_bid.get('amount_ht_cents')}"


# ---------------- Gardes régression lot 1.3 ----------------

class TestGuards:
    def test_publish_non_classified_blocked(self, admin_token):
        cat = f"test-unknown-{uuid.uuid4().hex[:6]}"
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter50 non classée", "category": cat,
                                "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "X"}], "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200
        cid = r.json()["id"]
        STATE["cid_unclass"] = cid
        assert r.json()["legal_status"] == "NON_CLASSE"
        requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                      json={"to": "EN_VALIDATION"}, headers=H(admin_token))
        requests.post(f"{BASE}/api/admin/consultations/{cid}/validate/commercial",
                      headers=H(admin_token))
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/publish",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 409, r.text
        assert "non classée" in r.text.lower() or "matrice" in r.text.lower()

    def test_locked_after_publish_criteria(self, admin_token):
        # utilise cid_red qui est CLOTUREE
        cid = STATE.get("cid_red")
        if not cid:
            pytest.skip("cid_red missing")
        r = requests.put(f"{BASE}/api/admin/consultations/{cid}",
                         json={"criteria": [{"key": "prix", "label": "P", "weight": 100}]},
                         headers=H(admin_token), timeout=30)
        assert r.status_code == 409, r.text

    def test_cancel_refunds_cpc(self, admin_token, vendor_token):
        # top up vendor for this test
        requests.post(f"{BASE}/api/admin/cpc/grant",
                      json={"user_email": VENDOR_EMAIL, "credits": 50, "reason": "test iter50 cancel"},
                      headers=H(admin_token), timeout=30)
        # crée une consultation VERT, publie, ouvre, vendor s'inscrit, ANNULEE → recrédit
        opens = datetime.now(timezone.utc).isoformat()
        closes = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        r = requests.post(f"{BASE}/api/admin/consultations",
                          json={"title": "TEST_iter50 annulation",
                                "category": TEST_CAT_GREEN,  # déjà VERT
                                "procedure": "ENCHERE_INVERSEE",
                                "products": [{"label": "Y"}], "territories": ["GUADELOUPE"],
                                "opens_at": opens, "closes_at": closes},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        STATE["cid_cancel"] = cid
        requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                      json={"to": "EN_VALIDATION"}, headers=H(admin_token))
        requests.post(f"{BASE}/api/admin/consultations/{cid}/validate/commercial",
                      headers=H(admin_token))
        rpub = requests.post(f"{BASE}/api/admin/consultations/{cid}/publish", headers=H(admin_token))
        assert rpub.status_code == 200, rpub.text
        requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                      json={"to": "INSCRIPTIONS_OUVERTES"}, headers=H(admin_token))
        # vendor inscription
        before = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        r = requests.post(f"{BASE}/api/consultations/{cid}/register",
                          json={"accept_rules": True}, headers=H(vendor_token), timeout=30)
        assert r.status_code == 200, r.text
        mid = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        assert mid == before - 20
        # ANNULEE
        r = requests.post(f"{BASE}/api/admin/consultations/{cid}/transition",
                          json={"to": "ANNULEE", "reason": "test iter50 annulation"},
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        assert r.json().get("cpc_refunded_entries") == 1
        after = requests.get(f"{BASE}/api/cpc/me", headers=H(vendor_token)).json()["balance"]
        assert after == before, f"refund failed: {before} → {mid} → {after}"


# ---------------- Cleanup ----------------

class TestZCleanup:
    """Nettoyage : suppression consultations, entries, bids, legal_matrix créés."""

    def test_cleanup(self):
        # cleanup via mongo directement
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            import asyncio
            mongo = os.environ.get("MONGO_URL")
            dbname = os.environ.get("DB_NAME")
            if not mongo or not dbname:
                pytest.skip("MONGO_URL/DB_NAME not accessible from this env")
            client = AsyncIOMotorClient(mongo)
            db = client[dbname]

            cids = [STATE.get(k) for k in ("cid_green", "cid_red", "cid_unclass", "cid_cancel") if STATE.get(k)]

            async def do():
                for cid in cids:
                    await db.consultations.delete_many({"id": cid})
                    await db.consultation_entries.delete_many({"consultation_id": cid})
                    await db.bids.delete_many({"consultation_id": cid})
                    await db.consultation_awards.delete_many({"consultation_id": cid})
                    await db.consultation_pv.delete_many({"consultation_id": cid})
                    await db.nominative_attestations.delete_many({"consultation_id": cid})
                    await db.winner_identity_requests.delete_many({"consultation_id": cid})
                await db.legal_matrix.delete_many({"category": {"$in": [TEST_CAT_GREEN, TEST_CAT_RED]}})

            asyncio.get_event_loop().run_until_complete(do())
            print(f"Cleanup: deleted {len(cids)} consultations + legal_matrix entries")
        except Exception as e:
            print(f"Cleanup skipped: {e}")
