"""
Iteration 6 sprint — backend tests:
- Catalog territory filter (GP/RE/GF/MQ): local products visible per DOM
- Brevo webhook IN + metrics summary (public endpoints)
- PASS auto-renew opt-in/out
- Referral codes (KDM-XXXXXX) lifecycle: create idempotent / claim / errors / stats admin
"""
import os
import pytest
import requests

def _resolve_base():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        try:
            with open("/app/frontend/.env") as f:
                for ln in f:
                    if ln.startswith("REACT_APP_BACKEND_URL="):
                        url = ln.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    assert url, "REACT_APP_BACKEND_URL not configured"
    return url.rstrip("/")


BASE_URL = _resolve_base()

ADMIN = ("admin@kdmarche-oscop.fr", "AdminKDM2025!")
MARIE = ("marie@example.com", "Demo2026!")
GERANT = ("gerant@lolopoint.fr", "Demo2026!")


def H(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token():
    return _login(*ADMIN)


@pytest.fixture(scope="session")
def marie_token():
    return _login(*MARIE)


@pytest.fixture(scope="session")
def gerant_token():
    return _login(*GERANT)


# ---------- Catalog territory filter (with local seeded products) ----------
class TestCatalogTerritoryLocal:
    def _products(self, token, territory):
        r = requests.get(f"{BASE_URL}/api/lolodrive/catalog/products?territory={territory}",
                         headers=H(token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        return data.get("products", data) if isinstance(data, dict) else data

    def test_gp_has_antilles_and_generic_no_re(self, marie_token):
        skus = {p["sku"] for p in self._products(marie_token, "GP")}
        # Generics (territories=[]) visible everywhere
        assert "LAIT-1L" in skus
        assert "HUILE-1L" in skus
        # Antilles products
        assert "RHUM-AGRICOLE-70CL" in skus
        assert "BANANE-1KG" in skus
        # No Réunion-only product
        assert "VANILLE-BOURBON-3G" not in skus
        assert "ACHARDS-LEGUMES-200G" not in skus
        assert "SUCRE-CANNE-RE-1KG" not in skus
        # No Guyane-only product
        assert "MANIOC-500G" not in skus
        assert "CACHIRI-1L" not in skus

    def test_re_has_reunion_and_generic(self, marie_token):
        skus = {p["sku"] for p in self._products(marie_token, "RE")}
        # All 3 RE products
        assert "VANILLE-BOURBON-3G" in skus
        assert "ACHARDS-LEGUMES-200G" in skus
        assert "SUCRE-CANNE-RE-1KG" in skus
        # Generics
        assert "LAIT-1L" in skus
        assert "HUILE-1L" in skus
        # No Antilles-only / Guyane-only
        assert "RHUM-AGRICOLE-70CL" not in skus
        assert "BANANE-1KG" not in skus
        assert "MANIOC-500G" not in skus

    def test_gf_has_guyane_and_generic_with_jus_mangue(self, marie_token):
        skus = {p["sku"] for p in self._products(marie_token, "GF")}
        # Guyane local
        assert "MANIOC-500G" in skus
        assert "CACHIRI-1L" in skus
        # Generics
        assert "RIZ-5KG" in skus
        assert "LAIT-1L" in skus
        # JUS-MANGUE includes GF in territories
        assert "JUS-MANGUE-1L" in skus

    def test_mq_excludes_manioc_and_vanille_keeps_oeufs_poulet(self, marie_token):
        skus = {p["sku"] for p in self._products(marie_token, "MQ")}
        assert "MANIOC-500G" not in skus
        assert "VANILLE-BOURBON-3G" not in skus
        assert "OEUFS-12" in skus
        assert "POULET-1KG" in skus


# ---------- Brevo webhook + metrics ----------
class TestBrevoWebhook:
    def test_webhook_post_list(self):
        payload = [
            {"event": "delivered", "email": "a@x.fr", "message-id": "m1"},
            {"event": "opened", "email": "a@x.fr", "message-id": "m1"},
            {"event": "hard_bounce", "email": "b@x.fr", "message-id": "m2"},
            {"event": "delivered", "email": "c@x.fr", "message-id": "m3"},
        ]
        r = requests.post(f"{BASE_URL}/api/brevo/webhook", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        assert body.get("received") == 4

    def test_metrics_summary(self):
        r = requests.get(f"{BASE_URL}/api/brevo/metrics/summary?days=30", timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("delivered", "bounced", "opened", "failures",
                  "delivery_rate", "bounce_rate", "open_rate", "by_event"):
            assert k in data, f"missing key {k} in metrics summary"
        assert data["delivered"] >= 2
        assert data["bounced"] >= 1
        assert data["opened"] >= 1
        assert isinstance(data["by_event"], dict)


# ---------- PASS auto-renew ----------
class TestPassAutoRenew:
    def test_enable_and_disable(self, marie_token):
        r1 = requests.post(f"{BASE_URL}/api/lolodrive/pass/auto-renew",
                           headers=H(marie_token), json={"enabled": True}, timeout=20)
        assert r1.status_code == 200, r1.text
        assert r1.json().get("is_auto_renew") is True

        # Verify persistence via my-pass / pass/me — try both
        r_me = requests.get(f"{BASE_URL}/api/lolodrive/pass/my-pass", headers=H(marie_token), timeout=20)
        if r_me.status_code != 200:
            r_me = requests.get(f"{BASE_URL}/api/lolodrive/pass/me", headers=H(marie_token), timeout=20)
        assert r_me.status_code == 200, r_me.text
        body = r_me.json()
        # is_auto_renew can be inside `pass` field or top-level
        ar = body.get("is_auto_renew")
        if ar is None and isinstance(body.get("pass"), dict):
            ar = body["pass"].get("is_auto_renew")
        assert ar is True, f"expected auto-renew True, got body {body}"

        r2 = requests.post(f"{BASE_URL}/api/lolodrive/pass/auto-renew",
                           headers=H(marie_token), json={"enabled": False}, timeout=20)
        assert r2.status_code == 200
        assert r2.json().get("is_auto_renew") is False


# ---------- Referral lifecycle ----------
@pytest.fixture(scope="class")
def marie_referral_code(marie_token):
    r = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/me", headers=H(marie_token), timeout=20)
    assert r.status_code == 200, r.text
    return r.json()["code"]


class TestReferral:
    def test_get_my_code_format_idempotent(self, marie_token):
        r1 = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/me", headers=H(marie_token), timeout=20)
        assert r1.status_code == 200
        c1 = r1.json()["code"]
        assert c1.startswith("KDM-")
        assert len(c1) == 10  # KDM- + 6 chars
        # idempotent
        r2 = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/me", headers=H(marie_token), timeout=20)
        assert r2.status_code == 200
        assert r2.json()["code"] == c1

    def test_claim_own_code_400(self, marie_token, marie_referral_code):
        r = requests.post(f"{BASE_URL}/api/lolodrive/pass/referral/claim",
                          headers=H(marie_token), json={"code": marie_referral_code}, timeout=20)
        assert r.status_code == 400, r.text

    def test_claim_invalid_code_404(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/lolodrive/pass/referral/claim",
                          headers=H(admin_token), json={"code": "KDM-NOPE99"}, timeout=20)
        assert r.status_code == 404, r.text

    def test_claim_success_and_credit(self, admin_token, marie_token, marie_referral_code):
        # admin claims marie's code → both wallets get +50 UC
        # Marie wallet baseline = 450; admin wallet has been ensured (0 baseline)
        r = requests.post(f"{BASE_URL}/api/lolodrive/pass/referral/claim",
                          headers=H(admin_token), json={"code": marie_referral_code}, timeout=20)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["bonus_uc_each"] == 50
        assert body["sponsor_credited"] is True
        assert body["referee_credited"] is True

        # Verify marie wallet went from 450 → 500
        r_me = requests.get(f"{BASE_URL}/api/lolodrive/pass/my-pass", headers=H(marie_token), timeout=20)
        if r_me.status_code == 200:
            data = r_me.json()
            wallet = data.get("wallet") or {}
            bal = wallet.get("balance_uc")
            if bal is not None:
                assert bal == 500, f"expected 500 UC for marie, got {bal}"

    def test_claim_twice_409(self, admin_token, marie_referral_code):
        r = requests.post(f"{BASE_URL}/api/lolodrive/pass/referral/claim",
                          headers=H(admin_token), json={"code": marie_referral_code}, timeout=20)
        assert r.status_code == 409, r.text

    def test_stats_admin(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/stats",
                         headers=H(admin_token), timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ("total_codes", "total_claims", "total_bonus_uc_distributed", "top_sponsors"):
            assert k in data
        assert data["total_codes"] >= 1
        assert data["total_claims"] >= 1
        assert data["total_bonus_uc_distributed"] == data["total_claims"] * 50 * 2
        assert isinstance(data["top_sponsors"], list)

    def test_stats_non_admin_403(self, gerant_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/stats",
                         headers=H(gerant_token), timeout=20)
        assert r.status_code == 403, r.text
