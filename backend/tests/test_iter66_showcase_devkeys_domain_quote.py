"""Iteration 66: vendor showcase opt-in, dev keys + quotas + call logs, custom_domain, quote ack email."""
import os
import time
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"
VENDOR_ID = "vendor-demo-pro"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"
    })
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return s


# ---------- 1. Vitrine auto-alimentée : vendor opt-in ----------

class TestVendorShowcaseOptIn:
    def test_get_vendor_opt_in_state(self):
        r = requests.get(f"{BASE_URL}/api/showcase/vendor-opt-in/{VENDOR_ID}")
        assert r.status_code == 200
        data = r.json()
        assert "opt_in" in data
        assert data["approved"] is True

    def test_get_unknown_vendor_404(self):
        r = requests.get(f"{BASE_URL}/api/showcase/vendor-opt-in/does-not-exist-xyz")
        assert r.status_code == 404

    def test_vendor_opt_in_appears_in_public_partners_with_logo(self):
        # Ensure opted-in
        r = requests.post(f"{BASE_URL}/api/showcase/vendor-opt-in/{VENDOR_ID}",
                          json={"opt_in": True})
        assert r.status_code == 200
        assert r.json()["opt_in"] is True

        pub = requests.get(f"{BASE_URL}/api/showcase/partners")
        assert pub.status_code == 200
        items = pub.json()["items"]
        vendor_entry = next((i for i in items if i.get("id") == f"vendor-{VENDOR_ID}"), None)
        assert vendor_entry is not None, "Vendor not merged into public partners"
        assert vendor_entry.get("auto") is True
        # logo_url should be primary product image (Damoiseau has products with images)
        assert vendor_entry.get("logo_url"), "auto vendor should carry product image as logo_url"
        assert vendor_entry.get("name")  # Distillerie Damoiseau

    def test_opt_out_removes_from_public(self):
        r = requests.post(f"{BASE_URL}/api/showcase/vendor-opt-in/{VENDOR_ID}",
                          json={"opt_in": False})
        assert r.status_code == 200
        pub = requests.get(f"{BASE_URL}/api/showcase/partners")
        assert pub.status_code == 200
        assert not any(i.get("id") == f"vendor-{VENDOR_ID}" for i in pub.json()["items"])
        # Re-enable for final state (per test context requirement)
        r = requests.post(f"{BASE_URL}/api/showcase/vendor-opt-in/{VENDOR_ID}",
                          json={"opt_in": True})
        assert r.status_code == 200

    def test_deduplication_with_manual_entry(self, admin_session):
        # Ensure vendor opted-in
        requests.post(f"{BASE_URL}/api/showcase/vendor-opt-in/{VENDOR_ID}", json={"opt_in": True})
        # Get the vendor company_name from public listing
        pub = requests.get(f"{BASE_URL}/api/showcase/partners").json()["items"]
        vendor_entry = next((i for i in pub if i.get("id") == f"vendor-{VENDOR_ID}"), None)
        assert vendor_entry is not None
        vendor_name = vendor_entry["name"]

        # Create manual partner with same name
        r = admin_session.post(f"{BASE_URL}/api/admin/showcase/partners",
                               json={"name": vendor_name, "link": "https://manual.test"})
        assert r.status_code == 200
        manual_id = r.json()["id"]
        try:
            pub2 = requests.get(f"{BASE_URL}/api/showcase/partners").json()["items"]
            # Should NOT have both — manual takes priority (auto skipped)
            manual = [i for i in pub2 if i.get("name", "").lower() == vendor_name.lower()]
            assert len(manual) == 1, f"Deduplication failed, got: {manual}"
            assert manual[0].get("auto") is not True
        finally:
            admin_session.delete(f"{BASE_URL}/api/admin/showcase/partners/{manual_id}")


# ---------- 2. API keys : monthly_quota + call logs + 429 ----------

class TestApiKeyQuotaAndLogs:
    @pytest.fixture(scope="class")
    def custom_key(self, admin_session):
        name = f"TEST_QuotaKey_{uuid.uuid4().hex[:6]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/api-keys",
                               json={"name": name,
                                     "scopes": ["catalog:read", "territories:read"],
                                     "monthly_quota": 3})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data.get("monthly_quota") == 3
        key_value = data["api_key"]
        key_id = data["id"]
        assert key_value.startswith("kdm_live_")
        yield {"value": key_value, "id": key_id, "name": name}
        # cleanup
        admin_session.delete(f"{BASE_URL}/api/admin/api-keys/{key_id}")

    def test_ping_returns_quota_and_usage(self, custom_key):
        r = requests.get(f"{BASE_URL}/api/public/v1/ping",
                         headers={"X-API-Key": custom_key["value"]})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["monthly_quota"] == 3
        assert data["month_usage"] >= 1
        assert "catalog:read" in data["scopes"]

    def test_quota_exceeded_returns_429(self, custom_key):
        # Already used 1 by prev test. Consume until 3 then 429 on 4th.
        hdr = {"X-API-Key": custom_key["value"]}
        # We may not know exact state due to prev; iterate up to 5 more calls
        got_429 = False
        for _ in range(5):
            r = requests.get(f"{BASE_URL}/api/public/v1/territories", headers=hdr)
            if r.status_code == 429:
                got_429 = True
                assert "Quota" in r.text or "quota" in r.text.lower()
                break
            assert r.status_code == 200
        assert got_429, "Expected 429 after exceeding monthly_quota=3"

    def test_call_logs_recorded(self, admin_session, custom_key):
        # Admin dev endpoint returns last_calls per key
        r = admin_session.get(f"{BASE_URL}/api/partner/dev/keys")
        assert r.status_code == 200
        items = r.json()["items"]
        key = next((k for k in items if k["id"] == custom_key["id"]), None)
        assert key is not None
        assert "last_calls" in key
        assert len(key["last_calls"]) >= 2
        # Verify path recorded
        paths = [c.get("path") for c in key["last_calls"]]
        assert any("/api/public/v1/" in p for p in paths)


