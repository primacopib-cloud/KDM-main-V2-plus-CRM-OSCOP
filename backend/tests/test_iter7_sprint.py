"""
Iteration 7 sprint — backend tests:
- Brevo metrics summary `days` filter (clamp + correct cutoff)
- Auto-renew batch (admin endpoint): dict format, throttle, payment_transactions tx
- Idempotent wallet ledger upsert (wallet_id, ref_id) — 3x replay = 1 credit
- Unique index (wallet_id, ref_id) on lolodrive_wallet_ledger
- 403 for non-admin auto-renew-batch
"""
import os
import asyncio
from datetime import datetime, timedelta

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


def H(t):
    return {"Authorization": f"Bearer {t}", "Content-Type": "application/json"}


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": email, "password": password}, timeout=20)
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


# ------------------------------------------------------------------
# Helper: direct DB access for setup / verification (uses backend env)
# ------------------------------------------------------------------
def _get_db():
    from pymongo import MongoClient
    mongo_url = None
    db_name = None
    with open("/app/backend/.env") as f:
        for ln in f:
            if ln.startswith("MONGO_URL="):
                mongo_url = ln.split("=", 1)[1].strip().strip('"')
            elif ln.startswith("DB_NAME="):
                db_name = ln.split("=", 1)[1].strip().strip('"')
    assert mongo_url and db_name, "MONGO_URL / DB_NAME required in backend/.env"
    return MongoClient(mongo_url)[db_name]


# ========== Brevo metrics summary days filter ==========
class TestBrevoMetricsDaysFilter:
    def test_days_clamps_to_min_1(self):
        for d in (0, -5, -100):
            r = requests.get(f"{BASE_URL}/api/brevo/metrics/summary?days={d}", timeout=20)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["days"] == 1, f"days={d} should clamp to 1, got {data['days']}"

    def test_days_clamps_to_max_365(self):
        r = requests.get(f"{BASE_URL}/api/brevo/metrics/summary?days=9999", timeout=20)
        assert r.status_code == 200
        assert r.json()["days"] == 365

    def test_days_1_vs_30_today_events_equal(self):
        """All test events are inserted today, so days=1 and days=30 should return same totals."""
        # Seed a known event via webhook to ensure data exists
        seed = [{"event": "delivered", "email": "iter7@test.fr", "message-id": "iter7-m1"}]
        rs = requests.post(f"{BASE_URL}/api/brevo/webhook", json=seed, timeout=20)
        assert rs.status_code == 200

        r1 = requests.get(f"{BASE_URL}/api/brevo/metrics/summary?days=1", timeout=20)
        r30 = requests.get(f"{BASE_URL}/api/brevo/metrics/summary?days=30", timeout=20)
        assert r1.status_code == 200 and r30.status_code == 200
        d1 = r1.json()
        d30 = r30.json()
        # Both must have data > 0 and today's events show up in both windows
        assert d1["delivered"] > 0
        assert d30["delivered"] > 0
        # With today-only events the totals must be equal
        assert d1["delivered"] == d30["delivered"]
        assert d1["by_event"] == d30["by_event"]


