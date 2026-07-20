"""Iter 60 — Lot 4 (bis): supply-risk, compare/pdf, remind-vendors (garde 24h), demand-forecast regression."""
import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")

ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PWD = "AdminKDM2025!"
BUYER_EMAIL = "acheteur-pro@kdmarche.fr"
BUYER_PWD = "Demo2026!"

SEED_CONS_A = "a9f6dc7b-9545-440c-b88e-8065563d5277"  # CONS-2026-0083
SEED_CONS_B = "a88078ad-852f-4576-b143-0b5be6fca818"  # CONS-2026-0084
SEED_CAMP = "85a62d49-19d1-474c-98c2-209de59e402b"


def _login(s, email, pwd, portal=None):
    body = {"email": email, "password": pwd}
    if portal:
        body["portal"] = portal
    r = s.post(f"{BASE_URL}/api/auth/login", json=body)
    assert r.status_code == 200, r.text
    return r


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    _login(s, ADMIN_EMAIL, ADMIN_PWD, portal="admin")
    return s


@pytest.fixture(scope="module")
def buyer_sess():
    s = requests.Session()
    _login(s, BUYER_EMAIL, BUYER_PWD)
    return s


@pytest.fixture(scope="module")
def anon_sess():
    return requests.Session()


# ------------- Supply Risk -------------
class TestSupplyRisk:
    def test_shape_and_expected_categories(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/supply-risk")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "categories" in d and isinstance(d["categories"], list)
        assert d["categories"], "supply-risk categories should not be empty"
        for c in d["categories"]:
            assert 5 <= c["risk_score"] <= 100
            assert c["risk_level"] in ("ELEVE", "MODERE", "FAIBLE")
            assert c["demand_trend"] in ("up", "down", "stable")
            assert "recommendation" in c and c["recommendation"]
            assert "eligible_vendors" in c
            assert "lots_6m" in c
        # sorted desc by risk_score
        scores = [c["risk_score"] for c in d["categories"]]
        assert scores == sorted(scores, reverse=True)

    def test_alimentaire_and_boissons_eleve(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/supply-risk")
        cats = {c["category"]: c for c in r.json()["categories"]}
        for target in ("alimentaire", "boissons"):
            assert target in cats, f"category {target} missing"
            c = cats[target]
            assert c["eligible_vendors"] == 1, f"{target} eligible_vendors={c['eligible_vendors']}"
            assert c["risk_score"] == 70, f"{target} score={c['risk_score']}"
            assert c["risk_level"] == "ELEVE"

    def test_requires_auth(self, anon_sess):
        r = anon_sess.get(f"{BASE_URL}/api/buyer-tools/supply-risk")
        assert r.status_code in (401, 403)


# ------------- Compare PDF -------------
class TestComparePdf:
    def test_pdf_ok(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare/pdf",
                           params={"a": SEED_CONS_A, "b": SEED_CONS_B})
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF", "content is not a PDF"
        # verify content contains refs
        try:
            from pypdf import PdfReader
            from io import BytesIO
            reader = PdfReader(BytesIO(r.content))
            text = "".join((p.extract_text() or "") for p in reader.pages)
            assert "CONS-2026-0083" in text
            assert "CONS-2026-0084" in text
            # 'Écarts constatés' section (may lose accent in extraction)
            assert "carts" in text or "Écarts" in text
        except ImportError:
            pass  # pypdf not installed; header check suffices

    def test_same_ids_400(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare/pdf",
                           params={"a": SEED_CONS_A, "b": SEED_CONS_A})
        assert r.status_code == 400

    def test_unknown_id_404(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/compare/pdf",
                           params={"a": SEED_CONS_A, "b": "nope-xxxx"})
        assert r.status_code == 404


# ------------- Remind Vendors (garde 24h) -------------
class TestRemindVendors24hGuard:
    def test_second_call_returns_409(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/campaigns/{SEED_CAMP}/remind-vendors")
        assert r.status_code == 409, f"expected 409 (24h guard), got {r.status_code} {r.text}"
        assert "24h" in r.text or "moins de 24" in r.text

    def test_unknown_campaign_404(self, admin_sess):
        r = admin_sess.post(f"{BASE_URL}/api/admin/campaigns/unknown-camp-id/remind-vendors")
        assert r.status_code == 404

    def test_buyer_forbidden(self, buyer_sess):
        r = buyer_sess.post(f"{BASE_URL}/api/admin/campaigns/{SEED_CAMP}/remind-vendors")
        assert r.status_code in (401, 403)


# ------------- Demand forecast regression -------------
class TestDemandForecastRegression:
    def test_transport_present(self, buyer_sess):
        r = buyer_sess.get(f"{BASE_URL}/api/buyer-tools/demand-forecast")
        assert r.status_code == 200
        d = r.json()
        assert len(d["months"]) == 6
        cats = {c["category"] for c in d["categories"]}
        assert "transport" in cats, f"transport must appear, got {cats}"
        for c in d["categories"]:
            assert len(c["series"]) == 6
            assert c["trend"] in ("up", "down", "stable")
