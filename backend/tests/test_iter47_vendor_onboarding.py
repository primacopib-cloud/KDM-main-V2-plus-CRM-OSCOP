"""
Iter 47 — Communityplace : parcours d'adhésion Vendeur Pro (Stripe LIVE — pas de vrai paiement).

E2E semi-simulé :
  1) POST /vendor-onboarding/start  → checkout_url Stripe LIVE (pas de paiement)
  2) status forcé à PAID directement en base
  3) POST /{oid}/convention-fields  → INFO_COMPLETED
  4) POST /{oid}/sign               → SIGNED + verification_code
  5) GET  /{oid}/convention.pdf     → PDF 34 pages
  6) POST /activate token invalide  → 404
  7) POST /activate token valide    → access_token
  8) Régression login acheteur-pro
"""

import io
import os
import time

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://coop-dashboard-8.preview.emergentagent.com"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "kdmarche_lolodrive")

QA_EMAIL = "qa-vendeur@example.com"
QA_SIRET = "55208131766522"


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def http():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def onboarding(http, mongo_db):
    # cleanup any prior test onboarding for the QA email
    mongo_db.vendor_onboarding.delete_many({"email": QA_EMAIL})
    mongo_db.users.delete_many({"email": QA_EMAIL})

    payload = {
        "company": "TEST QA Vendeur Pro",
        "contact_name": "Marie QA",
        "email": QA_EMAIL,
        "phone": "0690000000",
        "siret": QA_SIRET,
        "plan_slug": "ess-acces-pro",
        "origin_url": BASE_URL,
    }
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/start", json=payload, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert "onboarding_id" in d and "checkout_url" in d
    assert d["checkout_url"].startswith("https://checkout.stripe.com/"), d["checkout_url"]

    oid = d["onboarding_id"]
    # doc created with PAYMENT_PENDING
    doc = mongo_db.vendor_onboarding.find_one({"id": oid})
    assert doc is not None
    assert doc["status"] == "PAYMENT_PENDING"

    # simulate PAID (Stripe LIVE — do NOT pay)
    mongo_db.vendor_onboarding.update_one(
        {"id": oid},
        {"$set": {"status": "PAID", "paid_at": "2026-01-01T00:00:00+00:00"}},
    )
    yield oid, d["checkout_url"]

    # teardown
    mongo_db.vendor_onboarding.delete_many({"email": QA_EMAIL})
    mongo_db.users.delete_many({"email": QA_EMAIL})


def test_1_start_creates_stripe_session(onboarding):
    oid, checkout_url = onboarding
    assert oid
    assert "checkout.stripe.com" in checkout_url


def test_2_convention_fields_before_paid_forbidden(http, mongo_db):
    # scenario: fresh onboarding still PAYMENT_PENDING → convention-fields should 400
    # Re-use QA row by resetting status quickly
    doc = mongo_db.vendor_onboarding.find_one({"email": QA_EMAIL})
    assert doc
    oid = doc["id"]
    mongo_db.vendor_onboarding.update_one({"id": oid}, {"$set": {"status": "PAYMENT_PENDING"}})
    body = {
        "capital": "10000", "rcs_ville": "Pointe-à-Pitre",
        "adresse": "Rue Test", "rep_nom": "QA", "rep_prenom": "Marie",
        "rep_qualite": "Gérante", "territoires": ["Guadeloupe"],
        "lieu_signature": "Baie-Mahault",
    }
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/{oid}/convention-fields", json=body, timeout=15)
    assert r.status_code == 400
    # restore PAID
    mongo_db.vendor_onboarding.update_one({"id": oid}, {"$set": {"status": "PAID"}})


def test_3_convention_fields_ok(http, onboarding):
    oid, _ = onboarding
    body = {
        "forme_sociale": "SARL",
        "capital": "10000",
        "rcs_ville": "Pointe-à-Pitre",
        "adresse": "12 rue des Cocotiers, 97110 Pointe-à-Pitre",
        "rep_nom": "QA", "rep_prenom": "Marie",
        "rep_qualite": "Gérante",
        "territoires": ["Guadeloupe", "Martinique"],
        "lieu_signature": "Baie-Mahault",
    }
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/{oid}/convention-fields", json=body, timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "INFO_COMPLETED"


def test_4_pdf_before_sign(http, onboarding):
    oid, _ = onboarding
    r = http.get(f"{BASE_URL}/api/vendor-onboarding/{oid}/convention.pdf", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    # Count pages via pypdf if available, else naive /Type /Page count
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(io.BytesIO(r.content)).pages)
    except Exception:
        pages = r.content.count(b"/Type /Page") - r.content.count(b"/Type /Pages")
    assert pages == 34, f"expected 34 pages, got {pages}"


def test_5_sign_convention(http, onboarding, mongo_db):
    oid, _ = onboarding
    body = {"nom": "Marie QA", "qualite": "Gérante", "lu_approuve": True}
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/{oid}/sign", json=body, timeout=30)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "SIGNED"
    assert d["verification_code"].startswith("CONV-")
    # DB: signature present, activation_token, user created
    doc = mongo_db.vendor_onboarding.find_one({"id": oid})
    assert doc["status"] == "SIGNED"
    assert doc.get("signature", {}).get("verification_code") == d["verification_code"]
    assert doc.get("activation_token")
    assert doc.get("user_id")
    user = mongo_db.users.find_one({"email": QA_EMAIL})
    assert user and user["is_active"] is False


def test_6_pdf_after_sign_34_pages(http, onboarding):
    oid, _ = onboarding
    r = http.get(f"{BASE_URL}/api/vendor-onboarding/{oid}/convention.pdf", timeout=30)
    assert r.status_code == 200
    try:
        from pypdf import PdfReader
        pages = len(PdfReader(io.BytesIO(r.content)).pages)
    except Exception:
        pages = r.content.count(b"/Type /Page") - r.content.count(b"/Type /Pages")
    assert pages == 34, f"expected 34 pages after signature, got {pages}"


def test_7_activate_invalid_token_404(http):
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/activate",
                  json={"token": "invalid-xxxxx", "password": "TestQA2026!"}, timeout=15)
    assert r.status_code == 404


def test_8_activate_valid_token(http, onboarding, mongo_db):
    oid, _ = onboarding
    doc = mongo_db.vendor_onboarding.find_one({"id": oid})
    token = doc.get("activation_token")
    assert token
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/activate",
                  json={"token": token, "password": "TestQA2026!"}, timeout=20)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("access_token")
    assert d["user"]["role"] == "vendor"
    assert d["user"]["email"] == QA_EMAIL
    # user is_active True
    user = mongo_db.users.find_one({"email": QA_EMAIL})
    assert user["is_active"] is True
    # onboarding ACTIVATED
    doc2 = mongo_db.vendor_onboarding.find_one({"id": oid})
    assert doc2["status"] == "ACTIVATED"


def test_9_assistant_requires_auth(http):
    r = http.post(f"{BASE_URL}/api/vendor-onboarding/assistant",
                  json={"question": "Comment soumettre un produit ?"}, timeout=15)
    assert r.status_code in (401, 403)


def test_10_login_buyer_regression(http):
    r = http.post(f"{BASE_URL}/api/auth/login",
                  json={"email": "acheteur-pro@kdmarche.fr", "password": "Demo2026!"}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d.get("access_token") or d.get("token")