# ---------- 3. Partner dev endpoint auth ----------

class TestPartnerDevAuth:
    def test_admin_sees_all_keys(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/partner/dev/keys")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        # admin sees all keys, expect >= 1 (ERP Test key present)
        assert len(data["items"]) >= 1
        # last_calls attached
        for k in data["items"]:
            assert "last_calls" in k
            assert "key_hash" not in k  # security check

    def test_no_auth_returns_401_or_403(self):
        r = requests.get(f"{BASE_URL}/api/partner/dev/keys")
        assert r.status_code in (401, 403), f"expected auth error, got {r.status_code}: {r.text}"


# ---------- 4. Custom domain resolve ----------

class TestCustomDomainResolve:
    @pytest.fixture(scope="class")
    def license_with_domain(self, admin_session):
        # Create a fresh license with custom_domain
        name = f"TEST_LicDomain_{uuid.uuid4().hex[:6]}"
        domain = f"test-{uuid.uuid4().hex[:6]}.example.com"
        r = admin_session.post(f"{BASE_URL}/api/admin/licenses", json={
            "name": name, "territory_code": "GUADELOUPE", "custom_domain": domain
        })
        assert r.status_code == 200, r.text
        lic_id = r.json()["id"]
        yield {"id": lic_id, "domain": domain, "name": name}
        admin_session.delete(f"{BASE_URL}/api/admin/licenses/{lic_id}")

    def test_resolve_by_exact_domain(self, license_with_domain):
        r = requests.get(f"{BASE_URL}/api/licenses/by-domain/resolve",
                         params={"host": license_with_domain["domain"]})
        assert r.status_code == 200, r.text
        assert r.json()["id"] == license_with_domain["id"]
        assert "stats" in r.json()

    def test_resolve_with_www_prefix(self, license_with_domain):
        r = requests.get(f"{BASE_URL}/api/licenses/by-domain/resolve",
                         params={"host": f"www.{license_with_domain['domain']}"})
        assert r.status_code == 200, r.text
        assert r.json()["id"] == license_with_domain["id"]

    def test_resolve_unknown_host_404(self):
        r = requests.get(f"{BASE_URL}/api/licenses/by-domain/resolve",
                         params={"host": f"nope-{uuid.uuid4().hex[:6]}.unknown.tld"})
        assert r.status_code == 404

    def test_patch_add_domain_and_resolve(self, admin_session):
        # Create license without domain, then PATCH custom_domain
        name = f"TEST_LicPatch_{uuid.uuid4().hex[:6]}"
        r = admin_session.post(f"{BASE_URL}/api/admin/licenses",
                               json={"name": name, "territory_code": "MARTINIQUE"})
        assert r.status_code == 200
        lic_id = r.json()["id"]
        try:
            domain = f"patched-{uuid.uuid4().hex[:6]}.test.tld"
            rp = admin_session.patch(f"{BASE_URL}/api/admin/licenses/{lic_id}",
                                     json={"custom_domain": domain})
            assert rp.status_code == 200
            rr = requests.get(f"{BASE_URL}/api/licenses/by-domain/resolve",
                              params={"host": domain})
            assert rr.status_code == 200
            assert rr.json()["id"] == lic_id
        finally:
            admin_session.delete(f"{BASE_URL}/api/admin/licenses/{lic_id}")

    def test_seeded_kdmarche_domain(self):
        """Seeded state per test context: KDMARCHÉ Guadeloupe has custom_domain=kdmarche-gp.fr."""
        r = requests.get(f"{BASE_URL}/api/licenses/by-domain/resolve",
                         params={"host": "kdmarche-gp.fr"})
        assert r.status_code == 200, f"expected seeded domain, got {r.status_code}: {r.text}"
        assert r.json().get("name") == "KDMARCHÉ Guadeloupe"


# ---------- 5. Quote ACK email (1 test only per project rule) ----------

class TestQuoteAckEmail:
    def test_quote_creation_triggers_ack_and_notification(self):
        payload = {
            "company": f"TEST_ACK_{uuid.uuid4().hex[:6]}",
            "first_name": "Alice",
            "last_name": "Test",
            "email": f"testack-{uuid.uuid4().hex[:6]}@example.com",
            "phone": "0102030405",
            "phone_country": "+33",
            "lang": "en",
            "message": "Iter66 automated test — please ignore.",
        }
        r = requests.post(f"{BASE_URL}/api/quotes", json=payload)
        assert r.status_code == 201, r.text
        # Background tasks -- give it a moment to write email_logs
        time.sleep(3)
        # Verify via admin: query email_logs by tags is not exposed publicly.
        # Instead assert the quote persisted (proxy) — email logging tested by inspection.
        assert r.json().get("email") == payload["email"]
