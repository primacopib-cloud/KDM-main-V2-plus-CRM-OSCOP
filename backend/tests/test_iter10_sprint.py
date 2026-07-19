"""Iter10 sprint backend tests: admin portal gating, compliance report runs, member registry SIRET extract."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://coop-dashboard-8.preview.emergentagent.com').rstrip('/')
ADMIN_EMAIL = "admin@kdmarche-oscop.fr"
ADMIN_PASSWORD = "AdminKDM2025!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"},
                      timeout=15)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# --- (1) portal gating on /api/auth/login ---
class TestAdminPortalGating:
    def test_login_without_portal_admin_returns_403(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                          timeout=15)
        assert r.status_code == 403, f"expected 403 without portal:admin, got {r.status_code} — {r.text[:200]}"
        body = r.json()
        blob = str(body).lower()
        assert "admin" in blob, f"error should mention Administration: {body}"

    def test_login_with_portal_admin_returns_200(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "portal": "admin"},
                          timeout=15)
        assert r.status_code == 200, f"expected 200 with portal:admin, got {r.status_code}"
        data = r.json()
        assert data.get("token") or data.get("access_token")


# --- (2) compliance report archive-ged runs history ---
class TestComplianceArchiveGedRuns:
    def test_runs_endpoint_returns_list(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/admin/compliance-report/archive-ged/runs",
                         headers=admin_headers, timeout=15)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        data = r.json()
        assert "runs" in data, f"missing runs key: {data}"
        runs = data["runs"]
        assert isinstance(runs, list)
        # ensure 2026-07 SUCCESS run exists
        run_2026_07 = [x for x in runs if x.get("period") == "2026-07" or x.get("month") == "2026-07"]
        assert run_2026_07, f"no 2026-07 run found; runs keys sample: {runs[:1]}"
        found_success = any(
            (r.get("status") or "").upper() in ("SUCCESS", "OK", "ARCHIVED", "SUCCEEDED")
            for r in run_2026_07
        )
        assert found_success, f"no SUCCESS run for 2026-07: {run_2026_07}"


# --- (3) member registry SIRET extract ---
class TestMemberRegistryExtract:
    def test_extract_valid_siret_returns_pdf(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/v2/admin/member-registry/extract/55208131766522",
                         headers=admin_headers, timeout=45)
        assert r.status_code == 200, f"expected 200 for EDF SIRET, got {r.status_code}: {r.text[:300]}"
        ct = r.headers.get("content-type", "")
        assert "application/pdf" in ct.lower(), f"expected PDF content-type, got {ct}"
        assert r.content[:4] == b"%PDF", f"content is not PDF: {r.content[:20]}"

    def test_extract_invalid_siret_returns_404(self, admin_headers):
        r = requests.get(f"{BASE_URL}/api/v2/admin/member-registry/extract/00000000000000",
                         headers=admin_headers, timeout=30)
        assert r.status_code == 404, f"expected 404 for invalid SIRET, got {r.status_code}: {r.text[:200]}"
        blob = r.text.lower()
        assert "introuvable" in blob or "not found" in blob or "not_found" in blob, \
            f"expected 'introuvable' in error message: {r.text[:300]}"


# --- (5) scheduler / backend health smoke ---
class TestBackendHealth:
    def test_backend_up(self):
        r = requests.get(f"{BASE_URL}/api/public/plans", timeout=10)
        assert r.status_code == 200