# ========== Auto-renew batch admin endpoint ==========
class TestAutoRenewBatch:
    ENDPOINT = "/api/lolodrive/admin/notifications/auto-renew-batch"

    def test_non_admin_403(self, gerant_token):
        r = requests.post(f"{BASE_URL}{self.ENDPOINT}", headers=H(gerant_token), timeout=30)
        assert r.status_code == 403, r.text

    def test_returns_dict_with_sent_skipped(self, admin_token):
        # No PASS matches in default seed (marie's PASS is far in the future) → sent=0
        # First, ensure marie's PASS is NOT in renew window (push ends_at to +60 days)
        db = _get_db()
        far_future = datetime.utcnow() + timedelta(days=60)
        db.lolodrive_passes.update_many(
            {},
            {"$set": {"ends_at": far_future, "renew_email_sent_at": None}},
        )
        r = requests.post(f"{BASE_URL}{self.ENDPOINT}", headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, dict)
        assert "sent" in data and "skipped" in data
        assert data["sent"] == 0
        assert data["skipped"] == 0

    def test_marie_pass_in_window_sends_email(self, admin_token, marie_token):
        """Set marie's PASS ends_at to +20h, is_auto_renew=true, renew_email_sent_at=None.
        Batch should send 1 email and create a payment_transactions entry."""
        db = _get_db()
        # Find marie's user id
        marie = db.users.find_one({"email": MARIE[0]}, {"_id": 0, "id": 1})
        assert marie, "marie user not found"
        marie_id = marie["id"]
        ends_at_target = datetime.utcnow() + timedelta(hours=20)
        upd = db.lolodrive_passes.update_one(
            {"user_id": marie_id},
            {"$set": {
                "ends_at": ends_at_target,
                "is_auto_renew": True,
                "status": "ACTIVE",
                "renew_email_sent_at": None,
            }},
        )
        assert upd.matched_count >= 1, "marie's PASS not found"

        # Baseline: delivered count via webhook metrics + payment_transactions count
        pt_before = db.payment_transactions.count_documents({"user_id": marie_id, "auto_renew": True, "kind": "PASS"})

        r = requests.post(f"{BASE_URL}{self.ENDPOINT}", headers=H(admin_token), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["sent"] >= 1, f"expected sent>=1, got {data}"

        # payment_transactions must contain new entry
        pt_after = db.payment_transactions.count_documents({"user_id": marie_id, "auto_renew": True, "kind": "PASS"})
        assert pt_after > pt_before, f"payment_transactions not incremented ({pt_before}→{pt_after})"
        tx = db.payment_transactions.find_one(
            {"user_id": marie_id, "auto_renew": True, "kind": "PASS"},
            sort=[("created_at", -1)],
        )
        assert tx, "no PT row found"
        assert tx["payment_status"] == "initiated"
        assert tx.get("auto_renew") is True
        assert tx.get("kind") == "PASS"

        # The PASS now has renew_email_sent_at populated
        p = db.lolodrive_passes.find_one({"user_id": marie_id}, {"_id": 0})
        assert p.get("renew_email_sent_at") is not None

    def test_batch_throttle_replay(self, admin_token):
        """Re-trigger immediately: renew_email_sent_at is recent (<7d) → sent=0."""
        r = requests.post(f"{BASE_URL}/api/lolodrive/admin/notifications/auto-renew-batch",
                          headers=H(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["sent"] == 0, f"throttle failed, got {data}"


# ========== Idempotency wallet ledger ==========
class TestWalletLedgerIdempotency:
    def test_unique_index_present(self):
        db = _get_db()
        idx = list(db.lolodrive_wallet_ledger.list_indexes())
        # Find one with key (wallet_id, ref_id)
        matches = [
            i for i in idx
            if list(i.get("key", {}).keys()) == ["wallet_id", "ref_id"]
        ]
        assert matches, f"unique index (wallet_id, ref_id) missing. found indexes: {[i.get('name') for i in idx]}"
        assert matches[0].get("unique") is True, "index is not unique"

    def test_upsert_3x_replay_credits_once(self):
        """Simulate the credit loop being retried: 3x update_one upsert with same (wallet_id, ref_id)
        → only the 1st insert increments balance; the next 2 are no-op."""
        db = _get_db()
        import secrets as _secrets
        # Use marie's wallet
        marie = db.users.find_one({"email": MARIE[0]}, {"_id": 0, "id": 1})
        wallet = db.lolodrive_wallets.find_one({"user_id": marie["id"]}, {"_id": 0})
        assert wallet, "marie's wallet missing"

        ref_id = f"TEST-IDEMP-{_secrets.token_hex(4)}"
        bal_start = wallet["balance_uc"]
        BONUS = 50

        for i in range(3):
            result = db.lolodrive_wallet_ledger.update_one(
                {"wallet_id": wallet["id"], "ref_id": ref_id},
                {"$setOnInsert": {
                    "id": _secrets.token_hex(8),
                    "wallet_id": wallet["id"],
                    "ref_id": ref_id,
                    "type": "CREDIT",
                    "amount_uc": BONUS,
                    "reason": "TEST_IDEMPOTENCY",
                }},
                upsert=True,
            )
            if result.upserted_id is not None:
                # Only the 1st iteration should reach here
                assert i == 0, f"unexpected upsert on iteration {i}"
                db.lolodrive_wallets.update_one(
                    {"id": wallet["id"]},
                    {"$inc": {"balance_uc": BONUS}},
                )

        # Verify exactly 1 ledger row
        rows = list(db.lolodrive_wallet_ledger.find({"wallet_id": wallet["id"], "ref_id": ref_id}))
        assert len(rows) == 1, f"expected 1 ledger row, got {len(rows)}"

        # Verify wallet balance only +50
        wallet_now = db.lolodrive_wallets.find_one({"id": wallet["id"]})
        assert wallet_now["balance_uc"] == bal_start + BONUS, (
            f"expected balance {bal_start + BONUS}, got {wallet_now['balance_uc']}"
        )

        # Cleanup
        db.lolodrive_wallet_ledger.delete_one({"wallet_id": wallet["id"], "ref_id": ref_id})
        db.lolodrive_wallets.update_one({"id": wallet["id"]}, {"$inc": {"balance_uc": -BONUS}})


# ========== OG / Twitter meta on landing ==========
class TestLandingMetaTags:
    def test_og_meta_present(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        assert r.status_code == 200
        html = r.text
        assert 'og:title' in html
        assert "Communityplace coopérative B2B2C" in html
        assert 'og:description' in html
        assert 'og:image' in html
        assert 'og:type" content="website' in html
        assert 'og:locale" content="fr_FR' in html

    def test_twitter_meta_present(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        html = r.text
        assert 'twitter:card" content="summary_large_image' in html
        assert 'twitter:title' in html
        assert 'twitter:image' in html

    def test_title_contains_communityplace(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        html = r.text
        assert "<title>" in html
        # extract title content
        import re
        m = re.search(r"<title>(.*?)</title>", html, re.S)
        assert m and "Communityplace coopérative B2B2C" in m.group(1)

    def test_meta_description_mentions_lolodrive(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        html = r.text
        # find <meta name="description" ...>
        import re
        m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html)
        assert m, "description meta missing"
        assert "Réseau LOLODRIVE" in m.group(1)

    def test_og_image_unsplash_200(self):
        r = requests.get(f"{BASE_URL}/", timeout=20)
        html = r.text
        import re
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
        assert m, "og:image missing"
        og_url = m.group(1)
        assert "unsplash" in og_url.lower()
        img = requests.get(og_url, timeout=20)
        assert img.status_code == 200, f"og image returned {img.status_code}"
        ctype = img.headers.get("Content-Type", "")
        assert ctype.startswith("image/"), f"not image content-type: {ctype}"


# ========== Regression: referral claim (idempotent ledger) ==========
class TestReferralRegression:
    def test_referral_me_returns_marie_code(self, marie_token):
        r = requests.get(f"{BASE_URL}/api/lolodrive/pass/referral/me", headers=H(marie_token), timeout=20)
        assert r.status_code == 200
        c = r.json()["code"]
        assert c.startswith("KDM-") and len(c) == 10
